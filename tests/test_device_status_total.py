"""Tests for the inverter total (Fehler 5) and status availability (Fehler 6)."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import aiohttp
import pytest
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, Platform
from homeassistant.core import State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from custom_components.easy_pv_ew.const import (
    CONF_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
)

from .conftest import (
    URL_STATIONS,
    load_fixture,
    register_api,
    sensor_entity_id,
    sensor_state,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

DEVICE = "1001_2001"
PANEL_1 = "1001_2001_panel_1"
DEVICE_TOTAL = f"{DEVICE}_energy_total"
POLL = timedelta(seconds=60)

# Live measurements: unavailable while the inverter is offline.
LIVE = [
    "1001_power",
    f"{DEVICE}_power",
    f"{DEVICE}_grid_voltage",
    f"{PANEL_1}_power",
    f"{PANEL_1}_voltage",
    f"{PANEL_1}_current",
    f"{PANEL_1}_temperature",
    f"{PANEL_1}_frequency",
]
# Energy counters and firmware: still valid while offline.
COUNTERS = [
    "1001_energy_total",
    f"{DEVICE}_energy_today",
    f"{DEVICE}_energy_month",
    DEVICE_TOTAL,
    f"{DEVICE}_firmware_app",
]


async def _poll(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, interval: timedelta = POLL
) -> None:
    freezer.tick(interval)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _binary_state(hass: HomeAssistant, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        Platform.BINARY_SENSOR, DOMAIN, unique_id
    )
    assert entity_id
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


# --- Gesamtzähler je Gerät (Fehler 5) ---


@pytest.mark.usefixtures("setup_integration")
async def test_device_total_from_gen_power_total(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The inverter total comes from genPowerTotal, which the cloud sends in kWh."""
    register_api(aioclient_mock, device_total=500.0)
    await _poll(hass, freezer)

    assert sensor_state(hass, DEVICE_TOTAL).state == "500.0"


@pytest.mark.usefixtures("setup_integration")
async def test_device_energy_is_kwh_not_wh(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """
    Energy of getDeviceDataInfo is kWh, despite "Wh" in the OpenAPI description.

    Values as seen on 05.11.2026: the device reported 0.025 for today while the
    station reported 0.03 kWh; read as Wh, HA showed 0.00 kWh.
    """
    data = load_fixture("device_data.json")
    data["data"].update(
        genPowerTotal=91.23, genpowerTodayTotals=0.025, genpowerMonthTotals=0.03
    )
    register_api(aioclient_mock, device_data=data)
    await _poll(hass, freezer)

    assert sensor_state(hass, DEVICE_TOTAL).state == "123.45"  # never lower
    assert sensor_state(hass, f"{DEVICE}_energy_today").state == "0.025"
    assert sensor_state(hass, f"{DEVICE}_energy_month").state == "0.03"
    # genpowerTotals of an input is 400.0 on both inputs, not an energy value.
    registry = er.async_get(hass)
    assert (
        registry.async_get_entity_id(Platform.SENSOR, DOMAIN, f"{PANEL_1}_energy_total")
        is None
    )


@pytest.mark.parametrize("lower", [0, 100.0, 123.44])
@pytest.mark.usefixtures("setup_integration")
async def test_device_total_never_decreases(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    lower: float,
) -> None:
    """A lower genPowerTotal is ignored; higher values are taken over."""
    register_api(aioclient_mock, device_total=lower)
    await _poll(hass, freezer)
    assert sensor_state(hass, DEVICE_TOTAL).state == "123.45"

    register_api(aioclient_mock, device_total=125.5)
    await _poll(hass, freezer)
    assert sensor_state(hass, DEVICE_TOTAL).state == "125.5"


async def test_device_total_restored_after_restart(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """After a restart the inverter total does not drop below the value before."""
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State("sensor.vn2t08eu_energy_total", "200.0"),
                {"native_value": 200.0, "native_unit_of_measurement": "kWh"},
            )
        ],
    )
    config_entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        DEVICE_TOTAL,
        suggested_object_id="vn2t08eu_energy_total",
        config_entry=config_entry,
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert sensor_entity_id(hass, DEVICE_TOTAL) == "sensor.vn2t08eu_energy_total"
    assert sensor_state(hass, DEVICE_TOTAL).state == "200.0"


@pytest.mark.parametrize("bad", [None, "", "n/a", "NaN", "inf", True])
@pytest.mark.usefixtures("setup_integration")
async def test_device_total_invalid_keeps_value(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    bad: object,
) -> None:
    """A missing or invalid genPowerTotal keeps the last total."""
    register_api(aioclient_mock)
    device_data = load_fixture("device_data.json")
    if bad is None:
        del device_data["data"]["genPowerTotal"]
    else:
        device_data["data"]["genPowerTotal"] = bad
    aioclient_mock.clear_requests()
    register_api(aioclient_mock, device_data=device_data)
    await _poll(hass, freezer)

    assert sensor_state(hass, DEVICE_TOTAL).state == "123.45"


# --- Verfügbarkeit über status (Fehler 6) ---


@pytest.mark.usefixtures("setup_integration")
async def test_online_status(hass: HomeAssistant) -> None:
    """Status 1: online, no fault, all sensors available."""
    assert _binary_state(hass, f"{DEVICE}_online") == STATE_ON
    assert _binary_state(hass, f"{DEVICE}_fault") == STATE_OFF
    for unique_id in LIVE + COUNTERS:
        assert sensor_state(hass, unique_id).state != STATE_UNAVAILABLE, unique_id


@pytest.mark.parametrize(("status", "fault"), [(2, STATE_OFF), (3, STATE_ON)])
@pytest.mark.usefixtures("setup_integration")
async def test_offline_or_fault_hides_live_values(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    status: int,
    fault: str,
) -> None:
    """Offline (2) or fault (3): live values unavailable, counters kept."""
    register_api(aioclient_mock, device_status=status)
    await _poll(hass, freezer)

    for unique_id in LIVE[1:]:  # station power follows the station status
        assert sensor_state(hass, unique_id).state == STATE_UNAVAILABLE, unique_id
    for unique_id in COUNTERS:
        assert sensor_state(hass, unique_id).state != STATE_UNAVAILABLE, unique_id
    assert sensor_state(hass, DEVICE_TOTAL).state == "123.45"
    assert _binary_state(hass, f"{DEVICE}_online") == STATE_OFF
    assert _binary_state(hass, f"{DEVICE}_fault") == fault

    register_api(aioclient_mock)
    await _poll(hass, freezer)
    assert sensor_state(hass, f"{DEVICE}_power").state == "512.0"


# --- Abrufintervall an der Obergrenze ---


async def test_max_interval_bridges_one_failed_poll(
    hass: HomeAssistant,
    mock_api: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """At the longest interval one failed poll is still bridged."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Testkonto",
        unique_id="test@example.com",
        data={"title": "Testkonto", "token": "test-token"},
        options={CONF_SCAN_INTERVAL: MAX_SCAN_INTERVAL},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    mock_api.clear_requests()
    mock_api.get(URL_STATIONS, exc=aiohttp.ClientConnectionError("DNS failure"))
    interval = timedelta(seconds=MAX_SCAN_INTERVAL)

    await _poll(hass, freezer, interval)
    assert sensor_state(hass, f"{DEVICE}_power").state == "512.0"

    await _poll(hass, freezer, interval)
    assert sensor_state(hass, f"{DEVICE}_power").state == STATE_UNAVAILABLE
