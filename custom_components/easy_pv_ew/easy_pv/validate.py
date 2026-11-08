"""
Check Easy PV API responses against the expected fields at runtime.

Mirrors the response fields of tests/api_contract.yaml (the contract is not
shipped with the integration; tests/test_validate.py keeps both in sync).
Paths are relative to what the client returns: the station rows, the device
list and the device data object. "[]" stands for every element of a list.

An invalid value (wrong type that cannot be read, outside the plausible
range) is replaced by None, so the affected entity becomes unavailable
instead of showing a wrong value. Each problem is logged once per field and
start of the integration, not on every update.
"""

from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass
from typing import Any

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Field:
    """Expected type and plausible range of one response field."""

    type: str  # "string", "number" or "array"
    optional: bool = True
    min: float | None = None
    max: float | None = None
    # Measurements may be logged with their value; identifiers never.
    loggable: bool = False


def _measurement(low: float, high: float) -> Field:
    return Field("number", min=low, max=high, loggable=True)


STATION_LIST: dict[str, Field] = {
    "[].id": Field("string", optional=False),
    "[].name": Field("string"),
    "[].address": Field("string"),
    "[].plantLocation": Field("string"),
    "[].latitude": Field("string"),
    "[].longitude": Field("string"),
    "[].genPower": _measurement(0, 100_000),
    "[].todayPowerTotals": _measurement(0, 10_000),
    "[].powerTotals": _measurement(0, 10_000_000),
    "[].status": Field("string", loggable=True),
    "[].timeZone": Field("string"),
}

DEVICE_LIST: dict[str, Field] = {
    "[].id": Field("string", optional=False),
}

DEVICE_DATA: dict[str, Field] = {
    # May contain a device-specific suffix (e.g. VN2T08EU-<code>), never log.
    "productCode": Field("string"),
    "deviceNum": Field("string"),
    "status": Field("string", loggable=True),
    "genPower": _measurement(0, 5_000),
    "genPowerTotal": _measurement(0, 1_000_000),
    "genpowerTodayTotals": _measurement(0, 100),
    "genpowerMonthTotals": _measurement(0, 3_000),
    "gridVoltage": _measurement(0, 300),
    "appFirmVer": Field("string", loggable=True),
    "netFirmVer": Field("string", loggable=True),
    "devicePhotovoltaicPanel": Field("array"),
    "devicePhotovoltaicPanel[].sort": Field("string", optional=False, loggable=True),
    "devicePhotovoltaicPanel[].genPower": _measurement(0, 2_000),
    "devicePhotovoltaicPanel[].current": _measurement(0, 30),
    "devicePhotovoltaicPanel[].voltage": _measurement(0, 100),
    "devicePhotovoltaicPanel[].freq": _measurement(0, 70),
    "devicePhotovoltaicPanel[].temp": _measurement(-40, 120),
}

EXPECTED: dict[str, dict[str, Field]] = {
    "station_list": STATION_LIST,
    "device_list": DEVICE_LIST,
    "device_data": DEVICE_DATA,
}


class ResponseValidator:
    """Validates responses and remembers which problems were already logged."""

    def __init__(self) -> None:
        """Initialize with an empty set of logged problems."""
        self._warned: set[tuple[str, str, str]] = set()

    def sanitize(self, endpoint: str, data: Any) -> Any:
        """
        Return a copy of data with invalid values replaced by None.

        Missing required fields are only logged here; the parser then raises
        InvalidResponseError, which the coordinator bridges like an outage.
        """
        result = copy.deepcopy(data)
        for path, expected in EXPECTED[endpoint].items():
            *parents, name = path.split(".")
            for container in _containers(result, parents):
                self._check(endpoint, path, expected, container, name)
        return result

    def _check(
        self,
        endpoint: str,
        path: str,
        expected: Field,
        container: dict[str, Any],
        name: str,
    ) -> None:
        if name not in container or container[name] is None:
            if not expected.optional:
                self._warn(endpoint, path, "missing", "required field is missing")
            return

        value = container[name]
        problem, fixed = _validate(expected, value)
        if problem is None:
            return
        if expected.loggable:
            problem = f"{problem} (value {value!r})"
        if fixed is None:
            self._warn(endpoint, path, "invalid", f"{problem}; value ignored")
        else:
            self._warn(endpoint, path, "type", f"{problem}; value used")
        container[name] = fixed

    def _warn(self, endpoint: str, path: str, kind: str, text: str) -> None:
        key = (endpoint, path, kind)
        if key in self._warned:
            return
        self._warned.add(key)
        LOG.warning(
            "Unexpected Easy PV API response (%s, field %s): %s. "
            "The cloud API may have changed; please report this",
            endpoint,
            path,
            text,
        )


def _validate(expected: Field, value: Any) -> tuple[str | None, Any]:
    """
    Check one value.

    Returns (problem, value to use). problem is None if the value is fine; a
    value to use other than None means the value is readable despite the
    unexpected type (e.g. a number sent as string).
    """
    if expected.type == "array":
        return _validate_list(value)
    if expected.type == "string":
        return _validate_string(value)
    return _validate_number(expected, value)


def _validate_list(value: Any) -> tuple[str | None, Any]:
    if isinstance(value, list):
        return None, value
    return f"expected a list, got {type(value).__name__}", None


def _validate_string(value: Any) -> tuple[str | None, Any]:
    if isinstance(value, str):
        return None, value
    problem = f"expected a string, got {type(value).__name__}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # IDs and status codes as numbers: unambiguous, keep them.
        return problem, value
    return problem, None


def _validate_number(expected: Field, value: Any) -> tuple[str | None, Any]:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return f"expected a number, got {type(value).__name__}", None
    try:
        number = float(value)
    except OverflowError:
        return "not a finite number", None
    except ValueError:
        return "expected a number, got text", None

    problem: str | None = None
    if not math.isfinite(number):
        problem = "not a finite number"
    elif (expected.min is not None and number < expected.min) or (
        expected.max is not None and number > expected.max
    ):
        problem = f"outside the plausible range {expected.min}..{expected.max}"
    if problem is not None:
        return problem, None
    if isinstance(value, str):
        return "expected a number, got a string", value
    return None, value


def _containers(data: Any, parents: list[str]) -> list[dict[str, Any]]:
    """All dicts reached by following the parent parts of a path."""
    current = [data]
    for part in parents:
        is_list = part.endswith("[]")
        name = part.removesuffix("[]")
        next_level: list[Any] = []
        for item in current:
            value = item.get(name) if name and isinstance(item, dict) else item
            if not name and not isinstance(item, list):
                continue
            if is_list:
                next_level.extend(value if isinstance(value, list) else [])
            elif value is not None:
                next_level.append(value)
        current = next_level
    return [item for item in current if isinstance(item, dict)]
