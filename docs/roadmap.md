# Technical Roadmap

This document is the technical sequencing plan for ArtsPass — what we're building next, in what order, and why. It complements [`architecture.md`](architecture.md) (the system as it stands today) and the strategic framing in the [README](../README.md) (where the business is going). The focus here is engineering: which capabilities unlock which downstream work, and how we avoid retrofits.

## Near-term priorities

The next phase of work converts the validated read path into a complete reservation system and extends the platform across our second CRM.

- **Spektrix write path.** Complete `create_reservation()` and `cancel_reservation()` on top of Spektrix's basket → order sequence (`POST /baskets` → `POST /baskets/{id}/items` → `POST /baskets/{id}/orders`). The engineering complexity here is session state — the basket ID must survive multiple calls, partial completion needs rollback, and Spektrix sessions can expire mid-flow. See [`spektrix-integration.md`](spektrix-integration.md) for the full sequence.
- **FastAPI routes wired to the registry.** The application scaffolding and adapter registry are both live; the route handlers that bridge them are the next integration step. Routes resolve a venue from the database, call `get_adapter_for_venue()`, and return domain objects — no CRM-specific code on the route side.
- **Tessitura adapter implementation.** Four venues (Seattle Symphony, Seattle Rep, Seattle Opera, Pacific Northwest Ballet) are seeded and waiting on credentials. The adapter class and registry entry are already in place; the work is filling in four method bodies, not new scaffolding.
- **Patron identity service.** ArtsPass maintains its own patron records and reconciles to CRM-side patron IDs at reservation time. This service is a prerequisite for both Spektrix and Tessitura write paths — every reservation must resolve an ArtsPass patron to the appropriate CRM-native identity.
- **Initial ML/AI infrastructure.** An embedding pipeline over event descriptions and basic recommendation scaffolding. Built early — not as a feature retrofit — so that as patron behavior data accumulates, the substrate for personalization and discovery is already in place.

## Mid-term investments

Once the read and write paths are complete across both CRMs, the platform's focus shifts to payment, intelligence, and operational maturity.

- **Full Tessitura integration.** Implementing the four method bodies brings Tessitura coverage online across Seattle Symphony, Seattle Rep, Seattle Opera, and Pacific Northwest Ballet. Two venues (Seattle Children's Theatre, Union Arts Center) remain pending CRM identification. Tessitura's data model (productions and performances) differs structurally from Spektrix's (events and instances); the mapping layer absorbs the difference and the rest of the application sees only `Performance` and `SeatAvailability` domain objects.
- **Stripe payment integration.** Subscription billing for the monthly pass, and redemption flows that confirm pass eligibility before a CRM-side reservation is created. Payment is decoupled from CRM by design (see [`spektrix-integration.md`](spektrix-integration.md)) — Stripe is the system of record for patron payment regardless of which CRM holds the seat inventory.
- **Production ML/AI capabilities.** The early embedding pipeline matures into the capabilities described in the README's AI commerce framing: agentic discovery (patrons describe what they want; the system surfaces matches across all venues), personalized recommendations driven by the gap between booking intent and attendance, and dynamic patron LTV modeling that informs both venue partners and our own engagement strategy.
- **Operational infrastructure.** Structured logging, metrics, distributed tracing across the API/adapter/CRM boundary, and a deployment pipeline that supports zero-downtime schema changes (Alembic-managed from the first commit, see [`architecture.md`](architecture.md)). Live integration tests against real CRM accounts move from manual to automated.

## Longer-term direction

Beyond the mid-term work, the platform expands along three trajectories outlined in the README. These are directional commitments, not dated deliverables — the engineering principle is that the foundation we're building now should support each without architectural rework.

- **Geographic expansion.** The venue, performance, and reservation models are already metro-agnostic; what scaling adds is per-market venue onboarding, regional CRM coverage (new CRM systems beyond Spektrix and Tessitura will appear in other cities), and infrastructure for serving multiple markets from a shared platform.
- **Categorical expansion.** The adapter pattern that works for a regional theater CRM works for any ticketing system that can return a list of events and a seat count. Extending into live music, concerts, and comedy is primarily an integration exercise — onboarding new CRM systems via the same `VenueCRMAdapter` interface — not a rebuild.
- **Competitive positioning.** As coverage broadens, the platform becomes a venue-friendly alternative to ticketing incumbents: aggregated demand signals that give venues data they've never had, a patron relationship the venue still co-owns, and an inventory channel that turns underutilized seats into discovery rather than discount.

The foundation we're building now — domain-typed abstractions, adapter-based CRM interoperability, patron identity that lives in ArtsPass rather than any single CRM — is the substrate that makes all three trajectories tractable without architectural rework.

## Principles guiding the sequence

A few engineering decisions shape why the work is sequenced the way it is.

**Read path before write path.** Reading availability is independently signed, stateless, and safe to retry; writing reservations is a multi-step stateful flow with rollback concerns. Validating the read path against realistic sandbox data first means the write path is built on a foundation we know works — and means we can demonstrate end-to-end inventory visibility before any patron money moves.

**Validate against realistic data, not simplified mock data.** We validated the Spektrix read path against 104 events in a sandbox environment modeling Village Theatre's real production scenarios. Realistic validation surfaces the failure modes that simplified mock data hides: schema variation, null handling, edge cases in real catalogs. Live production integration is the next step, and we expect it may reveal further edge cases — which is exactly why we validate thoroughly before we get there. We extend this approach to every new CRM integration.

**Build the adapter pattern correctly once.** The cost of retrofitting CRM-agnostic abstractions onto a codebase that grew CRM-specific branches is high. We paid the abstraction cost upfront so that every subsequent CRM — Tessitura today, others later — is one module and one registry entry, with no changes to routes or business logic. See [`crm-adapter-pattern.md`](crm-adapter-pattern.md).

**ML/AI as core architecture, not a feature retrofit.** The embedding pipeline and recommendation scaffolding land before the user-facing intelligence features that depend on them. Patron behavior is the substrate the platform learns from; treating it as core data from day one — rather than as analytics bolted on later — is what makes the AI commerce capabilities tractable.

## Related docs

- [`README.md`](../README.md) — strategic framing and AI commerce capabilities
- [`architecture.md`](architecture.md) — the system as it stands today
- [`crm-adapter-pattern.md`](crm-adapter-pattern.md) — how new CRM integrations slot in
- [`spektrix-integration.md`](spektrix-integration.md) — the worked example of the read-path validation and write-path scope
