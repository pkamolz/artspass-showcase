# Spektrix Integration

This document describes how ArtsPass integrates with the Spektrix CRM (API v3). It covers the authentication scheme, our API surface usage, the domain mapping layer, validation results, and current implementation status. It is intended for engineers evaluating the integration in detail.

Spektrix was our first CRM integration for two reasons: its API v3 is a conventional REST interface with well-documented authentication, and Village Theatre (our first connected partner) completed the API access approval process quickly. Tessitura — used by four of our other Seattle partners — has a richer API but a longer credentialing process; its adapter is stubbed and ready once credentials arrive.

## Authentication: HMAC-SHA1 request signing

Spektrix API v3 uses HMAC-SHA1 request signing rather than a bearer token. Every request must carry a `Date` header and an `Authorization` header computed from the request method, full URL, and date string. For non-GET requests, a Base64-encoded MD5 hash of the request body is appended to the signed string.

The canonical string to sign is:

```
HTTP-METHOD\n
FULL-URL\n
RFC-7231-UTC-DATE
[+ \nBase64(MD5(body))  — POST/PUT/PATCH only]
```

The signature is produced by HMAC-SHA1 over the UTF-8 encoding of that string, using the API secret key (which is itself base64-encoded and must be decoded before use). The resulting `Authorization` header has the form:

```
SpektrixAPI3 <api_user>:<base64_signature>
```

All three credentials are loaded from environment variables — `SPEKTRIX_API_USER`, `SPEKTRIX_API_KEY`, and `SPEKTRIX_CLIENT_NAME` — and never hardcoded. The base URL is constructed at startup from the client name:

```
https://system.spektrix.com/{SPEKTRIX_CLIENT_NAME}/api/v3
```

The signing implementation (`spektrix_client.py`):

```python
def _sign_request(method: str, url: str, date: str, body: bytes = b"") -> str:
    parts = [method.upper(), url, date]

    if body:
        body_hash = base64.b64encode(hashlib.md5(body).digest()).decode()
        parts.append(body_hash)

    string_to_sign = "\n".join(parts)

    decoded_key = base64.b64decode(API_KEY)   # loaded from SPEKTRIX_API_KEY env var
    signature = base64.b64encode(
        hmac.new(decoded_key, string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()

    return f"SpektrixAPI3 {API_USER}:{signature}"
```

The `Date` header value fed into the signing function is the exact same string sent on the wire — Spektrix validates that the signed date and the `Date` header match within a tolerance window, which means the date string must be captured once and used consistently across both the header and the signature.

## API surface and domain mapping

We use two Spektrix endpoints:

- `GET /events` — all events for the client account; drives `get_performances()`
- `GET /events/{id}/instances` — all individual seatings under an event; drives `get_availability()`

### Event → Performance

Spektrix organizes its catalog around **events** (the production-level entity) and **instances** (individual showtime seatings). We map events to the `Performance` domain model:

| Spektrix field | Type | Domain field | Notes |
|----------------|------|--------------|-------|
| id | string | Performance.crm_ref | Bare Spektrix ID; used as path param for instance calls |
| id | string | Performance.id | Prefixed: "spektrix:{id}" |
| name | string | Performance.title |  |
| startDate | ISO string | Performance.start_dt | datetime.fromisoformat() |
| endDate | ISO string | Performance.end_dt | Nullable; None if absent |
| description | string | Performance.description | Nullable |

The `"spektrix:"` prefix on `Performance.id` ensures IDs remain globally unique across CRM systems — a venue migrating from one CRM to another won't collide with existing records.

### Instance → SeatAvailability

`GET /events/{id}/instances` returns a list of seatings. We aggregate across all of them into a single `SeatAvailability` snapshot, and flatten per-instance price bands into `PriceTier` records:

```python
for inst in instances:
    total += inst.get("capacity", 0)
    available += inst.get("availableCapacity", 0)

    for band in inst.get("priceBands", []):
        tiers.append(PriceTier(
            name=band.get("name", "Standard"),
            price_cents=int(band.get("price", 0) * 100),  # float → integer cents
            available=band.get("availableCount", 0),
        ))
```

Prices arrive as floats from Spektrix (e.g., `45.0`) and are immediately converted to integer cents (`4500`) to avoid floating-point drift in any downstream comparisons.

## Validation: the 104-event run

