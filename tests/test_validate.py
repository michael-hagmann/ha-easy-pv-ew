"""Tests for the runtime check of API responses (Briefing, API-Änderungen 5)."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from homeassistant.const import STATE_UNAVAILABLE, Platform
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.easy_pv_ew.const import DOMAIN
from custom_components.easy_pv_ew.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.easy_pv_ew.easy_pv.validate import (
    EXPECTED,
    ResponseValidator,
)

from .conftest import load_fixture, register_api, sensor_state

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

CONTRACT = yaml.safe_load(
    (Path(__file__).parent / "api_contract.yaml").read_text(encoding="utf-8")
)
# Where the client's return value sits in the contract's field paths.
PREFIX = {
    "station_list": "data.rows[]",
    "device_list": "data[]",
    "device_data": "data.",
}
POLL = timedelta(seconds=60)
DEVICE = "1001_2001"
PANEL_1 = "1001_2001_panel_1"
LOGGER = "custom_components.easy_pv_ew.easy_pv.validate"


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(POLL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _device_data(**changes: Any) -> dict[str, Any]:
    data = load_fixture("device_data.json")
    data["data"].update(changes)
    return data


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == LOGGER and record.levelno == logging.WARNING
    ]


# --- Validator and contract stay in sync ---


@pytest.mark.parametrize("endpoint", list(PREFIX))
def test_expected_fields_match_contract(endpoint: str) -> None:
    """Every response field of the contract is checked, with type and range."""
    contract_fields = {
        path.removeprefix(PREFIX[endpoint]).removeprefix("."): spec
        for path, spec in CONTRACT["endpoints"][endpoint]["response"].items()
        if path.startswith(PREFIX[endpoint].rstrip("."))
    }
    expected = EXPECTED[endpoint]
    contract_keys = {
        (f"[].{key}" if PREFIX[endpoint].endswith("[]") else key)
        for key in contract_fields
    }
    assert set(expected) == contract_keys

    for key, spec in contract_fields.items():
        field = expected[f"[].{key}" if PREFIX[endpoint].endswith("[]") else key]
        assert field.type == spec["type"], key
        assert field.optional == bool(spec.get("optional")), key
        assert (field.min, field.max) == tuple(spec.get("range", (None, None))), key


# --- ResponseValidator ---


def test_valid_response_unchanged(caplog: pytest.LogCaptureFixture) -> None:
    """The fixture passes without changes and without warnings."""
    data = load_fixture("device_data.json")["data"]
    assert ResponseValidator().sanitize("device_data", data) == data
    assert not _warnings(caplog)


@pytest.mark.parametrize(
    ("field", "value", "result"),
    [
        ("genPower", 99_999, None),  # implausible
        ("genPower", -5, None),  # implausible
        ("genPower", "512.0", "512.0"),  # number as string: used
        ("genPower", "n/a", None),
        ("genPower", {"w": 1}, None),
        ("genPower", True, None),
        ("status", 1, 1),  # number instead of string: used
        ("status", [1], None),
        ("devicePhotovoltaicPanel", {"sort": "1"}, None),
    ],
)
def test_invalid_value_replaced(
    caplog: pytest.LogCaptureFixture, field: str, value: Any, result: Any
) -> None:
    """Invalid values become None; readable ones are kept; one warning each."""
    data = _device_data(**{field: value})["data"]
    sanitized = ResponseValidator().sanitize("device_data", data)

    assert sanitized[field] == result
    assert data[field] == value  # the original stays unchanged
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert f"field {field}" in warnings[0]


def test_warning_once_per_field(caplog: pytest.LogCaptureFixture) -> None:
    """A problem is logged once, not on every update."""
    validator = ResponseValidator()
    data = _device_data(gridVoltage=999)["data"]
    for _ in range(3):
        validator.sanitize("device_data", data)
    assert len(_warnings(caplog)) == 1


def test_identifiers_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Values of identifying fields never appear in the log."""
    data = _device_data(deviceNum=["SN0000000000"])["data"]
    ResponseValidator().sanitize("device_data", data)
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "SN0000000000" not in warnings[0]


def test_missing_required_and_null_optional(caplog: pytest.LogCaptureFixture) -> None:
    """Missing required fields are logged, null optional fields are not."""
    data = _device_data(genPower=None)["data"]
    del data["devicePhotovoltaicPanel"][0]["sort"]
    ResponseValidator().sanitize("device_data", data)
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "devicePhotovoltaicPanel[].sort" in warnings[0]


def test_lists_are_checked(caplog: pytest.LogCaptureFixture) -> None:
    """Fields inside lists (stations, inputs) are checked for every element."""
    stations = load_fixture("station_list.json")["data"]["rows"]
    stations[0]["powerTotals"] = -1
    sanitized = ResponseValidator().sanitize("station_list", stations)
    assert sanitized[0]["powerTotals"] is None
    assert "[].powerTotals" in _warnings(caplog)[0]


# --- Effect on the entities ---


@pytest.mark.usefixtures("setup_integration")
async def test_implausible_value_makes_entity_unavailable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Only the affected entity is unavailable; the warning comes once."""
    data = _device_data(genPower=99_999)
    data["data"]["devicePhotovoltaicPanel"][0]["temp"] = 500
    register_api(aioclient_mock, device_data=data)
    await _poll(hass, freezer)
    await _poll(hass, freezer)

    assert sensor_state(hass, f"{DEVICE}_power").state == STATE_UNAVAILABLE
    assert sensor_state(hass, f"{PANEL_1}_temperature").state == STATE_UNAVAILABLE
    assert sensor_state(hass, f"{DEVICE}_grid_voltage").state == "230.4"
    assert sensor_state(hass, f"{PANEL_1}_power").state == "260.0"
    assert len(_warnings(caplog)) == 2

    register_api(aioclient_mock)
    await _poll(hass, freezer)
    assert sensor_state(hass, f"{DEVICE}_power").state == "512.0"


@pytest.mark.usefixtures("setup_integration")
async def test_total_holds_on_invalid_value(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The lifetime energy keeps its last value and stays available (decided)."""
    register_api(aioclient_mock, device_data=_device_data(genPowerTotal=-1))
    await _poll(hass, freezer)

    assert sensor_state(hass, f"{DEVICE}_energy_total").state == "123.45"


@pytest.mark.usefixtures("setup_integration")
async def test_invalid_status_makes_binary_sensors_unavailable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Without a valid status, online and fault are unavailable, not guessed."""
    register_api(aioclient_mock, device_data=_device_data(status=["1"]))
    await _poll(hass, freezer)

    registry = er.async_get(hass)
    for key in ("online", "fault"):
        entity_id = registry.async_get_entity_id(
            Platform.BINARY_SENSOR, DOMAIN, f"{DEVICE}_{key}"
        )
        assert entity_id
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("setup_integration")
async def test_missing_value_is_unavailable_not_unknown(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A field missing from the response makes its sensor unavailable."""
    data = _device_data()
    del data["data"]["genpowerTodayTotals"]
    register_api(aioclient_mock, device_data=data)
    await _poll(hass, freezer)

    assert sensor_state(hass, f"{DEVICE}_energy_today").state == STATE_UNAVAILABLE
    assert sensor_state(hass, f"{DEVICE}_energy_month").state == "8.5"


@pytest.mark.usefixtures("setup_integration")
async def test_diagnostics_keep_original_value(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The diagnostics show the raw value the cloud sent, not the cleaned one."""
    register_api(aioclient_mock, device_data=_device_data(genPower=99_999))
    await _poll(hass, freezer)

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["raw_data"]["device_data"][0]["genPower"] == 99_999
