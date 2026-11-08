"""
Tests for the API contract (tests/api_contract.yaml) and scripts/check_api.

The OpenAPI descriptions used here are built from the contract itself; the
manufacturer's description is never part of the tests.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from .conftest import load_fixture

ROOT = Path(__file__).parent.parent
CONTRACT_PATH = ROOT / "tests" / "api_contract.yaml"
CHECK_API = ROOT / "scripts" / "check_api"
CONTRACT = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

FIXTURES = {
    "login": "login.json",
    "user_info": "user_info.json",
    "station_list": "station_list.json",
    "device_list": "power_list.json",
    "device_data": "device_data.json",
}
JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "object": (dict,),
    "array": (list,),
}


# --- Fixtures follow the contract ---


def _values(data: Any, field_path: str) -> list[Any] | None:
    """All values at a contract field path; None if a part is missing."""
    values = [data]
    for part in field_path.split("."):
        name = part.removesuffix("[]")
        next_values = []
        for value in values:
            if not isinstance(value, dict) or name not in value:
                return None
            child = value[name]
            if part.endswith("[]"):
                next_values.extend(child or [])
            else:
                next_values.append(child)
        values = next_values
    return values


def _fields(endpoint: str) -> list[tuple[str, dict[str, Any]]]:
    return list(CONTRACT["endpoints"][endpoint]["response"].items())


@pytest.mark.parametrize(
    ("endpoint", "field_path", "expected"),
    [
        (endpoint, field_path, expected)
        for endpoint in FIXTURES
        for field_path, expected in _fields(endpoint)
    ],
)
def test_fixture_matches_contract(
    endpoint: str, field_path: str, expected: dict[str, Any]
) -> None:
    """Every field the code reads is in the fixture, with the contract type."""
    values = _values(load_fixture(FIXTURES[endpoint]), field_path)
    if values is None:
        assert expected.get("optional"), f"{field_path} fehlt im Fixture"
        return
    allowed = JSON_TYPES[expected["type"]]
    for value in values:
        assert isinstance(value, allowed), f"{field_path}: {value!r}"
        assert not (isinstance(value, bool) and bool not in allowed), field_path


def test_contract_covers_endpoints_used_by_client() -> None:
    """Every path the client calls is in the contract, and only those."""
    client = (
        ROOT / "custom_components" / "easy_pv_ew" / "easy_pv" / "__init__.py"
    ).read_text(encoding="utf-8")
    paths = {endpoint["path"] for endpoint in CONTRACT["endpoints"].values()}
    for path in paths:
        assert f'"{path}"' in client, path
    assert client.count('"/api/') == len(paths)


def test_openapi_url_belongs_to_the_client_api() -> None:
    """The documented description lives on the server the client talks to."""
    from custom_components.easy_pv_ew.easy_pv import BASE_URL  # noqa: PLC0415

    assert CONTRACT["openapi_url"] == f"{BASE_URL}/v3/api-docs"


# --- scripts/check_api ---


def _schema(tree: dict[str, Any]) -> dict[str, Any]:
    """Build an OpenAPI schema from a nested field tree."""
    if "__leaf__" in tree:
        expected = tree["__leaf__"]
        schema: dict[str, Any] = {"type": expected["type"]}
        unit = expected.get("spec_unit") or expected.get("unit")
        if unit:
            schema["description"] = f"Wert ({unit})"
        children = {k: v for k, v in tree.items() if k != "__leaf__"}
        if children and expected["type"] == "array":
            schema["items"] = _schema(children)
        elif children:
            schema["properties"] = {k: _schema(v) for k, v in children.items()}
        return schema
    properties = {}
    for name, child in tree.items():
        if name.endswith("[]"):
            properties[name[:-2]] = {"type": "array", "items": _schema(child)}
        else:
            properties[name] = _schema(child)
    return {"type": "object", "properties": properties}


def _tree(fields: dict[str, Any]) -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for field_path, expected in fields.items():
        node = tree
        parts = field_path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node.setdefault(parts[-1], {})["__leaf__"] = expected
    return tree


def _build_spec(contract: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal OpenAPI description that matches the contract exactly."""
    paths: dict[str, Any] = {}
    for endpoint in contract["endpoints"].values():
        operation: dict[str, Any] = {
            "parameters": [
                {"name": name, "in": "query", "schema": {"type": p["type"]}}
                for name, p in (endpoint.get("params") or {}).items()
            ],
            "responses": {
                "200": {
                    "content": {"*/*": {"schema": _schema(_tree(endpoint["response"]))}}
                }
            },
        }
        if endpoint.get("body"):
            operation["requestBody"] = {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                name: {"type": f["type"]}
                                for name, f in endpoint["body"].items()
                            },
                        }
                    }
                }
            }
        paths[endpoint["path"]] = {endpoint["method"].lower(): operation}
    return {"openapi": "3.0.1", "paths": paths, "components": {"schemas": {}}}