The 104 events are Village Theatre's actual current season data, not a synthetic test. We validated the integration end-to-end against their live Spektrix production account — including the real-time availability calls that ArtsPass depends on for live inventory.

Availability is the harder call: it is time-sensitive, requires a valid `crm_ref` carried forward from the event fetch, and drives whether a patron sees a show as bookable right now. A single call to `GET /events` returned 104 active events; we then called `GET /events/{id}/instances` for each — 105 total API calls — and verified:

- **Availability accuracy** — `total_seats`, `available_seats`, and `is_sold_out` aggregated correctly across multi-instance events; price band → `PriceTier` conversion handles float prices (`45.0` → `4500`) and zero-price entries without exceptions
- **Signing reliability** — all 104 signed requests returned HTTP 200; no 401s, confirming the HMAC-SHA1 implementation is correct
- **Field mapping completeness** — all 104 events mapped to valid `Performance` objects; nullable fields (`endDate`, `description`) handled correctly; `crm_ref` round-tripped as the instance call path parameter

The read path is production-ready.

## What's complete and what's in progress

**Complete (read side):**
- `get_performances()` — fetches all events; Spektrix date-range filter parameters (`startDate`, `endDate`) are forwarded as query-string arguments
- `get_availability()` — fetches instances for a given event and returns an aggregated `SeatAvailability` with full price tier detail

**In progress (write side):**

`create_reservation()` involves more steps than the read path, and they must execute in sequence with state carried across calls:

1. **Patron identity reconciliation** — ArtsPass maintains its own patron records and resolves to the appropriate CRM-side patron ID at reservation time.
2. **Open a basket** — `POST /baskets` to initiate a Spektrix session; the returned basket ID must be preserved for subsequent calls.
3. **Add items** — `POST /baskets/{id}/items` to add the requested seats to the basket.
4. **Confirm the order** — `POST /baskets/{id}/orders` to finalize the Spektrix-side reservation.

Unlike the read operations (independently signed, stateless, safe to retry), this sequence is stateful: the basket ID must survive across all three steps, partial completion requires rollback logic, and Spektrix sessions can expire mid-flow. That session state management is the primary engineering complexity on the write side.

**Payment processing is handled by Stripe, not Spektrix.** Patron payment is collected and processed by Stripe before or alongside the Spektrix reservation flow — it is not part of the basket → order sequence above. This is intentional: keeping payment in Stripe gives us full control over the checkout experience, PCI scope, and retry logic, and decouples us from Spektrix's own checkout flow entirely.

`cancel_reservation()` follows once the write path is in place; it requires a confirmed Spektrix order ID from a completed `create_reservation()` call.

Both methods raise `NotImplementedError` naming the exact API sequence to implement next — premature calls fail loudly, not silently.

## Design decisions

**All Spektrix logic is contained in two files.** The `spektrix_client` module owns transport and signing; `SpektrixAdapter` owns field mapping and aggregation. No Spektrix-specific field names, types, or concepts appear outside `spektrix_client.py` and `adapters/spektrix.py`. The rest of the application works with `Performance`, `SeatAvailability`, and `Venue` objects only.

**Payment is decoupled from CRM.** Stripe handles patron payment; Spektrix handles inventory and reservation. This separation means the checkout experience, retry behavior, and PCI scope remain under our control regardless of which CRM a venue uses. A future Tessitura venue gets the same payment flow with no changes to the Stripe integration.

**Stateless client.** Each request is independently signed using the current UTC timestamp. There is no session object to manage, no expiry to track, and no locking needed for concurrent requests. The client is safe to use as a module-level singleton.

**The adapter adds no authentication logic.** `SpektrixAdapter` delegates all signing to `spektrix_client`. This keeps the adapter focused on semantic mapping (Spektrix concepts → domain models) and makes it straightforward to test the mapping logic independently by mocking `spektrix_client.get`.

**The base class is CRM-agnostic by design.** `VenueCRMAdapter` defines the interface entirely in terms of domain types; it imports nothing from the Spektrix layer. Adding or removing Spektrix support touches exactly two files and nothing else.

## Further reading

- [`docs/crm-adapter-pattern.md`](crm-adapter-pattern.md) — the `VenueCRMAdapter` interface, the registry, and how to add a new CRM integration
- [`docs/architecture.md`](architecture.md) — system-level view of how the adapter layer fits into the broader application
