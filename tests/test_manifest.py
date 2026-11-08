"""Smoke test: the integration can be found and its manifest is valid."""

import json
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from custom_components.easy_pv_ew.const import DOMAIN


async def test_integration_is_loadable(hass: HomeAssistant) -> None:
    """Home Assistant finds the integration under its own domain."""
    integration = await async_get_integration(hass, DOMAIN)

    assert integration.domain == "easy_pv_ew"
    assert integration.name == "Easy PV (EW)"
    assert integration.config_flow is True


def test_hacs_json_has_only_valid_keys() -> None:
    """
    hacs.json only uses keys the HACS validation accepts.

    The HACS action rejects the old keys "domains" and "iot_class".
    """
    data = json.loads((Path(__file__).parent.parent / "hacs.json").read_text())

    allowed = {
        "name",
        "content_in_root",
        "zip_release",
        "filename",
        "hide_default_branch",
        "country",
        "homeassistant",
        "persistent_directory",
        "hacs",
    }
    assert set(data) <= allowed
    assert data["name"] == "Easy PV (EW)"


def test_manifest_keys_sorted() -> None:
    """Hassfest wants domain, name, then the other keys in alphabetical order."""
    manifest = (
        Path(__file__).parent.parent / "custom_components/easy_pv_ew/manifest.json"
    )
    keys = list(json.loads(manifest.read_text()))

    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])
