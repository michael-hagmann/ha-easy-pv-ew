"""Tests for token expiry and the reauth flow (Fehler 4)."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .conftest import (
    URL_LOGIN,
    URL_STATIONS,
    URL_USER_INFO,
    load_fixture,
    register_api,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

USER_INPUT = {CONF_USERNAME: "user", CONF_PASSWORD: "secret"}


def _reauth_flows(hass: HomeAssistant, entry: MockConfigEntry) -> list:
    return list(entry.async_get_active_flows(hass, {SOURCE_REAUTH}))


async def test_expired_token_at_startup_starts_reauth(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A token rejected during setup starts the reauth flow."""
    register_api(aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_USER_INFO, json=load_fixture("error_token.json"))

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    assert len(_reauth_flows(hass, config_entry)) == 1


async def test_expired_token_while_polling_starts_reauth(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A token rejected during polling starts reauth at once, not after 5 minutes."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_STATIONS, json=load_fixture("error_token.json"))

    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert len(_reauth_flows(hass, setup_integration)) == 1


async def test_reauth_success_stores_new_token(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Entering the credentials again stores the new token, not the password."""
    config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, "token": "old-token"}
    )
    register_api(aioclient_mock)

    result = await config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data["token"] == "test-token"
    assert CONF_PASSWORD not in config_entry.data
    assert config_entry.state is ConfigEntryState.LOADED


async def test_reauth_invalid_auth(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """A wrong password keeps the form open with an error."""
    config_entry.add_to_hass(hass)
    aioclient_mock.post(URL_LOGIN, json={"code": 500, "msg": "wrong password"})

    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_wrong_account(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Credentials of another account are rejected and nothing is changed."""
    config_entry.add_to_hass(hass)
    aioclient_mock.post(URL_LOGIN, json=load_fixture("login.json"))
    aioclient_mock.get(
        URL_USER_INFO,
        json={
            "code": 200,
            "msg": "success",
            "data": {"userName": "Anderes Konto", "email": "other@example.com"},
        },
    )

    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    assert config_entry.data["token"] == "test-token"


@pytest.mark.usefixtures("mock_api")
async def test_same_account_only_once(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """The same Easy PV account cannot be added twice."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        "easy_pv_ew", context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
