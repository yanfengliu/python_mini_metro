from __future__ import annotations

from typing import Any

from fleet_validation import carriage_state_is_canonical, identity_unique
from graph.graph_algo import build_station_nodes_dict
from passenger_capacity import pure_service_action, same_service_action

_LOCOMOTIVE_FLEET_KEYS = (
    "locomotives_total",
    "locomotives_assigned",
    "locomotives_available",
    "locomotives_queued",
)


def project_observation_fleet(
    fleet: dict[str, Any], *, include_carriages: bool
) -> dict[str, Any]:
    if include_carriages:
        return fleet
    return {key: fleet[key] for key in _LOCOMOTIVE_FLEET_KEYS}


def validate_observation_metro_prefix(env: Any, observation: dict[str, Any]) -> None:
    try:
        observed_ids = [item["id"] for item in observation["structured"]["metros"]]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "checkpoint observation is missing structured Metro IDs"
        ) from error
    if any(type(value) is not str for value in observed_ids):
        raise ValueError("checkpoint observation Metro IDs must be strings")
    if len(set(observed_ids)) != len(observed_ids):
        raise ValueError("checkpoint observation Metro IDs must be unique")
    if observed_ids != [metro.id for metro in env.mediator.metros]:
        raise ValueError("checkpoint observation Metro order is stale")


def metro_queue_state(metro: Any, *, required: bool = True) -> bool:
    value = getattr(metro, "is_unassignment_queued", None if required else False)
    if type(value) is not bool:
        raise ValueError("checkpoint Metro queue state must be boolean")
    return value


def validate_topology_metro_ownership(
    checkpoint: dict[str, Any], motion: list[Any]
) -> None:
    """Require every serialized Metro to have one ordered topology owner."""

    topology = checkpoint.get("topology")
    paths = topology.get("paths") if type(topology) is dict else None
    if type(paths) is not list:
        raise ValueError("checkpoint topology.paths must be an array")
    seen: set[int] = set()
    for path_index, path in enumerate(paths):
        references = path.get("metro_indices") if type(path) is dict else None
        if type(references) is not list or any(
            type(reference) is not int or not 0 <= reference < len(motion)
            for reference in references
        ):
            raise ValueError("checkpoint topology Metro references are malformed")
        for reference in references:
            metro = motion[reference]
            if (
                reference in seen
                or type(metro) is not dict
                or type(metro.get("path_index")) is not int
                or type(metro.get("declared_path_index")) is not int
                or metro["path_index"] != path_index
                or metro["declared_path_index"] != path_index
            ):
                raise ValueError("checkpoint topology Metro ownership disagrees")
            seen.add(reference)
    if seen != set(range(len(motion))):
        raise ValueError("checkpoint Metro ownership is not exhaustive")


def _validate_service_cache(mediator: Any, metro: Any) -> None:
    cache = getattr(metro, "_station_service_action", None)
    station = getattr(metro, "current_station", None)
    expected = (
        None
        if station is None
        else pure_service_action(
            mediator,
            metro,
            station,
            build_station_nodes_dict(mediator.stations, mediator.paths),
        )
    )
    if expected is None:
        if cache is not None or any(
            getattr(metro, name, 0)
            for name in ("stop_time_remaining_ms", "boarding_progress_ms")
        ):
            raise ValueError("checkpoint Metro service cache is stale")
        return
    if not same_service_action(cache, expected):
        raise ValueError("checkpoint Metro service cache is stale")
    interval = getattr(metro, "boarding_time_per_passenger_ms", None)
    progress = getattr(metro, "boarding_progress_ms", None)
    remaining = getattr(metro, "stop_time_remaining_ms", None)
    if (
        type(interval) is not int
        or interval <= 0
        or type(progress) is not int
        or not 0 <= progress < interval
        or remaining != interval - progress
    ):
        raise ValueError("checkpoint Metro service timing is stale")


