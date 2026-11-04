"""Tests for the Easy PV (EW) sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT

from .conftest import sensor_state

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

STATION = "1001"
DEVICE = "1001_2001"
PANEL_1 = "1001_2001_panel_1"


@pytest.mark.parametrize(
    ("unique_id", "value", "device_class", "state_class", "unit"),
    [
        # Station (aus getStationList)
        (f"{STATION}_power", "512.0", "power", "measurement", "W"),
        (f"{STATION}_energy_today", "1.25", "energy", "total_increasing", "kWh"),
        (f"{STATION}_energy_total", "123.45", "energy", "total_increasing", "kWh"),
        # Wechselrichter (aus getDeviceDataInfo)
        (f"{DEVICE}_power", "512.0", "power", "measurement", "W"),
        (f"{DEVICE}_energy_today", "1.25", "energy", "total_increasing", "kWh"),
        (f"{DEVICE}_energy_month", "8.5", "energy", "total_increasing", "kWh"),
        (f"{DEVICE}_grid_voltage", "230.4", "voltage", "measurement", "V"),
        # Panel bzw. MPPT-Eingang
        (f"{PANEL_1}_power", "260.0", "power", "measurement", "W"),
        (f"{PANEL_1}_voltage", "36.6", "voltage", "measurement", "V"),
        (f"{PANEL_1}_current", "7.1", "current", "measurement", "A"),
    ],
)
@pytest.mark.usefixtures("setup_integration")
async def test_sensor_states(  # noqa: PLR0913
    hass: HomeAssistant,
    unique_id: str,
    value: str,
    device_class: str,
    state_class: str,
    unit: str,
) -> None:
    """Every sensor reports value, device class, state class and unit."""
    state = sensor_state(hass, unique_id)

    assert state.state == value
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass(device_class)
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass(state_class)
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == unit


@pytest.mark.usefixtures("setup_integration")
async def test_energy_month_is_not_energy_today(hass: HomeAssistant) -> None:
    """Fehler 1: Ertrag Monat zeigte den Tageswert."""
    today = sensor_state(hass, f"{DEVICE}_energy_today").state
    month = sensor_state(hass, f"{DEVICE}_energy_month").state

    assert month == "8.5"
    assert month != today


async def test_second_panel_created(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Both MPPT inputs of the VN2T08EU get their own sensors."""
    assert sensor_state(hass, "1001_2001_panel_2_power").state == "252.0"
