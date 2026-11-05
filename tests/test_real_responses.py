"""
Tests with responses recorded from a real VN2T08EU (anonymized, step 7).

The other fixtures are built by hand and fill every field the code reads.
The real responses differ: temperature and frequency of the inputs are null,
the station power is a float with many digits, there are many extra fields,
and getPowerList carries null values the code must not trip over.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.const import STATE_UNAVAILABLE, Platform
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easy_pv_ew.const import DOMAIN
from custom_components.easy_pv_ew.easy_pv.redact import redact

from .conftest import (
    URL_DEVICE_DATA,
    URL_DEVICES,
    URL_LOGIN,
    URL_STATIONS,
    URL_USER_INFO,
    load_fixture,
    sensor_state,
)
from .test_api_contract import JSON_TYPES, _fields, _values

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

REAL_FIXTURES = {
    "station_list": "station_list_real.json",
    "device_list": "power_list_real.json",
    "device_data": "device_data_real.json",
}
STATION = "1001"
DEVICE = "1001_2001"
PANEL_1 = "1001_2001_panel_1"


@pytest.fixture
def real_api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Register the recorded responses for all endpoints."""
    aioclient_mock.post(URL_LOGIN, json=load_fixture("login.json"))
    aioclient_mock.get(URL_USER_INFO, json=load_fixture("user_info.json"))
    aioclient_mock.get(URL_STATIONS, json=load_fixture("station_list_real.json"))
    aioclient_mock.get(URL_DEVICES, json=load_fixture("power_list_real.json"))
    aioclient_mock.get(URL_DEVICE_DATA, json=load_fixture("device_data_real.json"))
    return aioclient_mock


@pytest.fixture
async def setup_real(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    real_api: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
) -> MockConfigEntry:
    """Set up the integration with the recorded responses."""
    caplog.set_level(logging.WARNING, logger="custom_components.easy_pv_ew")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.mark.parametrize(
    ("endpoint", "field_path", "expected"),
    [
        (endpoint, field_path, expected)
        for endpoint in REAL_FIXTURES
        for field_path, expected in _fields(endpoint)
    ],
)
def test_real_response_matches_contract(
    endpoint: str, field_path: str, expected: dict[str, Any]
) -> None:
    """Real responses have every non-optional field with the contract type."""
    values = _values(load_fixture(REAL_FIXTURES[endpoint]), field_path)
    if values is None:
        assert expected.get("optional"), f"{field_path} fehlt in der echten Antwort"
        return
    allowed = JSON_TYPES[expected["type"]]
    for value in values:
        if value is None:
            assert expected.get("nullable") or expected.get("optional"), field_path
            continue
        assert isinstance(value, allowed), f"{field_path}: {value!r}"


@pytest.mark.parametrize(
    ("unique_id", "value"),
    [
        (f"{STATION}_power", "169.7"),
        (f"{STATION}_energy_today", "0.34"),
        (f"{STATION}_energy_total", "421.92"),
        (f"{DEVICE}_power", "133.1"),
        (f"{DEVICE}_energy_today", "0.335"),
        (f"{DEVICE}_energy_month", "0.34"),
        (f"{DEVICE}_energy_total", "91.54"),
        (f"{DEVICE}_grid_voltage", "230.6"),
        (f"{PANEL_1}_power", "78.0"),
        (f"{PANEL_1}_voltage", "33.7"),
        (f"{PANEL_1}_current", "2.48"),
    ],
)
@pytest.mark.usefixtures("setup_real")
async def test_real_values(hass: HomeAssistant, unique_id: str, value: str) -> None:
    """The recorded values arrive unchanged (kWh and W, no factor 1000)."""
    state = sensor_state(hass, unique_id)
    assert float(state.state) == pytest.approx(float(value), abs=0.05)


@pytest.mark.parametrize("key", ["temperature", "frequency"])
@pytest.mark.usefixtures("enable_all_entities", "setup_real")
async def test_real_null_values_unavailable(hass: HomeAssistant, key: str) -> None:
    """The cloud sends null for temperature and frequency: unavailable, not 0."""
    assert sensor_state(hass, f"{PANEL_1}_{key}").state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("setup_real")
async def test_real_responses_cause_no_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Real responses pass the runtime check without warnings."""
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("custom_components.easy_pv_ew")
        and record.levelno >= logging.WARNING
    ]
    assert warnings == []


@pytest.mark.parametrize("name", sorted(REAL_FIXTURES.values()))
def test_real_fixture_redacted_completely(name: str) -> None:
    """Redaction removes every placeholder for identifying data."""
    text = repr(redact(load_fixture(name)))
    for placeholder in (
        "1001",
        "2001",
        "3001",
        "4001",
        "SN0000000000",
        "X000000",
        "Gartenhaus",
        "Musterstadt",
        "50.0",
        "'8.0'",
    ):
        assert placeholder not in text, f"{placeholder} in {name}"


@pytest.mark.parametrize("key", ["temperature", "frequency"])
@pytest.mark.usefixtures("setup_real")
async def test_temperature_frequency_disabled_by_default(
    hass: HomeAssistant, key: str
) -> None:
    """The VN2T08EU never reports them: registered, but disabled by default."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        Platform.SENSOR, DOMAIN, f"{PANEL_1}_{key}"
    )
    assert entity_id
    entry = registry.async_get(entity_id)
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(entity_id) is None
