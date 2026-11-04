"""Tests for the Easy PV (EW) config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.easy_pv_ew.const import DOMAIN

from .conftest import URL_LOGIN, URL_USER_INFO, load_fixture

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

USER_INPUT = {CONF_USERNAME: "user", CONF_PASSWORD: "secret"}


async def _start(hass: HomeAssistant) -> str:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return result["flow_id"]


async def test_user_flow_success(
    hass: HomeAssistant, mock_api: AiohttpClientMocker
) -> None:
    """Valid credentials create an entry that stores only the token."""
    flow_id = await _start(hass)
    result = await hass.config_entries.flow.async_configure(flow_id, USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Testkonto"
    assert result["data"]["token"] == "test-token"
    assert CONF_PASSWORD not in result["data"]


async def test_user_flow_invalid_auth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Wrong credentials show invalid_auth."""
    aioclient_mock.post(URL_LOGIN, json={"code": 500, "msg": "wrong password"})
    flow_id = await _start(hass)
    result = await hass.config_entries.flow.async_configure(flow_id, USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Network failures show cannot_connect."""
    aioclient_mock.post(URL_LOGIN, exc=aiohttp.ClientConnectionError())
    flow_id = await _start(hass)
    result = await hass.config_entries.flow.async_configure(flow_id, USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_recovers_after_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """After a failed attempt the user can retry successfully."""
    aioclient_mock.post(URL_LOGIN, exc=aiohttp.ClientConnectionError())
    flow_id = await _start(hass)
    await hass.config_entries.flow.async_configure(flow_id, USER_INPUT)

    aioclient_mock.clear_requests()
    aioclient_mock.post(URL_LOGIN, json=load_fixture("login.json"))
    aioclient_mock.get(URL_USER_INFO, json=load_fixture("user_info.json"))
    result = await hass.config_entries.flow.async_configure(flow_id, USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
