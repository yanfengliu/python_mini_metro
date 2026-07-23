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

from dataclasses import dataclass

from config import (
    station_shape_type_list,
    station_unique_shape_type_list,
    station_unique_spawn_chance,
    station_unique_spawn_start_index,
)
from geometry.type import ShapeType


@dataclass(frozen=True)
class MapDefinition:
    """An immutable map identity + station-shape palette.

    The palette fields are ordered ``tuple``s (not the mutable ``config`` lists),
    so a frozen ``MapDefinition`` is deeply immutable. GM-09a owns only the
    shape palette; station counts and spawn geometry stay global and are deferred
    to the terrain/progression integration units.
    """

    map_id: str
    map_definition_version: int
    shape_types: tuple[ShapeType, ...]
    unique_shape_types: tuple[ShapeType, ...]
    unique_spawn_start_index: int
    unique_spawn_chance: float

    def __post_init__(self) -> None:
        # Enforce deep immutability rather than trust the caller: coerce the
        # palettes to tuples so a future author passing a list still gets an
        # immutable definition (review NIT). frozen=True needs object.__setattr__.
        object.__setattr__(self, "shape_types", tuple(self.shape_types))
        object.__setattr__(self, "unique_shape_types", tuple(self.unique_shape_types))


CLASSIC = MapDefinition(
    map_id="classic",
    map_definition_version=1,
    shape_types=tuple(station_shape_type_list),
    unique_shape_types=tuple(station_unique_shape_type_list),
    unique_spawn_start_index=station_unique_spawn_start_index,
    unique_spawn_chance=station_unique_spawn_chance,
)

_REGISTRY: dict[tuple[str, int], MapDefinition] = {
    (CLASSIC.map_id, CLASSIC.map_definition_version): CLASSIC,
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
