"""The EasyPV integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PLATFORMS
from .coordinator import EasyPVCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry

type EasyPVConfigEntry = ConfigEntry[EasyPVCoordinator]

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: EasyPVConfigEntry) -> bool:
    """Set up EasyPV from a config entry."""
    entry.runtime_data = EasyPVCoordinator(hass, entry)

    await entry.runtime_data.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EasyPVConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    _hass: HomeAssistant, entry: EasyPVConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Allow removing a device by hand once the cloud no longer reports it."""
    coordinator = entry.runtime_data
    if coordinator.data is None:
        return False
    current = coordinator.enumerate_devices()
    return not any(
        domain == DOMAIN and identifier in current
        for domain, identifier in device_entry.identifiers
    )
