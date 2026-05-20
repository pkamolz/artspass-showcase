# CRM Adapter Pattern

This document is the implementation-level reference for the ArtsPass adapter pattern. [`architecture.md`](architecture.md) establishes where the adapter layer fits in the system; [`spektrix-integration.md`](spektrix-integration.md) goes deep on the Spektrix implementation. This doc answers the practical question: *what does it actually take to add a new CRM?*

The answer is intentionally narrow: implement one abstract class, register one entry. The rest of the system — routes, domain models, database schema — requires no changes.

## The VenueCRMAdapter interface

Every CRM integration implements `VenueCRMAdapter`, the abstract base class in `src/arts_pass/adapters/base.py`:

```python
from abc import ABC, abstractmethod

from arts_pass.models.availability import SeatAvailability
from arts_pass.models.performance import Performance
from arts_pass.models.reservation import Reservation
from arts_pass.models.venue import Venue


class VenueCRMAdapter(ABC):
    """
    Abstract base class for all venue CRM adapters.

    All CRM-specific concerns — authentication, request signing, field
    mapping — live entirely within the adapter subclass. The rest of the
    application works exclusively with the CRM-agnostic domain models.

    Adapters are expected to be stateless; credentials are sourced from
    environment variables inside each implementation.
    """

    @abstractmethod
    def get_performances(self, venue: Venue, **filters) -> list[Performance]: ...

    @abstractmethod
    def get_availability(self, performance: Performance) -> SeatAvailability: ...

    @abstractmethod
    def create_reservation(
        self,
        performance: Performance,
        patron_id: str,
        seat_refs: list[str],
    ) -> Reservation: ...

    @abstractmethod
    def cancel_reservation(self, reservation: Reservation) -> Reservation: ...
```

*(Method bodies elided for brevity; see the source for full per-method docstrings.)*

**Method contracts:**

- **`get_performances(venue, **filters)`** — Fetch upcoming performances for the venue. `**filters` are forwarded as CRM query parameters (e.g. `start_date`, `end_date`); supported keys are adapter-specific. Returns an empty list if no performances are available; raises on network or authentication failure — never returns an empty list to mask an error.

- **`get_availability(performance)`** — Return a point-in-time `SeatAvailability` snapshot for one performance. The `performance.crm_ref` field carries the CRM-native identifier used to construct the request. Raises `NotImplementedError` until implemented.

- **`create_reservation(performance, patron_id, seat_refs)`** — Reserve the specified seats and return a `Reservation` with `status=CONFIRMED`. `patron_id` is the ArtsPass-side patron identifier; the adapter resolves it to a CRM-side patron record. `seat_refs` are CRM-native seat identifiers, opaque to callers. Raises `NotImplementedError` until implemented.

- **`cancel_reservation(reservation)`** — Cancel the reservation in the CRM and return the updated `Reservation` with `status=CANCELLED`. Raises `NotImplementedError` until implemented.

The base class imports only domain types — no CRM SDK, no HTTP library. A concrete adapter that raises `NotImplementedError` on unimplemented methods is valid and instantiatable; that is exactly how `TessituraAdapter` works today.

## The registry

The registry (`src/arts_pass/adapters/registry.py`) is a module-level dict mapping CRM name strings to adapter singleton instances:

```python
_REGISTRY: dict[str, VenueCRMAdapter] = {
    "spektrix":  SpektrixAdapter(),
    "tessitura": TessituraAdapter(),
}
```

Three public functions expose it:

**`get_adapter(crm_system: str) -> VenueCRMAdapter`** — looks up the adapter by name. Raises `KeyError` (listing registered names) if the string is not found.

**`get_adapter_for_venue(venue: Venue) -> VenueCRMAdapter`** — reads `venue.crm_system` and calls `get_adapter()`. Raises `ValueError` if `venue.crm_system is None`, prompting the caller to update the venue record once the CRM is identified.

**`registered_crm_systems() -> list[str]`** — returns the sorted list of registered CRM names; used by tests.

The API routes use `get_adapter_for_venue()` exclusively — they never import an adapter class directly and never branch on CRM type. Adding a new CRM requires no changes to `app.py`.

The registry key strings (`"spektrix"`, `"tessitura"`) must match the `crm_system` column in the `venues` table. If you register a new CRM as `"ticketmaster"`, every venue record for that CRM must have `crm_system = "ticketmaster"` to route correctly.

## Walkthrough: adding a new CRM

The following steps take a new CRM from zero to a registered, tested integration. We use a hypothetical `TicketmasterAdapter` as the example.

### 1. Start with a stub adapter

Create `src/arts_pass/adapters/ticketmaster.py`. Starting with stubs gives you a valid, registered adapter immediately and lets other work — venue records, testing infrastructure — proceed while the integration is in progress:

```python
from arts_pass.adapters.base import VenueCRMAdapter
from arts_pass.models.availability import SeatAvailability
from arts_pass.models.performance import Performance
from arts_pass.models.reservation import Reservation
from arts_pass.models.venue import Venue


class TicketmasterAdapter(VenueCRMAdapter):

    def get_performances(self, venue: Venue, **filters) -> list[Performance]:
        raise NotImplementedError("Ticketmaster integration in progress.")

    def get_availability(self, performance: Performance) -> SeatAvailability:
        raise NotImplementedError("Ticketmaster integration in progress.")

    def create_reservation(
        self, performance: Performance, patron_id: str, seat_refs: list[str]
    ) -> Reservation:
        raise NotImplementedError("Ticketmaster integration in progress.")

    def cancel_reservation(self, reservation: Reservation) -> Reservation:
        raise NotImplementedError("Ticketmaster integration in progress.")
```

