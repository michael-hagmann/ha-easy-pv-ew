"""Tests for cloud outages and the monotonic total energy (Fehler 6)."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import aiohttp
import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from custom_components.easy_pv_ew.const import DOMAIN
from custom_components.easy_pv_ew.coordinator import EasyPVCoordinator

from .conftest import URL_STATIONS, register_api, sensor_entity_id, sensor_state

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

POWER = "1001_2001_power"
TOTAL = "1001_energy_total"
POLL = timedelta(seconds=60)


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Advance time by one update interval and let the coordinator run."""
    freezer.tick(POLL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _cloud_down(aioclient_mock: AiohttpClientMocker) -> None:
    """Simulate a DNS failure for every request."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL_STATIONS, exc=aiohttp.ClientConnectionError("DNS failure"))


@pytest.mark.usefixtures("setup_integration")
async def test_short_outage_keeps_values(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Outages shorter than 5 minutes keep the last values."""
    _cloud_down(aioclient_mock)

    for _ in range(4):  # 4 failed polls = 4 minutes
        await _poll(hass, freezer)
        assert sensor_state(hass, POWER).state == "512.0"
        assert sensor_state(hass, TOTAL).state == "123.45"


@pytest.mark.usefixtures("setup_integration")
async def test_short_outage_logs_error_type(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The overall 20 s timeout has an empty message; log the error type."""
    caplog.set_level("DEBUG", logger="custom_components.easy_pv_ew")

    with patch.object(EasyPVCoordinator, "_fetch_stations", side_effect=TimeoutError):
        await _poll(hass, freezer)

    assert "keeping last values: TimeoutError: " in caplog.text


@pytest.mark.usefixtures("setup_integration")
async def test_long_outage_unavailable_then_recovers(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """After 5 minutes without data entities become unavailable, then recover."""
    _cloud_down(aioclient_mock)
    for _ in range(5):
        await _poll(hass, freezer)

    assert sensor_state(hass, POWER).state == STATE_UNAVAILABLE
    assert sensor_state(hass, TOTAL).state == STATE_UNAVAILABLE

    register_api(aioclient_mock, energy_total=124.0)
    await _poll(hass, freezer)

    assert sensor_state(hass, POWER).state == "512.0"
    assert sensor_state(hass, TOTAL).state == "124.0"


@pytest.mark.usefixtures("setup_integration")
async def test_grace_counts_from_last_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A successful poll in between restarts the 5 minutes."""
    _cloud_down(aioclient_mock)
    for _ in range(3):
        await _poll(hass, freezer)

    register_api(aioclient_mock)
    await _poll(hass, freezer)

    _cloud_down(aioclient_mock)
    for _ in range(4):
        await _poll(hass, freezer)

    assert sensor_state(hass, POWER).state == "512.0"


@pytest.mark.parametrize("lower", [0.0, 100.0, 123.44])
@pytest.mark.usefixtures("setup_integration")
async def test_total_never_decreases(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    lower: float,
) -> None:
    """A lower total from the cloud is ignored; higher values are taken over."""
    register_api(aioclient_mock, energy_total=lower)
    await _poll(hass, freezer)
    assert sensor_state(hass, TOTAL).state == "123.45"

    register_api(aioclient_mock, energy_total=125.5)
    await _poll(hass, freezer)
    assert sensor_state(hass, TOTAL).state == "125.5"


async def test_total_restored_after_restart(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_api: AiohttpClientMocker,
) -> None:
    """After a restart the total does not drop below the value before."""
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State("sensor.teststation_energy_total", "200.0"),
                {"native_value": 200.0, "native_unit_of_measurement": "kWh"},
            )
        ],
    )
    # Pre-register the entity ID so the restored state matches it.
    config_entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        TOTAL,
        suggested_object_id="teststation_energy_total",
        config_entry=config_entry,
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert sensor_entity_id(hass, TOTAL) == "sensor.teststation_energy_total"
    assert sensor_state(hass, TOTAL).state == "200.0"


@pytest.mark.usefixtures("setup_integration")
async def test_unavailable_reason_is_translated(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """After a long outage the coordinator reports a translatable error."""
    _cloud_down(aioclient_mock)
    for _ in range(5):
        await _poll(hass, freezer)

    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    err = coordinator.last_exception
    assert err.translation_domain == DOMAIN
    assert err.translation_key == "cannot_connect"
    assert "DNS failure" in err.translation_placeholders["error"]
