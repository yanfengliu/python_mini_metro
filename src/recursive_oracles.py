from __future__ import annotations

import math
from typing import Any


def reference_errors(checkpoint: dict[str, Any]) -> list[str]:
    structured = checkpoint["structured"]
    observed_counts = {
        "station": len(structured["stations"]),
        "path": len(structured["paths"]),
        "metro": len(structured["metros"]),
        "passenger": len(structured["passengers"]),
    }
    latent_counts = {
        "station": len(checkpoint["stationPool"]),
        "path": len(checkpoint["topology"]["paths"]),
        "metro": len(checkpoint["metroMotion"]),
        "passenger": len(checkpoint["passengers"]),
        "path_button": len(checkpoint["progression"]["path_buttons"]),
    }
    errors: list[str] = []

    def check(
        value: Any,
        count: int,
        label: str,
        absent: tuple[Any, ...] = (),
    ) -> None:
        if value in absent:
            return
        if type(value) is not int or not 0 <= value < count:
            errors.append(label)

    def observed(
        value: Any, kind: str, label: str, absent: tuple[Any, ...] = ()
    ) -> None:
        check(value, observed_counts[kind], label, absent)

    def latent(value: Any, kind: str, label: str, absent: tuple[Any, ...] = ()) -> None:
        check(value, latent_counts[kind], label, absent)

    for number, path in enumerate(structured["paths"]):
        for value in path["station_indices"]:
            observed(value, "station", f"path {number} station reference {value}")
    for number, station in enumerate(structured["stations"]):
        for value in station["passenger_indices"]:
            observed(
                value,
                "passenger",
                f"station {number} passenger reference {value}",
            )
    for number, metro in enumerate(structured["metros"]):
        observed(metro["path_index"], "path", f"metro {number} path reference", (None,))
        observed(
            metro["current_station_index"],
            "station",
            f"metro {number} station reference",
            (None,),
        )
        for value in metro["passenger_indices"]:
            observed(
                value,
                "passenger",
                f"metro {number} passenger reference {value}",
            )
    for number, passenger in enumerate(structured["passengers"]):
        _check_location(
            passenger["location"],
            number,
            observed_counts,
            errors,
            "observed passenger",
        )

    arrays = checkpoint["arrays"]
    for number, indices in enumerate(arrays["path_station_indices"]):
        for value in indices:
            observed(value, "station", f"array path {number} station reference {value}")
    for number, value in enumerate(arrays["metro_path_indices"]):
        observed(value, "path", f"array metro {number} path reference {value}", (-1,))
    for key, kind in (
        ("passenger_station_indices", "station"),
        ("passenger_metro_indices", "metro"),
    ):
        for number, value in enumerate(arrays[key]):
            observed(
                value,
                kind,
                f"array passenger {number} {kind} reference {value}",
                (-1,),
            )

    for number, station in enumerate(checkpoint["stationPool"]):
        for value in station["passenger_indices"]:
            latent(
                value,
                "passenger",
                f"stationPool {number} passenger reference {value}",
            )
    topology = checkpoint["topology"]
    for value in topology["active_station_indices"]:
        latent(value, "station", f"active station reference {value}")
    latent(
        topology["path_being_created_index"],
        "path",
        "path being created reference",
        (None,),
    )
    for number, path in enumerate(topology["paths"]):
        for value in path["station_indices"]:
            latent(
                value, "station", f"topology path {number} station reference {value}"
            )
        for value in path["metro_indices"]:
            latent(value, "metro", f"topology path {number} metro reference {value}")
        for segment_number, segment in enumerate(path["segments"]):
            for key in ("start_station_index", "end_station_index"):
                latent(
                    segment[key],
                    "station",
                    f"topology path {number} segment {segment_number} {key}",
                    (None,),
                )
    for number, value in enumerate(topology["path_to_button"]):
        latent(
            value,
            "path_button",
            f"topology path {number} button reference",
            (None,),
        )
    for number, passenger in enumerate(checkpoint["passengers"]):
        _check_location(
            passenger["location"],
            number,
            latent_counts,
            errors,
            "latent passenger",
        )
    for number, plan in enumerate(checkpoint["travelPlans"]):
        latent(plan["passenger_index"], "passenger", f"travel plan {number} passenger")
        latent(
            plan["next_path_index"],
            "path",
            f"travel plan {number} next path",
            (None,),
        )
        latent(
            plan["next_station_index"],
            "station",
            f"travel plan {number} next station",
            (None,),
        )
        for node_number, node in enumerate(plan["node_path"]):
            latent(
                node["station_index"],
                "station",
                f"travel plan {number} node {node_number} station",
            )
            for value in node["path_indices"]:
                latent(value, "path", f"travel plan {number} node {node_number} path")
    for number, metro in enumerate(checkpoint["metroMotion"]):
        latent(metro["path_index"], "path", f"metroMotion {number} path", (None,))
        latent(
            metro["declared_path_index"],
            "path",
            f"metroMotion {number} declared path",
            (None,),
        )
        latent(
            metro["current_station_index"],
            "station",
            f"metroMotion {number} station",
            (None,),
        )
        current_segment = metro["current_segment"]
        if current_segment is not None:
            for key in ("start_station_index", "end_station_index"):
                latent(
                    current_segment[key],
                    "station",
                    f"metroMotion {number} current segment {key}",
                    (None,),
                )
            owner_index = metro["path_index"]
            if type(owner_index) is int and 0 <= owner_index < latent_counts["path"]:
                segment_count = len(topology["paths"][owner_index]["segments"])
                check(
                    metro["current_segment_index"],
                    segment_count,
                    f"metroMotion {number} current segment index",
                )
                check(
                    metro["current_segment_relation_index"],
                    segment_count,
                    f"metroMotion {number} current segment relation index",
                )
        for value in metro["passenger_indices"]:
            latent(value, "passenger", f"metroMotion {number} passenger {value}")
    for number, station in enumerate(checkpoint["spawning"]["stations"]):
        latent(
            station["station_index"],
            "station",
            f"spawning station {number} reference",
        )
    for number, button in enumerate(checkpoint["progression"]["path_buttons"]):
        latent(
            button["path_index"],
            "path",
            f"path button {number} path reference",
            (None,),
        )
    return errors


def _check_location(
    location: Any,
    number: int,
    counts: dict[str, int],
    errors: list[str],
    label: str,
) -> None:
    if location is None:
        return
    kind = location["kind"]
    if kind not in ("station", "metro"):
        errors.append(f"{label} {number} location kind")
        return
    value = location["index"]
    if type(value) is not int or not 0 <= value < counts[kind]:
        errors.append(f"{label} {number} location reference")


def nonfinite_paths(value: Any, path: str = "checkpoint") -> list[str]:
    if isinstance(value, dict):
        if set(value) == {"$nonFinite"}:
            return [path]
        return [
            item
            for key in sorted(value)
            for item in nonfinite_paths(value[key], f"{path}.{key}")
        ]
    if isinstance(value, list):
        return [
            item
            for index, child in enumerate(value)
            for item in nonfinite_paths(child, f"{path}[{index}]")
        ]
    if isinstance(value, float) and not math.isfinite(value):
        return [path]
    return []
