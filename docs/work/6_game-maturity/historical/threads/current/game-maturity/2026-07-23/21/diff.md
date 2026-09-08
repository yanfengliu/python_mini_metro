diff --git a/src/env.py b/src/env.py
index d6506f7..eef8271 100644
--- a/src/env.py
+++ b/src/env.py
@@ -228,6 +228,14 @@ class MiniMetroEnv:
                 "carriages_assigned": self.mediator.assigned_carriages,
                 "carriages_available": self.mediator.available_carriages,
             },
+            # GM-09c: a SIBLING of "fleet" (never inside it), so the checkpoint's
+            # exact fleet-key whitelist is untouched and _normalize_observation
+            # ignores this block; None on an unbounded map (CLASSIC).
+            "tunnels": {
+                "total": self.mediator.num_tunnels,
+                "consumed": self.mediator.consumed_tunnels,
+                "available": self.mediator.available_tunnels,
+            },
             "deliveries": self.mediator.deliveries,
             "line_credits": self.mediator.line_credits,
             "score": self.mediator.score,
diff --git a/src/maps.py b/src/maps.py
index 6078117..317b095 100644
--- a/src/maps.py
+++ b/src/maps.py
@@ -71,6 +71,10 @@ class MapDefinition:
     unique_spawn_chance: float
     spawn_regions: tuple[Rect, ...] = ()
     rivers: tuple[Rect, ...] = ()
+    # The finite tunnel/bridge budget for crossing this map's rivers (GM-09c).
+    # None = unbounded (no river to cross, e.g. CLASSIC); an int caps the total
+    # river crossings across all lines.
+    tunnel_budget: int | None = None

     def __post_init__(self) -> None:
         # Enforce deep immutability rather than trust the caller: coerce the
@@ -83,6 +87,13 @@ class MapDefinition:
             self, "spawn_regions", _coerce_rects(self.spawn_regions, "spawn_regions")
         )
         object.__setattr__(self, "rivers", _coerce_rects(self.rivers, "rivers"))
