"""Models for Easy PV integration."""

from dataclasses import dataclass

# Values of `status` in getStationList and getDeviceDataInfo.
STATUS_ONLINE = 1
STATUS_OFFLINE = 2
STATUS_FAULT = 3  # device; for a station 3 means "connecting"


@dataclass
class PVEntity:
    """Base Data class for a PV entities."""

    entity_id: str
    entity_name: str


@dataclass
class PVPanel(PVEntity):
    """Data class for a PV panel."""

    idx: int
    station_id: str
    device_id: str
    power: float | None
    current: float | None
    voltage: float | None
    energy_total: float | None  # kWh
    temperature: float | None
    frequency: float | None


@dataclass
class PVDevice(PVEntity):
    """Data class for a PV inverter."""

    id: str
    station_id: str
    power: float | None
    energy_month: float | None  # kWh
    energy_today: float | None  # kWh
    energy_total: float | None  # kWh
    status: int | None
    product_code: str
    device_serial: str | None
    grid_voltage: float | None
    app_fw: str | None
    net_fw: str | None

    panels: list[PVPanel]

    @property
    def is_online(self) -> bool:
        """Return False if the cloud reports the inverter offline or faulty."""
        return self.status is None or self.status == STATUS_ONLINE


@dataclass
class PVStation(PVEntity):
    """Data class for a PV station."""

    id: str
    name: str
    address: str
    location: str
    latitude: float | None
    longitude: float | None
    power: float | None
    energy_total: float | None
    energy_today: float | None
    status: int | None

    devices: dict[str, PVDevice]

    @property
    def is_online(self) -> bool:
        """Return False if the cloud reports the station offline."""
        return self.status is None or self.status == STATUS_ONLINE
