"""GM-09a: versioned map definitions (D-032).

A DATA-ONLY, dependency-light map layer. A :class:`MapDefinition` is an immutable
value describing a map's identity (``map_id`` + ``map_definition_version``) and
its station-shape palette; :data:`CLASSIC` reproduces the current game exactly.

This module imports ONLY ``config`` constants and ``geometry.type`` — never
``pygame``, ``entity``, or ``mediator`` — so ``get_entity``/``mediator`` consume a
``MapDefinition`` ONE-WAY and the module stays import-safe for every headless/RL
path (there is no map→gameplay import edge to leak or cycle).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from config import (
    screen_height,
    screen_width,
    station_shape_type_list,
    station_size,
    station_unique_shape_type_list,
    station_unique_spawn_chance,
    station_unique_spawn_start_index,
)
from geometry.type import ShapeType

# A terrain rect is a deeply-immutable (left, top, right, bottom) tuple of floats.
Rect = tuple[float, float, float, float]


def _coerce_rects(rects: Iterable, name: str) -> tuple[Rect, ...]:
    """Coerce a sequence of (left, top, right, bottom) rects to immutable tuples,
    validating positive area and finiteness (a degenerate region would hang the
    region-aware spawn or paint nothing)."""
    coerced: list[Rect] = []
    for rect in rects:
        values = tuple(rect)
        if len(values) != 4:
            raise ValueError(
                f"{name} rect must be (left, top, right, bottom); got {rect!r}"
            )
        left, top, right, bottom = (float(v) for v in values)
        if not all(
            v == v and abs(v) != float("inf") for v in (left, top, right, bottom)
        ):
            raise ValueError(f"{name} rect coordinates must be finite; got {rect!r}")
        if right <= left or bottom <= top:
            raise ValueError(f"{name} rect must have positive area; got {rect!r}")
        coerced.append((left, top, right, bottom))
    return tuple(coerced)


@dataclass(frozen=True)
class MapDefinition:
    """An immutable map identity + station-shape palette + terrain.

    Palette and terrain fields are deeply immutable ``tuple``s (not mutable
    ``config`` lists/caller lists). ``spawn_regions`` are the (eroded) land rects
    where stations may spawn; ``rivers`` are obstacle-band rects to RENDER. Both
    default empty, so the region-less CLASSIC map draws byte-identically and paints
    no terrain. Station counts stay global (deferred to the progression unit).
    """

    map_id: str
    map_definition_version: int
    shape_types: tuple[ShapeType, ...]
    unique_shape_types: tuple[ShapeType, ...]
    unique_spawn_start_index: int
    unique_spawn_chance: float
    spawn_regions: tuple[Rect, ...] = ()
    rivers: tuple[Rect, ...] = ()
    # The finite tunnel/bridge budget for crossing this map's rivers (GM-09c).
    # None = unbounded (no river to cross, e.g. CLASSIC); an int caps the total
    # river crossings across all lines.
    tunnel_budget: int | None = None

    def __post_init__(self) -> None:
        # Enforce deep immutability rather than trust the caller: coerce the
        # palettes AND terrain rects to tuples so a future author passing a list
        # still gets an immutable, validated definition. frozen=True needs
        # object.__setattr__.
        object.__setattr__(self, "shape_types", tuple(self.shape_types))
        object.__setattr__(self, "unique_shape_types", tuple(self.unique_shape_types))
        object.__setattr__(
            self, "spawn_regions", _coerce_rects(self.spawn_regions, "spawn_regions")
        )
        object.__setattr__(self, "rivers", _coerce_rects(self.rivers, "rivers"))
        budget = self.tunnel_budget
        if budget is not None and (
            isinstance(budget, bool) or not isinstance(budget, int) or budget < 0
        ):
            raise ValueError(
                f"tunnel_budget must be None or a non-negative integer; got {budget!r}"
            )


CLASSIC = MapDefinition(
    map_id="classic",
    map_definition_version=1,
    shape_types=tuple(station_shape_type_list),
    unique_shape_types=tuple(station_unique_shape_type_list),
    unique_spawn_start_index=station_unique_spawn_start_index,
    unique_spawn_chance=station_unique_spawn_chance,
)

# The first alternate map (GM-09b): a single vertical river down the screen centre
# splitting the play area into two land banks. The render band is the river's full
# height; the spawn banks are ERODED inward by station_size so a 30px station glyph
# never overlaps the water (only the river's x-band is excluded — the vertical river
# constrains x only, and get_random_position already applies the y padding).
_RIVER_HALF_WIDTH = 0.04 * screen_width
_RIVER_LEFT = 0.5 * screen_width - _RIVER_HALF_WIDTH
_RIVER_RIGHT = 0.5 * screen_width + _RIVER_HALF_WIDTH
_RIVER_BAND: Rect = (_RIVER_LEFT, 0.0, _RIVER_RIGHT, float(screen_height))
_LEFT_BANK: Rect = (0.0, 0.0, _RIVER_LEFT - station_size, float(screen_height))
_RIGHT_BANK: Rect = (
    _RIVER_RIGHT + station_size,
    0.0,
    float(screen_width),
    float(screen_height),
)

RIVER = MapDefinition(
    map_id="river",
    map_definition_version=1,
    shape_types=tuple(station_shape_type_list),
    unique_shape_types=tuple(station_unique_shape_type_list),
    unique_spawn_start_index=station_unique_spawn_start_index,
    unique_spawn_chance=station_unique_spawn_chance,
    spawn_regions=(_LEFT_BANK, _RIGHT_BANK),
    rivers=(_RIVER_BAND,),
    # A finite tunnel budget makes the river a real constraint while leaving a
    # connected cross-river network buildable (tunable; verified playable).
    tunnel_budget=3,
)

# The second alternate map (GM-09d): two vertical rivers -- a delta's twin channels
# -- splitting the play area into THREE land banks (left, mid, right). A line
# spanning the whole map crosses both channels and so uses TWO tunnels, exercising
# the multi-band crossing count and the finite budget more than the single RIVER.
# Each bank is eroded inward by station_size so a station's CENTER clears the water
# by station_size (a glyph extremity may still touch a band edge by a pixel, exactly
# as on RIVER -- shared erosion, not DELTA-specific). The two channels sit at 0.32
# and 0.68 of the width, leaving a positive-width mid bank (~516px at 1920x1080);
# like RIVER these bands assume a screen wide enough that _coerce_rects' positive-area
# check holds -- true for every shipped resolution. The budget stays generous enough
# to connect all three banks.
_DELTA_HALF_WIDTH = 0.03 * screen_width
_DELTA_C1 = 0.32 * screen_width
_DELTA_C2 = 0.68 * screen_width
_DELTA_R1: Rect = (
    _DELTA_C1 - _DELTA_HALF_WIDTH,
    0.0,
    _DELTA_C1 + _DELTA_HALF_WIDTH,
    float(screen_height),
)
_DELTA_R2: Rect = (
    _DELTA_C2 - _DELTA_HALF_WIDTH,
    0.0,
    _DELTA_C2 + _DELTA_HALF_WIDTH,
    float(screen_height),
)
_DELTA_LEFT_BANK: Rect = (
    0.0,
    0.0,
    _DELTA_C1 - _DELTA_HALF_WIDTH - station_size,
    float(screen_height),
)
_DELTA_MID_BANK: Rect = (
    _DELTA_C1 + _DELTA_HALF_WIDTH + station_size,
    0.0,
    _DELTA_C2 - _DELTA_HALF_WIDTH - station_size,
    float(screen_height),
)
_DELTA_RIGHT_BANK: Rect = (
    _DELTA_C2 + _DELTA_HALF_WIDTH + station_size,
    0.0,
    float(screen_width),
    float(screen_height),
)

DELTA = MapDefinition(
    map_id="delta",
    map_definition_version=1,
    shape_types=tuple(station_shape_type_list),
    unique_shape_types=tuple(station_unique_shape_type_list),
    unique_spawn_start_index=station_unique_spawn_start_index,
    unique_spawn_chance=station_unique_spawn_chance,
    spawn_regions=(_DELTA_LEFT_BANK, _DELTA_MID_BANK, _DELTA_RIGHT_BANK),
    rivers=(_DELTA_R1, _DELTA_R2),
    # Two channels to cross: a full-span line uses two tunnels. The budget stays
    # generous enough to connect all three banks (tunable; verified playable).
    tunnel_budget=4,
)

_REGISTRY: dict[tuple[str, int], MapDefinition] = {
    (CLASSIC.map_id, CLASSIC.map_definition_version): CLASSIC,
    (RIVER.map_id, RIVER.map_definition_version): RIVER,
    (DELTA.map_id, DELTA.map_definition_version): DELTA,
}


def resolve_map(map_id: str, map_definition_version: int) -> MapDefinition:
    """Return the map definition for an EXACT ``(map_id, version)`` pair.

    Version-aware: an id-only lookup could silently run the wrong version, so a
    mismatch raises a clear, named error rather than falling back to another map.
    """
    definition = _REGISTRY.get((map_id, map_definition_version))
    if definition is not None:
        return definition
    known_ids = sorted({registered_id for (registered_id, _v) in _REGISTRY})
    if map_id not in known_ids:
        raise ValueError(f"unknown map id {map_id!r}; known maps: {known_ids}")
    versions = sorted(v for (registered_id, v) in _REGISTRY if registered_id == map_id)
    raise ValueError(
        f"unsupported version {map_definition_version} for map {map_id!r}; "
        f"supported versions: {versions}"
    )


def map_by_id(map_id: str) -> MapDefinition:
    """Return the CURRENT (highest-version) definition for a map id.

    For the CLI, which names a map by id; the definition version is the map's
    current version. Raises a clear, named error for an unknown id.
    """
    matches = [
        definition
        for (registered_id, _v), definition in _REGISTRY.items()
        if registered_id == map_id
    ]
    if not matches:
        known_ids = sorted({registered_id for (registered_id, _v) in _REGISTRY})
        raise ValueError(f"unknown map id {map_id!r}; known maps: {known_ids}")
    return max(matches, key=lambda definition: definition.map_definition_version)


KNOWN_MAP_IDS: tuple[str, ...] = tuple(
    sorted({registered_id for (registered_id, _v) in _REGISTRY})
)
