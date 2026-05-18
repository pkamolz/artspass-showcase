# ArtsPass

**A performing arts subscription platform for Seattle — think ClassPass for theater, symphony, opera, and ballet.**

ArtsPass lets patrons buy a monthly pass and use it across Seattle's live arts venues. One subscription, seven venues, no per-show commitment friction. For venues, we turn underutilized inventory into a new acquisition channel and a new patron relationship they wouldn't otherwise own. Today the ecosystem is fragmented across dozens of venues with no shared discovery layer, no flexible access model, and no data infrastructure connecting them. We're building that infrastructure.

We're launching in Seattle's performing arts ecosystem, a market with both established scale and active public investment: King County voters approved a $782 million arts, heritage, and cultural funding levy in December 2023, the largest public commitment to arts and culture in the county's history (King County Doors Open). Nationally, the U.S. nonprofit arts and culture sector is a $151.7 billion industry supporting 2.6 million jobs (Americans for the Arts, Arts & Economic Prosperity 6, 2023). The same adapter-based architecture extends from performing arts into the broader U.S. live entertainment market — live music, concerts, comedy.

---

## Why this exists

**For patrons:** Discovering and attending live arts in Seattle means navigating a dozen separate box offices, separate ticketing platforms, separate subscription models, and a high per-show price point that turns casual interest into a deliberate financial commitment. The result is a city full of people who want to go to more shows and don't.

**For venues:** The traditional single-venue subscription model is in structural decline. Patrons — especially younger ones — increasingly want variety across venues and genres, not a year-long commitment to one organization's season. At the same time, patron acquisition is expensive and unsold seats the night of a show are permanently lost revenue. Existing tools — season subscriptions, last-minute discount apps — either compress margin or do nothing for long-term patron development. ArtsPass converts underutilized inventory into patron discovery, data, and durable relationships.

---

## Technical approach

The core platform is a **FastAPI** application backed by **PostgreSQL 17**, with a **SQLAlchemy ORM** layer and **Alembic**-managed migrations. The API is designed to stay CRM-agnostic: every venue in Seattle uses a different ticketing system (primarily Spektrix and Tessitura), and we need to query availability, check out tickets, and manage reservations across all of them through a single interface.

We handle this with an **adapter pattern**. A `VenueCRMAdapter` abstract base class defines the contract — `get_performances()`, `get_availability()`, `create_reservation()`, `cancel_reservation()` — and each CRM gets a concrete adapter subclass. The application layer never calls a CRM directly; it goes through the registry, which resolves the right adapter for each venue at runtime.

This is a deliberate architectural choice. Adding a new CRM integration means implementing one class and registering it, not touching application logic. It also means we can test the platform end-to-end against mock adapters while real CRM credentials are pending.

```
FastAPI routes
    └── adapter registry (venue → CRM adapter)
            ├── SpektrixAdapter    → Spektrix API v3 (HMAC-SHA1 signed)
            └── TessituraAdapter   → Tessitura REST API (stubbed)
```

---

## Current status

### Live
- **Spektrix integration** — Full HMAC-SHA1-signed HTTP client against the Spektrix API v3. Validated against 104 live events at Village Theatre (Issaquah). Events, instances, and seat availability map cleanly to our domain models.
- **ORM and migration layer** — Four tables (`venues`, `performances`, `seat_availabilities`, `reservations`) with indexes, FK cascades, and JSONB columns for price tiers and seat maps. Two Alembic migrations: initial schema and idempotent venue seed.
- **Seven partner venues seeded** — See venue list below.
- **Domain models** — `Venue`, `Performance`, `SeatAvailability`, `Reservation` as typed Python dataclasses, decoupled from both the ORM and the CRM layer.

### Stubbed / in progress
- **Tessitura adapter** — Adapter subclass in place; all methods raise `NotImplementedError` pending API credentials. Four venues (Seattle Symphony, Seattle Rep, Seattle Opera, Pacific Northwest Ballet) are seeded and waiting.
- **Spektrix reservation flow** — `create_reservation()` and `cancel_reservation()` are not yet implemented. The Spektrix basket → checkout flow requires multi-step session state; we're building it now.
- **FastAPI routes** — App scaffolding is live; routes are not yet wired to the adapter layer.

### Next
- Complete Spektrix basket → checkout reservation flow
- Wire FastAPI routes to adapter registry
- Begin Tessitura adapter implementation
- ML/AI capabilities (see roadmap)

---

## Seattle-area partner venues

