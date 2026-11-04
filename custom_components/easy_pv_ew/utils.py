"""
Utility functions and entity setup for the Easy PV Home Assistant integration.

This module provides helper types and the setup_platform_entry function for
managing entities and devices in the Easy PV integration.
"""

from collections.abc import Callable, Iterable

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyPVConfigEntry
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

    def _check_device() -> None:
        if coordinator.data is None:
            return
        new_devices = coordinator.enumerate_devices() - known_devices
        if not new_devices:
            return
        known_devices.update(new_devices)

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
