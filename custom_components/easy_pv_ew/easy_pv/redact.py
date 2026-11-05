"""Anonymize Easy PV API responses before they are logged or exported."""

import re
from typing import Any

REDACTED = "**REDACTED**"

# Words in field names that point to identifying data. Field names are split
# into words (camelCase, snake_case), so "deviceNum" -> {"device", "num"} and
# "plantLocation" -> {"plant", "location"}. Unknown fields are therefore
# covered as long as their name contains one of these words, also in plural.
SENSITIVE_WORDS = frozenset(
    {
        "account",
        "addr",
        "address",
        "avatar",
        "city",
        "country",
        "county",
        "district",
        "email",
        "gps",
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
        "post",
        "postal",
        "postcode",
        "province",
        "pwd",
        "region",
        "secret",
        "serial",
        "sn",
        "ssid",
        "street",
        "tel",
        "token",
        "town",
        "user",
        "username",
        "wifi",
        "zip",
    }
)

# Whole field names that hold identifying data although none of their words
# does: the product code of real devices carries a device-specific suffix
# (VN2T08EU-<code>), which may be part of the serial number.
SENSITIVE_KEYS = frozenset({"productcode", "customproductcode"})

_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")


def _words(key: str) -> set[str]:
    """Split a field name into lower-case words, plurals also as singular."""
    words = {word.lower() for word in _WORD.findall(key)}
    # "deviceIds" -> "ids" -> also "id"; "addresses" -> also "address".
    for word in list(words):
        if word.endswith("es"):
            words.add(word[:-2])
        if word.endswith("s"):
            words.add(word[:-1])
    return words


def is_sensitive(key: str) -> bool:
    """Return True if a field name looks like it holds identifying data."""
    return key.lower() in SENSITIVE_KEYS or not SENSITIVE_WORDS.isdisjoint(_words(key))


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
