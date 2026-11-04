"""Constants for the EasyPV integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "easy_pv_ew"
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.DEVICE_TRACKER,
]

# How long the last valid values are kept when the cloud cannot be reached.
# Short DNS or network hiccups must not make entities unavailable.
STALE_DATA_GRACE = timedelta(minutes=5)

# The lifetime energy never goes backwards: a lower value from the cloud is
# ignored. Only if the cloud keeps reporting a lower (non-zero) value for this
# long is it accepted as a real reset (e.g. counter reset by the manufacturer,
# corrected unit); otherwise the sensor would be stuck forever.
TOTAL_RESET_AFTER = timedelta(hours=6)

# Options
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 60  # seconds
# The manufacturer's servers must not be polled more often than every 60 s.
MIN_SCAN_INTERVAL = 60
# A failed poll one interval after the last success must still fall within
# STALE_DATA_GRACE, otherwise a single failure would already make all entities
# unavailable.
MAX_SCAN_INTERVAL = 240
