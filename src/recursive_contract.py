from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

SCHEMA_VERSION_V1 = 1
SCHEMA_VERSION_V2 = 2
SCHEMA_VERSION_V3 = 3
LEGACY_SCHEMA_VERSION = SCHEMA_VERSION_V1
SCHEMA_VERSION = SCHEMA_VERSION_V3
_SUPPORTED_SCHEMA_VERSIONS = {
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
}
DELIVERIES_REWARD_CONTRACT = "deliveries"
LINE_CREDITS_REWARD_CONTRACT = "line_credits_delta"

_SCENARIO_KEYS_V1 = {"schemaVersion", "seed", "defaultDtMs", "operations"}
_SCENARIO_KEYS_V2 = {*_SCENARIO_KEYS_V1, "environmentRewardContract"}
_SCENARIO_KEYS_V3 = {*_SCENARIO_KEYS_V2, "overduePassengerThreshold"}
_INPUT_KEYS_V1 = {
    "schemaVersion",
    "runId",
    "sourcePath",
    "seed",
    "defaultDtMs",
    "pythonExecutable",
    "pythonHashSeed",
    "operations",
}
_INPUT_KEYS_V2 = {*_INPUT_KEYS_V1, "environmentRewardContract"}
_INPUT_KEYS_V3 = {*_INPUT_KEYS_V2, "overduePassengerThreshold"}
_OPERATION_KEYS = {"name", "action", "expectedActionOk"}


