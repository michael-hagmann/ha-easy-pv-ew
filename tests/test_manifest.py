"""Smoke test: the integration can be found and its manifest is valid."""

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from custom_components.easy_pv_ew.const import DOMAIN


async def test_integration_is_loadable(hass: HomeAssistant) -> None:
    """Home Assistant finds the integration under its own domain."""
    integration = await async_get_integration(hass, DOMAIN)

    assert integration.domain == "easy_pv_ew"
    assert integration.name == "Easy PV (EW)"
    assert integration.config_flow is True
