"""GM-09e contract: the third alternate map -- LAKE (D-037).

A single central lake -- a bounded water body spanning NO screen edge -- reuses the
GM-09b/GM-09c map layer but adds a distinct axis: a PARTIAL band (bounded in x AND
y) that can OFTEN be DETOURED around as well as tunneled through. A line whose
centerline passes through the lake spends a tunnel; a line routed around it (bending
at an intermediate station beside the lake) spends none. The budget still limits
TOTAL crossings as on the rivers -- a station whose only routes cross the lake is
gated until a tunnel is freed -- so the lake makes crossing more often avoidable, not
always. CLASSIC/RIVER/DELTA stay byte-identical (purely additive).
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_height, screen_width, station_size
from crossings import path_crossings
from geometry.point import Point
from maps import CLASSIC, DELTA, KNOWN_MAP_IDS, LAKE, RIVER, map_by_id, resolve_map
from mediator import Mediator

_LAKE = LAKE.rivers[0]


def _in_lake(x: float, y: float) -> bool:
    return _LAKE[0] <= x <= _LAKE[2] and _LAKE[1] <= y <= _LAKE[3]


class TestGM09eLakeDefinition(unittest.TestCase):
    def test_lake_is_registered_and_resolvable(self):
        self.assertEqual(LAKE.map_id, "lake")
        self.assertEqual(LAKE.map_definition_version, 1)
        self.assertIs(resolve_map("lake", 1), LAKE)
        self.assertIs(map_by_id("lake"), LAKE)
        # Membership, not an exact tuple, so later maps do not break this test.
        self.assertIn("lake", KNOWN_MAP_IDS)
        self.assertIn("classic", KNOWN_MAP_IDS)

    def test_lake_has_one_bounded_water_body_and_a_land_frame(self):
        self.assertEqual(len(LAKE.rivers), 1)
        self.assertEqual(len(LAKE.spawn_regions), 4)
        self.assertEqual(LAKE.tunnel_budget, 3)
        for region in (*LAKE.spawn_regions, *LAKE.rivers):
            left, top, right, bottom = region
            self.assertLess(left, right, "positive-width rect")
            self.assertLess(top, bottom, "positive-height rect")

    def test_lake_is_a_partial_band_spanning_no_screen_edge(self):
        # The distinguishing property vs RIVER/DELTA: the water is bounded on ALL
        # four sides (spans neither the full width nor the full height), so it can be
        # routed around.
        left, top, right, bottom = _LAKE
        self.assertGreater(left, 0, "lake does not touch the left edge")
        self.assertLess(right, screen_width, "lake does not touch the right edge")
        self.assertGreater(top, 0, "lake does not touch the top edge")
        self.assertLess(bottom, screen_height, "lake does not touch the bottom edge")


class TestGM09eRegionSpawn(unittest.TestCase):
    def test_stations_spawn_in_all_four_frame_strips_and_never_in_the_lake(self):
        # Each frame strip covers a region no other strip does: top/bottom cover the
        # band directly above/below the lake (in its x-range), left/right cover the
        # flanks beside it (in its y-range). Asserting all four are reached catches a
        # missing or duplicated strip (review Codex); the center-clearance check
        # catches a station in or on the water.
        strips_reached = set()
        for seed in range(40):
            mediator = Mediator(seed=seed, map_definition=LAKE)
            for station in mediator.all_stations:
                x, y = station.position.left, station.position.top
                self.assertFalse(_in_lake(x, y), f"station ({x},{y}) is in the lake")
                self.assertFalse(
                    _LAKE[0] - station_size < x < _LAKE[2] + station_size
                    and _LAKE[1] - station_size < y < _LAKE[3] + station_size,
                    f"station ({x},{y}) center is within station_size of the lake",
                )
                if _LAKE[0] < x < _LAKE[2] and y < _LAKE[1]:
                    strips_reached.add("top")
                elif _LAKE[0] < x < _LAKE[2] and y > _LAKE[3]:
                    strips_reached.add("bottom")
                elif x < _LAKE[0] and _LAKE[1] < y < _LAKE[3]:
                    strips_reached.add("left")
                elif x > _LAKE[2] and _LAKE[1] < y < _LAKE[3]:
                    strips_reached.add("right")
        self.assertEqual(
            strips_reached,
            {"top", "bottom", "left", "right"},
            "stations reach all four frame strips",
        )

    def test_lake_construction_and_trajectory_are_deterministic(self):
        # Fingerprint construction AND a stepped RNG-driven trajectory (passenger
        # destinations): a fixed seed reproduces exactly and different seeds differ,
        # so LAKE's RNG consumption is deterministic and seed-sensitive across the
        # trajectory, not only the initial layout (the frozen CLASSIC fingerprints in
        # test_gm09a_maps guard the absolute values). Review Codex NIT.
        def project(seed):
            m = Mediator(seed=seed, map_definition=LAKE)
            m.overdue_passenger_threshold = 10**9
            for _ in range(60):
                m.increment_time(1000)
            stations = [
                (
                    type(s.shape).__name__,
                    round(s.position.left, 2),
                    round(s.position.top, 2),
                )
                for s in m.all_stations
            ]
            passengers = [
                type(p.destination_shape).__name__
                for station in m.stations
                for p in station.passengers
            ]
            return (stations, passengers)

        self.assertEqual(
            project(0), project(0), "seed 0 reproduces construction + trajectory"
        )
        self.assertNotEqual(project(0), project(1), "different seeds differ")


class TestGM09eOptionalCrossing(unittest.TestCase):
    def test_a_line_through_the_lake_crosses_but_a_detour_does_not(self):
        # The distinctive mechanic: crossing is OPTIONAL. A straight line through the
        # lake spends one tunnel; the same endpoints routed around the top spend none.
        mid_y = screen_height / 2
        left_x = _LAKE[0] - 50
        right_x = _LAKE[2] + 50
        through = path_crossings(
            [Point(left_x, mid_y), Point(right_x, mid_y)], False, LAKE.rivers
        )
        detour = path_crossings(
            [
                Point(left_x, mid_y),
                Point(left_x, 30),
                Point(right_x, 30),
                Point(right_x, mid_y),
            ],
            False,
            LAKE.rivers,
        )
        self.assertEqual(len(through), 1, "a line through the lake uses a tunnel")
        self.assertEqual(len(detour), 0, "a line routed around the lake uses none")

    def test_a_line_running_along_a_lake_edge_is_not_a_crossing(self):
        # LAKE's vertical water edges sit at integer x with no x-erosion of the
        # top/bottom banks, so a line CAN run exactly along an edge -- and that line
        # is on the boundary / dry land, not through the water interior, so it spends
        # no tunnel. Strict-interior geometry; this is the case GM-09c deferred as
        # then-unreachable and LAKE made reachable (review Codex/harness).
        left, top, right, bottom = _LAKE
        for edge_x in (left, right):
            along_edge = path_crossings(
                [Point(edge_x, top - 50), Point(edge_x, bottom + 50)],
                False,
                LAKE.rivers,
            )
            self.assertEqual(
                len(along_edge), 0, f"a line along the lake edge x={edge_x} is dry"
            )

    def test_budget_limits_crossings_and_a_non_crossing_line_stays_allowed(self):
        # The budget limits TOTAL lake crossings (like the rivers): three through-lines
        # exhaust it and a fourth crossing is rejected. A line whose centerline does
        # NOT cross the lake spends no tunnel and is allowed even at zero remaining --
        # a dry route is never blocked. (A station whose ONLY routes cross the lake IS
        # still gated until a tunnel is freed; the budget genuinely bites -- the lake
        # does not universally guarantee a detour, only more often than a channel.)
        for seed in range(200):
            mediator = Mediator(seed=seed, map_definition=LAKE)
            st = mediator.stations
            top = [i for i, s in enumerate(st) if s.position.top < _LAKE[1]]
            bottom = [i for i, s in enumerate(st) if s.position.top > _LAKE[3]]
            pair = None
            for t in top:
                for b in bottom:
                    if (
                        _LAKE[0] < st[t].position.left < _LAKE[2]
                        and _LAKE[0] < st[b].position.left < _LAKE[2]
                    ):
                        pair = [t, b]
                        break
                if pair:
                    break
            if pair is None or len(top) < 2:
                continue
            mediator.num_paths = 10
            mediator.unlocked_num_paths = 10
            for _ in range(3):
                self.assertIsNotNone(
                    mediator.create_path_from_station_indices(list(pair))
                )
            self.assertEqual(
                mediator.consumed_tunnels, 3, "three through-lines exhaust the budget"
            )
            rejected = mediator.create_path_from_station_indices(list(pair))
            self.assertIsNone(rejected, "a fourth lake crossing is rejected")
            # Two top-side stations: their straight line stays above the lake -> allowed.
            non_crossing = mediator.create_path_from_station_indices([top[0], top[1]])
            self.assertIsNotNone(
                non_crossing, "a non-crossing line is allowed at zero budget"
            )
            self.assertEqual(
                mediator.consumed_tunnels, 3, "the non-crossing line spends no tunnel"
            )
            return
        self.skipTest(
            "no seed placed a top/bottom-over-lake pair plus two top stations"
        )


class TestGM09eOtherMapsUnaffected(unittest.TestCase):
    def test_classic_river_delta_are_unchanged(self):
        self.assertEqual(CLASSIC.rivers, ())
        self.assertIsNone(CLASSIC.tunnel_budget)
        self.assertEqual(len(RIVER.rivers), 1)
        self.assertEqual(len(DELTA.rivers), 2)

    def test_classic_construction_is_byte_identical(self):
        m = Mediator(seed=0)  # default CLASSIC
        shapes = [type(s.shape).__name__ for s in m.all_stations[:3]]
        positions = [
            (round(s.position.left), round(s.position.top)) for s in m.all_stations[:3]
        ]
        self.assertEqual(shapes, ["Triangle", "Rect", "Rect"])
        self.assertEqual(positions, [(1232, 318), (1132, 474), (1213, 375)])


class TestGM09eSaveGuardAndRender(unittest.TestCase):
    def test_lake_map_is_not_serializable(self):
        from save_game import serialize_game

        with self.assertRaisesRegex(ValueError, r"lake'@1"):
            serialize_game(Mediator(seed=0, map_definition=LAKE))

    def test_terrain_paints_the_lake_interior_but_not_the_dry_corners(self):
        from rendering.terrain_renderer import RIVER_COLOR, draw_terrain

        background = (247, 245, 239)
        surface = pygame.Surface((screen_width, screen_height))
        surface.fill(background)
        draw_terrain(surface, LAKE)
        center = (int((_LAKE[0] + _LAKE[2]) / 2), int((_LAKE[1] + _LAKE[3]) / 2))
        corner = (30, 30)  # top-left dry land
        self.assertEqual(
            surface.get_at(center)[:3], RIVER_COLOR, "lake interior is water"
        )
        self.assertEqual(
            surface.get_at(corner)[:3], background, "the corner is dry land"
        )


if __name__ == "__main__":
    unittest.main()
