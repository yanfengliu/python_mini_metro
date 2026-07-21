from __future__ import annotations

import math
from enum import Enum
from typing import Any

import numpy as np

from env import DELIVERIES_REWARD_MODE, LINE_CREDITS_DELTA_REWARD_MODE

CHECKPOINT_SCHEMA_VERSION_V1 = 1
CHECKPOINT_SCHEMA_VERSION_V2 = 2
CHECKPOINT_SCHEMA_VERSION = 3
SUPPORTED_CHECKPOINT_SCHEMA_VERSIONS = {
    CHECKPOINT_SCHEMA_VERSION_V1,
    CHECKPOINT_SCHEMA_VERSION_V2,
    CHECKPOINT_SCHEMA_VERSION,
}
_FLEET_KEYS = {
    "locomotives_total",
    "locomotives_assigned",
    "locomotives_available",
    "locomotives_queued",
}


def safe_checkpoint_value(value: Any) -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isfinite(number):
            return number
        label = (
            "NaN" if math.isnan(number) else ("Infinity" if number > 0 else "-Infinity")
        )
        return {"$nonFinite": label}
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Enum):
        return safe_checkpoint_value(value.value)
    if isinstance(value, np.ndarray):
        return safe_checkpoint_value(value.tolist())
    if isinstance(value, (list, tuple)):
        return [safe_checkpoint_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): safe_checkpoint_value(item) for key, item in value.items()}
    raise TypeError(f"checkpoint contains unsupported {type(value).__name__}")


def _object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"checkpoint {label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        raise ValueError(f"checkpoint {label} must be an array")
    return value


def _integer(value: Any, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"checkpoint {label} must be an integer")
    return value


def _legacy_fields(
    checkpoint: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Any, Any, Any, Any]:
    try:
        environment = _object(checkpoint["environment"], "environment")
        progression = _object(checkpoint["progression"], "progression")
        limits = _object(progression["limits"], "progression.limits")
        last_score = environment["last_score"]
        score = progression["score"]
        deliveries = progression["total_travels_handled"]
        overdue_threshold = limits["max_waiting_passengers"]
    except (KeyError, TypeError) as error:
        raise ValueError("checkpoint is missing legacy compatibility fields") from error
    return (
        environment,
        progression,
        limits,
        last_score,
        score,
        deliveries,
        overdue_threshold,
    )


def _validate_reward_aliases(checkpoint: dict[str, Any]) -> None:
    (
        environment,
        progression,
        limits,
        last_score,
        score,
        deliveries,
        overdue_threshold,
    ) = _legacy_fields(checkpoint)
    required = (
        (environment, "reward_mode", "environment.reward_mode"),
        (environment, "last_deliveries", "environment.last_deliveries"),
        (environment, "last_line_credits", "environment.last_line_credits"),
        (progression, "deliveries", "progression.deliveries"),
        (progression, "line_credits", "progression.line_credits"),
        (
            limits,
            "overdue_passenger_threshold",
            "progression.limits.overdue_passenger_threshold",
        ),
    )
    for container, key, label in required:
        if key not in container:
            raise ValueError(f"checkpoint is missing {label}")
    if environment["reward_mode"] not in {
        DELIVERIES_REWARD_MODE,
        LINE_CREDITS_DELTA_REWARD_MODE,
    }:
        raise ValueError("checkpoint environment.reward_mode is unsupported")
    compatibility_pairs = (
        (environment["last_line_credits"], last_score, "environment line credits"),
        (progression["deliveries"], deliveries, "progression deliveries"),
        (progression["line_credits"], score, "progression line credits"),
        (
            limits["overdue_passenger_threshold"],
            overdue_threshold,
            "overdue passenger threshold",
        ),
    )
    for explicit, legacy, label in compatibility_pairs:
        if explicit != legacy:
            raise ValueError(f"checkpoint {label} disagrees with its legacy alias")


