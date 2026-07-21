"""Canonical primitive geometry for selected-route edit handles."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

if __package__ == "src":
    from . import config as cfg
else:
    import config as cfg

Position = tuple[float, float]
HandleKind = Literal["start", "end", "insert"]


@dataclass(frozen=True, slots=True)
class PathHandle:
    """One immutable render/hit descriptor without gameplay references."""

    kind: HandleKind
    slot: int
    center: Position
    anchor: Position
    path_id: str
    hit_radius: float


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _clean(value: float) -> float:
    result = round(value, 10)
    return 0.0 if result == 0 else result


def _position(value: Any) -> Position | None:
    try:
        raw = (value.left, value.top) if hasattr(value, "left") else value[:2]
        left, top = _number(raw[0]), _number(raw[1])
    except (AttributeError, IndexError, KeyError, TypeError):
        return None
    return None if left is None or top is None else (_clean(left), _clean(top))


def _basis(start: Position, end: Position) -> tuple[Position, Position] | None:
    first, second = sorted((start, end))
    dx, dy = second[0] - first[0], second[1] - first[1]
    length = math.hypot(dx, dy)
    if length <= 0 or not math.isfinite(length):
        return None
    tangent = (dx / length, dy / length)
    return ((-tangent[1], tangent[0]), tangent)


def _offset_edge(
    start: Position, end: Position, order: float
) -> tuple[Position, Position] | None:
    basis = _basis(start, end)
    if basis is None:
        return None
    normal, _ = basis
    dx, dy = (value * order * cfg.path_order_shift for value in normal)
    return (
        (_clean(start[0] + dx), _clean(start[1] + dy)),
        (_clean(end[0] + dx), _clean(end[1] + dy)),
    )


@dataclass(frozen=True, slots=True)
class _Draft:
    kind: HandleKind
    slot: int
    anchor: Position
    primary: Position
    secondary: Position
    sort_key: tuple[Any, ...]
    output_index: int


def _endpoint_draft(
    kind: HandleKind,
    slot: int,
    edge: tuple[Position, Position],
    station: Any,
    neighbor: Any,
    output_index: int,
) -> _Draft:
    endpoint, other = edge if kind == "start" else tuple(reversed(edge))
    dx, dy = endpoint[0] - other[0], endpoint[1] - other[1]
    length = math.hypot(dx, dy)
    outward = (dx / length, dy / length)
    anchor = tuple(
        _clean(value + unit * cfg.path_handle_endpoint_outset)
        for value, unit in zip(endpoint, outward)
    )
    ids = tuple(sorted((str(station.id), str(neighbor.id))))
    return _Draft(
        kind,
        slot,
        anchor,  # type: ignore[arg-type]
        outward,
        (-outward[1], outward[0]),
        (0, endpoint, ids),
        output_index,
    )


def _insert_draft(
    slot: int,
    edge: tuple[Position, Position],
    raw_edge: tuple[Position, Position],
    output_index: int,
) -> _Draft:
    anchor = tuple(_clean((left + right) / 2) for left, right in zip(*edge))
    basis = _basis(*raw_edge)
    assert basis is not None
    return _Draft(
        "insert",
        slot,
        anchor,  # type: ignore[arg-type]
        *basis,
        (1, tuple(sorted(raw_edge))),
        output_index,
    )


def _control_radius(control: Any) -> float | None:
    shape = getattr(control, "shape", None)
    radius = _number(getattr(shape, "radius", None))
    if radius is not None:
        return radius
    width = _number(getattr(shape, "width", None))
    height = _number(getattr(shape, "height", None))
    return (
        None if width is None or height is None else math.hypot(width / 2, height / 2)
    )


def _obstacles(state: Any, route_stations: Sequence[Any]):
    result: list[tuple[Position, float]] = []
    seen: set[int] = set()
    groups = [route_stations, getattr(state, "stations", ())]
    groups.extend(
        getattr(state, name, ())
        for name in ("buttons", "path_buttons", "speed_buttons")
    )
    for group_index, group in enumerate(groups):
        try:
            values = tuple(group)
        except TypeError:
            continue
        for value in values:
            if id(value) in seen:
                continue
            seen.add(id(value))
            center = _position(getattr(value, "position", None))
            radius = (
                _number(getattr(value, "size", None))
                if group_index < 2
                else _control_radius(value)
            )
            if center is not None and radius is not None and radius >= 0:
                result.append((center, radius))
    return tuple(result)


def _rect_distance(point: Position, rect: Sequence[float]) -> float:
    left, top, right, bottom = map(float, rect)
    x = min(max(point[0], min(left, right)), max(left, right))
    y = min(max(point[1], min(top, bottom)), max(top, bottom))
    return math.hypot(point[0] - x, point[1] - y)


def _fits(
    center: Position,
    viewport: Position,
    obstacles: Sequence[tuple[Position, float]],
    accepted: Sequence[PathHandle],
) -> bool:
    radius = float(cfg.path_handle_hit_radius)
    extra = float(cfg.path_handle_quantization_margin)
    margin = max(float(cfg.path_handle_viewport_margin), radius + extra)
    if not all(
        margin <= value <= extent - margin for value, extent in zip(center, viewport)
    ):
        return False
    if _rect_distance(center, cfg.path_handle_hud_exclusion) <= radius + extra:
        return False
    if any(
        math.dist(center, point) <= radius + obstacle_radius + extra
        for point, obstacle_radius in obstacles
    ):
        return False
    return all(
        math.dist(center, handle.center) > radius + handle.hit_radius + extra
        for handle in accepted
    )


def _candidates(draft: _Draft):
    yield draft.anchor
    step = float(cfg.path_handle_lattice_step)
    for ring in range(1, int(cfg.path_handle_search_rings) + 1):
        lattice = [
            (a, b)
            for a in range(-ring, ring + 1)
            for b in range(-ring, ring + 1)
            if max(abs(a), abs(b)) == ring
        ]
        for primary, secondary in sorted(
            lattice, key=lambda value: (-value[0], abs(value[1]), -value[1])
        ):
            yield tuple(
                _clean(anchor + step * (primary * first + secondary * second))
                for anchor, first, second in zip(
                    draft.anchor, draft.primary, draft.secondary
                )
            )


def build_path_handles_for_state(
    state: Any,
    path: Any,
    *,
    viewport_size: tuple[int | float, int | float],
) -> tuple[PathHandle, ...]:
    """Build canonical descriptors for one exact active path."""

    viewport = _position(viewport_size)
    try:
        paths, stations = tuple(state.paths), tuple(path.stations)
    except (AttributeError, TypeError):
        return ()
    matches = [index for index, item in enumerate(paths) if item is path]
    if (
        viewport is None
        or min(viewport) <= 0
        or len(matches) != 1
        or len(stations) < 2
        or len(stations) != len({id(item) for item in stations})
        or type(getattr(path, "is_looped", None)) is not bool
    ):
        return ()
    positions = tuple(_position(getattr(item, "position", None)) for item in stations)
    path_id = getattr(path, "id", None)
    if not isinstance(path_id, str) or not path_id or None in positions:
        return ()
    points: tuple[Position, ...] = positions  # type: ignore[assignment]
    loop = path.is_looped
    edge_count = len(stations) if loop else len(stations) - 1
    order = matches[0] - (len(paths) - 1) / 2
    raw_edges = tuple(
        (points[index], points[(index + 1) % len(points)])
        for index in range(edge_count)
    )
    edges = tuple(_offset_edge(*edge, order) for edge in raw_edges)

    drafts: list[_Draft] = []
    if not loop and edges[0] is not None:
        drafts.append(_endpoint_draft("start", 0, edges[0], *stations[:2], 0))
    if not loop and edges[-1] is not None:
        drafts.append(
            _endpoint_draft(
                "end", len(stations), edges[-1], stations[-1], stations[-2], len(drafts)
            )
        )
    insert_count = 1 if loop and len(stations) == 2 else edge_count
    for index in range(insert_count):
        if edges[index] is not None:
            drafts.append(
                _insert_draft(index + 1, edges[index], raw_edges[index], len(drafts))
            )

    obstacles = _obstacles(state, stations)
    accepted: list[PathHandle] = []
    output: dict[int, PathHandle] = {}
    for draft in sorted(drafts, key=lambda item: item.sort_key):
        center = next(
            (
                point
                for point in _candidates(draft)
                if _fits(point, viewport, obstacles, accepted)
            ),
            None,
        )
        if center is None:
            continue
        handle = PathHandle(
            draft.kind,
            draft.slot,
            center,  # type: ignore[arg-type]
            draft.anchor,
            path_id,
            float(cfg.path_handle_hit_radius),
        )
        accepted.append(handle)
        output[draft.output_index] = handle
    return tuple(output[index] for index in sorted(output))
