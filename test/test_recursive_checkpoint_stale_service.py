"""The checkpoint verifier tolerates the documented stale service cache.

Ordinary multi-locomotive play reaches tick boundaries where a metro's bound
``_station_service_action`` no longer matches the re-derivable pure oracle: a
later metro consumes the same rider inside the same tick, leaving a well-formed
cache pending the next reconcile (``passenger_flow.move_passengers`` walks the
metros in order and never revisits an earlier one). GM-07b save/load already
persists that shape verbatim; ``canonical_checkpoint`` used to raise on it
(``checkpoint runtime carriage graph is malformed`` for a stale bound cache,
``checkpoint Metro service cache is stale`` for a stale-reset null cache).

These tests pin the repaired contract: the checkpoint accepts a structurally
well-formed cache that references a live passenger even when it disagrees with
the oracle, while still rejecting a genuinely malformed cache (unknown kind,
dangling passenger, or timers off the boarding invariant).
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.passenger import Passenger
from env import MiniMetroEnv
from graph.graph_algo import build_station_nodes_dict
from passenger_capacity import pure_service_action, same_service_action
from recursive_checkpoint import canonical_checkpoint
from test.gm06c_simulation_ui_support import boardable_passenger


def _apply(env, action):
    _, _, _, info = env.step(action, dt_ms=0)
    if not info["action_ok"]:
        raise AssertionError(f"scenario action was rejected: {action!r}")


def _line_env(seed, dt_ms=250):
    env = MiniMetroEnv(dt_ms=dt_ms)
    env.reset(seed=seed)
    _apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    _apply(env, {"type": "assign_locomotive", "path_index": 0})
    return env


def _has_stale_cache(mediator):
    nodes = build_station_nodes_dict(mediator.stations, mediator.paths)
    for metro in mediator.metros:
        cache = metro._station_service_action
        station = metro.current_station
        pure = (
            None
            if station is None
            else pure_service_action(mediator, metro, station, nodes)
        )
        if (cache is None) != (pure is None):
            return True
        if cache is not None and not same_service_action(cache, pure):
            return True
    return False


def _bound_mid_board_env(seed=829):
    """A canonical single-metro stop with a live bound BOARD cache.

    Mirrors the proven GM-06c fixture: canonical_checkpoint(v4) succeeds on the
    returned env, and ``metro._station_service_action`` is ``(board, rider)``.
    """

    env = MiniMetroEnv()
    env.reset(seed=seed)
    _apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    _apply(env, {"type": "assign_locomotive", "path_index": 0})
    mediator = env.mediator
    path = mediator.paths[0]
    metro = mediator.metros[0]
    start = path.stations[0]
    metro.current_station = start
    metro.position = start.position
    for existing in tuple(start.passengers):
        start.remove_passenger(existing)
        if existing in mediator.passengers:
            mediator.passengers.remove(existing)
        mediator.travel_plans.pop(existing, None)
    rider = boardable_passenger(
        mediator, start, path.stations[1], path, name="stale-service-boarder"
    )
    mediator.move_passengers(250)
    cache = metro._station_service_action
    if cache is None or cache[0] != "board" or cache[1] is not rider:
        raise AssertionError("mid-board fixture did not bind the expected cache")
    return env, metro, rider


class TestStaleBoundServiceCacheCheckpoints(unittest.TestCase):
    """A bound cache stranded by a same-tick sibling metro must checkpoint."""

    def test_seed_4501_two_locomotive_boundary_checkpoints(self):
        # The exact harness repro: two locomotives on one line, the second
        # assigned at tick 6; tick 26 leaves the first metro a stale BOARD
        # cache (its rider was boarded by the second metro that same tick).
        env = _line_env(4501)
        schedule = {6: {"type": "assign_locomotive", "path_index": 0}}
        for tick in range(1, 27):
            env.step(schedule.get(tick, {"type": "noop"}))

        self.assertEqual(len(env.mediator.metros), 2)
        self.assertTrue(
            _has_stale_cache(env.mediator),
            "seed 4501 tick 26 must exhibit a stale service cache",
        )
        checkpoint = canonical_checkpoint(env, schema_version=4)
        self.assertEqual(checkpoint["schemaVersion"], 4)

    def test_seed_127_stale_board_cache_checkpoints(self):
        # codex repro: seed 127 at dt 125, assign, 17 noops, assign, 94 noops
        # -> the first metro keeps a stale BOARD cache with timers (500, 0).
        env = _line_env(127, dt_ms=125)
        for _ in range(17):
            env.step({"type": "noop"})
        _apply(env, {"type": "assign_locomotive", "path_index": 0})
        for _ in range(94):
            env.step({"type": "noop"})

        self.assertTrue(
            _has_stale_cache(env.mediator),
            "seed 127 window must exhibit a stale service cache",
        )
        checkpoint = canonical_checkpoint(env, schema_version=4)
        self.assertEqual(checkpoint["schemaVersion"], 4)


class TestStaleResetServiceCacheCheckpoints(unittest.TestCase):
    """A null cache with a still-derivable oracle (the reset boundary)."""

    def test_null_cache_with_derivable_action_checkpoints(self):
        env, metro, _ = _bound_mid_board_env(seed=831)
        mediator = env.mediator
        nodes = build_station_nodes_dict(mediator.stations, mediator.paths)
        # The oracle still derives (board, rider); only the cache was reset.
        self.assertIsNotNone(
            pure_service_action(mediator, metro, metro.current_station, nodes)
        )

        metro._station_service_action = None
        metro.stop_time_remaining_ms = 0
        metro.boarding_progress_ms = 0
        self.assertTrue(_has_stale_cache(mediator))

        checkpoint = canonical_checkpoint(env, schema_version=4)
        self.assertEqual(checkpoint["schemaVersion"], 4)


class TestCheckpointStillRejectsMalformedServiceCache(unittest.TestCase):
    """Relaxing the oracle match must not weaken structural corruption checks."""

    def test_rejects_unknown_kind_dangling_passenger_and_broken_timers(self):
        env, metro, rider = _bound_mid_board_env(seed=833)
        path = env.mediator.paths[0]
        bound = metro._station_service_action
        kind = bound[0]

        # A fresh passenger that never belonged to the game is dangling.
        dangling = Passenger(path.stations[1].shape)
        corruptions = {
            "unknown kind": ("not-a-real-kind", rider),
            "dangling passenger": (kind, dangling),
        }
        for name, corrupt in corruptions.items():
            metro._station_service_action = corrupt
            with self.subTest(name=name), self.assertRaises(ValueError):
                canonical_checkpoint(env, schema_version=4)

        metro._station_service_action = bound
        # Progress at the interval violates the boarding timer invariant.
        metro.boarding_progress_ms = metro.boarding_time_per_passenger_ms
        with self.subTest(name="broken timers"), self.assertRaises(ValueError):
            canonical_checkpoint(env, schema_version=4)


if __name__ == "__main__":
    unittest.main()