+        budget = self.tunnel_budget
+        if budget is not None and (
+            isinstance(budget, bool) or not isinstance(budget, int) or budget < 0
+        ):
+            raise ValueError(
+                f"tunnel_budget must be None or a non-negative integer; got {budget!r}"
+            )


 CLASSIC = MapDefinition(
@@ -120,6 +131,9 @@ RIVER = MapDefinition(
     unique_spawn_chance=station_unique_spawn_chance,
     spawn_regions=(_LEFT_BANK, _RIGHT_BANK),
     rivers=(_RIVER_BAND,),
+    # A finite tunnel budget makes the river a real constraint while leaving a
+    # connected cross-river network buildable (tunable; verified playable).
+    tunnel_budget=3,
 )

 _REGISTRY: dict[tuple[str, int], MapDefinition] = {
diff --git a/src/mediator.py b/src/mediator.py
index 690f084..e27034d 100644
--- a/src/mediator.py
+++ b/src/mediator.py
@@ -28,6 +28,7 @@ from config import (
     screen_width,
     station_unlock_milestones,
 )
+from crossings import path_crossings
 from entity.carriage import Carriage
 from entity.get_entity import get_random_stations
 from entity.metro import Metro
@@ -246,6 +247,50 @@ class Mediator:

         return max(0, self.num_carriages - self.assigned_carriages)

+    @property
+    def num_tunnels(self) -> int | None:
+        """The map's river-crossing budget (GM-09c); None = unbounded (CLASSIC).
+
+        DERIVED live from `map_definition` — not a cached field — so it always
+        agrees with `consumed_tunnels` (which reads `map_definition.rivers`) even if
+        the map is swapped; a stale cached copy would fail open (review Codex).
+        """
+
+        return self.map_definition.tunnel_budget
+
+    @property
+    def consumed_tunnels(self) -> int:
+        """Total river crossings across all COMMITTED lines (GM-09c).
+
+        DERIVED from live-path centerlines (like available_locomotives), so it
+        owns no stored state and every route-edit rollback restores it for free.
+        An in-creation draft (is_being_created) is excluded so the count is clean
+        mid-gesture; the creation gate adds the finishing path's own crossings.
+        """
+
+        rivers = self.map_definition.rivers
+        if not rivers:
+            return 0
+        return sum(
+            len(
+                path_crossings(
+                    [station.position for station in path.stations],
+                    path.is_looped,
+                    rivers,
+                )
+            )
+            for path in self.paths
+            if not getattr(path, "is_being_created", False)
+        )
+
+    @property
+    def available_tunnels(self) -> int | None:
+        """Remaining tunnel budget, or None when the map is unbounded (CLASSIC)."""
+
+        if self.num_tunnels is None:
+            return None
+        return max(0, self.num_tunnels - self.consumed_tunnels)
+
     @property
     def purchased_num_paths(self) -> int:
         return self._progression.purchased_num_paths
diff --git a/src/path_lifecycle.py b/src/path_lifecycle.py
index 5d89f43..cdec432 100644
--- a/src/path_lifecycle.py
+++ b/src/path_lifecycle.py
@@ -3,6 +3,7 @@ from __future__ import annotations
 from collections.abc import Callable
 from typing import Any, Protocol

+from crossings import within_tunnel_budget
 from path_removal_snapshot import restore_removal_state, snapshot_removal_state
 from path_replacement import replace_path as replace_path_transaction

@@ -406,28 +407,53 @@ class PathLifecycle:

     def finish_path_creation(self, host: PathLifecycleHost) -> None:
         assert host.path_being_created is not None
+        draft = host.path_being_created
+        # GM-09c commit-boundary guard: clearing is_being_created is the moment a
+        # draft becomes a COUNTED crossing, so the authoritative budget check lives
+        # here and counts the REAL draft (`draft.stations`/`is_looped`), never a
+        # route predicted from raw indices -- this also catches a direct
+        # start/add/finish that bypasses end_path_on_station (review Codex). Over
+        # budget -> the ordinary abort (unchanged from pre-GM-09c: it removes the
+        # draft and frees its color; a transient snap-blip from the drag fades as it
+        # always has, so CLASSIC stays byte-identical). No crossing commits.
+        if not within_tunnel_budget(
+            host, draft.stations, draft.is_looped, exclude=draft
+        ):
+            host.abort_path_creation()
+            return
         host.is_creating_path = False
-        host.path_being_created.is_being_created = False
-        host.path_being_created.remove_temporary_point()
+        draft.is_being_created = False
+        draft.remove_temporary_point()
         host.path_being_created = None
         host.assign_paths_to_buttons()

     def end_path_on_station(self, host: PathLifecycleHost, station: Any) -> None:
         assert host.path_being_created is not None
-        if (
-            len(host.path_being_created.stations) > 1
-            and host.path_being_created.stations[-1] == station
-        ):
-            host.finish_path_creation()
-        elif (
-            len(host.path_being_created.stations) > 1
-            and host.path_being_created.stations[0] == station
-        ):
-            host.path_being_created.set_loop()
-            host.finish_path_creation()
-        elif host.path_being_created.stations[0] != station:
-            host.path_being_created.add_station(station)
-            station.start_snap_blip(host.time_ms, host.path_being_created.color)
-            host.finish_path_creation()
+        creating = host.path_being_created
+        stations = creating.stations
+        if len(stations) > 1 and stations[-1] == station:
+            action = "finish"
+        elif len(stations) > 1 and stations[0] == station:
+            action = "loop"
+        elif stations[0] != station:
+            action = "extend"
         else:
             host.abort_path_creation()
+            return
+        # GM-09c tunnel-budget gate on the RESOLVED route (the real draft plus the
+        # ending station), so it counts exactly what commits -- an explicit-closure
+        # loop [X,Y,X] resolves to the 2-station loop [X,Y] (one crossing), never
+        # the raw round trip (review re-review). Gated BEFORE the extend/loop
+        # mutation, so an over-budget release adds no station and commits no
+        # crossing; the ordinary abort (unchanged) removes the draft.
+        final_stations = list(stations) + ([station] if action == "extend" else [])
+        final_loop = bool(creating.is_looped) or action == "loop"
+        if not within_tunnel_budget(host, final_stations, final_loop, exclude=creating):
+            host.abort_path_creation()
+            return
+        if action == "loop":
+            creating.set_loop()
+        elif action == "extend":
+            creating.add_station(station)
+            station.start_snap_blip(host.time_ms, creating.color)
+        host.finish_path_creation()
diff --git a/src/path_replacement.py b/src/path_replacement.py
index b32e289..f6e0bb9 100644
--- a/src/path_replacement.py
+++ b/src/path_replacement.py
@@ -6,6 +6,7 @@ import math
 from dataclasses import dataclass
 from typing import Any

+from crossings import within_tunnel_budget
 from path_replacement_geometry import (
     build_candidate,
     is_canonical_point,
@@ -444,6 +445,9 @@ def replace_path(
     ):
         return True

+    if not within_tunnel_budget(host, stations, loop, exclude=path):
+        return False
+
     candidate = build_candidate(
         path,
         stations,
diff --git a/src/rendering/game_renderer.py b/src/rendering/game_renderer.py
index f8db1bd..24a5155 100644
--- a/src/rendering/game_renderer.py
+++ b/src/rendering/game_renderer.py
@@ -11,7 +11,7 @@ from .interpolation import MetroInterpolator
 from .layout import MetroPose
 from .network_renderer import NetworkRenderer
 from .path_handle_renderer import PathHandleRenderer, removal_on_layout
-from .terrain_renderer import draw_terrain
+from .terrain_renderer import draw_crossings, draw_terrain


 def _config() -> Any:
@@ -101,6 +101,10 @@ class GameRenderer:
         draw_terrain(surface, getattr(state, "map_definition", None))
         paths = tuple(getattr(state, "paths", ()))
         layouts = self.network_renderer.draw(surface, paths)
+        # A tunnel-portal marker where each line crosses a river, ON TOP of the
+        # lines (trains then pass over it). CLASSIC (no rivers) draws nothing, so
+        # the CLASSIC frame stays byte-identical (GM-09c).
+        draw_crossings(surface, getattr(state, "map_definition", None), paths)
         layouts_by_path_id = {layout.path_id: layout for layout in layouts}
         paths_by_id = {str(getattr(path, "id", id(path))): path for path in paths}
         current_time_ms = int(getattr(state, "time_ms", 0))
diff --git a/src/rendering/terrain_renderer.py b/src/rendering/terrain_renderer.py
index 5c45704..5cbacd9 100644
--- a/src/rendering/terrain_renderer.py
+++ b/src/rendering/terrain_renderer.py
@@ -14,6 +14,9 @@ import pygame

 # Light steel-blue water; a per-map render concern kept out of the balance config.
 RIVER_COLOR = (176, 196, 222)
+# A tunnel/bridge portal marker where a line crosses the river.
+CROSSING_MARKER_COLOR = (40, 40, 60)
+CROSSING_MARKER_RADIUS = 9


 def draw_terrain(surface: pygame.Surface, map_definition) -> None:
@@ -29,3 +32,28 @@ def draw_terrain(surface: pygame.Surface, map_definition) -> None:
                 round(left), round(top), round(right - left), round(bottom - top)
             ),
         )
+
+
+def draw_crossings(surface: pygame.Surface, map_definition, paths) -> None:
+    """Draw a tunnel-portal marker where each line crosses the river, ON TOP of the
+    network (unlike the terrain band, which sits under it). A map with no rivers
+    (CLASSIC) draws nothing (GM-09c)."""
+    rivers = getattr(map_definition, "rivers", ()) or ()
+    if not rivers:
+        return
+    # Lazy import: a rendering module reaches a src-level sibling inside the
+    # function (as network_renderer does with config) so the package stays
+    # importable both as ``rendering`` and as ``src.rendering`` during discovery.
+    from crossings import path_crossings
+
+    for path in paths:
+        positions = [station.position for station in getattr(path, "stations", ())]
+        for point in path_crossings(
+            positions, getattr(path, "is_looped", False), rivers
+        ):
+            pygame.draw.circle(
+                surface,
+                CROSSING_MARKER_COLOR,
+                (round(point.left), round(point.top)),
+                CROSSING_MARKER_RADIUS,
+            )

=== NEW: src/crossings.py ===
diff --git a/src/crossings.py b/src/crossings.py
new file mode 100644
index 0000000..db4a9e2
--- /dev/null
+++ b/src/crossings.py
@@ -0,0 +1,124 @@
+"""GM-09c river-crossing geometry (D-035).
+
+Pure, dependency-light: imports only ``geometry.point`` and reads plain
+``(left, top, right, bottom)`` river-band tuples (from a ``MapDefinition``) — no
+``pygame``, ``shapely``, ``entity``, or ``mediator`` — so it is import-safe for
+every headless/RL path and consumed one-way by the mediator, the route-edit gate,
+and the renderer.
+
+A crossing is counted on a path's CENTERLINE (consecutive ``station.position``
+pairs plus the loop closure), never the lane-offset ``PathSegment`` geometry,
+which is ``path_order``-dependent and ``round()``-quantized (non-deterministic
+w.r.t. the logical route). So a line's crossing count depends only on its own
+stations, and ``available_tunnels`` derived from it needs no snapshot state.
+"""
+
+from __future__ import annotations
+
+from collections.abc import Sequence
+
+from geometry.point import Point
+
+Band = tuple[float, float, float, float]
+
+
+def segment_crosses_band(start: Point, end: Point, band: Band) -> Point | None:
+    """Return the ENTRY point where segment start→end first enters the axis-aligned
+    ``band`` (Liang-Barsky), or None if it does not cross. A mere grazing touch
+    (a zero-length overlap, ``t_enter == t_exit``) does NOT count as a crossing —
+    a determinism tie-break so a future diagonal river cannot flip counts.
+
+    Boundary semantics: a segment with a POSITIVE-length overlap that runs along a
+    band EDGE (collinear) does count. This is unreachable for the current
+    eroded-bank maps — a centerline between two banks can never lie on the river's
+    edge (stations are inset by ``station_size``), and consecutive stations are
+    distinct so a zero-length interior segment cannot arise. Strict-interior-only
+    semantics are deferred (with a test) to the first map that can actually place a
+    line along a river edge (review Codex MINOR)."""
+    left, top, right, bottom = band
+    ax, ay = float(start.left), float(start.top)
+    dx, dy = float(end.left) - ax, float(end.top) - ay
+    t_enter, t_exit = 0.0, 1.0
+    for p, q in (
+        (-dx, ax - left),
+        (dx, right - ax),
+        (-dy, ay - top),
+        (dy, bottom - ay),
+    ):
+        if p == 0.0:
+            if q < 0.0:
+                return None  # parallel to this edge and wholly outside it
+        else:
+            r = q / p
+            if p < 0.0:
+                if r > t_exit:
+                    return None
+                t_enter = max(t_enter, r)
+            else:
+                if r < t_enter:
+                    return None
+                t_exit = min(t_exit, r)
+    if t_enter >= t_exit:
+        # Empty overlap (miss) or a zero-length grazing touch -> not a crossing.
+        return None
+    return Point(round(ax + t_enter * dx), round(ay + t_enter * dy))
+
+
+def _centerline_segments(
+    positions: Sequence[Point], is_looped: bool
+) -> list[tuple[Point, Point]]:
+    segments = [(positions[i], positions[i + 1]) for i in range(len(positions) - 1)]
+    # The loop closure adds a NEW segment only for 3+ stations; a 2-station loop's
+    # closure RETRACES the single segment, so counting it would double-charge one
+    # physical crossing (review Codex).
+    if is_looped and len(positions) >= 3:
+        segments.append((positions[-1], positions[0]))
+    return segments
+
+
+def path_crossings(
+    positions: Sequence[Point], is_looped: bool, rivers: Sequence[Band]
+) -> tuple[Point, ...]:
+    """Every river-band entry point on the path's centerline (one per crossing)."""
+    if not rivers or len(positions) < 2:
+        return ()
+    crossings: list[Point] = []
+    for start, end in _centerline_segments(positions, is_looped):
+        for band in rivers:
+            point = segment_crosses_band(start, end, band)
+            if point is not None:
+                crossings.append(point)
+    return tuple(crossings)
+
+
+def within_tunnel_budget(
+    host: object, stations: Sequence, is_looped: bool, *, exclude: object = None
+) -> bool:
+    """The single route-edit gate for both creation and reroute (GM-09c).
+
+    Would a line over ``stations`` (looped or not) fit ``host``'s finite tunnel
+    budget? Counts the CANDIDATE line's crossings plus every committed line's
+    crossings EXCEPT ``exclude`` (the draft being finished or the line being
+    rerouted) and any line still being drafted. A None budget (CLASSIC, or any map
+    without rivers) is always within budget. Read-only, so a rejected edit mutates
+    nothing; ``available_tunnels`` is derived, so a later removal/reroute refunds
+    for free. Reads the host by duck-typed ``getattr`` so this module imports no
+    gameplay code and stays import-safe for every headless/RL path. The budget and
+    the rivers come from the SAME ``map_definition`` (not a cached ``num_tunnels``
+    field), so a swapped map or a host without that field can never fail open on a
+    finite map (review Codex).
+    """
+    map_definition = getattr(host, "map_definition", None)
+    num_tunnels = getattr(map_definition, "tunnel_budget", None)
+    if num_tunnels is None:
+        return True
+    rivers = getattr(map_definition, "rivers", ())
+    if not rivers:
+        return True
+    candidate = len(path_crossings([s.position for s in stations], is_looped, rivers))
+    others = sum(
+        len(path_crossings([s.position for s in path.stations], path.is_looped, rivers))
+        for path in getattr(host, "paths", ())
+        if path is not exclude and not getattr(path, "is_being_created", False)
+    )
+    return candidate + others <= num_tunnels
=== NEW: test/test_gm09c_crossings.py ===
diff --git a/test/test_gm09c_crossings.py b/test/test_gm09c_crossings.py
new file mode 100644
index 0000000..3df56c9
--- /dev/null
+++ b/test/test_gm09c_crossings.py
@@ -0,0 +1,375 @@
+"""GM-09c contract: river-crossing tunnel budget (D-035).
+
+A river map carries a finite ``tunnel_budget``; every point where a line's
+CENTERLINE crosses a river band consumes one tunnel. The count is DERIVED from the
+live network (never a stored counter), so removing or rerouting a line refunds its
+crossings for free and a failed edit can leave no stale charge. The route-edit gate
+rejects a creation or reroute that would exceed the budget BEFORE mutating anything.
+CLASSIC (no rivers) is unbounded and byte-identical. The env exposes a ``tunnels``
+observation block as a SIBLING of ``fleet`` so the canonical checkpoint is untouched.
+"""
+
+from __future__ import annotations
+
+import os
+import subprocess
+import sys
+import unittest
+
+sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
+
+import pygame
+
+from crossings import _centerline_segments, path_crossings, segment_crosses_band
+from geometry.point import Point
+from maps import CLASSIC, RIVER
+from mediator import Mediator
+
+# A synthetic vertical band x in [10, 20] for the pure-geometry cases.
+_BAND = (10.0, 0.0, 20.0, 100.0)
+# seed=0 RIVER stations: 0 -> right bank (x~1232), 1 -> right (x~1132), 2 -> left (x~584).
+# So [2, 0] is the canonical single-crossing line and [0, 1] is same-bank (no cross).
+_LEFT, _RIGHT, _RIGHT2 = 2, 0, 1
+
+
+def _river_mediator(seed: int = 0, *, paths: int = 6) -> Mediator:
+    """A RIVER mediator with the path limit raised so a test can build several
+    crossing lines from the three starting stations without hitting the path cap."""
+    mediator = Mediator(seed=seed, map_definition=RIVER)
+    mediator.num_paths = paths
+    mediator.unlocked_num_paths = paths
+    return mediator
+
+
+class TestGM09cCrossingGeometry(unittest.TestCase):
+    """The pure geometry: no mediator, no pygame."""
+
+    def test_clear_crossing_returns_entry_point_on_the_near_edge(self):
+        entry = segment_crosses_band(Point(0, 50), Point(30, 50), _BAND)
+        self.assertIsNotNone(entry)
+        self.assertEqual((entry.left, entry.top), (10, 50))
+
+    def test_segment_wholly_on_either_side_does_not_cross(self):
+        self.assertIsNone(segment_crosses_band(Point(0, 50), Point(5, 50), _BAND))
+        self.assertIsNone(segment_crosses_band(Point(25, 50), Point(40, 50), _BAND))
+
+    def test_parallel_outside_segment_does_not_cross(self):
+        self.assertIsNone(segment_crosses_band(Point(5, 0), Point(5, 100), _BAND))
+
+    def test_corner_tangency_is_not_a_crossing(self):
+        # A segment that only grazes a corner (t_enter == t_exit) is a determinism
+        # tie-break: it must NOT count, so no future diagonal river can flip counts.
+        self.assertIsNone(segment_crosses_band(Point(10, -10), Point(30, 10), _BAND))
+
+    def test_two_station_loop_closure_does_not_double_charge(self):
+        # A 2-station loop's closure RETRACES the single segment; counting it would
+        # charge one physical crossing twice (review Codex).
+        positions = [Point(0, 50), Point(30, 50)]
+        self.assertEqual(len(_centerline_segments(positions, True)), 1)
+        self.assertEqual(len(path_crossings(positions, True, (_BAND,))), 1)
+
+    def test_three_station_loop_counts_the_closure_crossing(self):
+        # left, right, right; closed -> A->B crosses, B->C stays right, C->A crosses.
+        tri = [Point(0, 50), Point(30, 20), Point(30, 80)]
+        self.assertEqual(len(_centerline_segments(tri, True)), 3)
+        self.assertEqual(len(path_crossings(tri, True, (_BAND,))), 2)
+        # Open (unlooped) the same three stations cross only once.
+        self.assertEqual(len(path_crossings(tri, False, (_BAND,))), 1)
+
+    def test_multiple_bands_each_count(self):
+        second = (50.0, 0.0, 60.0, 100.0)
+        crossings = path_crossings(
+            [Point(0, 50), Point(100, 50)], False, (_BAND, second)
+        )
+        self.assertEqual(len(crossings), 2)
+
+    def test_no_rivers_or_too_few_positions_is_empty(self):
+        self.assertEqual(path_crossings([Point(0, 50), Point(30, 50)], False, ()), ())
+        self.assertEqual(path_crossings([Point(0, 50)], False, (_BAND,)), ())
+
+
+class TestGM09cDerivedCounts(unittest.TestCase):
+    """Mediator-level consumed/available derived from the live network."""
+
+    def test_river_starts_at_full_budget(self):
+        mediator = Mediator(seed=0, map_definition=RIVER)
+        self.assertEqual(mediator.num_tunnels, 3)
+        self.assertEqual(mediator.consumed_tunnels, 0)
+        self.assertEqual(mediator.available_tunnels, 3)
+
+    def test_crossing_line_consumes_one_tunnel(self):
+        mediator = _river_mediator()
+        mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        self.assertEqual(mediator.consumed_tunnels, 1)
+        self.assertEqual(mediator.available_tunnels, 2)
+
+    def test_same_bank_line_consumes_no_tunnel(self):
+        mediator = _river_mediator()
+        mediator.create_path_from_station_indices([_RIGHT, _RIGHT2])
+        self.assertEqual(mediator.consumed_tunnels, 0)
+        self.assertEqual(mediator.available_tunnels, 3)
+
+    def test_removing_a_crossing_line_refunds_its_tunnel(self):
+        mediator = _river_mediator()
+        path = mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        self.assertEqual(mediator.consumed_tunnels, 1)
+        mediator.remove_path(path)
+        self.assertEqual(mediator.consumed_tunnels, 0)
+        self.assertEqual(mediator.available_tunnels, 3)
+
+    def test_num_tunnels_is_derived_from_the_map_not_cached(self):
+        # num_tunnels must track map_definition live (like consumed_tunnels reads
+        # map_definition.rivers), so a swapped map stays consistent; a field cached
+        # at construction would fail open on a finite map (review Codex MAJOR).
+        mediator = Mediator(seed=1)  # CLASSIC, unbounded
+        self.assertIsNone(mediator.num_tunnels)
+        mediator.map_definition = RIVER
+        self.assertEqual(mediator.num_tunnels, 3)
+        self.assertEqual(mediator.available_tunnels, 3)
+
+
+class TestGM09cCreationGate(unittest.TestCase):
+    def test_creation_over_budget_is_rejected_without_consuming(self):
+        mediator = _river_mediator()
+        for _ in range(3):
+            self.assertIsNotNone(
+                mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+            )
+        self.assertEqual(mediator.consumed_tunnels, 3)
+        self.assertEqual(mediator.available_tunnels, 0)
+        before_paths = len(mediator.paths)
+        rejected = mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        self.assertIsNone(rejected, "a 4th crossing exceeds the budget of 3")
+        self.assertEqual(mediator.consumed_tunnels, 3, "rejection consumes nothing")
+        self.assertEqual(len(mediator.paths), before_paths, "no ghost path is left")
+
+    def test_same_bank_line_is_allowed_at_zero_budget(self):
+        # A non-crossing line needs no tunnel, so it builds even when the budget is
+        # fully spent -- the constraint is on crossings, not on lines.
+        mediator = _river_mediator()
+        for _ in range(3):
+            mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        self.assertEqual(mediator.available_tunnels, 0)
+        built = mediator.create_path_from_station_indices([_RIGHT, _RIGHT2])
+        self.assertIsNotNone(built)
+        self.assertEqual(mediator.consumed_tunnels, 3)
+
+    def test_direct_finish_cannot_bypass_the_budget(self):
+        # finish_path_creation is the COMMIT boundary (clearing is_being_created is
+        # what makes a draft count). A direct start/add/finish that skips
+        # end_path_on_station's preflight must still be caught there, or the budget
+        # is bypassable (review Codex MAJOR).
+        mediator = _river_mediator()
+        for _ in range(3):
+            mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        self.assertEqual(mediator.available_tunnels, 0)
+        paths_before = len(mediator.paths)
+        mediator.start_path_on_station(mediator.stations[_LEFT])
+        mediator.add_station_to_path(mediator.stations[_RIGHT])
+        mediator.finish_path_creation()  # a 4th crossing -- must be rejected here
+        self.assertEqual(
+            mediator.consumed_tunnels, 3, "commit boundary rejects over-budget"
+        )
+        self.assertEqual(len(mediator.paths), paths_before, "no ghost path committed")
+        self.assertIsNone(mediator.path_being_created, "draft aborted cleanly")
+
+    def test_rejected_multistation_creation_commits_and_draws_nothing(self):
+        # A rejected over-budget creation commits NO crossing, leaves NO ghost path,
+        # and draws NO RNG. (It may leave a transient snap-blip on a station the
+        # aborted drag touched -- exactly the feedback an ordinary drag-abort paints,
+        # unchanged from pre-GM-09c, so CLASSIC's abort stays byte-identical; a
+        # re-review showed that scoping a blip-rollback into abort instead broke
+        # that invariant.) The RNG and path count are the load-bearing guarantees.
+        from env import MiniMetroEnv
+        from recursive_checkpoint import canonical_checkpoint
+
+        mediator = _river_mediator()
+        for _ in range(3):
+            mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        self.assertEqual(mediator.available_tunnels, 0)
+        env = MiniMetroEnv()
+        env.mediator = mediator
+        before = canonical_checkpoint(env)
+        paths_before = len(mediator.paths)
+        # [_LEFT, _RIGHT, _RIGHT2] crosses once (L->R), so 1 + 3 committed = 4 > 3.
+        rejected = mediator.create_path_from_station_indices([_LEFT, _RIGHT, _RIGHT2])
+        after = canonical_checkpoint(env)
+        self.assertIsNone(rejected)
+        self.assertEqual(mediator.consumed_tunnels, 3, "no crossing is committed")
+        self.assertEqual(len(mediator.paths), paths_before, "no ghost path")
+        self.assertIsNone(mediator.path_being_created, "draft aborted")
+        self.assertEqual(
+            before["rng"], after["rng"], "a rejected creation draws no RNG"
+        )
+
+    def test_explicit_closure_loop_is_not_false_rejected(self):
+        # A there-and-back index list [X, Y, X] with loop=True builds a 2-STATION
+        # loop [X, Y], whose retraced closure crosses the river ONCE -- not the raw
+        # round trip's two. The gate must count the RESOLVED route, or a valid
+        # within-budget loop is wrongly rejected (re-review MAJOR: a raw-index
+        # pre-check counted 2 and rejected a total of 3 <= 3).
+        mediator = _river_mediator()
+        mediator.create_path_from_station_indices([_LEFT, _RIGHT])  # consumed 1
+        mediator.create_path_from_station_indices([_LEFT, _RIGHT2])  # consumed 2
+        self.assertEqual(mediator.consumed_tunnels, 2)
+        looped = mediator.create_path_from_station_indices(
+            [_LEFT, _RIGHT, _LEFT], loop=True
+        )
+        self.assertIsNotNone(
+            looped, "the 2-station loop crosses once; 2+1=3 is in budget"
+        )
+        self.assertTrue(looped.is_looped)
+        self.assertEqual(mediator.consumed_tunnels, 3)
+
+
+class TestGM09cRerouteGate(unittest.TestCase):
+    def test_reroute_that_would_exceed_budget_is_rejected(self):
+        mediator = _river_mediator()
+        for _ in range(3):
+            mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        same_bank = mediator.create_path_from_station_indices([_RIGHT, _RIGHT2])
+        self.assertEqual(mediator.consumed_tunnels, 3)
+        # Rerouting the same-bank line to cross would be a 4th crossing -> rejected.
+        rejected = mediator.replace_path(same_bank, [_RIGHT2, _LEFT])
+        self.assertFalse(rejected)
+        self.assertEqual(mediator.consumed_tunnels, 3, "a rejected reroute is inert")
+
+    def test_reroute_crossing_line_to_same_bank_refunds(self):
+        mediator = _river_mediator()
+        crossing = mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        self.assertEqual(mediator.consumed_tunnels, 1)
+        ok = mediator.replace_path(crossing, [_RIGHT, _RIGHT2])
+        self.assertTrue(ok)
+        self.assertEqual(mediator.consumed_tunnels, 0, "the freed crossing is refunded")
+        self.assertEqual(mediator.available_tunnels, 3)
+
+
+class TestGM09cClassicUnbounded(unittest.TestCase):
+    def test_classic_has_no_tunnel_constraint(self):
+        mediator = Mediator(seed=0)  # default CLASSIC
+        mediator.num_paths = 5
+        mediator.unlocked_num_paths = 5
+        self.assertIsNone(mediator.num_tunnels)
+        self.assertIsNone(mediator.available_tunnels)
+        self.assertEqual(mediator.consumed_tunnels, 0)
+        # Any line builds; the derived count stays 0 and available stays None.
+        mediator.create_path_from_station_indices([0, 1])
+        self.assertEqual(mediator.consumed_tunnels, 0)
+        self.assertIsNone(mediator.available_tunnels)
+
+
+class TestGM09cObservation(unittest.TestCase):
+    def _observe(self, mediator):
+        from env import MiniMetroEnv
+
+        env = MiniMetroEnv()
+        env.mediator = mediator
+        return env.observe()
+
+    def test_river_observation_exposes_the_tunnel_block(self):
+        obs = self._observe(Mediator(seed=0, map_definition=RIVER))
+        self.assertEqual(
+            obs["structured"]["tunnels"],
+            {"total": 3, "consumed": 0, "available": 3},
+        )
+
+    def test_tunnel_block_tracks_consumption(self):
+        mediator = _river_mediator()
+        mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        obs = self._observe(mediator)
+        self.assertEqual(
+            obs["structured"]["tunnels"],
+            {"total": 3, "consumed": 1, "available": 2},
+        )
+
+    def test_classic_observation_reports_unbounded(self):
+        obs = self._observe(Mediator(seed=0))
+        self.assertEqual(
+            obs["structured"]["tunnels"],
+            {"total": None, "consumed": 0, "available": None},
+        )
+
+    def test_tunnels_is_a_sibling_not_a_fleet_key(self):
+        # The block MUST NOT live inside "fleet" -- the canonical checkpoint asserts
+        # an EXACT fleet-key set, so an extra fleet key would break every map.
+        obs = self._observe(Mediator(seed=0, map_definition=RIVER))
+        self.assertNotIn("tunnels", obs["structured"]["fleet"])
+        self.assertIn("tunnels", obs["structured"])
+
+
+class TestGM09cCheckpoint(unittest.TestCase):
+    def _checkpoint(self, mediator):
+        from env import MiniMetroEnv
+        from recursive_checkpoint import canonical_checkpoint
+
+        env = MiniMetroEnv()
+        env.mediator = mediator
+        return canonical_checkpoint(env)
+
+    def test_checkpoint_is_valid_on_a_river_env(self):
+        # The sibling tunnels block is ignored by _normalize_observation's fixed
+        # whitelist, so the checkpoint of a river game raises nothing.
+        cp = self._checkpoint(Mediator(seed=0, map_definition=RIVER))
+        self.assertIn("structured", cp)
+
+    def test_checkpoint_is_valid_after_a_crossing(self):
+        mediator = _river_mediator()
+        mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        cp = self._checkpoint(mediator)
+        self.assertIn("structured", cp)
+
+
+class TestGM09cRender(unittest.TestCase):
+    def test_crossing_marker_paints_on_a_river_line_and_nothing_on_classic(self):
+        from rendering.terrain_renderer import draw_crossings
+
+        mediator = _river_mediator()
+        mediator.create_path_from_station_indices([_LEFT, _RIGHT])
+        paths = list(mediator.paths)
+        surface = pygame.Surface((1920, 1080))
+        surface.fill((247, 245, 239))
+        before = surface.copy()
+        # CLASSIC (no rivers) paints nothing even with crossing-shaped lines.
+        draw_crossings(surface, CLASSIC, paths)
+        self.assertEqual(surface.get_view("2").raw, before.get_view("2").raw)
+        # RIVER with a crossing line paints a marker.
+        draw_crossings(surface, RIVER, paths)
+        self.assertNotEqual(surface.get_view("2").raw, before.get_view("2").raw)
+
+    def test_no_crossing_line_paints_no_marker(self):
+        from rendering.terrain_renderer import draw_crossings
+
+        mediator = _river_mediator()
+        mediator.create_path_from_station_indices([_RIGHT, _RIGHT2])  # same bank
+        surface = pygame.Surface((1400, 1080))
+        surface.fill((247, 245, 239))
+        before = surface.copy()
+        draw_crossings(surface, RIVER, list(mediator.paths))
+        self.assertEqual(
+            surface.get_view("2").raw,
+            before.get_view("2").raw,
+            "a same-bank line has no crossing to mark",
+        )
+
+
+class TestGM09cImportSafety(unittest.TestCase):
+    def test_crossings_pulls_no_pygame_mediator_or_shapely(self):
+        code = (
+            "import sys; sys.path.insert(0, 'src'); import crossings; "
+            "bad=[m for m in ('pygame','mediator','shapely','geometry.polygon',"
+            "'entity.station') if m in sys.modules]; "
+            "print('LEAK' if bad else 'CLEAN', bad)"
+        )
+        result = subprocess.run(
+            [sys.executable, "-c", code],
+            capture_output=True,
+            text=True,
+            cwd=os.path.dirname(os.path.realpath(__file__)) + "/..",
+        )
+        self.assertIn(
+            "CLEAN", result.stdout, f"crossings leaked: {result.stdout}{result.stderr}"
+        )
+
+
+if __name__ == "__main__":
+    unittest.main()
