"""Constants for the EasyPV integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "easy_pv_ew"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]

# How long the last valid values are kept when the cloud cannot be reached.
# Short DNS or network hiccups must not make entities unavailable.
STALE_DATA_GRACE = timedelta(minutes=5)

# Options
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 60  # seconds
# Upper limit stays below STALE_DATA_GRACE, otherwise a single failed poll
# would already make all entities unavailable.
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 300
