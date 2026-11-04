"""Config flow for the EasyPV integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .easy_pv import BaseError, EasyPVClient, LoginError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    hub = EasyPVClient(async_get_clientsession(hass))

    try:
        await hub.login_with_password(data[CONF_USERNAME], data[CONF_PASSWORD])
        user_info = await hub.get_user_info()
    except LoginError as err:
        raise InvalidAuth from err
    except BaseError as err:
        raise CannotConnect from err

    # Accounts registered with a phone number may have no email address, and
    # userName may be empty; fall back to the login name.
    email = user_info.get("email") or None
    title = user_info.get("userName") or email or data[CONF_USERNAME]
    return {
        "title": str(title),
        "token": hub.token,
        "email": email,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for EasyPV.

    Only the token is stored, never the password. When the token expires,
    the coordinator raises ConfigEntryAuthFailed and Home Assistant starts
    the reauth flow below, which asks for the credentials again.
    """

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Return the options flow."""
        return OptionsFlowHandler()

    async def _async_try_login(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ) -> dict[str, Any] | None:
        """Log in with the given credentials; fill errors and return None on failure."""
        try:
            return await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            info = await self._async_try_login(user_input, errors)
            if info is not None:
                await self.async_set_unique_id(_account_id(info))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=info)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, _entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after the token was rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the credentials again and store the new token."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            info = await self._async_try_login(user_input, errors)
            if info is not None:
                account_id = _account_id(info)
                if entry.unique_id is not None and entry.unique_id != account_id:
                    return self.async_abort(
                        reason="wrong_account",
                        description_placeholders={"account": entry.title},
                    )
                if entry.unique_id is None:
                    self.hass.config_entries.async_update_entry(
                        entry, unique_id=account_id
                    )
                return self.async_update_reload_and_abort(entry, data_updates=info)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            description_placeholders={"account": entry.title},
            errors=errors,
        )


class OptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Options for Easy PV (EW); the entry is reloaded after a change."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and store the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _account_id(info: dict[str, Any]) -> str:
    """Return a stable ID for the Easy PV account (used as unique_id)."""
    return str(info.get("email") or info["title"]).strip().lower()


class CannotConnect(HomeAssistantError):  # noqa: N818
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):  # noqa: N818
    """Error to indicate there is invalid auth."""
