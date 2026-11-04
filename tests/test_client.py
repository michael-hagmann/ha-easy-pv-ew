"""Tests for the Easy PV API client."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp
import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.easy_pv_ew.easy_pv import (
    ApiError,
    CommunicationError,
    EasyPVClient,
    InvalidResponseError,
    LoginError,
)

from .conftest import (
    URL_DEVICE_DATA,
    URL_LOGIN,
    URL_STATIONS,
    URL_USER_INFO,
    load_fixture,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )


def _client(hass: HomeAssistant) -> EasyPVClient:
    return EasyPVClient(async_get_clientsession(hass))


async def test_login_with_password(
    hass: HomeAssistant, mock_api: AiohttpClientMocker
) -> None:
    """A successful login stores the token and sends the credentials."""
    client = _client(hass)
    await client.login_with_password("user", "secret")

    assert client.token == "test-token"
    assert client.is_logged_in
    _, _, body, headers = mock_api.mock_calls[0]
    assert body == {"num": "user", "password": "secret"}
    assert "Authorization" not in headers


async def test_login_rejected(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A login with wrong credentials raises LoginError."""
    aioclient_mock.post(URL_LOGIN, json={"code": 500, "msg": "wrong password"})
    client = _client(hass)

    with pytest.raises(LoginError):
        await client.login_with_password("user", "wrong")
    assert not client.is_logged_in


async def test_requests_use_bearer_token(
    hass: HomeAssistant, mock_api: AiohttpClientMocker
) -> None:
    """Authenticated requests send the token and the query parameters."""
    client = _client(hass)
    await client.login_with_token("test-token")
    stations = await client.get_stations()
    device = await client.get_device_data("1001", "2001", "2026-11")

    assert stations[0]["powerTotals"] == 123.45
    assert device["genPower"] == 512.0
    _, url, _, headers = mock_api.mock_calls[-1]
    assert headers["Authorization"] == "Bearer test-token"
    assert url.query == {"deviceId": "2001", "stationId": "1001", "date": "2026-11"}


async def test_login_with_token_rejected(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An expired token raises LoginError and clears the token."""
    aioclient_mock.get(URL_USER_INFO, json=load_fixture("error_token.json"))
    client = _client(hass)

    with pytest.raises(LoginError):
        await client.login_with_token("old-token")
    assert not client.is_logged_in


async def test_api_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An error code in the body raises ApiError."""
    aioclient_mock.get(URL_STATIONS, json={"code": 500, "msg": "server error"})

    with pytest.raises(ApiError):
        await _client(hass).get_stations()


async def test_http_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A non-200 HTTP status raises InvalidResponseError."""
    aioclient_mock.get(URL_DEVICE_DATA, status=502)

    with pytest.raises(InvalidResponseError):
        await _client(hass).get_device_data("1001", "2001")


@pytest.mark.parametrize(
    "exc", [aiohttp.ClientConnectionError("DNS failure"), TimeoutError()]
)
async def test_network_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, exc: Exception
) -> None:
    """Network and DNS failures raise CommunicationError."""
    aioclient_mock.get(URL_STATIONS, exc=exc)

    with pytest.raises(CommunicationError):
        await _client(hass).get_stations()


async def test_shared_session(
    hass: HomeAssistant, mock_api: AiohttpClientMocker
) -> None:
    """The client reuses the session it was given instead of creating new ones."""
    session = async_get_clientsession(hass)
    client = EasyPVClient(session)
    await client.login_with_token("test-token")
    await client.get_stations()

    assert not session.closed
    assert client._session is session  # noqa: SLF001
