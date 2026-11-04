"""Tests for the findings of the code review on 04.11.2026 (one test per fix)."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import aiohttp
import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, STATE_UNAVAILABLE
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from multidict import CIMultiDict, CIMultiDictProxy
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from yarl import URL

from custom_components.easy_pv_ew import async_remove_config_entry_device
from custom_components.easy_pv_ew.const import DOMAIN, TOTAL_RESET_AFTER
from custom_components.easy_pv_ew.easy_pv import (
    ApiError,
    CommunicationError,
    EasyPVClient,
    InvalidResponseError,
    LoginError,
)
from custom_components.easy_pv_ew.easy_pv.redact import REDACTED, is_sensitive, redact

from .conftest import (
    URL_DEVICE_DATA,
    URL_LOGIN,
    URL_STATIONS,
    URL_USER_INFO,
    load_fixture,
    register_api,
    sensor_entity_id,
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
DEVICE = "1001_2001"
DEVICE_POWER = f"{DEVICE}_power"
DEVICE_TOTAL = f"{DEVICE}_energy_total"
STATION_TOTAL = "1001_energy_total"
PANEL_1 = "1001_2001_panel_1"
PANEL_2 = "1001_2001_panel_2"


async def _poll(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, interval: timedelta = POLL
) -> None:
    freezer.tick(interval)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _client(hass: HomeAssistant) -> EasyPVClient:
    return EasyPVClient(async_get_clientsession(hass))


def _request_info_with_token() -> aiohttp.RequestInfo:
    url = URL(f"{URL_DEVICE_DATA}?deviceId=2001&stationId=1001")
    return aiohttp.RequestInfo(
        url=url,
        method="GET",
        headers=CIMultiDictProxy(CIMultiDict({"Authorization": "Bearer test-token"})),
        real_url=url,
    )


def _device(hass: HomeAssistant) -> dr.DeviceEntry | None:
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    return dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, DEVICE), entry.entry_id
    )


def _device_data(**changes: object) -> dict:
    data = load_fixture("device_data.json")
    data["data"].update(changes)
    return data


# --- 1: no token or IDs in error messages ---


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (
            aiohttp.ContentTypeError(_request_info_with_token(), (), status=200),
            InvalidResponseError,
        ),
        (
            aiohttp.ClientResponseError(_request_info_with_token(), (), status=502),
            CommunicationError,
        ),
    ],
)
async def test_error_message_without_request_details(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    exc: Exception,
    expected: type[Exception],
) -> None:
    """Errors with request info must not carry the token or IDs into the log."""
    aioclient_mock.get(URL_DEVICE_DATA, exc=exc)
    client = _client(hass)
    client._token = "test-token"  # noqa: SLF001

    with pytest.raises(expected) as err:
        await client.get_device_data("1001", "2001")
    message = str(err.value)
    assert "test-token" not in message
    assert "2001" not in message
    assert "1001" not in message


async def test_html_instead_of_json(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A maintenance page (no JSON) is an invalid response, not a crash."""
    aioclient_mock.get(URL_STATIONS, text="<html>Wartung</html>")
    client = _client(hass)
    client._token = "test-token"  # noqa: SLF001

    with pytest.raises(InvalidResponseError):
        await client.get_stations()


# --- 2: server errors of selectUserInfo are no login errors ---


async def test_user_info_server_error_is_no_login_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Code 500 from selectUserInfo raises ApiError, only 401 is a LoginError."""
    aioclient_mock.get(URL_USER_INFO, json={"code": 500, "msg": "system busy"})
    client = _client(hass)

    with pytest.raises(ApiError) as err:
        await client.login_with_token("test-token")
    assert not isinstance(err.value, LoginError)


async def test_setup_retries_on_server_error(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A busy cloud at startup retries the setup instead of asking for reauth."""
    register_api(aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_USER_INFO, json={"code": 500, "msg": "system busy"})
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.config_entries.flow.async_progress()


