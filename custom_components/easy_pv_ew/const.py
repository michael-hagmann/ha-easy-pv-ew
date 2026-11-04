"""Constants for the EasyPV integration."""

from homeassistant.const import Platform

DOMAIN = "easy_pv_ew"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]
