"""GM-09d contract: the second alternate map -- DELTA (D-036).

Two vertical rivers split the play area into THREE land banks. It reuses the
proven GM-09b/GM-09c map layer (regions + rivers + tunnel_budget) unchanged, so
the value here is generality: a full-span line crosses BOTH channels (two tunnels),
stations spawn on all three banks and never in the water, and CLASSIC/RIVER stay
byte-identical. Adding DELTA to the registry is purely additive.
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
from maps import CLASSIC, DELTA, KNOWN_MAP_IDS, RIVER, map_by_id, resolve_map
from mediator import Mediator


def _bank_of(x: float) -> str:
    """left / mid / right by the two river x-bands (or 'water' inside a channel)."""
    r1, r2 = DELTA.rivers
    if x < r1[0]:
        return "L"
    if r1[2] < x < r2[0]:
        return "M"
    if x > r2[2]:
        return "R"
    return "water"


class TestGM09dDeltaDefinition(unittest.TestCase):
    def test_delta_is_registered_and_resolvable(self):
        self.assertEqual(DELTA.map_id, "delta")
        self.assertEqual(DELTA.map_definition_version, 1)
        self.assertIs(resolve_map("delta", 1), DELTA)
        self.assertIs(map_by_id("delta"), DELTA)
        # Membership, not an exact tuple: the registry grows as later units add
        # maps (GM-09e's third map, etc.), which must not break this test.
        self.assertIn("delta", KNOWN_MAP_IDS)
        self.assertIn("classic", KNOWN_MAP_IDS)

    def test_delta_has_three_banks_and_two_rivers(self):
        self.assertEqual(len(DELTA.spawn_regions), 3)
        self.assertEqual(len(DELTA.rivers), 2)
        self.assertEqual(DELTA.tunnel_budget, 4)
        for region in (*DELTA.spawn_regions, *DELTA.rivers):
            left, top, right, bottom = region
            self.assertLess(left, right, "positive-width rect")
            self.assertLess(top, bottom, "positive-height rect")

    def test_the_two_channels_do_not_overlap_the_mid_bank(self):
        # The mid bank must sit strictly between the two channels with positive
        # width, or a spanning network is unbuildable.
        r1, r2 = DELTA.rivers
        mid = DELTA.spawn_regions[1]
        self.assertLess(r1[2], mid[0], "mid bank starts after river 1")
        self.assertLess(mid[2], r2[0], "mid bank ends before river 2")


class TestGM09dRegionSpawn(unittest.TestCase):
    def test_stations_spawn_on_all_three_banks_and_never_in_water(self):
        banks_seen = set()
        for seed in range(40):
            mediator = Mediator(seed=seed, map_definition=DELTA)
            for station in mediator.all_stations:
                x, y = station.position.left, station.position.top
                self.assertNotEqual(
                    _bank_of(x), "water", f"station ({x},{y}) in a channel"
                )
                # The whole glyph clears both channels (eroded by station_size).
                for band in DELTA.rivers:
                    left, _t, right, _b = band
                    self.assertFalse(
                        left - station_size < x < right + station_size,
                        f"station ({x},{y}) glyph overlaps channel {band}",
                    )
                banks_seen.add(_bank_of(x))
        self.assertEqual(banks_seen, {"L", "M", "R"}, "all three banks are reachable")

    def test_delta_construction_and_trajectory_are_deterministic(self):
        # Fingerprint the construction AND a stepped trajectory (RNG-driven
        # passenger destinations), so a spurious extra RNG draw -- which would leave
        # the stations identical but shift every later draw -- is still caught
        # (review Codex). Overload game-over is suppressed so the sim keeps running.
        def project(seed):
            m = Mediator(seed=seed, map_definition=DELTA)
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


class TestGM09dCrossingsAndBudget(unittest.TestCase):
    def test_full_span_line_crosses_both_channels(self):
        left_x = DELTA.spawn_regions[0][2] - 50
        right_x = DELTA.spawn_regions[2][0] + 50
        crossings = path_crossings(
            [Point(left_x, screen_height / 2), Point(right_x, screen_height / 2)],
            False,
            DELTA.rivers,
        )
        self.assertEqual(len(crossings), 2, "a full-span line uses two tunnels")

    def test_a_left_to_mid_line_crosses_one_channel(self):
        left_x = DELTA.spawn_regions[0][2] - 50
        mid_x = DELTA.spawn_regions[1][0] + 50
        crossings = path_crossings(
            [Point(left_x, screen_height / 2), Point(mid_x, screen_height / 2)],
            False,
            DELTA.rivers,
        )
        self.assertEqual(len(crossings), 1)

    def test_budget_four_connects_all_three_banks(self):
        # Find a seed with a station on each bank, connect them within budget 4, and
        # confirm the network spans all three banks without exhausting the budget.
        for seed in range(80):
            mediator = Mediator(seed=seed, map_definition=DELTA)
            by_bank: dict[str, int] = {}
            for i, s in enumerate(mediator.stations):
                by_bank.setdefault(_bank_of(s.position.left), i)
            if {"L", "M", "R"} <= by_bank.keys():
                mediator.num_paths = 6
                mediator.unlocked_num_paths = 6
                self.assertIsNotNone(
                    mediator.create_path_from_station_indices(
                        [by_bank["L"], by_bank["M"]]
                    )
                )
                self.assertIsNotNone(
                    mediator.create_path_from_station_indices(
                        [by_bank["M"], by_bank["R"]]
                    )
                )
                self.assertEqual(mediator.consumed_tunnels, 2, "L-M-R uses two tunnels")
                self.assertEqual(mediator.available_tunnels, 2, "budget 4 leaves room")
                return
        self.skipTest("no seed in 0..79 placed a station on all three banks")

    def test_budget_four_is_a_real_ceiling(self):
        # Budget 4 must REJECT a 5th crossing, not just permit the first four --
        # else the test would pass with any budget (review harness).
        for seed in range(80):
            mediator = Mediator(seed=seed, map_definition=DELTA)
            by_bank: dict[str, int] = {}
            for i, s in enumerate(mediator.stations):
                by_bank.setdefault(_bank_of(s.position.left), i)
            if {"L", "M", "R"} <= by_bank.keys():
                mediator.num_paths = 8
                mediator.unlocked_num_paths = 8
                mediator.create_path_from_station_indices([by_bank["L"], by_bank["M"]])
                mediator.create_path_from_station_indices([by_bank["M"], by_bank["R"]])
                # A full-span L-R line crosses BOTH channels (two tunnels) -> total 4.
                mediator.create_path_from_station_indices([by_bank["L"], by_bank["R"]])
                self.assertEqual(mediator.consumed_tunnels, 4)
                self.assertEqual(mediator.available_tunnels, 0)
                rejected = mediator.create_path_from_station_indices(
                    [by_bank["L"], by_bank["M"]]
                )
                self.assertIsNone(rejected, "a 5th crossing exceeds the budget of 4")
                self.assertEqual(
                    mediator.consumed_tunnels, 4, "rejection consumes nothing"
                )
                return
        self.skipTest("no seed in 0..79 placed a station on all three banks")


class TestGM09dClassicRiverUnaffected(unittest.TestCase):
    def test_classic_and_river_are_unchanged(self):
        # Adding DELTA is additive: CLASSIC stays region-free/unbounded and RIVER
        # keeps its single channel + budget 3.
        self.assertEqual(CLASSIC.spawn_regions, ())
        self.assertEqual(CLASSIC.rivers, ())
        self.assertIsNone(CLASSIC.tunnel_budget)
        self.assertEqual(len(RIVER.rivers), 1)
        self.assertEqual(RIVER.tunnel_budget, 3)

    def test_classic_construction_is_byte_identical(self):
        # The GM-09a determinism fingerprints must still hold; a direct guard that
        # CLASSIC's first stations are unchanged for seed 0.
        m = Mediator(seed=0)  # default CLASSIC
        shapes = [type(s.shape).__name__ for s in m.all_stations[:3]]
        positions = [
            (round(s.position.left), round(s.position.top)) for s in m.all_stations[:3]
        ]
        self.assertEqual(shapes, ["Triangle", "Rect", "Rect"])
        self.assertEqual(positions, [(1232, 318), (1132, 474), (1213, 375)])


class TestGM09dSaveGuardAndRender(unittest.TestCase):
    def test_delta_map_round_trips_through_a_v2_save(self):
        # GM-09f: a registered DELTA map now serializes (v2 records the map identity)
        # and reloads with its map preserved.
        from save_game import serialize_game
        from save_load import deserialize_game
        from save_schema import validate_save

        document = serialize_game(Mediator(seed=0, map_definition=DELTA))
        self.assertEqual(document["mapId"], "delta")
        validate_save(document)
        self.assertEqual(deserialize_game(document).map_definition, DELTA)

    def test_terrain_paints_both_channels_and_not_the_mid_bank(self):
        # Assert BOTH channels are water and the mid bank is not -- a regression that
        # dropped one of the two bands would still change some pixel, so a bare
        # "something changed" check is too weak (review harness).
        from rendering.terrain_renderer import RIVER_COLOR, draw_terrain

        background = (247, 245, 239)
        surface = pygame.Surface((screen_width, screen_height))
        surface.fill(background)
        draw_terrain(surface, DELTA)
        r1, r2 = DELTA.rivers
        y = screen_height // 2
        channel_1 = int((r1[0] + r1[2]) / 2)
        channel_2 = int((r2[0] + r2[2]) / 2)
        between = int((r1[2] + r2[0]) / 2)  # in the mid bank
        self.assertEqual(surface.get_at((channel_1, y))[:3], RIVER_COLOR, "channel 1")
        self.assertEqual(surface.get_at((channel_2, y))[:3], RIVER_COLOR, "channel 2")
        self.assertEqual(
            surface.get_at((between, y))[:3], background, "mid bank is dry"
        )

    def test_full_span_line_renders_a_portal_at_each_channel(self):
        # A full-span line crosses BOTH channels; draw_crossings must paint a portal
        # marker at each entry point. A regression that marked only rivers[:1] would
        # pass every other test but drop the second portal (review Codex).
        from crossings import path_crossings
        from rendering.terrain_renderer import CROSSING_MARKER_COLOR, draw_crossings

        for seed in range(80):
            mediator = Mediator(seed=seed, map_definition=DELTA)
            by_bank: dict[str, int] = {}
            for i, s in enumerate(mediator.stations):
                by_bank.setdefault(_bank_of(s.position.left), i)
            if "L" in by_bank and "R" in by_bank:
                mediator.num_paths = 6
                mediator.unlocked_num_paths = 6
                mediator.create_path_from_station_indices([by_bank["L"], by_bank["R"]])
                points = path_crossings(
                    [s.position for s in mediator.paths[0].stations],
                    mediator.paths[0].is_looped,
                    DELTA.rivers,
                )
                self.assertEqual(len(points), 2, "full-span line crosses both channels")
                surface = pygame.Surface((screen_width, screen_height))
                surface.fill((247, 245, 239))
                draw_crossings(surface, DELTA, list(mediator.paths))
                for point in points:
                    self.assertEqual(
                        surface.get_at((round(point.left), round(point.top)))[:3],
                        CROSSING_MARKER_COLOR,
                        "a portal is painted at each crossing",
                    )
                return
        self.skipTest(
            "no seed in 0..79 placed a station on both the left and right banks"
        )


if __name__ == "__main__":
    unittest.main()
