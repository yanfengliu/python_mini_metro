"""GM-06d Case 4: narrow ``FleetManagement.reconcile`` and its per-tick seam."""

from __future__ import annotations

import os
import sys
import unittest
from copy import deepcopy

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.metro import Metro
from entity.passenger import Passenger
from mediator import Mediator


def _unlock_all_paths(mediator: Mediator) -> None:
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _different_shape_indices(mediator: Mediator) -> tuple[int, int]:
    for first, source in enumerate(mediator.stations):
        for second, destination in enumerate(mediator.stations):
            if source.shape.type != destination.shape.type:
                return first, second
    raise AssertionError("test setup requires two station shape types")


def _served_path(mediator: Mediator):
    _unlock_all_paths(mediator)
    first, second = _different_shape_indices(mediator)
    path = mediator.create_path_from_station_indices([first, second])
    if path is None:
        raise AssertionError("test setup could not create a path")
    for stale in tuple(path.metros):
        if stale in mediator.metros:
            mediator.metros.remove(stale)
    path.metros.clear()
    metro = Metro()
    path.add_metro(metro)
    mediator.metros.append(metro)
    return path, metro


def _ghost_metro(mediator: Mediator, path, *, queued: bool = False, occupied=None):
    """Install a ``path.metros`` entry that is absent from ``mediator.metros``."""

    ghost = Metro()
    path.add_metro(ghost)
    ghost.is_unassignment_queued = queued
    if occupied is not None:
        ghost.add_passenger(occupied)
        mediator.passengers.append(occupied)
    return ghost


def _quiet_simulation(mediator: Mediator) -> None:
    future = 10**9
    mediator.passenger_spawning_step = future
    mediator.passenger_spawning_interval_step = future
    mediator.overdue_passenger_threshold = future
    for station in mediator.stations:
        mediator.station_steps_since_last_spawn[station] = 0
        mediator.station_spawn_interval_steps[station] = future


def _rng_state(mediator: Mediator):
    return (
        mediator.context.python_random.getstate(),
        deepcopy(mediator.context.numpy_random.bit_generator.state),
    )


def _all_metros(mediator: Mediator) -> tuple[Metro, ...]:
    result = list(mediator.metros)
    for path in mediator.paths:
        for metro in path.metros:
            if all(metro is not seen for seen in result):
                result.append(metro)
    return tuple(result)


def _conservation(mediator: Mediator):
    aboard = sum(len(metro.passengers) for metro in _all_metros(mediator))
    return (
        len(mediator.passengers),
        aboard,
        mediator.num_metros,
        mediator.num_carriages,
        len(mediator.metros),
        mediator.available_locomotives,
        mediator.assigned_carriages,
        mediator.available_carriages,
    )


def _fleet_state(mediator: Mediator) -> dict[str, object]:
    paths = tuple(mediator.paths)
    metros = _all_metros(mediator)
    return {
        "paths": (mediator.paths, paths),
        "metros": (mediator.metros, tuple(mediator.metros)),
        "path_metros": tuple((path, path.metros, tuple(path.metros)) for path in paths),
        "metro_state": tuple(
            (
                metro,
                metro.is_unassignment_queued,
                metro.passengers,
                tuple(metro.passengers),
                metro.current_station,
                metro.current_segment,
                metro.current_segment_idx,
                metro.path_id,
            )
            for metro in metros
        ),
        "passengers": (mediator.passengers, tuple(mediator.passengers)),
        "station_riders": tuple(
            (station, station.passengers, tuple(station.passengers))
            for station in mediator.stations
        ),
        "conservation": _conservation(mediator),
        "rng": _rng_state(mediator),
    }


def _assert_fleet_state(test: unittest.TestCase, mediator: Mediator, before) -> None:
    for key, current in (
        ("paths", mediator.paths),
        ("metros", mediator.metros),
        ("passengers", mediator.passengers),
    ):
        collection, contents = before[key]
        test.assertIs(current, collection)
        test.assertEqual(len(current), len(contents))
        for item, expected in zip(current, contents):
            test.assertIs(item, expected)
    for owner, collection, contents in before["path_metros"]:
        test.assertIs(owner.metros, collection)
        test.assertEqual(len(collection), len(contents))
        for item, expected in zip(collection, contents):
            test.assertIs(item, expected)
    for owner, collection, contents in before["station_riders"]:
        test.assertIs(owner.passengers, collection)
        test.assertEqual(tuple(collection), contents)
    for state in before["metro_state"]:
        metro, queued, riders, rider_items, station, segment, idx, path_id = state
        test.assertIs(metro.is_unassignment_queued, queued)
        test.assertIs(metro.passengers, riders)
        test.assertEqual(tuple(metro.passengers), rider_items)
        test.assertIs(metro.current_station, station)
        test.assertIs(metro.current_segment, segment)
        test.assertEqual(metro.current_segment_idx, idx)
        test.assertEqual(metro.path_id, path_id)
    test.assertEqual(_conservation(mediator), before["conservation"])
    test.assertEqual(_rng_state(mediator), before["rng"])


def _reconcile(test: unittest.TestCase, mediator: Mediator):
    fleet = mediator._fleet
    test.assertTrue(
        hasattr(fleet, "reconcile"),
        "GM-06d product attribute is missing: FleetManagement.reconcile",
    )
    return fleet.reconcile(mediator)


