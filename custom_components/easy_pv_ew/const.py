"""Constants for the EasyPV integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "easy_pv_ew"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]

# How long the last valid values are kept when the cloud cannot be reached.
# Short DNS or network hiccups must not make entities unavailable.
STALE_DATA_GRACE = timedelta(minutes=5)
