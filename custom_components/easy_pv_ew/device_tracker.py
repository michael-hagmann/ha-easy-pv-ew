"""Sensor platform for EasyPV integration."""

import logging

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EasyPVConfigEntry
from .coordinator import EasyPVCoordinator
from .entity import EasyPVStationEntity
from .utils import setup_platform_entry

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EasyPVConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add device_trackers for passed config_entry in HA."""
    await setup_platform_entry(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        create_station_entities=lambda coordinator, station_id: [
            StationDeviceTracker(coordinator, station_id),
        ],
    )


class StationDeviceTracker(EasyPVStationEntity, TrackerEntity):  # type: ignore[override]
    """Representation of a Sensor."""

    _attr_translation_key = "location"
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EasyPVCoordinator, station_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            station_id,
        )

        self._attr_unique_id = f"{self._id}_location"

    @property
    def location_name(self) -> str | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return f"{self._data.address}" if self._data else None

    @property
    def longitude(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.longitude if self._data else None

    @property
    def latitude(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.latitude if self._data else None

    @property
    def source_type(self) -> SourceType:  # type: ignore[override]
        """Return the state of the sensor."""
        return SourceType.ROUTER
