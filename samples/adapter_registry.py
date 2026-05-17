"""
Adapter registry — maps CRM system names to concrete adapter instances.

Usage::

    from arts_pass.adapters.registry import get_adapter_for_venue

    venue = ...  # a Venue with crm_system="spektrix"
    adapter = get_adapter_for_venue(venue)
    performances = adapter.get_performances(venue)

Raises ValueError for venues whose CRM system is not yet known
(crm_system is None) and KeyError for unregistered CRM names.
"""

from arts_pass.adapters.base import VenueCRMAdapter
from arts_pass.adapters.spektrix import SpektrixAdapter
from arts_pass.adapters.tessitura import TessituraAdapter
from arts_pass.models.venue import Venue

_REGISTRY: dict[str, VenueCRMAdapter] = {
    "spektrix": SpektrixAdapter(),
    "tessitura": TessituraAdapter(),
}


def get_adapter(crm_system: str) -> VenueCRMAdapter:
    """
    Return the adapter registered for *crm_system*.

    Args:
        crm_system: One of the keys in the registry (e.g. "spektrix").

    Raises:
        KeyError: No adapter is registered for *crm_system*.
    """
    if crm_system not in _REGISTRY:
        raise KeyError(
            f"No adapter registered for CRM system '{crm_system}'. "
            f"Registered: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[crm_system]


def get_adapter_for_venue(venue: Venue) -> VenueCRMAdapter:
    """
    Convenience wrapper that resolves the adapter from a Venue.

    Args:
        venue: The venue whose crm_system will be used for lookup.

    Raises:
        ValueError: venue.crm_system is None (integration unknown).
        KeyError:   No adapter is registered for the venue's CRM system.
    """
    if venue.crm_system is None:
        raise ValueError(
            f"Venue '{venue.name}' has no CRM system configured "
            f"(integration_status={venue.integration_status!r}). "
            "Update the venue record once the CRM system is identified."
        )
    return get_adapter(venue.crm_system)


def registered_crm_systems() -> list[str]:
    """Return a sorted list of all registered CRM system names."""
    return sorted(_REGISTRY)
