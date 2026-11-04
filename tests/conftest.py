"""Shared fixtures for the Easy PV (EW) tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from custom_components.easy_pv_ew.easy_pv import BASE_URL

if TYPE_CHECKING:
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


@pytest.fixture
def mock_api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Register successful responses for all Easy PV endpoints."""
    aioclient_mock.post(URL_LOGIN, json=load_fixture("login.json"))
    aioclient_mock.get(URL_USER_INFO, json=load_fixture("user_info.json"))
    aioclient_mock.get(URL_STATIONS, json=load_fixture("station_list.json"))
    aioclient_mock.get(URL_DEVICES, json=load_fixture("power_list.json"))
    aioclient_mock.get(URL_DEVICE_DATA, json=load_fixture("device_data.json"))
    return aioclient_mock
