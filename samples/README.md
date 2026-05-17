# Code Samples

These files are sanitized excerpts from the ArtsPass production codebase, curated to illustrate the architectural patterns described in [`../docs/`](../docs/). They are not complete or runnable as-is. For full context on each pattern, read the corresponding doc.

## Files

- **[`venue_crm_adapter.py`](venue_crm_adapter.py)** — The `VenueCRMAdapter` abstract base class. Every CRM integration implements this four-method contract. Pairs with [`../docs/crm-adapter-pattern.md`](../docs/crm-adapter-pattern.md).

- **[`spektrix_signing.py`](spektrix_signing.py)** — HMAC-SHA1 request signing for the Spektrix API v3: date formatting, the signed-string construction, and header assembly. Pairs with [`../docs/spektrix-integration.md`](../docs/spektrix-integration.md).

- **[`spektrix_adapter_excerpt.py`](spektrix_adapter_excerpt.py)** — The read path of `SpektrixAdapter`: event-to-`Performance` mapping and instance aggregation into `SeatAvailability`. Write-path methods are elided. Pairs with [`../docs/spektrix-integration.md`](../docs/spektrix-integration.md).

- **[`adapter_registry.py`](adapter_registry.py)** — The full registry implementation: the `_REGISTRY` dict, `get_adapter()`, `get_adapter_for_venue()`, and `registered_crm_systems()`. Small enough to show end-to-end. Pairs with [`../docs/crm-adapter-pattern.md`](../docs/crm-adapter-pattern.md).
