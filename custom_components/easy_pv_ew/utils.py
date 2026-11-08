"""
Utility functions and entity setup for the Easy PV Home Assistant integration.

This module provides helper types and the setup_platform_entry function for
managing entities and devices in the Easy PV integration.
"""

from collections.abc import Callable, Iterable

from homeassistant.core import Event, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyPVConfigEntry
from .const import DOMAIN
from .coordinator import EasyPVCoordinator

type CreateStationEntitiesCallback = Callable[
    [EasyPVCoordinator, str], Iterable[Entity]
]
type CreateDeviceEntitiesCallback = Callable[
    [EasyPVCoordinator, str, str], Iterable[Entity]
]
type CreatePanelEntitiesCallback = Callable[
    [EasyPVCoordinator, str, str, int], Iterable[Entity]
]


def _register_device_hierarchy(
    config_entry: EasyPVConfigEntry, coordinator: EasyPVCoordinator
) -> None:
    """
    Register station, inverter and PV input devices with their parent links.

    ``via_device_id`` needs the registry id of an already registered parent.
    The platforms add their entities independently (the binary sensor platform
    has no station entity), so the parent device may not exist yet when a
    child entity is added. Registering the hierarchy here, parents first,
    makes the links independent of that order. The entities add the details
    (name, model, firmware) through their device info.
    """
    if coordinator.data is None:
        return
    dev_reg = dr.async_get(coordinator.hass)
    entry_id = config_entry.entry_id
    for station in coordinator.data.values():
        station_entry = dev_reg.async_get_or_create(
            config_entry_id=entry_id, identifiers={(DOMAIN, station.entity_id)}
        )
        for device in station.devices.values():
            device_entry = dev_reg.async_get_or_create(
                config_entry_id=entry_id,
                identifiers={(DOMAIN, device.entity_id)},
                via_device_id=station_entry.id,
            )
            for panel in device.panels or []:
                dev_reg.async_get_or_create(
                    config_entry_id=entry_id,
                    identifiers={(DOMAIN, panel.entity_id)},
                    via_device_id=device_entry.id,
                )


async def setup_platform_entry(
    config_entry: EasyPVConfigEntry,
    async_add_entities: AddEntitiesCallback,
    create_station_entities: CreateStationEntitiesCallback = lambda _, __: [],
    create_device_entities: CreateDeviceEntitiesCallback = lambda _, __, ___: [],
    create_panel_entities: CreatePanelEntitiesCallback = lambda _, __, ___, ____: [],
) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator = config_entry.runtime_data

    # Devices seen since setup. A device or PV input missing from one response
    # (e.g. no inputs while the inverter is offline at night) is not removed:
    # its entities become unavailable and come back with the next data. That
    # keeps entity IDs and settings stable. Devices that are really gone can be
    # deleted by hand (async_remove_config_entry_device).
    known_devices: set[str] = set()

    @callback
    def _forget_removed_device(event: Event[dr.EventDeviceRegistryUpdatedData]) -> None:
        # A device deleted by hand (e.g. a PV input missing at night) must be
        # created again when the cloud reports it later. Every platform keeps
        # its own set, so each one listens for the removal itself.
        if event.data["action"] != "remove":
            return
        device = event.data["device"]
        if device.get("config_entry_id") != config_entry.entry_id:
            return
        for domain, identifier in device.get("identifiers", []):
            if domain == DOMAIN:
                known_devices.discard(identifier)

    config_entry.async_on_unload(
        coordinator.hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED, _forget_removed_device
        )
    )

    def _check_device() -> None:
        if coordinator.data is None:
            return
        new_devices = coordinator.enumerate_devices() - known_devices
        if not new_devices:
            return
        known_devices.update(new_devices)
        _register_device_hierarchy(config_entry, coordinator)

        new_entities: list[Entity] = []
        for station in coordinator.data.values():
            if station.entity_id in new_devices:
                new_entities.extend(
                    create_station_entities(coordinator, station.entity_id)
                )

            for device in station.devices.values():
                if device.entity_id in new_devices:
                    new_entities.extend(
                        create_device_entities(
                            coordinator, station.entity_id, device.id
                        )
                    )

                for panel in device.panels or []:
                    if panel.entity_id in new_devices:
                        new_entities.extend(
                            create_panel_entities(
                                coordinator, station.entity_id, device.id, panel.idx
                            )
                        )

        async_add_entities(new_entities)

    _check_device()
    config_entry.async_on_unload(coordinator.async_add_listener(_check_device))