def _device_data_props(spec: dict[str, Any]) -> dict[str, Any]:
    op = spec["paths"]["/api/powerStation/v3/getDeviceDataInfo"]["get"]
    schema = op["responses"]["200"]["content"]["*/*"]["schema"]
    return schema["properties"]["data"]["properties"]


def _run(directory: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(CHECK_API), "--dir", str(directory)],
        capture_output=True,
        text=True,
        check=False,
    )


def _write(directory: Path, name: str, spec: dict[str, Any]) -> None:
    directory.mkdir(exist_ok=True)
    (directory / name).write_text(json.dumps(spec), encoding="utf-8")


def test_check_api_without_local_copy(tmp_path: Path) -> None:
    """Without a local description only a note is printed, exit code 0."""
    result = _run(tmp_path / "missing")
    assert result.returncode == 0
    assert "Keine lokale OpenAPI-Beschreibung" in result.stdout
    assert CONTRACT["openapi_url"] in result.stdout


def test_check_api_matching_spec(tmp_path: Path) -> None:
    """A description that matches the contract gives no errors."""
    _write(tmp_path, "easy-pv-2026-11-04.json", _build_spec(CONTRACT))
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout
    assert "0 Fehler, 0 Warnungen" in result.stdout


def test_check_api_reports_changes(tmp_path: Path) -> None:
    """Renamed fields, changed units and types and newer versions are found."""
    spec = _build_spec(CONTRACT)
    props = _device_data_props(spec)
    props["genPowerTotals"] = props.pop("genPowerTotal")  # renamed
    props["genPower"]["description"] = "Wert (kW)"  # unit changed
    props["genpowerTodayTotals"]["description"] = "Wert (kWh)"  # known unit changed
    props["gridVoltage"]["type"] = "string"  # type changed
    spec["paths"]["/api/powerStation/v4/getDeviceDataInfo"] = copy.deepcopy(
        spec["paths"]["/api/powerStation/v3/getDeviceDataInfo"]
    )
    del spec["paths"]["/api/user/v2/selectUserInfo"]  # endpoint missing
    _write(tmp_path, "easy-pv-2026-11-04.json", spec)

    result = _run(tmp_path)
    out = result.stdout
    assert result.returncode == 1, out
    assert "data.genPowerTotal fehlt" in out
    assert "ähnlich: genPowerTotals" in out
    assert "Einheit laut Beschreibung kW, im Vertrag W" in out
    assert (
        "data.genpowerTodayTotals: Einheit laut Beschreibung kWh, bekannt war Wh"
    ) in out
    assert "Feld data.gridVoltage: Typ laut Beschreibung string" in out
    assert "neuere Version vorhanden: /api/powerStation/v4/getDeviceDataInfo" in out
    assert "Endpunkt fehlt" in out


def test_check_api_compares_two_newest_copies(tmp_path: Path) -> None:
    """With two local copies the differences between them are reported."""
    old = _build_spec(CONTRACT)
    new = copy.deepcopy(old)
    _device_data_props(new)["newField"] = {"type": "number"}
    new["paths"]["/api/other/v1/somethingNew"] = {"get": {"responses": {}}}
    _write(tmp_path, "easy-pv-2026-10-01.json", {"openapi": "3.0.1", "paths": {}})
    _write(tmp_path, "easy-pv-2026-11-01.json", old)
    _write(tmp_path, "easy-pv-2026-11-04.json", new)

    result = _run(tmp_path)
    out = result.stdout
    assert "Vergleich easy-pv-2026-11-01.json -> easy-pv-2026-11-04.json" in out
    assert "device_data: Antwortfeld neu: data.newField" in out
    assert "Endpunkt neu: /api/other/v1/somethingNew" in out
    assert result.returncode == 0, out
