"""Tests for the findings of the code review before the release (one per fix)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.easy_pv_ew import async_remove_config_entry_device
from custom_components.easy_pv_ew.const import DOMAIN
from custom_components.easy_pv_ew.easy_pv import EasyPVClient, LoginError
from custom_components.easy_pv_ew.easy_pv.validate import ResponseValidator

from .conftest import (
    URL_DEVICE_DATA,
    URL_LOGIN,
    load_fixture,
    register_api,
    sensor_state,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

POLL = timedelta(seconds=60)
PANEL_1 = "1001_2001_panel_1"


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(POLL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _device_data_without_panels() -> dict:
    data = load_fixture("device_data.json")
    data["data"]["devicePhotovoltaicPanel"] = []
    return data


async def test_panel_deleted_at_night_comes_back(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    setup_integration: MockConfigEntry,
) -> None:
    """A PV input deleted by hand while missing at night is created again."""
    entry = setup_integration
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    unique_id = f"{PANEL_1}_power"
    assert ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)

    # At night the cloud sends no PV inputs; HA offers to delete them.
    register_api(aioclient_mock, device_data=_device_data_without_panels())
    await _poll(hass, freezer)
    panel = dev_reg.async_get_device_by_identifier((DOMAIN, PANEL_1), entry.entry_id)
    assert panel is not None
    assert await async_remove_config_entry_device(hass, entry, panel)
    dev_reg.async_remove_device(panel.id)
    await hass.async_block_till_done()
    assert (
        dev_reg.async_get_device_by_identifier((DOMAIN, PANEL_1), entry.entry_id)
        is None
    )
    assert ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id) is None

    # In the morning the inputs are back: device and entities again.
    register_api(aioclient_mock)
    await _poll(hass, freezer)
    assert (
        dev_reg.async_get_device_by_identifier((DOMAIN, PANEL_1), entry.entry_id)
        is not None
    )
    assert ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert sensor_state(hass, unique_id).state == "260.0"


@pytest.mark.parametrize(
    ("time_zone", "expected"),
    [("+1", "2026-12"), ("+0", "2026-11"), ("-5", "2026-11")],
)
async def test_device_data_month_in_station_time_zone(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    config_entry: MockConfigEntry,
    time_zone: str,
    expected: str,
) -> None:
    """The month asked for follows the time zone of the station, not UTC."""
    freezer.move_to(datetime(2026, 11, 30, 23, 30, tzinfo=UTC))
    stations = load_fixture("station_list.json")
    stations["data"]["rows"][0]["timeZone"] = time_zone
    register_api(aioclient_mock, stations=stations)

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    dates = {
        url.query.get("date")
        for _, url, _, _ in aioclient_mock.mock_calls
        if str(url).startswith(URL_DEVICE_DATA)
    }
    assert dates == {expected}


async def test_login_http_401_is_login_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """HTTP 401 at passLogin means wrong credentials, not a connection problem."""
    aioclient_mock.post(URL_LOGIN, status=401)
    client = EasyPVClient(async_get_clientsession(hass))

    with pytest.raises(LoginError):
        await client.login_with_password("test@example.com", "wrong")


def test_huge_integer_is_rejected_not_raised() -> None:
    """An integer too large for a float is a validation problem, not a crash."""
    data = load_fixture("station_list.json")["data"]["rows"]
    data[0]["powerTotals"] = 10**400

    sanitized = ResponseValidator().sanitize("station_list", data)

    assert sanitized[0]["powerTotals"] is None
