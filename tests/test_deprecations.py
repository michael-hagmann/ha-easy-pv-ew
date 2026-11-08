"""Tests for HA deprecations (via_device, TrackerEntity.location_name)."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.easy_pv_ew.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

STATION = "1001"
DEVICE = "1001_2001"
PANELS = ("1001_2001_panel_1", "1001_2001_panel_2")


def _get(hass: HomeAssistant, entry: MockConfigEntry, ident: str) -> dr.DeviceEntry:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, ident), entry.entry_id
    )
    assert device is not None, ident
    return device


async def test_device_hierarchy_uses_via_device_id(
    hass: HomeAssistant,
    mock_api: object,
    config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Inverter links to the station, PV inputs to the inverter, without warning."""
    caplog.set_level(logging.WARNING)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    station = _get(hass, config_entry, STATION)
    device = _get(hass, config_entry, DEVICE)
    assert station.via_device_id is None
    assert device.via_device_id == station.id
    for panel in PANELS:
        assert _get(hass, config_entry, panel).via_device_id == device.id

    assert "via_device" not in caplog.text


async def test_device_info_survives_registration(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Pre-registering the hierarchy keeps the details from the entities."""
    device = _get(hass, setup_integration, DEVICE)
    assert device.manufacturer == "Electronic Way Technology"
    assert device.name
    assert _get(hass, setup_integration, STATION).name
    for panel in PANELS:
        assert _get(hass, setup_integration, panel).name

    # Every device carries entities, none is left empty.
    ent_reg = er.async_get(hass)
    for ident in (STATION, DEVICE, *PANELS):
        dev = _get(hass, setup_integration, ident)
        assert er.async_entries_for_device(ent_reg, dev.id)


def test_tracker_does_not_override_location_name(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Overriding TrackerEntity.location_name is unsupported from HA 2027.7."""
    module = importlib.import_module("custom_components.easy_pv_ew.device_tracker")
    assert "location_name" not in module.StationDeviceTracker.__dict__
    with caplog.at_level(logging.WARNING):
        importlib.reload(module)
    assert "location_name" not in caplog.text
