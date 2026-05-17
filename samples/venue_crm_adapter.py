"""
VenueCRMAdapter — abstract base class for all venue CRM integrations.

This is the contract every CRM adapter implements. The application layer
works exclusively with the four domain types declared in the signatures
(Venue, Performance, SeatAvailability, Reservation); CRM-specific shapes
are translated at the adapter boundary and never propagate further.

Sanitized excerpt; method bodies elided for brevity.
See ../docs/crm-adapter-pattern.md for the full interface contract,
registry, and walkthrough of adding a new CRM.
"""

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
