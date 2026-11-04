"""Sensor platform for EasyPV integration."""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EasyPVConfigEntry
from .coordinator import EasyPVCoordinator
from .entity import EasyPVDeviceEntity, EasyPVPanelEntity, EasyPVStationEntity
from .utils import setup_platform_entry

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EasyPVConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    await setup_platform_entry(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        create_station_entities=lambda coordinator, station_id: [
            StationPowerSensor(coordinator, station_id),
            StationEnergyTodaySensor(coordinator, station_id),
            StationEnergyTotalSensor(coordinator, station_id),
        ],
        create_device_entities=lambda coordinator, station_id, device_id: [
            DevicePowerSensor(coordinator, station_id, device_id),
            DeviceEnergyTodaySensor(coordinator, station_id, device_id),
            DeviceEnergyMonthSensor(coordinator, station_id, device_id),
            DeviceGridVoltageSensor(coordinator, station_id, device_id),
        ],
        create_panel_entities=lambda coordinator, station_id, device_id, panel_number: [
            PanelPowerSensor(
                coordinator,
                station_id,
                device_id,
                panel_number,
            ),
            PanelVoltageSensor(
                coordinator,
                station_id,
                device_id,
                panel_number,
            ),
            PanelCurrentSensor(
                coordinator,
                station_id,
                device_id,
                panel_number,
            ),
        ],
    )


class StationPowerSensor(EasyPVStationEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.POWER  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "power"
    _attr_has_entity_name = True

    def __init__(self, coordinator: EasyPVCoordinator, station_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            station_id,
        )

        self._attr_unique_id = f"{self._id}_power"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.power if self._data else None


class StationEnergyTodaySensor(EasyPVStationEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.ENERGY  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_translation_key = "energy_today"
    _attr_has_entity_name = True

    def __init__(self, coordinator: EasyPVCoordinator, station_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            station_id,
        )

        self._attr_unique_id = f"{self._id}_energy_today"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.energy_today if self._data else None


class StationEnergyTotalSensor(EasyPVStationEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.ENERGY  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_translation_key = "energy_total"
    _attr_has_entity_name = True

    def __init__(self, coordinator: EasyPVCoordinator, station_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            station_id,
        )

        self._attr_unique_id = f"{self._id}_energy_total"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.energy_total if self._data else None


class DevicePowerSensor(EasyPVDeviceEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.POWER  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "power"
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EasyPVCoordinator, station_id: str, device_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            station_id,
            device_id,
        )

        self._attr_unique_id = f"{self._id}_power"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.power if self._data else None


class DeviceGridVoltageSensor(EasyPVDeviceEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.VOLTAGE  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "grid_voltage"
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EasyPVCoordinator, station_id: str, device_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            station_id,
            device_id,
        )

        self._attr_unique_id = f"{self._id}_grid_voltage"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.grid_voltage if self._data else None


class DeviceEnergyTodaySensor(EasyPVDeviceEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.ENERGY  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_translation_key = "energy_today"
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EasyPVCoordinator, station_id: str, device_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id)

        self._attr_unique_id = f"{self._id}_energy_today"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.energy_today if self._data else None


class DeviceEnergyMonthSensor(EasyPVDeviceEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.ENERGY  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_translation_key = "energy_month"
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EasyPVCoordinator, station_id: str, device_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id)

        self._attr_unique_id = f"{self._id}_energy_month"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.energy_today if self._data else None


class PanelPowerSensor(EasyPVPanelEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.POWER  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_translation_key = "power"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        panel_number: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            station_id,
            device_id,
            panel_number,
        )

        self._attr_unique_id = f"{self._id}_power"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.power if self._data else None


class PanelVoltageSensor(EasyPVPanelEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.VOLTAGE  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_translation_key = "voltage"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        panel_number: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            station_id,
            device_id,
            panel_number,
        )

        self._attr_unique_id = f"{self._id}_voltage"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.voltage if self._data else None


class PanelCurrentSensor(EasyPVPanelEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    device_class = SensorDeviceClass.CURRENT  # type: ignore[override]
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_translation_key = "current"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        panel_number: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            station_id,
            device_id,
            panel_number,
        )

        self._attr_unique_id = f"{self._id}_current"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.current if self._data else None
