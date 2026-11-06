"""
Counters around midnight, as seen in the night 05./06.11.2026 (UTC).

At 00:00 UTC (station time zone "+0") the cloud reported for about five
minutes the station total minus the day's energy and a month energy of 0,
then the old month value again and a station total 0.01 kWh below the value
before; it only rose again with the next yield in the morning.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.easy_pv_ew.const import TOTAL_LOWER_WARN_AFTER
from custom_components.easy_pv_ew.coordinator import _utc_offset

from .conftest import load_fixture, register_api, sensor_state

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

POLL = timedelta(seconds=60)
STATION_TOTAL = "1001_energy_total"
MONTH = "1001_2001_energy_month"
SENSOR_LOGGER = "custom_components.easy_pv_ew.sensor"


async def _poll(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, interval: timedelta = POLL
) -> None:
    freezer.tick(interval)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def _at(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, when: datetime
) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _register(
    aioclient_mock: AiohttpClientMocker,
    *,
    month: float = 8.5,
    time_zone: str = "+0",
    **kwargs: Any,
) -> None:
    stations = load_fixture("station_list.json")
    stations["data"]["rows"][0]["timeZone"] = time_zone
    data = load_fixture("device_data.json")
    data["data"]["genpowerMonthTotals"] = month
    register_api(aioclient_mock, stations=stations, device_data=data, **kwargs)


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == SENSOR_LOGGER and record.levelno >= logging.WARNING
    ]


# --- Gesamtzähler der Station: kleinere Werte nie übernehmen ---


@pytest.mark.usefixtures("setup_integration")
async def test_station_total_midnight_dip_is_never_taken_over(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Dip at midnight and 0.01 below until morning: value kept, no warning."""
    _register(aioclient_mock, energy_total=122.92)  # minus the day's energy
    await _poll(hass, freezer)
    assert sensor_state(hass, STATION_TOTAL).state == "123.45"

    _register(aioclient_mock, energy_total=123.44)  # 0.01 below until morning
    await _poll(hass, freezer, timedelta(minutes=5))
    await _poll(hass, freezer, timedelta(hours=7))  # the 6-hour rule is gone
    assert sensor_state(hass, STATION_TOTAL).state == "123.45"
    assert _warnings(caplog) == []

    _register(aioclient_mock, energy_total=123.46)  # next yield
    await _poll(hass, freezer)
    assert sensor_state(hass, STATION_TOTAL).state == "123.46"


@pytest.mark.usefixtures("setup_integration")
async def test_station_total_lasting_lower_value_warns_once(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A lower value lasting a day is logged once, but still not taken over."""
    _register(aioclient_mock, energy_total=50.0)
    await _poll(hass, freezer)
    await _poll(hass, freezer, TOTAL_LOWER_WARN_AFTER - POLL)
    assert _warnings(caplog) == []

    await _poll(hass, freezer)
    await _poll(hass, freezer)
    assert len(_warnings(caplog)) == 1
    assert "not taken over" in _warnings(caplog)[0]
    assert sensor_state(hass, STATION_TOTAL).state == "123.45"


# --- Ertrag Monat: kleinere Werte nur beim Monatswechsel ---


@pytest.mark.usefixtures("setup_integration")
async def test_month_zero_at_midnight_is_ignored(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Mid-month the brief 0 at midnight does not reset the month energy."""
    await _at(hass, freezer, datetime(2026, 11, 5, 23, 59, tzinfo=UTC))
    _register(aioclient_mock, month=8.5)
    await _poll(hass, freezer)

    _register(aioclient_mock, month=0.0)
    await _poll(hass, freezer)
    assert sensor_state(hass, MONTH).state == "8.5"

    _register(aioclient_mock, month=8.5)
    await _poll(hass, freezer, timedelta(minutes=5))
    assert sensor_state(hass, MONTH).state == "8.5"


@pytest.mark.usefixtures("setup_integration")
async def test_month_reset_on_first_day(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """On the 1st (station time zone) the cloud's reset to 0 is taken over."""
    await _at(hass, freezer, datetime(2026, 11, 30, 23, 59, tzinfo=UTC))
    _register(aioclient_mock, month=12.3)
    await _poll(hass, freezer)

    _register(aioclient_mock, month=0.0)
    await _poll(hass, freezer)
    assert sensor_state(hass, MONTH).state == "0.0"

    # The midnight glitch may show the old value again; on the 1st the next
    # lower value is still taken over.
    _register(aioclient_mock, month=12.3)
    await _poll(hass, freezer)
    _register(aioclient_mock, month=0.01)
    await _poll(hass, freezer)
    assert sensor_state(hass, MONTH).state == "0.01"


@pytest.mark.usefixtures("setup_integration")
async def test_month_reset_uses_station_time_zone(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """With "+1" the month starts at 23:00 UTC, with "+0" not yet."""
    await _at(hass, freezer, datetime(2026, 11, 30, 22, 0, tzinfo=UTC))
    _register(aioclient_mock, month=12.3, time_zone="+0")
    await _poll(hass, freezer)

    await _at(hass, freezer, datetime(2026, 11, 30, 23, 30, tzinfo=UTC))
    _register(aioclient_mock, month=0.0, time_zone="+0")
    await _poll(hass, freezer)
    assert sensor_state(hass, MONTH).state == "12.3"

    _register(aioclient_mock, month=0.0, time_zone="+1")
    await _poll(hass, freezer)
    assert sensor_state(hass, MONTH).state == "0.0"


@pytest.mark.usefixtures("setup_integration")
async def test_month_reset_after_missed_first_day(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Without data on the 1st, a lower value in a new month is taken over."""
    await _at(hass, freezer, datetime(2026, 11, 30, 12, 0, tzinfo=UTC))
    _register(aioclient_mock, month=12.3)
    await _poll(hass, freezer)

    # Home Assistant was not running on the 1st: the next poll already gets
    # the new month's value.
    _register(aioclient_mock, month=1.2)
    await _at(hass, freezer, datetime(2026, 12, 2, 12, 0, tzinfo=UTC))
    await _poll(hass, freezer)
    assert sensor_state(hass, MONTH).state == "1.2"


# --- Zeitzone der Station ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("+0", timedelta()),
        ("+1", timedelta(hours=1)),
        ("1", timedelta(hours=1)),
        (2, timedelta(hours=2)),
        ("-5", timedelta(hours=-5)),
        ("+5:30", timedelta(hours=5, minutes=30)),
        ("-0930", timedelta(hours=-9, minutes=-30)),
        ("", None),
        (None, None),
        (True, None),
        ("Europe/Berlin", None),
        ("+15", None),
    ],
)
def test_utc_offset(value: object, expected: timedelta | None) -> None:
    """The station time zone is parsed leniently; anything else is None."""
    assert _utc_offset(value) == expected
