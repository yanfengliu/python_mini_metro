from __future__ import annotations

import math
from enum import Enum
from typing import Any

import numpy as np

from env import DELIVERIES_REWARD_MODE, LINE_CREDITS_DELTA_REWARD_MODE
from recursive_checkpoint_carriages import validate_topology_metro_ownership

CHECKPOINT_SCHEMA_VERSION_V1 = 1
CHECKPOINT_SCHEMA_VERSION_V2 = 2
CHECKPOINT_SCHEMA_VERSION_V3 = 3
CHECKPOINT_SCHEMA_VERSION_V4 = 4
CHECKPOINT_SCHEMA_VERSION = CHECKPOINT_SCHEMA_VERSION_V4
SUPPORTED_CHECKPOINT_SCHEMA_VERSIONS = {
    CHECKPOINT_SCHEMA_VERSION_V1,
    CHECKPOINT_SCHEMA_VERSION_V2,
    CHECKPOINT_SCHEMA_VERSION_V3,
    CHECKPOINT_SCHEMA_VERSION,
}
_LOCOMOTIVE_FLEET_KEYS = {
    "locomotives_total",
    "locomotives_assigned",
    "locomotives_available",
    "locomotives_queued",
}
_CARRIAGE_FLEET_KEYS = {
    "carriages_total",
    "carriages_assigned",
    "carriages_available",
}
_FLEET_KEYS_V4 = _LOCOMOTIVE_FLEET_KEYS | _CARRIAGE_FLEET_KEYS
_CARRIAGE_RECORD_KEYS = {
    "capacity",
    "metro_motion_index",
    "attachment_index",
}
_ENTITY_ID_PREFIXES = ("Metro-", "Carriage-", "Path-", "Station-", "Passenger-")


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


def _nonnegative_integer(value: Any, label: str) -> int:
    integer = _integer(value, label)
    if integer < 0:
        raise ValueError(f"checkpoint {label} must be nonnegative")
    return integer


def _positive_integer(value: Any, label: str) -> int:
    integer = _integer(value, label)
    if integer <= 0:
        raise ValueError(f"checkpoint {label} must be positive")
    return integer


def _reject_entity_ids(value: Any, label: str = "checkpoint") -> None:
    if type(value) is dict:
        for key, item in value.items():
            if key == "id" or key.endswith("_id") or key.endswith("_ids"):
                raise ValueError(f"checkpoint {label}.{key} contains an entity ID")
            _reject_entity_ids(item, f"{label}.{key}")
    elif type(value) is list:
        for index, item in enumerate(value):
            _reject_entity_ids(item, f"{label}[{index}]")
    elif type(value) is str and any(prefix in value for prefix in _ENTITY_ID_PREFIXES):
        raise ValueError(f"checkpoint {label} contains an entity ID")


def _reject_legacy_carriage_fields(checkpoint: dict[str, Any]) -> None:
    if "carriages" in checkpoint:
        raise ValueError("legacy checkpoint declares top-level carriages")
    structured = _object(checkpoint.get("structured"), "structured")
    if "carriages" in structured:
        raise ValueError("legacy checkpoint declares structured.carriages")
    fleet = structured.get("fleet")
    if fleet is not None:
        fleet = _object(fleet, "structured.fleet")
        if _CARRIAGE_FLEET_KEYS & set(fleet):
            raise ValueError("legacy checkpoint declares carriage fleet fields")
    progression = _object(checkpoint.get("progression"), "progression")
    limits = _object(progression.get("limits"), "progression.limits")
    if "num_carriages" in limits:
        raise ValueError("legacy checkpoint declares progression.limits.num_carriages")
    for index, item in enumerate(_array(structured.get("metros"), "structured.metros")):
        metro = _object(item, f"structured.metros[{index}]")
        if {"capacity", "carriage_indices", "carriage_ids"} & set(metro):
            raise ValueError("legacy checkpoint declares structured carriage state")
    for index, item in enumerate(_array(checkpoint.get("metroMotion"), "metroMotion")):
        metro = _object(item, f"metroMotion[{index}]")
        if {"base_capacity", "carriage_indices", "carriage_ids"} & set(metro):
            raise ValueError("legacy checkpoint declares Metro carriage motion state")


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