def _validate_observation(
    mediator: Any,
    observation: dict[str, Any],
    global_metros: list[Any],
    raw_carriages: list[dict[str, Any]],
) -> None:
    structured = observation.get("structured")
    if type(structured) is not dict:
        raise ValueError("checkpoint observation is missing structured carriage state")
    observed_metros = structured.get("metros")
    if type(observed_metros) is not list or len(observed_metros) != len(global_metros):
        raise ValueError("checkpoint observation Metro composition is stale")
    for source, metro in zip(observed_metros, global_metros, strict=True):
        if (
            type(source) is not dict
            or source.get("capacity") != metro.capacity
            or source.get("carriage_ids")
            != [carriage.id for carriage in metro.carriages]
        ):
            raise ValueError("checkpoint observation Metro composition is stale")
    if structured.get("carriages") != raw_carriages:
        raise ValueError("checkpoint observation carriage order is stale")
    fleet = structured.get("fleet")
    assigned = sum(len(metro.carriages) for metro in global_metros)
    expected = {
        "carriages_total": mediator.num_carriages,
        "carriages_assigned": assigned,
        "carriages_available": max(0, mediator.num_carriages - assigned),
    }
    if type(fleet) is not dict or any(
        fleet.get(key) != value for key, value in expected.items()
    ):
        raise ValueError("checkpoint observation carriage fleet is stale")


def runtime_carriage_state(
    env: Any,
    observation: dict[str, Any],
    metros: list[Any],
) -> tuple[list[dict[str, int]], dict[int, list[int]]]:
    """Validate v4 runtime/raw composition and return its UUID-free projection."""

    mediator = env.mediator
    if not carriage_state_is_canonical(mediator):
        raise ValueError("checkpoint runtime carriage graph is malformed")
    global_metros = list(mediator.metros)
    if not identity_unique(global_metros):
        raise ValueError("checkpoint global Metro ownership is duplicated")
    owned: set[int] = set()
    for path in mediator.paths:
        if not identity_unique(path.metros):
            raise ValueError("checkpoint path Metro ownership is duplicated")
        for metro in path.metros:
            if id(metro) in owned or getattr(metro, "path_id", None) != path.id:
                raise ValueError("checkpoint Metro ownership is malformed")
            owned.add(id(metro))
    if any(id(metro) not in owned for metro in global_metros):
        raise ValueError("checkpoint global Metro has no exact path owner")
    list_ids: set[int] = set()
    metro_ids: set[str] = set()
    carriage_objects: set[int] = set()
    carriage_ids: set[str] = set()
    records: list[dict[str, int]] = []
    references: dict[int, list[int]] = {}
    raw_carriages: list[dict[str, Any]] = []
    for metro_index, metro in enumerate(metros):
        if type(metro.id) is not str or not metro.id or metro.id in metro_ids:
            raise ValueError("checkpoint Metro IDs must be nonempty and unique")
        metro_ids.add(metro.id)
        if type(metro.carriages) is not list or id(metro.carriages) in list_ids:
            raise ValueError("checkpoint Metro carriage lists must be distinct lists")
        list_ids.add(id(metro.carriages))
        base_capacity = getattr(metro, "_base_capacity", None)
        if type(base_capacity) is not int or base_capacity < 0:
            raise ValueError("checkpoint Metro base capacity must be nonnegative")
        attached_capacity = 0
        owner_references: list[int] = []
        for attachment_index, carriage in enumerate(metro.carriages):
            capacity = getattr(carriage, "capacity", None)
            carriage_id = getattr(carriage, "id", None)
            if type(capacity) is not int or capacity <= 0:
                raise ValueError("checkpoint Carriage capacity must be positive")
            if (
                id(carriage) in carriage_objects
                or type(carriage_id) is not str
                or not carriage_id
                or carriage_id in carriage_ids
            ):
                raise ValueError(
                    "checkpoint Carriage identities and IDs must be unique"
                )
            carriage_objects.add(id(carriage))
            carriage_ids.add(carriage_id)
            attached_capacity += capacity
            owner_references.append(len(records))
            records.append(
                {
                    "capacity": capacity,
                    "metro_motion_index": metro_index,
                    "attachment_index": attachment_index,
                }
            )
            if metro_index < len(global_metros):
                raw_carriages.append(
                    {
                        "id": carriage_id,
                        "capacity": capacity,
                        "metro_id": metro.id,
                        "attachment_index": attachment_index,
                    }
                )
        references[id(metro)] = owner_references
        capacity = metro.capacity
        if (
            type(capacity) is not int
            or capacity < 0
            or capacity != base_capacity + attached_capacity
            or len(metro.passengers) > capacity
        ):
            raise ValueError("checkpoint Metro capacity state is inconsistent")
        if (
            metro_index >= len(global_metros)
            and metro.carriages
            and not metro_queue_state(metro)
        ):
            raise ValueError("checkpoint path-only carriage owner must be queued")
        _validate_service_cache(mediator, metro)
    _validate_observation(mediator, observation, global_metros, raw_carriages)
    return records, references