| Venue | CRM | Status |
|-------|-----|--------|
| Village Theatre (Issaquah) | Spektrix | Connected |
| Seattle Symphony | Tessitura | Pending |
| Seattle Repertory Theatre | Tessitura | Pending |
| Seattle Opera | Tessitura | Pending |
| Pacific Northwest Ballet | Tessitura | Pending |
| Seattle Children's Theatre | TBD | Pending |
| Union Arts Center | TBD | Pending |

---

## AI-native commerce roadmap

Performing arts is a domain rich in latent preference signals — what patrons book, what they actually attend, what they return for — and almost none of that signal has historically been usable across venues. A unified pass changes that. We're building ML/AI capabilities from day one, treating patron behavior as the substrate the platform learns from.

**Agentic discovery** — A patron describes what they're looking for; the system surfaces relevant performances across all venues. Built on embeddings over event descriptions, patron history, and behavioral signals.

**Personalized recommendations** — We learn from the gap between what patrons book and what they actually attend. That signal drives recommendations that improve pass utilization over time.

**Dynamic patron LTV modeling** — Churn prediction and LTV models identify which patrons need engagement intervention and which venues are driving long-term retention.

**Venue intelligence** — Aggregated, anonymized demand signals give venues data they've never had: who attended via ArtsPass, what they saw before and after, and how to think about inventory relative to actual demand.

---

## Where this is going

ArtsPass is launching in Seattle's performing arts ecosystem — theater, symphony, opera, and ballet. From there, the expansion path runs in three directions:

- **Geographically** — into additional metro markets.
- **Categorically** — into live music, concerts, comedy, and the broader live entertainment landscape.
- **Competitively** — as a venue-friendly alternative to ticketing incumbents that extract value from both venues and patrons.

We're starting with a focused wedge that's underserved and ready to move — and building infrastructure designed to scale across all three dimensions.

---

## About this repository

This is a curated technical showcase. The production codebase is private.

What's here represents the architecture, integration patterns, and design decisions we think are worth making visible — not the full implementation. Sanitized code samples are in [`samples/`](./samples/). Technical documentation is in [`docs/`](./docs/):

- [`docs/architecture.md`](./docs/architecture.md) — System diagram and component overview
- [`docs/spektrix-integration.md`](./docs/spektrix-integration.md) — HMAC-SHA1 signing, API v3 integration, 104-event validation
- [`docs/crm-adapter-pattern.md`](./docs/crm-adapter-pattern.md) — Design rationale and multi-CRM strategy
- [`docs/roadmap.md`](./docs/roadmap.md) — Technical roadmap

---

## Team

We're three Seattle-based product, design, and engineering leaders with shared roots at T-Mobile and a deep personal investment in the live arts and entertainment space.

**Phil Kamolz — Co-founder and CEO.** Phil brings 25+ years building consumer and enterprise products across telecom, eCommerce, and healthcare, including co-leading T-Mobile's eSIM rollout and architecting the digital upgrade path now serving 70% of T-Mobile upgrades. As founder of Elevation Consulting, he has shaped product strategy for Costco, Nordstrom, and other category leaders. A multi-year Seattle Theatre season ticket holder and symphony enthusiast, Phil is the reason ArtsPass exists. Outside of work, he's skiing, surfing, or traveling with his family.

**Martin Chvoj — Co-founder and CPO.** Martin brings 20+ years of product leadership across B2B SaaS, enterprise platforms, and consumer products. At T-Mobile, he led the $550M API Developer program and the company's enhanced scam protection initiative. Most recently as Head of Product at DevBlock Technologies, he has been leading cloud-native and AI software solutions with deep expertise in Generative AI and ML-driven workflow automation. When he's not building products, Martin is in the mountains or at a concert — a Pacific Northwest outdoor enthusiast, skier, and live music fan.

**Jason Luna — Co-founder and Head of Design.** Jason brings 20+ years of design leadership across consumer SaaS, AI tools, and platform products. At Redfin, he led design for the company's consumer AI tools (Ask Redfin) and oversaw the launch of Blueprint, Redfin's design system. At Indy, his work drove a 150% subscription increase on the freelancer SaaS platform. At Genius Sports, he directed a global design team of 30 across six countries. A passionate concertgoer. Also: World Champion Churro Eater, 2001. (Yes, he wants you to read that.)

---

ArtsPass is in active development in Seattle, with a roadmap that spans cities, categories, and the broader live entertainment market. If you're a venue, an investor, or a patron interested in what we're building, we'd love to talk.

Reach out to Phil.Kamolz@ElevationC2.com