def _exact_keys(
    value: object, required: set[str], optional: set[str], label: str
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be an object")
    keys = set(value)
    if keys - required - optional or required - keys:
        raise ValueError(
            f"{label} keys must be exactly {sorted(required)}"
            + (f" plus optional {sorted(optional)}" if optional else "")
        )
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _positive_int(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _uint32(value: object, label: str) -> int:
    integer = _nonnegative_int(value, label)
    if integer > 4_294_967_295:
        raise ValueError(f"{label} must be a uint32 integer")
    return integer


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a nonempty trimmed string")
    return value


def _hash_seed(value: object) -> str:
    seed = _nonempty_string(value, "inputs.pythonHashSeed")
    if not seed.isdecimal() or not 0 <= int(seed) <= 4_294_967_295:
        raise ValueError("inputs.pythonHashSeed must be a uint32 string")
    return seed


def _schema_version(value: object, label: str) -> int:
    if type(value) is not int or value not in _SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"{label} schemaVersion must be 1, 2, or 3")
    return value


def _environment_reward_contract(value: object, label: str) -> str:
    contract = _nonempty_string(value, f"{label}.environmentRewardContract")
    if contract != DELIVERIES_REWARD_CONTRACT:
        raise ValueError(
            f"{label}.environmentRewardContract must be {DELIVERIES_REWARD_CONTRACT!r}"
        )
    return contract


def _reward_contract_for_document(document: dict[str, Any]) -> str:
    if document["schemaVersion"] == SCHEMA_VERSION_V1:
        return LINE_CREDITS_REWARD_CONTRACT
    return _environment_reward_contract(
        document["environmentRewardContract"], "document"
    )


def _overdue_threshold_for_document(document: dict[str, Any]) -> int:
    if document["schemaVersion"] in {SCHEMA_VERSION_V1, SCHEMA_VERSION_V2}:
        return 1
    return _positive_int(
        document["overduePassengerThreshold"],
        "document.overduePassengerThreshold",
    )


def _validate_json(value: object, label: str, seen: set[int] | None = None) -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{label} must not contain non-finite numbers")
        return
    if seen is None:
        seen = set()
    if type(value) in (list, dict):
        if id(value) in seen:
            raise ValueError(f"{label} must not contain cycles")
        seen.add(id(value))
        children = enumerate(value) if isinstance(value, list) else value.items()
        for key, item in children:
            if isinstance(value, dict) and not isinstance(key, str):
                raise ValueError(f"{label} keys must be strings")
            _validate_json(item, f"{label}.{key}", seen)
        seen.remove(id(value))
        return
    raise ValueError(f"{label} must contain only JSON values")


def _json_copy(value: Any, label: str = "value") -> Any:
    _validate_json(value, label)
    return json.loads(json.dumps(value, allow_nan=False, sort_keys=True))


def _validate_operations(value: object) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise ValueError("operations must be a nonempty array")
    result: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, raw in enumerate(value):
        operation = _exact_keys(raw, _OPERATION_KEYS, {"dtMs"}, f"operations[{index}]")
        name = _nonempty_string(operation["name"], f"operations[{index}].name")
        if name in names:
            raise ValueError("operation names must be unique")
        names.add(name)
        if type(operation["expectedActionOk"]) is not bool:
            raise ValueError(f"operations[{index}].expectedActionOk must be boolean")
        if "dtMs" in operation:
            _nonnegative_int(operation["dtMs"], f"operations[{index}].dtMs")
        _validate_json(operation["action"], f"operations[{index}].action")
        result.append(_json_copy(operation, f"operations[{index}]"))
    return result


def validate_scenario(value: object) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("scenario must be an object")
    version = _schema_version(value.get("schemaVersion"), "scenario")
    required_by_version = {
        SCHEMA_VERSION_V1: _SCENARIO_KEYS_V1,
        SCHEMA_VERSION_V2: _SCENARIO_KEYS_V2,
        SCHEMA_VERSION_V3: _SCENARIO_KEYS_V3,
    }
    required = required_by_version[version]
    document = _exact_keys(value, required, set(), "scenario")
    result = {
        "schemaVersion": version,
        "seed": _uint32(document["seed"], "scenario.seed"),
        "defaultDtMs": _nonnegative_int(
            document["defaultDtMs"], "scenario.defaultDtMs"
        ),
        "operations": _validate_operations(document["operations"]),
    }
    if version in {SCHEMA_VERSION_V2, SCHEMA_VERSION_V3}:
        result["environmentRewardContract"] = _environment_reward_contract(
            document["environmentRewardContract"], "scenario"
        )
    if version == SCHEMA_VERSION_V3:
        result["overduePassengerThreshold"] = _positive_int(
            document["overduePassengerThreshold"],
            "scenario.overduePassengerThreshold",
        )
    return _json_copy(result, "scenario")


def validate_inputs(value: object) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("inputs must be an object")
    version = _schema_version(value.get("schemaVersion"), "inputs")
    required_by_version = {
        SCHEMA_VERSION_V1: _INPUT_KEYS_V1,
        SCHEMA_VERSION_V2: _INPUT_KEYS_V2,
        SCHEMA_VERSION_V3: _INPUT_KEYS_V3,
    }
    required = required_by_version[version]
    document = _exact_keys(value, required, set(), "inputs")
    result = {
        "schemaVersion": version,
        "runId": _nonempty_string(document["runId"], "inputs.runId"),
        "sourcePath": _nonempty_string(document["sourcePath"], "inputs.sourcePath"),
        "seed": _uint32(document["seed"], "inputs.seed"),
        "defaultDtMs": _nonnegative_int(document["defaultDtMs"], "inputs.defaultDtMs"),
        "pythonExecutable": _nonempty_string(
            document["pythonExecutable"], "inputs.pythonExecutable"
        ),
        "pythonHashSeed": _hash_seed(document["pythonHashSeed"]),
        "operations": _validate_operations(document["operations"]),
    }
    if version in {SCHEMA_VERSION_V2, SCHEMA_VERSION_V3}:
        result["environmentRewardContract"] = _environment_reward_contract(
            document["environmentRewardContract"], "inputs"
        )
    if version == SCHEMA_VERSION_V3:
        result["overduePassengerThreshold"] = _positive_int(
            document["overduePassengerThreshold"],
            "inputs.overduePassengerThreshold",
        )
    return _json_copy(result, "inputs")


def load_inputs(path: str | Path) -> dict[str, Any]:
    return validate_inputs(json.loads(Path(path).read_text(encoding="utf-8")))
