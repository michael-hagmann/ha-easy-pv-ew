"""Diagnostics download for Easy PV (EW), anonymized."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data

from .easy_pv.redact import redact

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import EasyPVConfigEntry

TO_REDACT_ENTRY = {"token", "email", "title", "unique_id"}


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: EasyPVConfigEntry
) -> dict[str, Any]:
    """
    Return diagnostics for a config entry.

    Contains the raw API responses of the last successful update, so units
    and field names can be checked. Identifying values are removed.
    """
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT_ENTRY),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_success": (
                coordinator.last_success.isoformat()
                if coordinator.last_success
                else None
            ),
            "update_interval": str(coordinator.update_interval),
        },
        "raw_data": redact(coordinator.raw_data),
    }
