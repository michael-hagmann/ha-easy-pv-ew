"""Coordinator for EasyPV integration."""

import logging
import math
from asyncio import timeout
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    STALE_DATA_GRACE,
)
from .easy_pv import BaseError, EasyPVClient, InvalidResponseError, LoginError
from .easy_pv.validate import ResponseValidator
from .model import PVDevice, PVPanel, PVStation

LOGGER = logging.getLogger(__name__)

# getDeviceDataInfo reports energy in Wh according to the OpenAPI description
# (the MQTT telegram of the device uses kWh). Verify with real data.
WH_PER_KWH = 1000


class EasyPVCoordinator(DataUpdateCoordinator[dict[str, PVStation]]):
    """My custom coordinator."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry[EasyPVCoordinator]
    ) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name="EasyPV Coordinator",
            config_entry=config_entry,
            update_interval=timedelta(
                seconds=config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            ),
            always_update=True,
        )
        self._config_entry = config_entry
        self._client = EasyPVClient(async_get_clientsession(hass))
        self._last_success: datetime | None = None
        # Raw API responses of the last successful update, for diagnostics.
        self.raw_data: dict[str, Any] = {}
        self._raw_pending: dict[str, Any] = {}
        # Checks every response; logs each problem once per start.
        self._validator = ResponseValidator()

    @property
    def is_logged_in(self) -> bool:
        """Check if the client is logged in."""
        return self._client.is_logged_in

    async def fetch_device(self, station_id: str, device_id: str) -> PVDevice:
        """Fetch a specific device by its ID."""
        data = await self._client.get_device_data(station_id, device_id)
        # Lists, not dicts keyed by ID: redact() works on field names only.
        self._raw_pending.setdefault("device_data", []).append(data)
        data = self._validator.sanitize("device_data", data)
        try:
            return _parse_device(station_id, device_id, data)
        except (KeyError, TypeError, ValueError, AttributeError) as err:
            raise InvalidResponseError from err

    async def _fetch_devices(self, station_id: str) -> list[PVDevice]:
        """Fetch the list of devices for a given station."""
        data = await self._client.get_station_devices(station_id)
        self._raw_pending.setdefault("station_devices", []).append(data)
        data = self._validator.sanitize("device_list", data)
        try:
            device_ids = [str(device["id"]) for device in data]
        except (KeyError, TypeError) as err:
            raise InvalidResponseError from err
        return [
            await self.fetch_device(station_id, device_id) for device_id in device_ids
        ]

    async def _fetch_stations(self) -> list[PVStation]:
        """Fetch the list of PV stations from the API."""
        data = await self._client.get_stations()
        self._raw_pending["stations"] = data
        data = self._validator.sanitize("station_list", data)
        stations = []
        for station in data:
            try:
                parsed = _parse_station(station)
            except (KeyError, TypeError, ValueError, AttributeError) as err:
                raise InvalidResponseError from err
            parsed.devices = {
                device.id: device for device in await self._fetch_devices(parsed.id)
            }
            stations.append(parsed)
        return stations

    async def _async_setup(self) -> None:
        try:
            await self._client.login_with_token(self._config_entry.data["token"])

        except LoginError as err:
            raise _auth_failed() from err
        except (BaseError, TimeoutError) as err:
            raise _cannot_connect(err) from err

    async def _async_update_data(self) -> dict[str, PVStation]:
        """Fetch data from API endpoint."""
        self._raw_pending = {}
        try:
            async with timeout(20):
                data = {station.id: station for station in await self._fetch_stations()}

        except LoginError as err:
            raise _auth_failed() from err
        except (BaseError, TimeoutError) as err:
            if self._within_grace():
                # Short outage: keep the last valid values instead of making
                # every entity unavailable.
                LOGGER.debug("Update failed, keeping last values: %s", err)
                return self.data
            raise _cannot_connect(err) from err

        self._last_success = dt_util.utcnow()
        self.raw_data = self._raw_pending
        return data

    @property
    def last_success(self) -> datetime | None:
        """Return the time of the last successful update."""
        return self._last_success

    def _within_grace(self) -> bool:
        """Return True if the last successful update is recent enough to reuse."""
        return (
            self.data is not None
            and self._last_success is not None
            and dt_util.utcnow() - self._last_success < STALE_DATA_GRACE
        )

    def enumerate_devices(self) -> set[str]:
        """Enumerate all devices across all stations."""
        devices: set[str] = set()
        for station in self.data.values():
            devices.add(station.entity_id)
            for station_device in station.devices.values():
                devices.add(station_device.entity_id)
                for panel in station_device.panels or []:
                    devices.add(panel.entity_id)

        return devices

    def get_station(self, station_id: str) -> PVStation | None:
        """Get a specific station by its ID."""
        return self.data.get(station_id, None)

    def get_device(self, station_id: str, device_id: str) -> PVDevice | None:
        """Get a specific device by its ID."""
        station = self.get_station(station_id)
        return station.devices.get(device_id, None) if station else None

    def get_panel(
        self, station_id: str, device_id: str, panel_number: int
    ) -> PVPanel | None:
        """Get a specific panel by its index."""
        device = self.get_device(station_id, device_id)
        if device is None:
            return None
        # Look up by input number, not list position: the order is not fixed.
        return next(
            (panel for panel in device.panels if panel.idx == panel_number), None
        )


def _auth_failed() -> ConfigEntryAuthFailed:
    return ConfigEntryAuthFailed(
        translation_domain=DOMAIN, translation_key="auth_failed"
    )


def _cannot_connect(err: Exception) -> UpdateFailed:
    return UpdateFailed(
        translation_domain=DOMAIN,
        translation_key="cannot_connect",
        translation_placeholders={"error": str(err) or type(err).__name__},
    )


def _parse_station(station: dict[str, Any]) -> PVStation:
    """Build a station from getStationList; devices are added by the caller."""
    station_id = str(station["id"])
    name = str(station.get("name") or station_id)
    return PVStation(
        entity_id=station_id,
        entity_name=name,
        id=station_id,
        name=name,
        address=station.get("address") or "",
        location=station.get("plantLocation") or "",
        latitude=_number(station.get("latitude")),
        longitude=_number(station.get("longitude")),
        power=_number(station.get("genPower")),
        energy_today=_number(station.get("todayPowerTotals")),
        energy_total=_number(station.get("powerTotals")),
        status=_status(station.get("status")),
        devices={},
    )


def _parse_device(station_id: str, device_id: str, data: dict[str, Any]) -> PVDevice:
    """
    Build a device from getDeviceDataInfo.

    Only the IDs and the input numbers are required. Missing measurements
    (e.g. while the inverter is offline at night) become None.
    """
    product_code = str(data.get("productCode") or "Inverter")
    return PVDevice(
        entity_id=f"{station_id}_{device_id}",
        entity_name=product_code,
        id=device_id,
        station_id=station_id,
        power=_number(data.get("genPower")),
        energy_month=_wh_to_kwh(data.get("genpowerMonthTotals")),
        energy_today=_wh_to_kwh(data.get("genpowerTodayTotals")),
        energy_total=_wh_to_kwh(data.get("genPowerTotal")),
        status=_status(data.get("status")),
        product_code=product_code,
        device_serial=_text(data.get("deviceNum")),
        grid_voltage=_number(data.get("gridVoltage")),
        app_fw=_text(data.get("appFirmVer")),
        net_fw=_text(data.get("netFirmVer")),
        panels=[
            _parse_panel(station_id, device_id, product_code, panel_data)
            for panel_data in data.get("devicePhotovoltaicPanel") or []
        ],
    )


def _parse_panel(
    station_id: str, device_id: str, product_code: str, panel_data: dict[str, Any]
) -> PVPanel:
    """Build one PV input of a device."""
    sort = int(panel_data["sort"])
    return PVPanel(
        entity_id=f"{station_id}_{device_id}_panel_{sort}",
        entity_name=f"{product_code} Panel {sort}",
        idx=sort - 1,
        station_id=station_id,
        device_id=device_id,
        power=_number(panel_data.get("genPower")),
        current=_number(panel_data.get("current")),
        voltage=_number(panel_data.get("voltage")),
        energy_total=_wh_to_kwh(panel_data.get("genpowerTotals")),
        temperature=_number(panel_data.get("temp")),
        frequency=_number(panel_data.get("freq")),
    )


def _text(value: Any) -> str | None:
    """Return value as string, or None if missing."""
    return None if value in (None, "") else str(value)


def _number(value: Any) -> float | None:
    """Return value as float, or None if missing or not a finite number."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except TypeError, ValueError:
        return None
    return number if math.isfinite(number) else None


def _wh_to_kwh(value: Any) -> float | None:
    """Convert an energy value in Wh from the cloud to kWh."""
    number = _number(value)
    return None if number is None else number / WH_PER_KWH


def _status(value: Any) -> int | None:
    """Return the status code, or None if missing or not a number."""
    number = _number(value)
    return None if number is None else int(number)
