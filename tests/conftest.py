"""Shared fixtures for the Easy PV (EW) tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easy_pv_ew.const import DOMAIN
from custom_components.easy_pv_ew.easy_pv import BASE_URL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

FIXTURES = Path(__file__).parent / "fixtures"

URL_LOGIN = f"{BASE_URL}/api/sys/v2/passLogin"
URL_USER_INFO = f"{BASE_URL}/api/user/v2/selectUserInfo"
URL_STATIONS = f"{BASE_URL}/api/powerStation/v3/getStationList"
URL_DEVICES = f"{BASE_URL}/api/powerStation/v2/getPowerList"
URL_DEVICE_DATA = f"{BASE_URL}/api/powerStation/v3/getDeviceDataInfo"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture from tests/fixtures."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""


def register_api(
    aioclient_mock: AiohttpClientMocker,
    *,
    energy_total: float | None = None,
    device_total_wh: float | None = None,
    device_status: int | None = None,
    device_data: dict[str, Any] | None = None,
    device_text: str | None = None,
    power_list: dict[str, Any] | None = None,
) -> None:
    """
    Replace all registered responses with successful ones.

    ``energy_total`` overrides ``powerTotals`` of the station (kWh),
    ``device_total_wh`` ``genPowerTotal`` of the inverter (Wh) and
    ``device_status`` its ``status``; ``device_data`` replaces the whole
    getDeviceDataInfo response, ``device_text`` sends it as raw text (e.g.
    broken JSON) and ``power_list`` replaces the getPowerList response.
    """
    aioclient_mock.clear_requests()
    stations = load_fixture("station_list.json")
    if energy_total is not None:
        stations["data"]["rows"][0]["powerTotals"] = energy_total
    if device_data is None:
        device_data = load_fixture("device_data.json")
    if device_total_wh is not None:
        device_data["data"]["genPowerTotal"] = device_total_wh
    if device_status is not None:
        device_data["data"]["status"] = str(device_status)

    aioclient_mock.post(URL_LOGIN, json=load_fixture("login.json"))
    aioclient_mock.get(URL_USER_INFO, json=load_fixture("user_info.json"))
    aioclient_mock.get(URL_STATIONS, json=stations)
    aioclient_mock.get(URL_DEVICES, json=power_list or load_fixture("power_list.json"))
    if device_text is not None:
        aioclient_mock.get(URL_DEVICE_DATA, text=device_text)
    else:
        aioclient_mock.get(URL_DEVICE_DATA, json=device_data)


def sensor_entity_id(hass: HomeAssistant, unique_id: str) -> str:
    """Return the entity ID of the sensor with the given unique ID."""
    entity_id = er.async_get(hass).async_get_entity_id(
        Platform.SENSOR, DOMAIN, unique_id
    )
    assert entity_id, f"no sensor with unique_id {unique_id}"
    return entity_id


def sensor_state(hass: HomeAssistant, unique_id: str) -> State:
    """Return the state of the sensor with the given unique ID."""
    state = hass.states.get(sensor_entity_id(hass, unique_id))
    assert state is not None
    return state


@pytest.fixture
def mock_api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Register successful responses for all Easy PV endpoints."""
    register_api(aioclient_mock)
    return aioclient_mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Config entry as created by the config flow (token only, no password)."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Testkonto",
        unique_id="test@example.com",
        data={"title": "Testkonto", "token": "test-token", "email": "test@example.com"},
    )


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api: AiohttpClientMocker
) -> MockConfigEntry:
    """Set up the integration with all API endpoints answering successfully."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
