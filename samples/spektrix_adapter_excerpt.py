"""
SpektrixAdapter — read-path excerpt.

Maps Spektrix concepts to ArtsPass domain models:
    Spektrix "event"    → Performance
    Spektrix "instance" → contributes to SeatAvailability

Credentials are read from the environment by the Spektrix HTTP client;
this adapter adds no authentication logic of its own.

Sanitized excerpt focused on the read-path mapping logic. The class
inherits from VenueCRMAdapter (see venue_crm_adapter.py). Write-path
methods (create_reservation, cancel_reservation) are elided — see
../docs/spektrix-integration.md for the basket → order sequence.
"""

from datetime import datetime

from arts_pass import spektrix_client
from arts_pass.adapters.base import VenueCRMAdapter
from arts_pass.models.availability import PriceTier, SeatAvailability
from arts_pass.models.performance import Performance
from arts_pass.models.venue import Venue


class SpektrixAdapter(VenueCRMAdapter):
    """Concrete adapter wrapping the Spektrix HTTP client."""

    def get_performances(self, venue: Venue, **filters) -> list[Performance]:
        """
        GET /events — returns all active Spektrix events for the client.

        ``**filters`` are forwarded as query-string parameters and may
        include Spektrix-supported keys such as ``startDate``, ``endDate``.
        """
        response = spektrix_client.get("/events", params=filters or None)
        response.raise_for_status()
        return [self._map_event(venue, raw) for raw in response.json()]

    def get_availability(self, performance: Performance) -> SeatAvailability:
        """
        GET /events/{id}/instances — aggregate capacity across all instances.

        Spektrix stores individual seatings (instances) under an event; we
        roll them up into a single SeatAvailability with per-instance price
        tiers preserved.
        """
        response = spektrix_client.get(f"/events/{performance.crm_ref}/instances")
        response.raise_for_status()

        instances = response.json()
        total = 0
        available = 0
        tiers: list[PriceTier] = []

        for inst in instances:
            total += inst.get("capacity", 0)
            available += inst.get("availableCapacity", 0)

            for price_band in inst.get("priceBands", []):
                tiers.append(
                    PriceTier(
                        name=price_band.get("name", "Standard"),
                        price_cents=int(price_band.get("price", 0) * 100),
                        available=price_band.get("availableCount", 0),
                    )
                )

        return SeatAvailability(
            venue_id=performance.venue_id,
            performance_id=performance.id,
            total_seats=total,
            available_seats=available,
            price_tiers=tiers,
        )

    # Write-path methods (create_reservation, cancel_reservation) elided —
    # see ../docs/spektrix-integration.md for the basket → order sequence.

    def _map_event(self, venue: Venue, raw: dict) -> Performance:
        """Map a raw Spektrix event dict to a Performance domain object."""
        end_dt = (
            datetime.fromisoformat(raw["endDate"])
            if raw.get("endDate")
            else None
        )
        return Performance(
            id=f"spektrix:{raw['id']}",
            venue_id=venue.id,
            title=raw.get("name", ""),
            start_dt=datetime.fromisoformat(raw["startDate"]),
            end_dt=end_dt,
            description=raw.get("description"),
            crm_ref=str(raw["id"]),
        )