def _validate_locomotive_state(
    checkpoint: dict[str, Any], *, fleet_keys: set[str]
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[Any],
    list[Any],
    dict[str, Any],
]:
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
    if set(fleet) != fleet_keys:
        raise ValueError("checkpoint structured.fleet is incomplete")
    for key in fleet_keys:
        _integer(fleet[key], f"structured.fleet.{key}")
    total = _integer(limits.get("num_metros"), "progression.limits.num_metros")
    expected = {
        "locomotives_total": total,
        "locomotives_assigned": len(metros),
        "locomotives_available": max(0, total - len(metros)),
        "locomotives_queued": sum(item["unassignment_queued"] for item in metros),
    }
    if any(fleet[key] != value for key, value in expected.items()):
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
    return structured, progression, limits, metros, motion, fleet


def validate_checkpoint_v3(checkpoint: dict[str, Any]) -> None:
    if checkpoint.get("schemaVersion") != CHECKPOINT_SCHEMA_VERSION_V3:
        raise ValueError("checkpoint schemaVersion must be 3")
    _reject_legacy_carriage_fields(checkpoint)
    _validate_locomotive_state(checkpoint, fleet_keys=_LOCOMOTIVE_FLEET_KEYS)


def _validate_carriage_record(
    value: Any, label: str, *, motion_count: int
) -> dict[str, Any]:
    record = _object(value, label)
    if set(record) != _CARRIAGE_RECORD_KEYS:
        raise ValueError(f"checkpoint {label} has unexpected carriage fields")
    _positive_integer(record["capacity"], f"{label}.capacity")
    owner = _nonnegative_integer(
        record["metro_motion_index"], f"{label}.metro_motion_index"
    )
    if owner >= motion_count:
        raise ValueError(f"checkpoint {label}.metro_motion_index is out of range")
    _nonnegative_integer(record["attachment_index"], f"{label}.attachment_index")
    return record


def validate_checkpoint_v4(checkpoint: dict[str, Any]) -> None:
    if checkpoint.get("schemaVersion") != CHECKPOINT_SCHEMA_VERSION_V4:
        raise ValueError("checkpoint schemaVersion must be 4")
    _reject_entity_ids(checkpoint)
    structured, _, limits, metros, motion, fleet = _validate_locomotive_state(
        checkpoint, fleet_keys=_FLEET_KEYS_V4
    )
    validate_topology_metro_ownership(checkpoint, motion)
    top = _array(checkpoint.get("carriages"), "carriages")
    structured_carriages = _array(structured.get("carriages"), "structured.carriages")
    total = _nonnegative_integer(
        limits.get("num_carriages"), "progression.limits.num_carriages"
    )
    for key in _CARRIAGE_FLEET_KEYS:
        _nonnegative_integer(fleet[key], f"structured.fleet.{key}")
    if fleet["carriages_total"] != total:
        raise ValueError("checkpoint carriage total disagrees with progression limit")

    records = [
        _validate_carriage_record(item, f"carriages[{index}]", motion_count=len(motion))
        for index, item in enumerate(top)
    ]
    cursor = 0
    global_carriage_count = 0
    for metro_index, item in enumerate(motion):
        metro = _object(item, f"metroMotion[{metro_index}]")
        base_capacity = _nonnegative_integer(
            metro.get("base_capacity"),
            f"metroMotion[{metro_index}].base_capacity",
        )
        capacity = _nonnegative_integer(
            metro.get("capacity"), f"metroMotion[{metro_index}].capacity"
        )
        references = _array(
            metro.get("carriage_indices"),
            f"metroMotion[{metro_index}].carriage_indices",
        )
        for reference_index, value in enumerate(references):
            _nonnegative_integer(
                value,
                f"metroMotion[{metro_index}].carriage_indices[{reference_index}]",
            )
        expected = list(range(cursor, cursor + len(references)))
        if references != expected:
            raise ValueError("checkpoint carriage owner slices must be contiguous")
        attached_capacity = 0
        for attachment_index, carriage_index in enumerate(expected):
            if carriage_index >= len(records):
                raise ValueError("checkpoint carriage reference is out of range")
            carriage = records[carriage_index]
            if (
                carriage["metro_motion_index"] != metro_index
                or carriage["attachment_index"] != attachment_index
            ):
                raise ValueError("checkpoint carriage owner reference disagrees")
            attached_capacity += carriage["capacity"]
        if capacity != base_capacity + attached_capacity:
            raise ValueError("checkpoint Metro capacity disagrees with its consist")
        passengers = _array(
            metro.get("passenger_indices"),
            f"metroMotion[{metro_index}].passenger_indices",
        )
        if len(passengers) > capacity:
            raise ValueError("checkpoint Metro passenger count exceeds capacity")
        if (
            metro_index >= len(metros)
            and references
            and not metro["unassignment_queued"]
        ):
            raise ValueError("checkpoint path-only carriage owner must be queued")
        cursor += len(references)
        if metro_index + 1 == len(metros):
            global_carriage_count = cursor
    if not metros:
        global_carriage_count = 0
    if cursor != len(records):
        raise ValueError("checkpoint carriage records are not exhaustively referenced")
    if structured_carriages != records[:global_carriage_count]:
        raise ValueError("checkpoint structured carriage prefix disagrees")

    for index, item in enumerate(structured_carriages):
        _validate_carriage_record(
            item,
            f"structured.carriages[{index}]",
            motion_count=len(motion),
        )
    for metro_index, item in enumerate(metros):
        metro = _object(item, f"structured.metros[{metro_index}]")
        capacity = _nonnegative_integer(
            metro.get("capacity"), f"structured.metros[{metro_index}].capacity"
        )
        references = _array(
            metro.get("carriage_indices"),
            f"structured.metros[{metro_index}].carriage_indices",
        )
        for reference_index, value in enumerate(references):
            reference = _nonnegative_integer(
                value,
                f"structured.metros[{metro_index}].carriage_indices[{reference_index}]",
            )
            if reference >= global_carriage_count:
                raise ValueError(
                    "checkpoint structured carriage reference is out of range"
                )
        if (
            capacity != motion[metro_index]["capacity"]
            or references != motion[metro_index]["carriage_indices"]
        ):
            raise ValueError(
                "checkpoint structured Metro consist disagrees with motion"
            )

    expected_assigned = global_carriage_count
    expected_available = max(0, total - expected_assigned)
    if (
        fleet["carriages_assigned"] != expected_assigned
        or fleet["carriages_available"] != expected_available
    ):
        raise ValueError("checkpoint carriage fleet disagrees with assigned state")


