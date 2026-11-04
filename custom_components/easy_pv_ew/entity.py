"""Entity representations for the Easy PV integration."""

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EasyPVCoordinator
from .model import PVDevice, PVEntity, PVPanel, PVStation


class EasyPVEntity[T](CoordinatorEntity[EasyPVCoordinator]):
    """Base representation of an Easy PV entity."""

    def __init__(self, coordinator: EasyPVCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

    @property
    def _data(self) -> T | None:
        raise NotImplementedError("_data not implemented in subclasses")

    @property
    def _id(self) -> str | None:
        return self._data.entity_id if isinstance(self._data, PVEntity) else None

    @property
    def _name(self) -> str | None:
        return self._data.entity_name if isinstance(self._data, PVEntity) else None

    @property
    def _device_info(self) -> DeviceInfo | None:
        return DeviceInfo()

    @property
    def device_info(self) -> DeviceInfo | None:  # type: ignore[override]
        """Return information to link this entity with the correct device."""
        device_info = self._device_info
        if device_info is not None and self._id is not None:
            device_info["identifiers"] = {(DOMAIN, self._id)}

        if device_info is not None and self._name is not None:
            device_info["name"] = self._name

        return device_info

    @property
    def available(self) -> bool:  # type: ignore[override]
        """
        Return True if the last update succeeded and data for this entity exists.

        The coordinator bridges short cloud outages itself (STALE_DATA_GRACE),
        so a failed update here means the outage lasted longer.
        """
        return (
            super().available
            and self.coordinator.is_logged_in
            and self._data is not None
        )

    def _handle_update(self) -> None:
        pass

    @callback
    def _handle_coordinator_update(self) -> None:
        self._handle_update()
        self.async_write_ha_state()


class EasyPVStationEntity(EasyPVEntity[PVStation]):
    """Representation of a PV station entity."""

    @property
    def _data(self) -> PVStation | None:
        return self.coordinator.get_station(self._station_id)

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._station_id = station_id

        super().__init__(coordinator)


class EasyPVDeviceEntity(EasyPVEntity[PVDevice]):
    """Representation of a PV device entity."""

    @property
    def _data(self) -> PVDevice | None:
        return self.coordinator.get_device(self._station_id, self._device_id)

    @property
    def _device_info(self) -> DeviceInfo | None:
        if not self._data:
            return None

        return DeviceInfo(
            manufacturer="Electronic Way Technology",
            model=self._data.product_code,
            serial_number=self._data.device_serial,
            sw_version=self._data.app_fw,
            via_device=(DOMAIN, self._station_id),
        )

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._station_id = station_id
        self._device_id = device_id

        super().__init__(coordinator)


class EasyPVPanelEntity(EasyPVEntity[PVPanel]):
    """Representation of a PV panel entity."""

    @property
    def _data(self) -> PVPanel | None:
        return self.coordinator.get_panel(
            self._station_id, self._device_id, self._panel_number
        )

    @property
    def _device_info(self) -> DeviceInfo | None:
        if not self._data:
            return None

        parent = self.coordinator.get_device(self._station_id, self._device_id)

        return (
            DeviceInfo(
                translation_key="panel",
                translation_placeholders={
                    "connected_inverter": parent.entity_name if parent else "",
                    "panel_number": str(self._panel_number + 1),
                },
                via_device=(DOMAIN, f"{self._station_id}_{self._device_id}"),
            )
            if self._data
            else None
        )

    def __init__(
        self,
        coordinator: EasyPVCoordinator,
        station_id: str,
        device_id: str,
        panel_number: int,
    ) -> None:
        """Initialize the sensor."""
        self._station_id = station_id
        self._device_id = device_id
        self._panel_number = panel_number

        super().__init__(coordinator)
