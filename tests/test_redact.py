"""Tests for anonymized logging of raw API responses (Fehler 5)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from custom_components.easy_pv_ew.easy_pv.redact import REDACTED, is_sensitive, redact

from .conftest import load_fixture

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.mark.parametrize(
    "key",
    [
        "id",
        "deviceId",
        "stationId",
        "powerId",
        "deviceNum",
        "sn",
        "deviceSN",
        "serial_number",
        "name",
        "stationName",
        "userName",
        "email",
        "address",
        "plantLocation",
        "latitude",
        "longitude",
        "macAddress",
        "wifiSsid",
        "phoneNumber",
        "token",
        "productCode",
        "customProductCode",
    ],
)
def test_sensitive_keys(key: str) -> None:
    """Identifying field names are recognized, also unknown variants."""
    assert is_sensitive(key)


@pytest.mark.parametrize(
    "key",
    [
        "genPower",
        "genPowerTotal",
        "genpowerTodayTotals",
        "genpowerMonthTotals",
        "powerTotals",
        "todayPowerTotals",
        "gridVoltage",
        "current",
        "voltage",
        "sort",
        "appFirmVer",
        "netFirmVer",
        "code",
        "msg",
        "devicePhotovoltaicPanel",
    ],
)
def test_measurement_keys_kept(key: str) -> None:
    """Measurements, units and firmware stay visible."""
    assert not is_sensitive(key)


def test_redact_nested() -> None:
    """Nested dicts and lists are anonymized, values kept otherwise."""
    data = load_fixture("device_data.json")
    result = redact(data)

    assert result["data"]["deviceNum"] == REDACTED
    assert result["data"]["genPower"] == 512.0
    assert result["data"]["devicePhotovoltaicPanel"][0]["voltage"] == 36.6
    assert data["data"]["deviceNum"] == "SN0000000000", "input must not change"


@pytest.mark.usefixtures("setup_integration")
async def test_debug_log_is_anonymized(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Raw responses appear in the debug log without identifying values."""
    caplog.clear()
    caplog.set_level(logging.DEBUG, logger="custom_components.easy_pv_ew")
    coordinator = hass.config_entries.async_entries("easy_pv_ew")[0].runtime_data
    await coordinator.async_refresh()

    log = caplog.text
    assert "getStationList" in log
    assert "getDeviceDataInfo" in log
    assert "123.45" in log, "lifetime total must be visible for step 6"
    for secret in (
        "1001",
        "2001",
        "SN0000000000",
        "Gartenhaus",
        "Musterstadt",
        "Musterstraße",
        "50.0",
        "test-token",
        "test@example.com",
        "Testkonto",
    ):
        assert secret not in log, f"{secret!r} leaked into the log"


def test_product_code_redacted() -> None:
    """Real product codes carry a device-specific suffix and are never shown."""
    data = load_fixture("device_data.json")
    data["data"]["productCode"] = "VN2T08EU-X000000"
    result = redact(data)

    assert result["data"]["productCode"] == REDACTED
    assert "X000000" not in str(result)
