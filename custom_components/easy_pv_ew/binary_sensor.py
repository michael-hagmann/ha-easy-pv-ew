"""Binary sensor platform for EasyPV integration."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EasyPVConfigEntry
from .coordinator import EasyPVCoordinator
from .entity import EasyPVDeviceEntity
from .model import STATUS_FAULT, STATUS_ONLINE
from .utils import setup_platform_entry

# All entities read from the coordinator, which does the polling.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EasyPVConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add binary sensors for passed config_entry in HA."""
    await setup_platform_entry(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        create_device_entities=lambda coordinator, station_id, device_id: [
            DeviceOnlineSensor(coordinator, station_id, device_id),
            DeviceFaultSensor(coordinator, station_id, device_id),
        ],
    )


class DeviceOnlineSensor(EasyPVDeviceEntity, BinarySensorEntity):  # type: ignore[misc]
    """On while the cloud reports the inverter online (status 1)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "online"
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EasyPVCoordinator, station_id: str, device_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id)

        self._attr_unique_id = f"{self._id}_online"

    @property
    def is_on(self) -> bool | None:  # type: ignore[override]
        """Return True if the inverter is online."""
        if not self._data or self._data.status is None:
            return None
        return self._data.status == STATUS_ONLINE


class DeviceFaultSensor(EasyPVDeviceEntity, BinarySensorEntity):  # type: ignore[misc]
    """On while the cloud reports a fault of the inverter (status 3)."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "fault"
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EasyPVCoordinator, station_id: str, device_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id)

        self._attr_unique_id = f"{self._id}_fault"

    @property
    def is_on(self) -> bool | None:  # type: ignore[override]
        """Return True if the inverter reports a fault."""
        if not self._data or self._data.status is None:
            return None
        return self._data.status == STATUS_FAULT