### 2. Register the adapter

In `registry.py`, import the new adapter and add it to `_REGISTRY`:

```python
from arts_pass.adapters.ticketmaster import TicketmasterAdapter

_REGISTRY: dict[str, VenueCRMAdapter] = {
    "spektrix":     SpektrixAdapter(),
    "tessitura":    TessituraAdapter(),
    "ticketmaster": TicketmasterAdapter(),
}
```

That is the entire registration step. Requests to venues with `crm_system = "ticketmaster"` now route to `TicketmasterAdapter` and return HTTP 501 until methods are implemented.

### 3. Add a transport module for authentication

Create a dedicated transport module (e.g., `src/arts_pass/ticketmaster_client.py`) that owns all HTTP and authentication logic. Keep auth entirely out of the adapter class — the adapter should only handle semantic mapping, not signing or token management:

```python
import os
import requests

API_KEY = os.environ.get("TICKETMASTER_API_KEY", "")
BASE_URL = "https://app.ticketmaster.com/discovery/v2"

def get(path: str, **kwargs) -> requests.Response:
    params = kwargs.pop("params", {}) or {}
    params["apikey"] = API_KEY          # API_KEY loaded from environment
    return requests.get(f"{BASE_URL}{path}", params=params, **kwargs)
```

Credentials always come from environment variables. The exact scheme varies by CRM (API key, OAuth 2.0, HMAC-SHA1); see [`spektrix-integration.md`](spektrix-integration.md) for a detailed example of the HMAC approach.

### 4. Map CRM types to domain types

Implement `get_performances()` and `get_availability()` by translating the CRM's response shapes into domain objects. A few conventions the codebase follows:

- **Prefix `Performance.id`** with the CRM name — `f"ticketmaster:{crm_id}"` — so IDs are globally unique across CRMs.
- **Store the bare CRM-native ID in `Performance.crm_ref`** — this is the value used as a path parameter for availability calls.
- **Convert prices to integer cents** at the boundary: `int(float_price * 100)`. Never store floats in `PriceTier.price_cents`.
- **Guard nullable fields** — CRMs vary in what they populate. Use `.get()` with `None` defaults for optional fields like `endDate` and `description`.

### 5. Update venue records

Ensure venue rows in the database (and the seed migration) have `crm_system = "ticketmaster"`. The registry key and the `crm_system` column must match exactly.

### 6. Test the adapter

Follow the pattern in `tests/test_adapters.py`:

- **Unit-test the mapping logic** by patching the transport module (e.g., `ticketmaster_client.get`), not the adapter class. Pass fixture data and assert the returned domain objects have the correct field values.
- **Cover edge cases** — null end dates, missing descriptions, zero-price tiers, events with multiple seatings.
- **Verify unimplemented methods raise `NotImplementedError`** before the full implementation lands.
- **Test registry wiring** — `get_adapter("ticketmaster")` should return a `TicketmasterAdapter`.

Live integration tests run against the real CRM API separately and manually, kept out of the standard test suite. The Spektrix read path was validated this way against 104 events in a sandbox modeling Village Theatre's production scenarios.

## Current state

| CRM | Adapter | Status | Venues |
|-----|---------|--------|--------|
| Spektrix | SpektrixAdapter | Read side sandbox-validated; write side in progress | Village Theatre (Issaquah) |
| Tessitura | TessituraAdapter | Stub — awaiting API credentials | Seattle Symphony, Seattle Repertory Theatre, Seattle Opera, Pacific Northwest Ballet |
| TBD | — | Not yet scoped | Seattle Children's Theatre, Union Arts Center |

The Tessitura adapter is structurally complete: the class exists, is registered, and raises `NotImplementedError` with context on every method. The remaining work is implementing four method bodies once credentials arrive — not a new integration, just filling in a scaffold that is already in place.

## Design principles the pattern enforces

**Domain-type purity.** Adapters consume and produce `Venue`, `Performance`, `SeatAvailability`, and `Reservation` objects only. CRM-specific response shapes, field names, and SDK types are translated at the adapter boundary and never propagate further. The API routes and business logic are entirely CRM-agnostic.

**Per-CRM authentication encapsulation.** Each CRM has its own authentication scheme. That logic lives in a dedicated transport module; the adapter class never constructs auth headers or manages tokens. If credentials rotate or the auth scheme changes, only the transport module changes.

**Stateless clients where possible.** Transport modules are designed so that each request is independently authenticated — no shared session state between requests. This makes clients safe for concurrent use and simplifies error recovery. Where session state is unavoidable (e.g., the Spektrix basket flow for reservations), it is scoped to the duration of a single reservation operation, not shared across requests.

**Testability via mock transports.** Because the adapter interface is defined in terms of domain types, unit tests substitute mock transport responses for any concrete HTTP client. Route-level tests never need real credentials or network access to verify mapping logic.

## Extensibility implications

Each new CRM adds one module and one registry entry — nothing else changes. We have seven Seattle-area partner venues across two known CRM systems today, with two venues pending CRM identification. As we expand to additional Pacific Northwest venues and nationally, each new CRM system is additive, not disruptive: existing integrations are untouched, and the new adapter follows the same sequence described in this walkthrough. The pattern also applies directly to broader live entertainment platforms — the same interface that works for a regional theater CRM works for any ticketing system that can return a list of events and a seat count.

## Related docs

- [`docs/spektrix-integration.md`](spektrix-integration.md) — the Spektrix adapter as a worked example: HMAC-SHA1 signing, event-to-performance mapping, and the sandbox validation run against realistic partner scenarios
- [`docs/architecture.md`](architecture.md) — system-level view showing where the adapter layer fits relative to the API and persistence layers
