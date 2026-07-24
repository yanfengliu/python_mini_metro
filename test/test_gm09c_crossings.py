"""GM-09c contract: river-crossing tunnel budget (D-035).

A river map carries a finite ``tunnel_budget``; every point where a line's
CENTERLINE crosses a river band consumes one tunnel. The count is DERIVED from the
live network (never a stored counter), so removing or rerouting a line refunds its
crossings for free and a failed edit can leave no stale charge. The route-edit gate
rejects a creation or reroute that would exceed the budget BEFORE mutating anything.
CLASSIC (no rivers) is unbounded and byte-identical. The env exposes a ``tunnels``
observation block as a SIBLING of ``fleet`` so the canonical checkpoint is untouched.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from crossings import _centerline_segments, path_crossings, segment_crosses_band
from geometry.point import Point
from maps import CLASSIC, RIVER
from mediator import Mediator

# A synthetic vertical band x in [10, 20] for the pure-geometry cases.
_BAND = (10.0, 0.0, 20.0, 100.0)
# seed=0 RIVER stations: 0 -> right bank (x~1232), 1 -> right (x~1132), 2 -> left (x~584).
# So [2, 0] is the canonical single-crossing line and [0, 1] is same-bank (no cross).
_LEFT, _RIGHT, _RIGHT2 = 2, 0, 1


def _river_mediator(seed: int = 0, *, paths: int = 6) -> Mediator:
    """A RIVER mediator with the path limit raised so a test can build several
    crossing lines from the three starting stations without hitting the path cap."""
    mediator = Mediator(seed=seed, map_definition=RIVER)
    mediator.num_paths = paths
    mediator.unlocked_num_paths = paths
    return mediator


class TestGM09cCrossingGeometry(unittest.TestCase):
    """The pure geometry: no mediator, no pygame."""

    def test_clear_crossing_returns_entry_point_on_the_near_edge(self):
        entry = segment_crosses_band(Point(0, 50), Point(30, 50), _BAND)
        self.assertIsNotNone(entry)
        self.assertEqual((entry.left, entry.top), (10, 50))

    def test_segment_wholly_on_either_side_does_not_cross(self):
        self.assertIsNone(segment_crosses_band(Point(0, 50), Point(5, 50), _BAND))
        self.assertIsNone(segment_crosses_band(Point(25, 50), Point(40, 50), _BAND))

    def test_parallel_outside_segment_does_not_cross(self):
        self.assertIsNone(segment_crosses_band(Point(5, 0), Point(5, 100), _BAND))

    def test_corner_tangency_is_not_a_crossing(self):
        # A segment that only grazes a corner (t_enter == t_exit) is a determinism
        # tie-break: it must NOT count, so no future diagonal river can flip counts.
        self.assertIsNone(segment_crosses_band(Point(10, -10), Point(30, 10), _BAND))

    def test_two_station_loop_closure_does_not_double_charge(self):
        # A 2-station loop's closure RETRACES the single segment; counting it would
        # charge one physical crossing twice (review Codex).
        positions = [Point(0, 50), Point(30, 50)]
        self.assertEqual(len(_centerline_segments(positions, True)), 1)
        self.assertEqual(len(path_crossings(positions, True, (_BAND,))), 1)

    def test_three_station_loop_counts_the_closure_crossing(self):
        # left, right, right; closed -> A->B crosses, B->C stays right, C->A crosses.
        tri = [Point(0, 50), Point(30, 20), Point(30, 80)]
        self.assertEqual(len(_centerline_segments(tri, True)), 3)
        self.assertEqual(len(path_crossings(tri, True, (_BAND,))), 2)
        # Open (unlooped) the same three stations cross only once.
        self.assertEqual(len(path_crossings(tri, False, (_BAND,))), 1)

    def test_multiple_bands_each_count(self):
        second = (50.0, 0.0, 60.0, 100.0)
        crossings = path_crossings(
            [Point(0, 50), Point(100, 50)], False, (_BAND, second)
        )
        self.assertEqual(len(crossings), 2)

    def test_no_rivers_or_too_few_positions_is_empty(self):
        self.assertEqual(path_crossings([Point(0, 50), Point(30, 50)], False, ()), ())
        self.assertEqual(path_crossings([Point(0, 50)], False, (_BAND,)), ())


class TestGM09cDerivedCounts(unittest.TestCase):
    """Mediator-level consumed/available derived from the live network."""

    def test_river_starts_at_full_budget(self):
        mediator = Mediator(seed=0, map_definition=RIVER)
        self.assertEqual(mediator.num_tunnels, 3)
        self.assertEqual(mediator.consumed_tunnels, 0)
        self.assertEqual(mediator.available_tunnels, 3)

    def test_crossing_line_consumes_one_tunnel(self):
        mediator = _river_mediator()
        mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        self.assertEqual(mediator.consumed_tunnels, 1)
        self.assertEqual(mediator.available_tunnels, 2)

    def test_same_bank_line_consumes_no_tunnel(self):
        mediator = _river_mediator()
        mediator.create_path_from_station_indices([_RIGHT, _RIGHT2])
        self.assertEqual(mediator.consumed_tunnels, 0)
        self.assertEqual(mediator.available_tunnels, 3)

    def test_removing_a_crossing_line_refunds_its_tunnel(self):
        mediator = _river_mediator()
        path = mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        self.assertEqual(mediator.consumed_tunnels, 1)
        mediator.remove_path(path)
        self.assertEqual(mediator.consumed_tunnels, 0)
        self.assertEqual(mediator.available_tunnels, 3)

    def test_num_tunnels_is_derived_from_the_map_not_cached(self):
        # num_tunnels must track map_definition live (like consumed_tunnels reads
        # map_definition.rivers), so a swapped map stays consistent; a field cached
        # at construction would fail open on a finite map (review Codex MAJOR).
        mediator = Mediator(seed=1)  # CLASSIC, unbounded
        self.assertIsNone(mediator.num_tunnels)
        mediator.map_definition = RIVER
        self.assertEqual(mediator.num_tunnels, 3)
        self.assertEqual(mediator.available_tunnels, 3)


class TestGM09cCreationGate(unittest.TestCase):
    def test_creation_over_budget_is_rejected_without_consuming(self):
        mediator = _river_mediator()
        for _ in range(3):
            self.assertIsNotNone(
                mediator.create_path_from_station_indices([_LEFT, _RIGHT])
            )
        self.assertEqual(mediator.consumed_tunnels, 3)
        self.assertEqual(mediator.available_tunnels, 0)
        before_paths = len(mediator.paths)
        rejected = mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        self.assertIsNone(rejected, "a 4th crossing exceeds the budget of 3")
        self.assertEqual(mediator.consumed_tunnels, 3, "rejection consumes nothing")
        self.assertEqual(len(mediator.paths), before_paths, "no ghost path is left")

    def test_same_bank_line_is_allowed_at_zero_budget(self):
        # A non-crossing line needs no tunnel, so it builds even when the budget is
        # fully spent -- the constraint is on crossings, not on lines.
        mediator = _river_mediator()
        for _ in range(3):
            mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        self.assertEqual(mediator.available_tunnels, 0)
        built = mediator.create_path_from_station_indices([_RIGHT, _RIGHT2])
        self.assertIsNotNone(built)
        self.assertEqual(mediator.consumed_tunnels, 3)

    def test_direct_finish_cannot_bypass_the_budget(self):
        # finish_path_creation is the COMMIT boundary (clearing is_being_created is
        # what makes a draft count). A direct start/add/finish that skips
        # end_path_on_station's preflight must still be caught there, or the budget
        # is bypassable (review Codex MAJOR).
        mediator = _river_mediator()
        for _ in range(3):
            mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        self.assertEqual(mediator.available_tunnels, 0)
        paths_before = len(mediator.paths)
        mediator.start_path_on_station(mediator.stations[_LEFT])
        mediator.add_station_to_path(mediator.stations[_RIGHT])
        mediator.finish_path_creation()  # a 4th crossing -- must be rejected here
        self.assertEqual(
            mediator.consumed_tunnels, 3, "commit boundary rejects over-budget"
        )
        self.assertEqual(len(mediator.paths), paths_before, "no ghost path committed")
        self.assertIsNone(mediator.path_being_created, "draft aborted cleanly")

    def test_rejected_multistation_creation_is_fully_inert(self):
        # A rejected over-budget creation is a COMPLETE no-op: no crossing committed,
        # no ghost path, no RNG drawn, and (task_384488d0) the transient snap-blip the
        # aborted drag painted is dropped too -- so the whole canonical checkpoint is
        # byte-identical before and after. Abort removes the draft's OWN blip (its
        # last-recorded value-match), leaving the three committed lines' blips on the
        # shared station untouched.
        from env import MiniMetroEnv
        from recursive_checkpoint import canonical_checkpoint

        mediator = _river_mediator()
        for _ in range(3):
            mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        self.assertEqual(mediator.available_tunnels, 0)
        env = MiniMetroEnv()
        env.mediator = mediator
        before = canonical_checkpoint(env)
        paths_before = len(mediator.paths)
        # [_LEFT, _RIGHT, _RIGHT2] crosses once (L->R), so 1 + 3 committed = 4 > 3.
        rejected = mediator.create_path_from_station_indices([_LEFT, _RIGHT, _RIGHT2])
        after = canonical_checkpoint(env)
        self.assertIsNone(rejected)
        self.assertEqual(mediator.consumed_tunnels, 3, "no crossing is committed")
        self.assertEqual(len(mediator.paths), paths_before, "no ghost path")
        self.assertIsNone(mediator.path_being_created, "draft aborted")
        self.assertEqual(before, after, "a rejected creation is fully checkpoint-inert")

    def test_explicit_closure_loop_is_not_false_rejected(self):
        # A there-and-back index list [X, Y, X] with loop=True builds a 2-STATION
        # loop [X, Y], whose retraced closure crosses the river ONCE -- not the raw
        # round trip's two. The gate must count the RESOLVED route, or a valid
        # within-budget loop is wrongly rejected (re-review MAJOR: a raw-index
        # pre-check counted 2 and rejected a total of 3 <= 3).
        mediator = _river_mediator()
        mediator.create_path_from_station_indices([_LEFT, _RIGHT])  # consumed 1
        mediator.create_path_from_station_indices([_LEFT, _RIGHT2])  # consumed 2
        self.assertEqual(mediator.consumed_tunnels, 2)
        looped = mediator.create_path_from_station_indices(
            [_LEFT, _RIGHT, _LEFT], loop=True
        )
        self.assertIsNotNone(
            looped, "the 2-station loop crosses once; 2+1=3 is in budget"
        )
        self.assertTrue(looped.is_looped)
        self.assertEqual(mediator.consumed_tunnels, 3)


class TestGM09cRerouteGate(unittest.TestCase):
    def test_reroute_that_would_exceed_budget_is_rejected(self):
        mediator = _river_mediator()
        for _ in range(3):
            mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        same_bank = mediator.create_path_from_station_indices([_RIGHT, _RIGHT2])
        self.assertEqual(mediator.consumed_tunnels, 3)
        # Rerouting the same-bank line to cross would be a 4th crossing -> rejected.
        rejected = mediator.replace_path(same_bank, [_RIGHT2, _LEFT])
        self.assertFalse(rejected)
        self.assertEqual(mediator.consumed_tunnels, 3, "a rejected reroute is inert")

    def test_reroute_crossing_line_to_same_bank_refunds(self):
        mediator = _river_mediator()
        crossing = mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        self.assertEqual(mediator.consumed_tunnels, 1)
        ok = mediator.replace_path(crossing, [_RIGHT, _RIGHT2])
        self.assertTrue(ok)
        self.assertEqual(mediator.consumed_tunnels, 0, "the freed crossing is refunded")
        self.assertEqual(mediator.available_tunnels, 3)


class TestGM09cClassicUnbounded(unittest.TestCase):
    def test_classic_has_no_tunnel_constraint(self):
        mediator = Mediator(seed=0)  # default CLASSIC
        mediator.num_paths = 5
        mediator.unlocked_num_paths = 5
        self.assertIsNone(mediator.num_tunnels)
        self.assertIsNone(mediator.available_tunnels)
        self.assertEqual(mediator.consumed_tunnels, 0)
        # Any line builds; the derived count stays 0 and available stays None.
        mediator.create_path_from_station_indices([0, 1])
        self.assertEqual(mediator.consumed_tunnels, 0)
        self.assertIsNone(mediator.available_tunnels)


class TestGM09cObservation(unittest.TestCase):
    def _observe(self, mediator):
        from env import MiniMetroEnv

        env = MiniMetroEnv()
        env.mediator = mediator
        return env.observe()

    def test_river_observation_exposes_the_tunnel_block(self):
        obs = self._observe(Mediator(seed=0, map_definition=RIVER))
        self.assertEqual(
            obs["structured"]["tunnels"],
            {"total": 3, "consumed": 0, "available": 3},
        )

    def test_tunnel_block_tracks_consumption(self):
        mediator = _river_mediator()
        mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        obs = self._observe(mediator)
        self.assertEqual(
            obs["structured"]["tunnels"],
            {"total": 3, "consumed": 1, "available": 2},
        )

    def test_classic_observation_reports_unbounded(self):
        obs = self._observe(Mediator(seed=0))
        self.assertEqual(
            obs["structured"]["tunnels"],
            {"total": None, "consumed": 0, "available": None},
        )

    def test_tunnels_is_a_sibling_not_a_fleet_key(self):
        # The block MUST NOT live inside "fleet" -- the canonical checkpoint asserts
        # an EXACT fleet-key set, so an extra fleet key would break every map.
        obs = self._observe(Mediator(seed=0, map_definition=RIVER))
        self.assertNotIn("tunnels", obs["structured"]["fleet"])
        self.assertIn("tunnels", obs["structured"])


class TestGM09cCheckpoint(unittest.TestCase):
    def _checkpoint(self, mediator):
        from env import MiniMetroEnv
        from recursive_checkpoint import canonical_checkpoint

        env = MiniMetroEnv()
        env.mediator = mediator
        return canonical_checkpoint(env)

    def test_checkpoint_is_valid_on_a_river_env(self):
        # The sibling tunnels block is ignored by _normalize_observation's fixed
        # whitelist, so the checkpoint of a river game raises nothing.
        cp = self._checkpoint(Mediator(seed=0, map_definition=RIVER))
        self.assertIn("structured", cp)

    def test_checkpoint_is_valid_after_a_crossing(self):
        mediator = _river_mediator()
        mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        cp = self._checkpoint(mediator)
        self.assertIn("structured", cp)


class TestGM09cRender(unittest.TestCase):
    def test_crossing_marker_paints_on_a_river_line_and_nothing_on_classic(self):
        from rendering.terrain_renderer import draw_crossings

        mediator = _river_mediator()
        mediator.create_path_from_station_indices([_LEFT, _RIGHT])
        paths = list(mediator.paths)
        surface = pygame.Surface((1920, 1080))
        surface.fill((247, 245, 239))
        before = surface.copy()
        # CLASSIC (no rivers) paints nothing even with crossing-shaped lines.
        draw_crossings(surface, CLASSIC, paths)
        self.assertEqual(surface.get_view("2").raw, before.get_view("2").raw)
        # RIVER with a crossing line paints a marker.
        draw_crossings(surface, RIVER, paths)
        self.assertNotEqual(surface.get_view("2").raw, before.get_view("2").raw)

    def test_no_crossing_line_paints_no_marker(self):
        from rendering.terrain_renderer import draw_crossings

        mediator = _river_mediator()
        mediator.create_path_from_station_indices([_RIGHT, _RIGHT2])  # same bank
        surface = pygame.Surface((1400, 1080))
        surface.fill((247, 245, 239))
        before = surface.copy()
        draw_crossings(surface, RIVER, list(mediator.paths))
        self.assertEqual(
            surface.get_view("2").raw,
            before.get_view("2").raw,
            "a same-bank line has no crossing to mark",
        )


class TestGM09cImportSafety(unittest.TestCase):
    def test_crossings_pulls_no_pygame_mediator_or_shapely(self):
        code = (
            "import sys; sys.path.insert(0, 'src'); import crossings; "
            "bad=[m for m in ('pygame','mediator','shapely','geometry.polygon',"
            "'entity.station') if m in sys.modules]; "
            "print('LEAK' if bad else 'CLEAN', bad)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.realpath(__file__)) + "/..",
        )
        self.assertIn(
            "CLEAN", result.stdout, f"crossings leaked: {result.stdout}{result.stderr}"
        )


if __name__ == "__main__":
    unittest.main()
