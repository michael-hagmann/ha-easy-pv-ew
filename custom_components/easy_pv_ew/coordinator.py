"""Coordinator for EasyPV integration."""

import logging
from asyncio import timeout
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import STALE_DATA_GRACE
from .easy_pv import BaseError, EasyPVClient, LoginError
from .model import PVDevice, PVPanel, PVStation

LOGGER = logging.getLogger(__name__)


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
            update_interval=timedelta(seconds=60),
            always_update=True,
        )
        self._config_entry = config_entry
        self._client = EasyPVClient(async_get_clientsession(hass))
        self._last_success: datetime | None = None

    @property
    def is_logged_in(self) -> bool:
        """Check if the client is logged in."""
        return self._client.is_logged_in

    async def fetch_device(self, station_id: str, device_id: str) -> PVDevice:
        """Fetch a specific device by its ID."""
        data = await self._client.get_device_data(station_id, device_id)

        return PVDevice(
            entity_id=f"{station_id}_{device_id}",
            entity_name=data["productCode"],
            id=device_id,
            station_id=station_id,
            power=data["genPower"],
            energy_month=data["genpowerMonthTotals"],
            energy_today=data["genpowerTodayTotals"],
            product_code=data["productCode"],
            device_serial=data["deviceNum"],
            grid_voltage=data["gridVoltage"],
            app_fw=data["appFirmVer"],
            net_fw=data["netFirmVer"],
            panels=[
                PVPanel(
                    entity_id=f"{station_id}_{device_id}_panel_{panel_data['sort']}",
                    entity_name=f"{data['productCode']} Panel {panel_data['sort']}",
                    idx=int(panel_data["sort"]) - 1,
                    station_id=station_id,
                    device_id=device_id,
                    power=panel_data["genPower"],
                    current=panel_data["current"],
                    voltage=panel_data["voltage"],
                )
                for panel_data in data.get("devicePhotovoltaicPanel", [])
            ],
        )

    async def _fetch_devices(self, station_id: str) -> list[PVDevice]:
        """Fetch the list of devices for a given station."""
        data = await self._client.get_station_devices(station_id)
        return [await self.fetch_device(station_id, device["id"]) for device in data]

    async def _fetch_stations(self) -> list[PVStation]:
        """Fetch the list of PV stations from the API."""
        data = await self._client.get_stations()
        return [
            PVStation(
                entity_id=station["id"],
                entity_name=station["name"],
                id=station["id"],
                name=station["name"],
                address=station["address"],
                location=station["plantLocation"],
                latitude=station["latitude"],
                longitude=station["longitude"],
                power=station["genPower"],
                energy_today=station["todayPowerTotals"],
                energy_total=station["powerTotals"],
                devices={
                    device.id: device
                    for device in await self._fetch_devices(station["id"])
                },
            )
            for station in data
        ]

    async def _async_setup(self) -> None:
        try:
            await self._client.login_with_token(self._config_entry.data["token"])

        except LoginError as err:
            raise ConfigEntryAuthFailed from err
        except BaseError as err:
            raise UpdateFailed("Error communicating with API") from err

    async def _async_update_data(self) -> dict[str, PVStation]:
        """Fetch data from API endpoint."""
        try:
            async with timeout(20):
                data = {station.id: station for station in await self._fetch_stations()}

        except LoginError as err:
            raise ConfigEntryAuthFailed from err
        except (BaseError, TimeoutError) as err:
            if self._within_grace():
                # Short outage: keep the last valid values instead of making
                # every entity unavailable.
                LOGGER.debug("Update failed, keeping last values: %s", err)
                return self.data
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        self._last_success = dt_util.utcnow()
        return data

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
        return (
            device.panels[panel_number]
            if device and len(device.panels) > panel_number
            else None
        )