class TestGM06dReconcileRepairs(unittest.TestCase):
    def test_clears_queue_flag_on_globally_absent_occupied_metro(self):
        mediator = Mediator(seed=6420)
        path, legit = _served_path(mediator)
        rider = Passenger(path.stations[1].shape)
        ghost = _ghost_metro(mediator, path, queued=True, occupied=rider)
        before_path_metros = tuple(path.metros)
        before = _conservation(mediator)

        _reconcile(self, mediator)

        self.assertIs(ghost.is_unassignment_queued, False)
        self.assertEqual(tuple(path.metros), before_path_metros)
        self.assertIs(ghost.passengers[0], rider)
        self.assertIn(rider, mediator.passengers)
        self.assertNotIn(ghost, mediator.metros)
        self.assertIn(legit, mediator.metros)
        self.assertEqual(_conservation(mediator), before)

    def test_drops_empty_globally_absent_metro_from_path_metros(self):
        mediator = Mediator(seed=6421)
        path, legit = _served_path(mediator)
        ghost = _ghost_metro(mediator, path)
        path_collection = path.metros
        global_collection = mediator.metros
        before = _conservation(mediator)
        self.assertFalse(mediator.can_queue_locomotive_unassignment(path))

        _reconcile(self, mediator)

        self.assertIs(path.metros, path_collection)
        self.assertIs(mediator.metros, global_collection)
        self.assertNotIn(ghost, path.metros)
        self.assertEqual(path.metros, [legit])
        self.assertEqual(mediator.metros, [legit])
        self.assertEqual(_conservation(mediator), before)
        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))

    def test_refuses_to_drop_occupied_globally_absent_metro(self):
        mediator = Mediator(seed=6422)
        path, _legit = _served_path(mediator)
        rider = Passenger(path.stations[1].shape)
        ghost = _ghost_metro(mediator, path, occupied=rider)
        before = _conservation(mediator)
        before_path_metros = tuple(path.metros)
        self.assertFalse(mediator.can_assign_locomotive(path))
        self.assertFalse(mediator.can_queue_locomotive_unassignment(path))
        self.assertEqual(mediator.queued_locomotives_for_path(path), 0)

        _reconcile(self, mediator)

        self.assertEqual(tuple(path.metros), before_path_metros)
        self.assertIn(ghost, path.metros)
        self.assertNotIn(ghost, mediator.metros)
        self.assertIs(ghost.passengers[0], rider)
        self.assertIn(rider, mediator.passengers)
        self.assertEqual(_conservation(mediator), before)
        self.assertFalse(mediator.can_assign_locomotive(path))
        self.assertFalse(mediator.can_queue_locomotive_unassignment(path))
        self.assertEqual(mediator.queued_locomotives_for_path(path), 0)

    def test_reconcile_is_idempotent_and_a_noop_on_canonical_state(self):
        mediator = Mediator(seed=6423)
        path, _legit = _served_path(mediator)
        queued_canonical = Metro()
        path.add_metro(queued_canonical)
        mediator.metros.append(queued_canonical)
        queued_canonical.is_unassignment_queued = True
        canonical_before = _fleet_state(mediator)

        _reconcile(self, mediator)

        _assert_fleet_state(self, mediator, canonical_before)
        self.assertIs(queued_canonical.is_unassignment_queued, True)

        rider = Passenger(path.stations[1].shape)
        _ghost_metro(mediator, path, queued=True, occupied=rider)
        _ghost_metro(mediator, path)
        _reconcile(self, mediator)
        repaired_once = _fleet_state(mediator)
        _reconcile(self, mediator)
        _assert_fleet_state(self, mediator, repaired_once)


class TestGM06dReconcileSeam(unittest.TestCase):
    def test_increment_time_repairs_unconditionally_in_paused_and_terminal_states(
        self,
    ):
        for mode in ("paused", "terminal"):
            with self.subTest(mode=mode):
                mediator = Mediator(seed=6424)
                _quiet_simulation(mediator)
                path, _legit = _served_path(mediator)
                rider = Passenger(path.stations[1].shape)
                queued_ghost = _ghost_metro(mediator, path, queued=True, occupied=rider)
                empty_ghost = _ghost_metro(mediator, path)
                if mode == "paused":
                    mediator.is_paused = True
                else:
                    mediator.is_game_over = True
                before_time = mediator.time_ms
                before = _conservation(mediator)

                mediator.increment_time(250)

                self.assertNotIn(empty_ghost, path.metros)
                self.assertIn(queued_ghost, path.metros)
                self.assertIs(queued_ghost.is_unassignment_queued, False)
                self.assertIs(queued_ghost.passengers[0], rider)
                self.assertEqual(mediator.time_ms, before_time)
                self.assertEqual(_conservation(mediator), before)

    def test_same_tick_repair_reenables_settlement_before_the_next_tick(self):
        mediator = Mediator(seed=6425)
        _quiet_simulation(mediator)
        path, legit = _served_path(mediator)
        empty_ghost = _ghost_metro(mediator, path)
        legit.is_unassignment_queued = True
        legit.position = legit.current_segment.segment_end

        mediator.increment_time(1)

        self.assertNotIn(empty_ghost, path.metros)
        self.assertNotIn(legit, path.metros)
        self.assertNotIn(legit, mediator.metros)
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)
        self.assertEqual(mediator.passengers, [])

    def test_paused_and_terminal_ticks_on_canonical_state_change_nothing(self):
        # regression guard: green at baseline (canonical reconcile is a no-op).
        for mode in ("paused", "terminal"):
            with self.subTest(mode=mode):
                mediator = Mediator(seed=6426)
                _quiet_simulation(mediator)
                _served_path(mediator)
                if mode == "paused":
                    mediator.is_paused = True
                else:
                    mediator.is_game_over = True
                before = _fleet_state(mediator)
                before_clock = (mediator.time_ms, mediator.steps)

                mediator.increment_time(1000)

                _assert_fleet_state(self, mediator, before)
                self.assertEqual((mediator.time_ms, mediator.steps), before_clock)


if __name__ == "__main__":
    unittest.main()
