"""Sensor platform for EasyPV integration."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
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
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from . import EasyPVConfigEntry
from .const import TOTAL_LOWER_WARN_AFTER, TOTAL_RESET_AFTER
from .coordinator import EasyPVCoordinator
from .entity import EasyPVDeviceEntity, EasyPVPanelEntity, EasyPVStationEntity
from .model import PVDevice, PVPanel, PVStation
from .utils import setup_platform_entry

LOGGER = logging.getLogger(__name__)

# All entities read from the coordinator, which does the polling.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class EasyPVSensorEntityDescription(SensorEntityDescription):
    """
    Describes an Easy PV sensor.

    The key is also the suffix of the unique ID, so it must never change.
    Live measurements set requires_online (see EasyPVEntity).
    """

    value_fn: Callable[[Any], StateType]
    requires_online: bool = False


_POWER: dict[str, Any] = {
    "key": "power",
    "translation_key": "power",
    "device_class": SensorDeviceClass.POWER,
    "state_class": SensorStateClass.MEASUREMENT,
    "native_unit_of_measurement": UnitOfPower.WATT,
    "requires_online": True,
}
_ENERGY: dict[str, Any] = {
    "device_class": SensorDeviceClass.ENERGY,
    "state_class": SensorStateClass.TOTAL_INCREASING,
    "native_unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
    "suggested_display_precision": 2,
}
_ENERGY_TOTAL: dict[str, Any] = {
    **_ENERGY,
    "key": "energy_total",
    "translation_key": "energy_total",
}
_ENERGY_TODAY: dict[str, Any] = {
    **_ENERGY,
    "key": "energy_today",
    "translation_key": "energy_today",
}


def _station(fn: Callable[[PVStation], StateType]) -> Callable[[Any], StateType]:
    return fn


def _device(fn: Callable[[PVDevice], StateType]) -> Callable[[Any], StateType]:
    return fn


def _panel(fn: Callable[[PVPanel], StateType]) -> Callable[[Any], StateType]:
    return fn


STATION_SENSORS: tuple[EasyPVSensorEntityDescription, ...] = (
    EasyPVSensorEntityDescription(
        **_POWER,
        suggested_display_precision=2,
        value_fn=_station(lambda station: station.power),
    ),
    EasyPVSensorEntityDescription(
        **_ENERGY_TODAY,
        value_fn=_station(lambda station: station.energy_today),
    ),
)
STATION_TOTAL = EasyPVSensorEntityDescription(
    **_ENERGY_TOTAL,
    value_fn=_station(lambda station: station.energy_total),
)

DEVICE_SENSORS: tuple[EasyPVSensorEntityDescription, ...] = (
    EasyPVSensorEntityDescription(
        **_POWER,
        suggested_display_precision=2,
        value_fn=_device(lambda device: device.power),
    ),
    EasyPVSensorEntityDescription(
        **_ENERGY_TODAY,
        value_fn=_device(lambda device: device.energy_today),
    ),
    EasyPVSensorEntityDescription(
        key="grid_voltage",
        translation_key="grid_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=2,
        requires_online=True,
        value_fn=_device(lambda device: device.grid_voltage),
    ),
    EasyPVSensorEntityDescription(
        key="firmware_app",
        translation_key="firmware_app",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_device(lambda device: device.app_fw),
    ),
    EasyPVSensorEntityDescription(
        key="firmware_net",
        translation_key="firmware_net",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_device(lambda device: device.net_fw),
    ),
)
DEVICE_MONTH = EasyPVSensorEntityDescription(
    **_ENERGY,
    key="energy_month",
    translation_key="energy_month",
    value_fn=_device(lambda device: device.energy_month),
)
DEVICE_TOTAL = EasyPVSensorEntityDescription(
    **_ENERGY_TOTAL,
    value_fn=_device(lambda device: device.energy_total),
)

PANEL_SENSORS: tuple[EasyPVSensorEntityDescription, ...] = (
    EasyPVSensorEntityDescription(
        **_POWER,
        value_fn=_panel(lambda panel: panel.power),
    ),
    EasyPVSensorEntityDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        requires_online=True,
        value_fn=_panel(lambda panel: panel.voltage),
    ),
    EasyPVSensorEntityDescription(
        key="current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        requires_online=True,
        value_fn=_panel(lambda panel: panel.current),
    ),
    EasyPVSensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        # The VN2T08EU sends null; enable manually if an inverter reports it.
        entity_registry_enabled_default=False,
        requires_online=True,
        value_fn=_panel(lambda panel: panel.temperature),
    ),
    EasyPVSensorEntityDescription(
        key="frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        entity_category=EntityCategory.DIAGNOSTIC,
        # The VN2T08EU sends null; enable manually if an inverter reports it.
        entity_registry_enabled_default=False,
        requires_online=True,
        value_fn=_panel(lambda panel: panel.frequency),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: EasyPVConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    await setup_platform_entry(
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        create_station_entities=lambda coordinator, station_id: [
            *(
                EasyPVStationSensor(coordinator, station_id, description)
                for description in STATION_SENSORS
            ),
            StationEnergyTotalSensor(coordinator, station_id, STATION_TOTAL),
        ],
        create_device_entities=lambda coordinator, station_id, device_id: [
            *(
                EasyPVDeviceSensor(coordinator, station_id, device_id, description)
                for description in DEVICE_SENSORS
            ),
            DeviceEnergyMonthSensor(coordinator, station_id, device_id, DEVICE_MONTH),
            DeviceEnergyTotalSensor(coordinator, station_id, device_id, DEVICE_TOTAL),
        ],
        create_panel_entities=lambda coordinator, station_id, device_id, number: [
            EasyPVPanelSensor(coordinator, station_id, device_id, number, description)
            for description in PANEL_SENSORS
        ],
    )


class EasyPVSensorMixin:
    """Common part of all Easy PV sensors: value and unique ID from the description."""

    entity_description: EasyPVSensorEntityDescription
    _attr_has_entity_name = True

    def _apply_description(self, description: EasyPVSensorEntityDescription) -> None:
        self.entity_description = description
        self._requires_online = description.requires_online
        self._attr_unique_id = f"{self._id}_{description.key}"  # type: ignore[attr-defined]

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        data = self._data  # type: ignore[attr-defined]
        return self.entity_description.value_fn(data) if data else None

    @property
    def available(self) -> bool:
        """
        Return False without a value.

        A missing or invalid value from the cloud (see easy_pv.validate) makes
        the sensor unavailable instead of showing a wrong or unknown value.
        The lifetime energy keeps its last value and stays available.
        """
        return super().available and self.native_value is not None  # type: ignore[misc]


class EasyPVStationSensor(  # type: ignore[misc]
    EasyPVSensorMixin, EasyPVStationEntity, SensorEntity
):
    """Sensor of a station (getStationList)."""

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        description: EasyPVSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id)
        self._apply_description(description)


class EasyPVDeviceSensor(  # type: ignore[misc]
    EasyPVSensorMixin, EasyPVDeviceEntity, SensorEntity
):
    """Sensor of an inverter (getDeviceDataInfo)."""

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        description: EasyPVSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id)
        self._apply_description(description)


class EasyPVPanelSensor(  # type: ignore[misc]
    EasyPVSensorMixin, EasyPVPanelEntity, SensorEntity
):
    """Sensor of one PV input of an inverter."""

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        panel_number: int,
        description: EasyPVSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id, panel_number)
        self._apply_description(description)


class MonotonicEnergyMixin:
    """
    Energy counter that does not go backwards on a glitch of the cloud.

    A lower value from the cloud (glitch, 0 during an outage, the dip around
    midnight) is ignored and the last value is kept, also across Home
    Assistant restarts. Whether a lower value is a real reset decides
    _accept_lower of the subclass; by default never. Must come first in the
    bases, before the Easy PV entity and RestoreSensor.
    """

    _total: float | None = None
    # When the cloud last reported the current value or a higher one.
    _accepted_at: datetime | None = None
    # Since when the cloud reports a lower value.
    _lower_since: datetime | None = None

    entity_description: EasyPVSensorEntityDescription

    @property
    def _cloud_total(self) -> float | None:
        data = self._data  # type: ignore[attr-defined]
        if data is None:
            return None
        value = self.entity_description.value_fn(data)
        return None if value is None else float(value)  # type: ignore[arg-type]

    async def async_added_to_hass(self) -> None:
        """Restore the last known value, then apply the current cloud value."""
        await super().async_added_to_hass()  # type: ignore[misc]
        last = await self.async_get_last_sensor_data()  # type: ignore[attr-defined]
        if last is not None and last.native_value is not None:
            try:
                self._total = float(last.native_value)
            except TypeError, ValueError:
                self._total = None
        if self._total is not None:
            state = await self.async_get_last_state()  # type: ignore[attr-defined]
            self._accepted_at = state.last_reported if state else None
        self._handle_update()

    def _handle_update(self) -> None:
        value = self._cloud_total
        if value is None:
            return

        now = dt_util.utcnow()
        if self._total is None or value >= self._total:
            self._take_over(value, now)
            return

        if self._lower_since is None:
            LOGGER.debug(
                "Cloud reports a lower %s (%s kWh) than before (%s kWh); "
                "keeping the previous value",
                self.entity_description.key,
                value,
                self._total,
            )
            self._lower_since = now
        if self._accept_lower(value, now):
            self._take_over(value, now)

    def _take_over(self, value: float, now: datetime) -> None:
        self._total = value
        self._accepted_at = now
        self._lower_since = None

    def _accept_lower(self, value: float, now: datetime) -> bool:  # noqa: ARG002
        """Return True if a lower value from the cloud is a real reset."""
        return False

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self._total


class StationEnergyTotalSensor(  # type: ignore[misc]
    MonotonicEnergyMixin, EasyPVSensorMixin, EasyPVStationEntity, RestoreSensor
):
    """
    Lifetime energy of the station (powerTotals of getStationList).

    The absolute meter for the energy balance. It is never reset: it keeps
    counting when the inverter is registered again in the app. A lower value
    is never taken over; the sensor waits until the cloud exceeds the last
    value again (around midnight the cloud reports it 0.01 kWh lower until
    the next yield). Only a lower value lasting TOTAL_LOWER_WARN_AFTER is
    logged as a warning, once.
    """

    _lower_warned = False

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        description: EasyPVSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id)
        self._apply_description(description)

    def _take_over(self, value: float, now: datetime) -> None:
        super()._take_over(value, now)
        self._lower_warned = False

    def _accept_lower(self, value: float, now: datetime) -> bool:
        if (
            not self._lower_warned
            and self._lower_since is not None
            and now - self._lower_since >= TOTAL_LOWER_WARN_AFTER
        ):
            LOGGER.warning(
                "Cloud has reported a lower total energy of the station for "
                "%s (%s kWh, keeping %s kWh); the value is not taken over",
                TOTAL_LOWER_WARN_AFTER,
                value,
                self._total,
            )
            self._lower_warned = True
        return False


class DeviceEnergyMonthSensor(  # type: ignore[misc]
    MonotonicEnergyMixin, EasyPVSensorMixin, EasyPVDeviceEntity, RestoreSensor
):
    """
    Energy of the inverter this month (genpowerMonthTotals).

    Around midnight the cloud reports 0 for a few minutes and then the old
    value again. With total_increasing Home Assistant would count that as a
    new cycle and add the month's energy a second time. A lower value is
    therefore only taken over on the first day of a month or when the month
    has changed since the last value, both in the time zone of the station
    (the cloud resets its counters at midnight there).
    """

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        description: EasyPVSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id)
        self._apply_description(description)

    def _accept_lower(self, value: float, now: datetime) -> bool:  # noqa: ARG002
        station = self.coordinator.get_station(self._station_id)
        offset = (station.utc_offset if station else None) or timedelta()
        local_now = now + offset
        if local_now.day == 1 or self._accepted_at is None:
            return True
        local_accepted = self._accepted_at + offset
        return (local_now.year, local_now.month) != (
            local_accepted.year,
            local_accepted.month,
        )


class DeviceEnergyTotalSensor(  # type: ignore[misc]
    MonotonicEnergyMixin, EasyPVSensorMixin, EasyPVDeviceEntity, RestoreSensor
):
    """
    Lifetime energy of the inverter (genPowerTotal of getDeviceDataInfo).

    Falls to 0 when the inverter is registered again in the app. A lower,
    non-zero value that the cloud reports for TOTAL_RESET_AFTER is taken over
    as such a reset; 0 means "no data" and is never taken over.
    """

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        description: EasyPVSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_id, device_id)
        self._apply_description(description)

    def _accept_lower(self, value: float, now: datetime) -> bool:
        if value <= 0 or self._lower_since is None:
            return False
        if now - self._lower_since < TOTAL_RESET_AFTER:
            return False
        LOGGER.warning(
            "Cloud has reported a lower total energy of the inverter for %s; "
            "taking over %s kWh (before %s kWh) as a reset of the counter",
            TOTAL_RESET_AFTER,
            value,
            self._total,
        )
        return True