def validate_checkpoint_v3(checkpoint: dict[str, Any]) -> None:
    if checkpoint.get("schemaVersion") != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError("checkpoint schemaVersion must be 3")
    _validate_reward_aliases(checkpoint)
    structured = _object(checkpoint.get("structured"), "structured")
    progression = _object(checkpoint.get("progression"), "progression")
    limits = _object(progression.get("limits"), "progression.limits")
    for key, value in limits.items():
        _integer(value, f"progression.limits.{key}")

    metros = _array(structured.get("metros"), "structured.metros")
    motion = _array(checkpoint.get("metroMotion"), "metroMotion")
    if len(motion) < len(metros):
        raise ValueError("checkpoint metroMotion is shorter than structured.metros")
    for index, item in enumerate(metros):
        metro = _object(item, f"structured.metros[{index}]")
        if type(metro.get("unassignment_queued")) is not bool:
            raise ValueError(
                f"checkpoint structured.metros[{index}].unassignment_queued "
                "must be boolean"
            )
    for index, item in enumerate(motion):
        metro = _object(item, f"metroMotion[{index}]")
        if type(metro.get("unassignment_queued")) is not bool:
            raise ValueError(
                f"checkpoint metroMotion[{index}].unassignment_queued must be boolean"
            )

    fleet = _object(structured.get("fleet"), "structured.fleet")
    if set(fleet) != _FLEET_KEYS:
        raise ValueError("checkpoint structured.fleet is incomplete")
    for key in _FLEET_KEYS:
        _integer(fleet[key], f"structured.fleet.{key}")
    total = _integer(limits.get("num_metros"), "progression.limits.num_metros")
    assigned = len(metros)
    queued = sum(item["unassignment_queued"] for item in metros)
    expected = {
        "locomotives_total": total,
        "locomotives_assigned": assigned,
        "locomotives_available": max(0, total - assigned),
        "locomotives_queued": queued,
    }
    if fleet != expected:
        raise ValueError("checkpoint structured.fleet disagrees with assigned state")

    overlap = (
        ("path_index", "declared_path_index"),
        ("position", "position"),
        ("current_station_index", "current_station_index"),
        ("passenger_indices", "passenger_indices"),
        ("unassignment_queued", "unassignment_queued"),
    )
    for index, structured_metro in enumerate(metros):
        motion_metro = motion[index]
        for structured_key, motion_key in overlap:
            if structured_key not in structured_metro or motion_key not in motion_metro:
                raise ValueError(
                    f"checkpoint metro prefix is missing {structured_key} correspondence"
                )
            if structured_metro[structured_key] != motion_metro[motion_key]:
                raise ValueError(f"checkpoint metro prefix disagrees at index {index}")


def normalize_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    """Return one schema-v3 checkpoint view without mutating recorded evidence."""

    if type(checkpoint) is not dict:
        raise ValueError("checkpoint must be an object")
    normalized = safe_checkpoint_value(checkpoint)
    version = normalized.get("schemaVersion")
    if type(version) is not int or version not in SUPPORTED_CHECKPOINT_SCHEMA_VERSIONS:
        raise ValueError("checkpoint schemaVersion must be 1, 2, or 3")
    (
        environment,
        progression,
        limits,
        last_score,
        score,
        deliveries,
        overdue_threshold,
    ) = _legacy_fields(normalized)

    if version == CHECKPOINT_SCHEMA_VERSION_V1:
        environment["reward_mode"] = LINE_CREDITS_DELTA_REWARD_MODE
        environment["last_deliveries"] = deliveries
        environment["last_line_credits"] = last_score
        progression["deliveries"] = deliveries
        progression["line_credits"] = score
        limits["overdue_passenger_threshold"] = overdue_threshold
    if version in {CHECKPOINT_SCHEMA_VERSION_V1, CHECKPOINT_SCHEMA_VERSION_V2}:
        _validate_reward_aliases(normalized)
        for key, value in limits.items():
            _integer(value, f"progression.limits.{key}")
        structured = _object(normalized.get("structured"), "structured")
        metros = _array(structured.get("metros"), "structured.metros")
        motion = _array(normalized.get("metroMotion"), "metroMotion")
        for item in metros:
            _object(item, "structured metro")["unassignment_queued"] = False
        for item in motion:
            _object(item, "metro motion")["unassignment_queued"] = False
        total = _integer(limits.get("num_metros"), "progression.limits.num_metros")
        assigned = len(metros)
        structured["fleet"] = {
            "locomotives_total": total,
            "locomotives_assigned": assigned,
            "locomotives_available": max(0, total - assigned),
            "locomotives_queued": 0,
        }
        normalized["schemaVersion"] = CHECKPOINT_SCHEMA_VERSION

    validate_checkpoint_v3(normalized)
    return normalized
