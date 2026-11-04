"""Models for Easy PV integration."""

from dataclasses import dataclass


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
    power: float
    current: float
    voltage: float


@dataclass
class PVDevice(PVEntity):
    """Data class for a PV inverter."""

    id: str
    station_id: str
    power: float
    energy_month: float
    energy_today: float
    product_code: str
    device_serial: str
    grid_voltage: float
    app_fw: str
    net_fw: str

    panels: list[PVPanel]


@dataclass
class PVStation(PVEntity):
    """Data class for a PV station."""

    id: str
    name: str
    address: str
    location: str
    latitude: float
    longitude: float
    power: float
    energy_total: float
    energy_today: float

    devices: dict[str, PVDevice]
