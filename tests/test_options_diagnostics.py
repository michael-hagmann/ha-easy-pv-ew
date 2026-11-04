"""Tests for the options flow and the diagnostics download."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
import voluptuous as vol
from homeassistant.data_entry_flow import FlowResultType

from custom_components.easy_pv_ew.const import CONF_SCAN_INTERVAL
from custom_components.easy_pv_ew.diagnostics import (
    async_get_config_entry_diagnostics,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_scan_interval_option(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The polling interval can be changed and is used after the reload."""
    assert setup_integration.runtime_data.update_interval == timedelta(seconds=60)

    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 120}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_integration.options[CONF_SCAN_INTERVAL] == 120
    assert setup_integration.runtime_data.update_interval == timedelta(seconds=120)


@pytest.mark.parametrize("value", [10, 600])
async def test_scan_interval_limits(
    hass: HomeAssistant, setup_integration: MockConfigEntry, value: int
) -> None:
    """Intervals outside 30-300 seconds are rejected."""
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)

    with pytest.raises(vol.Invalid):
        await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: value}
        )


async def test_diagnostics_anonymized(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Diagnostics contain the raw responses without identifying values."""
    diagnostics = await async_get_config_entry_diagnostics(hass, setup_integration)
    dump = json.dumps(diagnostics, ensure_ascii=False)

    raw = diagnostics["raw_data"]
    assert raw["stations"][0]["powerTotals"] == 123.45
    assert raw["device_data"][0]["genpowerMonthTotals"] == 8.5
    assert diagnostics["coordinator"]["last_update_success"] is True
    for secret in (
        "1001",
        "2001",
        "SN0000000000",
        "Gartenhaus",
        "Musterstadt",
        "Musterstraße",
        "test-token",
        "test@example.com",
        "Testkonto",
    ):
        assert secret not in dump, f"{secret!r} leaked into diagnostics"
