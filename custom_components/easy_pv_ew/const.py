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
# Short network hiccups must not make entities unavailable.
STALE_DATA_GRACE = timedelta(minutes=5)

# The lifetime energy never goes backwards: a lower value from the cloud is
# ignored. The station total is never reset (it keeps counting when the
# inverter is registered again); every night around midnight the cloud reports
# it briefly lower and then 0.01 kWh below the previous value until the next
# yield. A warning is logged only if the lower value lasts this long.
TOTAL_LOWER_WARN_AFTER = timedelta(days=1)
# The inverter total really falls to 0 when the inverter is registered again
# in the app. A lower (non-zero) value that the cloud keeps reporting for this
# long is accepted as such a reset; otherwise the sensor would be stuck. A full
# day, so that the nightly switch-off of the inverter (up to about 16 hours
# in winter) and the dip around midnight are never taken for a reset.
TOTAL_RESET_AFTER = timedelta(hours=24)

# Options
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 60  # seconds
# The manufacturer's servers must not be polled more often than every 60 s.
MIN_SCAN_INTERVAL = 60
# A failed poll one interval after the last success must still fall within
# STALE_DATA_GRACE, otherwise a single failure would already make all entities
# unavailable.
MAX_SCAN_INTERVAL = 240
