"""Anonymize Easy PV API responses before they are logged or exported."""

import re
from typing import Any

REDACTED = "**REDACTED**"

# Words in field names that point to identifying data. Field names are split
# into words (camelCase, snake_case), so "deviceNum" -> {"device", "num"} and
# "plantLocation" -> {"plant", "location"}. Unknown fields are therefore
# covered as long as their name contains one of these words.
SENSITIVE_WORDS = frozenset(
    {
        "account",
        "addr",
        "address",
        "avatar",
        "city",
        "country",
        "email",
        "iccid",
        "id",
        "imei",
        "ip",
        "key",
        "lat",
        "latitude",
        "lng",
        "location",
        "lon",
        "longitude",
        "mac",
        "mail",
        "mobile",
        "name",
        "nick",
        "no",
        "num",
        "number",
        "password",
        "phone",
        "pwd",
        "secret",
        "serial",
        "sn",
        "ssid",
        "street",
        "tel",
        "token",
        "user",
        "username",
        "wifi",
        "zip",
    }
)

_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")


def _words(key: str) -> set[str]:
    return {word.lower() for word in _WORD.findall(key)}


def is_sensitive(key: str) -> bool:
    """Return True if a field name looks like it holds identifying data."""
    return not SENSITIVE_WORDS.isdisjoint(_words(key))


def redact(data: Any) -> Any:
    """Return a copy of data with identifying values replaced, measurements kept."""
    if isinstance(data, dict):
        return {
            key: REDACTED
            if is_sensitive(str(key)) and value not in (None, "")
            else redact(value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redact(item) for item in data]
    return data
