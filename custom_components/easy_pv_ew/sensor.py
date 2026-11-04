"""Sensor platform for EasyPV integration."""

import logging

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EasyPVConfigEntry
from .coordinator import EasyPVCoordinator
from .entity import EasyPVDeviceEntity, EasyPVPanelEntity, EasyPVStationEntity
from .utils import setup_platform_entry

LOGGER = logging.getLogger(__name__)

# All entities read from the coordinator, which does the polling.
PARALLEL_UPDATES = 0


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
            DeviceEnergyTotalSensor(coordinator, station_id, device_id),
            DeviceGridVoltageSensor(coordinator, station_id, device_id),
            DeviceFirmwareSensor(coordinator, station_id, device_id, "app"),
            DeviceFirmwareSensor(coordinator, station_id, device_id, "net"),
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
            PanelEnergyTotalSensor(coordinator, station_id, device_id, panel_number),
            PanelTemperatureSensor(coordinator, station_id, device_id, panel_number),
            PanelFrequencySensor(coordinator, station_id, device_id, panel_number),
        ],
    )


class StationPowerSensor(EasyPVStationEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "power"
    _attr_has_entity_name = True
    _requires_online = True

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

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
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


class MonotonicEnergyTotalMixin:
    """
    Lifetime energy that never goes backwards.

    Used as the absolute energy meter of the inverter: a lower value from the
    cloud (glitch, 0 during an outage) is ignored and the last value is kept,
    also across Home Assistant restarts. Must come first in the bases, before
    the Easy PV entity and RestoreSensor.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_translation_key = "energy_total"
    _attr_has_entity_name = True

    _total: float | None = None
    _ignoring_lower = False

    @property
    def _cloud_total(self) -> float | None:
        raise NotImplementedError

    async def async_added_to_hass(self) -> None:
        """Restore the last known total, then apply the current cloud value."""
        await super().async_added_to_hass()  # type: ignore[misc]
        last = await self.async_get_last_sensor_data()  # type: ignore[attr-defined]
        if last is not None and last.native_value is not None:
            try:
                self._total = float(last.native_value)
            except TypeError, ValueError:
                self._total = None
        self._handle_update()

    def _handle_update(self) -> None:
        value = self._cloud_total
        if value is None:
            return

        value = float(value)
        if self._total is None or value >= self._total:
            self._total = value
            self._ignoring_lower = False
        elif not self._ignoring_lower:
            LOGGER.warning(
                "Cloud reports a lower total energy (%s kWh) than before "
                "(%s kWh); keeping the previous value",
                value,
                self._total,
            )
            self._ignoring_lower = True

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._total


class StationEnergyTotalSensor(  # type: ignore[misc]
    MonotonicEnergyTotalMixin, EasyPVStationEntity, RestoreSensor
):
    """Lifetime energy of the station (powerTotals of getStationList)."""

    def __init__(self, coordinator: EasyPVCoordinator, station_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id)

        self._attr_unique_id = f"{self._id}_energy_total"

    @property
    def _cloud_total(self) -> float | None:
        return self._data.energy_total if self._data else None


class DeviceEnergyTotalSensor(  # type: ignore[misc]
    MonotonicEnergyTotalMixin, EasyPVDeviceEntity, RestoreSensor
):
    """Lifetime energy of the inverter (genPowerTotal of getDeviceDataInfo)."""

    def __init__(
        self, coordinator: EasyPVCoordinator, station_id: str, device_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id)

        self._attr_unique_id = f"{self._id}_energy_total"

    @property
    def _cloud_total(self) -> float | None:
        return self._data.energy_total if self._data else None


class DevicePowerSensor(EasyPVDeviceEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "power"
    _attr_has_entity_name = True
    _requires_online = True

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

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "grid_voltage"
    _attr_has_entity_name = True
    _requires_online = True

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

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
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

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
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
        return self._data.energy_month if self._data else None


class PanelPowerSensor(EasyPVPanelEntity, SensorEntity):  # type: ignore[misc]
    """Representation of a Sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_translation_key = "power"
    _attr_has_entity_name = True
    _requires_online = True

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

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_translation_key = "voltage"
    _attr_has_entity_name = True
    _requires_online = True

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

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_translation_key = "current"
    _attr_has_entity_name = True
    _requires_online = True

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


class DeviceFirmwareSensor(EasyPVDeviceEntity, SensorEntity):  # type: ignore[misc]
    """Firmware version of the inverter (app) or its network module (net)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        kind: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id)

        self._kind = kind
        self._attr_translation_key = f"firmware_{kind}"
        self._attr_unique_id = f"{self._id}_firmware_{kind}"

    @property
    def native_value(self) -> str | None:  # type: ignore[override]
        """Return the state of the sensor."""
        if not self._data:
            return None
        return self._data.app_fw if self._kind == "app" else self._data.net_fw


class PanelEnergyTotalSensor(EasyPVPanelEntity, SensorEntity):  # type: ignore[misc]
    """Lifetime energy of one PV input (diagnostic, no rollback protection)."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "energy_total"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        panel_number: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id, panel_number)

        self._attr_unique_id = f"{self._id}_energy_total"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.energy_total if self._data else None


class PanelTemperatureSensor(EasyPVPanelEntity, SensorEntity):  # type: ignore[misc]
    """Temperature reported for one PV input (diagnostic)."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _requires_online = True

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        panel_number: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id, panel_number)

        self._attr_unique_id = f"{self._id}_temperature"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.temperature if self._data else None


class PanelFrequencySensor(EasyPVPanelEntity, SensorEntity):  # type: ignore[misc]
    """Grid frequency reported for one PV input (diagnostic)."""

    _attr_device_class = SensorDeviceClass.FREQUENCY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfFrequency.HERTZ
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _requires_online = True

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        panel_number: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id, panel_number)

        self._attr_unique_id = f"{self._id}_frequency"

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        """Return the state of the sensor."""
        return self._data.frequency if self._data else None