async def test_config_flow_server_error_is_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """In the config flow a busy cloud shows cannot_connect, not invalid_auth."""
    aioclient_mock.post(URL_LOGIN, json=load_fixture("login.json"))
    aioclient_mock.get(URL_USER_INFO, json={"code": 500, "msg": "system busy"})

    result = await _configure(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


# --- 3: parse errors are bridged like outages ---


@pytest.mark.parametrize(
    "response",
    [
        {"device_text": "{broken json"},
        {"device_data": _device_data(devicePhotovoltaicPanel=[{"genPower": 1.0}])},
        {"device_data": {"code": 200, "data": "unexpected"}},
    ],
    ids=["broken_json", "panel_without_sort", "data_not_object"],
)
@pytest.mark.usefixtures("setup_integration")
async def test_bad_response_is_bridged(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    response: dict,
) -> None:
    """A malformed response keeps the last values within the grace period."""
    register_api(aioclient_mock, **response)
    await _poll(hass, freezer)

    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    assert coordinator.last_update_success
    assert sensor_state(hass, DEVICE_POWER).state == "512.0"


@pytest.mark.usefixtures("setup_integration")
async def test_offline_without_panels_and_fields(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """At night: offline, no inputs (null) and missing fields are no error."""
    data = _device_data(status=2, devicePhotovoltaicPanel=None)
    for field in ("genPower", "gridVoltage", "productCode", "deviceNum"):
        del data["data"][field]
    register_api(aioclient_mock, device_data=data)
    await _poll(hass, freezer)

    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    assert coordinator.last_update_success
    assert sensor_state(hass, DEVICE_TOTAL).state == "123.45"
    assert sensor_state(hass, DEVICE_POWER).state == STATE_UNAVAILABLE
    assert sensor_state(hass, f"{PANEL_1}_power").state == STATE_UNAVAILABLE


# --- 4: a lasting reset of the total is taken over ---


@pytest.mark.usefixtures("setup_integration")
async def test_lasting_lower_total_is_taken_over(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A lower total reported for TOTAL_RESET_AFTER is accepted as a reset."""
    register_api(aioclient_mock, device_total_wh=50_000)
    await _poll(hass, freezer)
    assert sensor_state(hass, DEVICE_TOTAL).state == "123.45"

    await _poll(hass, freezer, TOTAL_RESET_AFTER - POLL)
    assert sensor_state(hass, DEVICE_TOTAL).state == "123.45"

    await _poll(hass, freezer)
    assert sensor_state(hass, DEVICE_TOTAL).state == "50.0"


@pytest.mark.usefixtures("setup_integration")
async def test_zero_total_is_never_taken_over(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """0 means no data and never resets the total, however long it lasts."""
    register_api(aioclient_mock, device_total_wh=0)
    await _poll(hass, freezer)
    await _poll(hass, freezer, TOTAL_RESET_AFTER * 2)

    assert sensor_state(hass, DEVICE_TOTAL).state == "123.45"


@pytest.mark.usefixtures("setup_integration")
async def test_short_lower_total_restarts_timer(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A normal value in between restarts the wait for a reset."""
    register_api(aioclient_mock, device_total_wh=50_000)
    await _poll(hass, freezer)
    await _poll(hass, freezer, TOTAL_RESET_AFTER - POLL * 2)

    register_api(aioclient_mock, device_total_wh=123_500)
    await _poll(hass, freezer)

    register_api(aioclient_mock, device_total_wh=50_000)
    await _poll(hass, freezer)
    await _poll(hass, freezer)
    assert sensor_state(hass, DEVICE_TOTAL).state == "123.5"


# --- 5: accounts without email ---


async def _configure(hass: HomeAssistant) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: "+490000000", CONF_PASSWORD: "secret"}
    )


@pytest.mark.parametrize(
    ("user_info", "title", "unique_id"),
    [
        ({"userName": "Testkonto"}, "Testkonto", "testkonto"),
        ({}, "+490000000", "+490000000"),
    ],
)
async def test_config_flow_without_email(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    user_info: dict,
    title: str,
    unique_id: str,
) -> None:
    """Accounts registered with a phone number have no email address."""
    aioclient_mock.post(URL_LOGIN, json=load_fixture("login.json"))
    aioclient_mock.get(URL_USER_INFO, json={"code": 200, "data": user_info})

    result = await _configure(hass)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == title
    assert result["result"].unique_id == unique_id


# --- 6 and 8: missing devices are kept, empty lists are valid ---


@pytest.mark.usefixtures("setup_integration")
async def test_missing_device_is_kept(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A device missing in one response is not removed and comes back."""
    entity_id = sensor_entity_id(hass, DEVICE_TOTAL)
    register_api(aioclient_mock, power_list={"code": 200, "data": []})
    await _poll(hass, freezer)

    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    assert coordinator.last_update_success
    assert sensor_state(hass, "1001_power").state == "512.0"
    assert sensor_state(hass, DEVICE_TOTAL).state == STATE_UNAVAILABLE
    device = _device(hass)
    assert device is not None

    register_api(aioclient_mock)
    await _poll(hass, freezer)
    assert sensor_entity_id(hass, DEVICE_TOTAL) == entity_id
    assert sensor_state(hass, DEVICE_TOTAL).state == "123.45"
    assert len(er.async_get(hass).entities) == len(
        {entry.unique_id for entry in er.async_get(hass).entities.values()}
    )


@pytest.mark.usefixtures("setup_integration")
async def test_remove_device_by_hand(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Only devices the cloud no longer reports can be removed by hand."""
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    device = _device(hass)
    assert device is not None
    assert not await async_remove_config_entry_device(hass, entry, device)

    register_api(aioclient_mock, power_list={"code": 200, "data": []})
    await _poll(hass, freezer)
    assert await async_remove_config_entry_device(hass, entry, device)


async def test_empty_station_list(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An account without stations is valid (empty list, no error)."""
    aioclient_mock.get(URL_STATIONS, json={"code": 200, "data": {"rows": []}})
    client = _client(hass)
    client._token = "test-token"  # noqa: SLF001

    assert await client.get_stations() == []


# --- 7: plurals and location fields are redacted ---


@pytest.mark.parametrize(
    "key",
    [
        "deviceIds",
        "deviceNums",
        "userNames",
        "addresses",
        "province",
        "district",
        "region",
        "county",
        "town",
        "postCode",
        "postalCode",
        "gpsInfo",
    ],
)
def test_redact_plurals_and_location(key: str) -> None:
    """Plural field names and further location fields are anonymized."""
    assert is_sensitive(key)
    assert redact({key: "secret"}) == {key: REDACTED}


@pytest.mark.parametrize(
    "key", ["status", "genPowerTotals", "todayPowerTotals", "timeZone", "sort"]
)
def test_redact_keeps_measurements(key: str) -> None:
    """Plural handling does not hide measurement fields."""
    assert not is_sensitive(key)


# --- 9: inputs are matched by number, not list position ---


@pytest.mark.usefixtures("setup_integration")
async def test_panels_in_other_order(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Inputs reported as [2, 1] still show their own values."""
    data = load_fixture("device_data.json")
    data["data"]["devicePhotovoltaicPanel"].reverse()
    register_api(aioclient_mock, device_data=data)
    await _poll(hass, freezer)

    assert sensor_state(hass, f"{PANEL_1}_power").state == "260.0"
    assert sensor_state(hass, f"{PANEL_2}_power").state == "252.0"