def _upgrade_v1_v2_to_v3(normalized: dict[str, Any], version: int) -> None:
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
    structured["fleet"] = {
        "locomotives_total": total,
        "locomotives_assigned": len(metros),
        "locomotives_available": max(0, total - len(metros)),
        "locomotives_queued": 0,
    }
    normalized["schemaVersion"] = CHECKPOINT_SCHEMA_VERSION_V3


def _upgrade_v3_to_v4(normalized: dict[str, Any]) -> None:
    validate_checkpoint_v3(normalized)
    structured = _object(normalized["structured"], "structured")
    metros = _array(structured["metros"], "structured.metros")
    motion = _array(normalized["metroMotion"], "metroMotion")
    limits = _object(normalized["progression"]["limits"], "progression.limits")
    structured["carriages"] = []
    limits["num_carriages"] = 0
    fleet = _object(structured["fleet"], "structured.fleet")
    fleet.update(
        {
            "carriages_total": 0,
            "carriages_assigned": 0,
            "carriages_available": 0,
        }
    )
    for index, metro in enumerate(metros):
        item = _object(metro, f"structured.metros[{index}]")
        item["capacity"] = motion[index]["capacity"]
        item["carriage_indices"] = []
    for index, metro in enumerate(motion):
        item = _object(metro, f"metroMotion[{index}]")
        item["base_capacity"] = item["capacity"]
        item["carriage_indices"] = []
    normalized["carriages"] = []
    normalized["schemaVersion"] = CHECKPOINT_SCHEMA_VERSION_V4


def normalize_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    """Return one schema-v4 checkpoint view without mutating recorded evidence."""

    if type(checkpoint) is not dict:
        raise ValueError("checkpoint must be an object")
    normalized = safe_checkpoint_value(checkpoint)
    version = normalized.get("schemaVersion")
    if type(version) is not int or version not in SUPPORTED_CHECKPOINT_SCHEMA_VERSIONS:
        raise ValueError("checkpoint schemaVersion must be 1, 2, 3, or 4")
    if version != CHECKPOINT_SCHEMA_VERSION_V4:
        _reject_legacy_carriage_fields(normalized)
        if version in {CHECKPOINT_SCHEMA_VERSION_V1, CHECKPOINT_SCHEMA_VERSION_V2}:
            _upgrade_v1_v2_to_v3(normalized, version)
        _upgrade_v3_to_v4(normalized)
    validate_checkpoint_v4(normalized)
    return normalized
