"""Consistency checks for strings.json and translations (Fehler 7)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "easy_pv_ew"
LANGUAGES = ["en", "de"]
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _load(name: str) -> dict[str, Any]:
    return json.loads((COMPONENT / name).read_text(encoding="utf-8"))


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in data.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            result.update(_flatten(value, f"{path}."))
        else:
            result[path] = value
    return result


STRINGS = _flatten(_load("strings.json"))
TRANSLATIONS = {
    lang: _flatten(_load(f"translations/{lang}.json")) for lang in LANGUAGES
}


@pytest.mark.parametrize("lang", LANGUAGES)
def test_same_keys_as_strings(lang: str) -> None:
    """Every translation has exactly the keys of strings.json."""
    assert set(TRANSLATIONS[lang]) == set(STRINGS)


@pytest.mark.parametrize("lang", LANGUAGES)
def test_no_unresolved_references(lang: str) -> None:
    """Custom integrations do not resolve [%key:...%]; translations need plain text."""
    unresolved = {k: v for k, v in TRANSLATIONS[lang].items() if "[%key:" in v}
    assert not unresolved


def test_strings_has_no_self_references() -> None:
    """strings.json must not point to its own keys (the original did)."""
    assert not [v for v in STRINGS.values() if "component::easy_pv_ew::" in v]


@pytest.mark.parametrize("key", sorted(TRANSLATIONS["en"]))
def test_placeholders_match(key: str) -> None:
    """German and English texts use the same placeholders."""
    en = set(PLACEHOLDER.findall(TRANSLATIONS["en"][key]))
    de = set(PLACEHOLDER.findall(TRANSLATIONS["de"][key]))
    assert en == de


def test_translation_keys_in_code_exist() -> None:
    """Every translation_key used in the code has a translation."""
    code = "\n".join(p.read_text(encoding="utf-8") for p in COMPONENT.glob("*.py"))
    used = set(re.findall(r'translation_key\s*=\s*"(\w+)"', code))
    known = {
        key.split(".")[-2] for key in STRINGS if key.endswith((".name", ".message"))
    }

    assert used, "no translation keys found in the code"
    assert used <= known, f"missing translations: {used - known}"
