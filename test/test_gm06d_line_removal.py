"""GM-06d Case 3: transactional, rider-conserving ``remove_path`` (D-024)."""

from __future__ import annotations

import os
import sys
import unittest
from copy import deepcopy

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import (
    station_capacity,
    station_color,
    station_size,
    station_unlock_milestones,
)
from entity.carriage import Carriage
from entity.metro import Metro
from entity.padding_segment import PaddingSegment
from entity.passenger import Passenger
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from geometry.triangle import Triangle
from graph.node import Node
from mediator import Mediator
from test.gm06c_simulation_ui_support import make_two_station_game, passenger_for
from travel_plan import TravelPlan


def _removal_game(seed: int):
    # Two-station game with bound buttons so remove_path is dispatchable.
    mediator, start, end, path, metro = make_two_station_game(seed=seed)
    mediator.assign_paths_to_buttons()
    return mediator, start, end, path, metro


def _create_served_path(mediator: Mediator, indices: list[int]):
    path = mediator.create_path_from_station_indices(indices)
    if path is None:
        raise AssertionError(f"test setup could not create path {indices!r}")
    for stale in tuple(path.metros):
        if stale in mediator.metros:
            mediator.metros.remove(stale)
    path.metros.clear()
    metro = Metro()
    path.add_metro(metro)
    mediator.metros.append(metro)
    return path, metro


def _adopt_stations(mediator: Mediator, stations: list[Station]) -> None:
    mediator.stations = list(stations)
    mediator.all_stations = list(stations)
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _assert_removal_dispatchable(mediator: Mediator, path) -> None:
    # Fail setup, not the contract, when the canonical removal gate rejects.
    if not mediator.can_assign_locomotive(path):
        raise AssertionError("test setup must keep the removal target dispatchable")


def _onboard(mediator: Mediator, metro: Metro, destination_shape, name: str):
    passenger = Passenger(destination_shape)
    passenger.id = name
    metro.add_passenger(passenger)
    mediator.passengers.append(passenger)
    return passenger


def _quiet_spawning(mediator: Mediator) -> None:
    future = 10**9
    mediator.passenger_spawning_step = future
    mediator.passenger_spawning_interval_step = future
    for station in mediator.stations:
        mediator.station_steps_since_last_spawn[station] = 0
        mediator.station_spawn_interval_steps[station] = future


def _rng_state(mediator: Mediator):
    return (
        mediator.context.python_random.getstate(),
        deepcopy(mediator.context.numpy_random.bit_generator.state),
    )


def _progression_views(mediator: Mediator):
    aggregate = mediator._progression
    names = ("deliveries", "line_credits", "unlocked_num_paths")
    names += ("unlocked_num_stations", "purchased_num_paths")
    return tuple((getattr(mediator, n), getattr(aggregate, n)) for n in names)


def _all_metros(mediator: Mediator) -> tuple[Metro, ...]:
    result = list(mediator.metros)
    for path in mediator.paths:
        for metro in path.metros:
            if all(metro is not seen for seen in result):
                result.append(metro)
    return tuple(result)


def _footprint(mediator: Mediator) -> dict[str, object]:
    paths = tuple(mediator.paths)
    metros = _all_metros(mediator)
    riders = tuple(mediator.passengers)
    named = {
        name: (getattr(mediator, name), tuple(getattr(mediator, name)))
        for name in ("paths", "stations", "metros", "passengers")
    }
    mappings = {
        name: (getattr(mediator, name), tuple(getattr(mediator, name).items()))
        for name in ("travel_plans", "path_colors", "path_to_color", "path_to_button")
    }
    owners = tuple(
        (owner, attribute, getattr(owner, attribute), tuple(getattr(owner, attribute)))
        for owner, attribute in (
            *((path, "metros") for path in paths),
            *((station, "passengers") for station in mediator.stations),
            *((metro, "passengers") for metro in metros),
            *((metro, "carriages") for metro in metros),
        )
    )
    return {
        "named": named,
        "mappings": mappings,
        "owners": owners,
        "buttons": tuple(
            (button, button.path, button.is_locked, button.unlock_blink_start_time_ms)
            for button in mediator.path_buttons
        ),
        "metro_scalars": tuple(
            (
                metro,
                metro.is_unassignment_queued,
                metro.current_station,
                metro.current_segment,
                metro.current_segment_idx,
            )
            for metro in metros
        ),
        "rider_state": tuple((r, r.wait_ms, r.is_at_destination) for r in riders),
        "progression": _progression_views(mediator),
        "counts": (mediator.num_metros, mediator.num_carriages),
        "rng": _rng_state(mediator),
    }


def _assert_footprint(test: unittest.TestCase, mediator: Mediator, before) -> None:
    for name, (collection, contents) in before["named"].items():
        current = getattr(mediator, name)
        test.assertIs(current, collection)
        test.assertEqual(len(current), len(contents))
        for item, expected in zip(current, contents):
            test.assertIs(item, expected)
    for name, (mapping, items) in before["mappings"].items():
        current = getattr(mediator, name)
        test.assertIs(current, mapping)
        test.assertEqual(len(current), len(items))
        for actual, expected in zip(current.items(), items):
            test.assertIs(actual[0], expected[0])
            test.assertIs(actual[1], expected[1])
    for owner, attribute, collection, contents in before["owners"]:
        test.assertIs(getattr(owner, attribute), collection)
        test.assertEqual(len(collection), len(contents))
        for item, expected in zip(collection, contents):
            test.assertIs(item, expected)
    for button, bound_path, locked, blink in before["buttons"]:
        test.assertIs(button.path, bound_path)
        test.assertIs(button.is_locked, locked)
        test.assertEqual(button.unlock_blink_start_time_ms, blink)
    for metro, queued, station, segment, index in before["metro_scalars"]:
        test.assertIs(metro.is_unassignment_queued, queued)
        test.assertIs(metro.current_station, station)
        test.assertIs(metro.current_segment, segment)
        test.assertEqual(metro.current_segment_idx, index)
    for rider, wait_ms, is_at_destination in before["rider_state"]:
        test.assertEqual(rider.wait_ms, wait_ms)
        test.assertIs(rider.is_at_destination, is_at_destination)
    test.assertEqual(_progression_views(mediator), before["progression"])
    test.assertEqual((mediator.num_metros, mediator.num_carriages), before["counts"])
    test.assertEqual(_rng_state(mediator), before["rng"])


class TestGM06dRemovalConservation(unittest.TestCase):
    def test_remove_path_keeps_every_rider_and_credits_destination_alights(self):
        mediator, start, end, path, metro = _removal_game(6400)
        metro.carriages.extend((Carriage(), Carriage()))
        mediator.num_carriages = 2
        credited = _onboard(mediator, metro, start.shape, "credited")
        other_riders = [
            _onboard(mediator, metro, end.shape, f"kept-{index}") for index in range(2)
        ]
        old_plans = {}
        for rider in (credited, *other_riders):
            old_plans[rider] = TravelPlan([Node(end)])
            mediator.travel_plans[rider] = old_plans[rider]
            rider.wait_ms = 4321
        before_deliveries = mediator.deliveries
        before_credits = mediator.line_credits
        _assert_removal_dispatchable(mediator, path)

        mediator.remove_path(path)

        self.assertNotIn(path, mediator.paths)
        self.assertEqual(mediator.metros, [])
        self.assertEqual(mediator.deliveries, before_deliveries + 1)
        self.assertEqual(mediator.line_credits, before_credits + 1)
        self.assertNotIn(credited, mediator.passengers)
        self.assertNotIn(credited, start.passengers)
        self.assertNotIn(credited, metro.passengers)
        self.assertNotIn(credited, mediator.travel_plans)
        self.assertTrue(credited.is_at_destination)
        for rider in other_riders:
            self.assertIn(rider, mediator.passengers)
            self.assertIn(rider, start.passengers)
            self.assertNotIn(rider, metro.passengers)
            self.assertEqual(rider.wait_ms, 0)
            self.assertFalse(rider.is_at_destination)
            self.assertIsNot(mediator.travel_plans.get(rider), old_plans[rider])
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)
        self.assertEqual(mediator.available_carriages, mediator.num_carriages)

    def test_alight_placement_at_station_and_mid_segment_by_progress(self):
        cases = (
            ("stopped-at-station", None, True, "end"),
            ("mid-segment-near-start", Point(150, 200), True, "start"),
            ("mid-segment-near-end", Point(450, 200), False, "end"),
        )
        for name, position, is_forward, expected in cases:
            with self.subTest(case=name):
                mediator, start, end, path, metro = _removal_game(6401)
                if position is None:
                    metro.current_station = end
                    metro.position = end.position
                else:
                    metro.current_station = None
                    metro.position = position
                    metro.is_forward = is_forward
                rider = _onboard(
                    mediator,
                    metro,
                    Triangle(station_color, station_size),
                    f"placement-{name}",
                )
                _assert_removal_dispatchable(mediator, path)

                mediator.remove_path(path)

                target = start if expected == "start" else end
                self.assertIn(rider, target.passengers)
                self.assertIn(rider, mediator.passengers)
                self.assertEqual(rider.wait_ms, 0)

    def test_alight_on_padding_segment_uses_adjacent_station_in_travel_order(self):
        for is_forward in (True, False):
            with self.subTest(is_forward=is_forward):
                mediator = Mediator(seed=6402)
                bend = [
                    Station(
                        Rect(station_color, 2 * station_size, 2 * station_size),
                        Point(100, 200),
                    ),
                    Station(Circle(station_color, station_size), Point(400, 200)),
                    Station(Triangle(station_color, station_size), Point(400, 500)),
                ]
                _adopt_stations(mediator, bend)
                path, metro = _create_served_path(mediator, [0, 1, 2])
                self.assertIsInstance(path.segments[1], PaddingSegment)
                metro.current_segment_idx = 1
                metro.current_segment = path.segments[1]
                metro.position = path.segments[1].segment_start
                metro.current_station = None
                metro.is_forward = is_forward
                rider = _onboard(
                    mediator, metro, Rect(station_color, 10, 10), "padding-rider"
                )
                _assert_removal_dispatchable(mediator, path)

                mediator.remove_path(path)

                self.assertIn(rider, bend[1].passengers)
                self.assertIn(rider, mediator.passengers)

    def test_overflow_dump_succeeds_and_station_only_drains_afterwards(self):
        mediator = Mediator(seed=6403)
        shared = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(100, 200)
        )
        other = Station(Circle(station_color, station_size), Point(900, 200))
        drain = Station(Triangle(station_color, station_size), Point(100, 700))
        _adopt_stations(mediator, [shared, other, drain])
        removed_path, loaded = _create_served_path(mediator, [0, 1])
        surviving_path, server = _create_served_path(mediator, [0, 2])
        loaded.carriages.extend((Carriage(), Carriage()))
        mediator.num_carriages = 2
        for holder in (loaded, server):
            holder.current_station = shared
            holder.position = shared.position
        riders = [
            _onboard(mediator, loaded, drain.shape, f"dumped-{index}")
            for index in range(14)
        ]
        _quiet_spawning(mediator)
        before_total = len(mediator.passengers)
        _assert_removal_dispatchable(mediator, removed_path)

        mediator.remove_path(removed_path)

        self.assertEqual(len(shared.passengers), 14)
        self.assertGreater(len(shared.passengers), station_capacity)
        self.assertFalse(shared.has_room())
        for rider in riders:
            self.assertIn(rider, mediator.passengers)
        mediator.station_spawn_interval_steps[shared] = 1
        mediator.station_steps_since_last_spawn[shared] = 5
        mediator.spawn_passengers()
        self.assertEqual(len(shared.passengers), 14)
        self.assertEqual(len(mediator.passengers), before_total)
        self.assertEqual(mediator.station_steps_since_last_spawn[shared], 0)
        mediator.move_passengers(server.boarding_time_per_passenger_ms)
        self.assertEqual(len(shared.passengers), 13)
        self.assertEqual(len(server.passengers), 1)
        self.assertIs(server.passengers[0], riders[0])

    def test_overflow_gates_stay_ordinary_at_and_above_capacity(self):
        # regression guard: green at baseline (D-024 keeps every ordinary gate).
        mediator, start, end, path, metro = _removal_game(6404)
        metro.current_station = end
        metro.position = end.position
        transfer_rider = _onboard(mediator, metro, start.shape, "blocked-transfer")
        plan = TravelPlan([Node(end)])
        mediator.travel_plans[transfer_rider] = plan
        for index in range(13):
            rider = passenger_for(start, name=f"crowd-{index}")
            end.passengers.append(rider)
            mediator.passengers.append(rider)
        _quiet_spawning(mediator)
        self.assertFalse(end.has_room())

        before_total = len(mediator.passengers)
        mediator.station_spawn_interval_steps[end] = 1
        mediator.station_steps_since_last_spawn[end] = 5
        mediator.spawn_passengers()
        self.assertEqual(len(end.passengers), 13)
        self.assertEqual(len(mediator.passengers), before_total)
        self.assertEqual(mediator.station_steps_since_last_spawn[end], 0)

        mediator.move_passengers(metro.boarding_time_per_passenger_ms)
        self.assertEqual(len(end.passengers), 12)
        self.assertIn(transfer_rider, metro.passengers)
        mediator.move_passengers(metro.boarding_time_per_passenger_ms)
        self.assertEqual(len(end.passengers), 11)
        self.assertIn(transfer_rider, metro.passengers)
        mediator.move_passengers(metro.boarding_time_per_passenger_ms)
        self.assertEqual(len(end.passengers), 12)
        self.assertIn(transfer_rider, end.passengers)

    def test_consist_refund_returns_availability_exactly_once(self):
        # regression guard: green at baseline (derived counts already refund).
        mediator, _start, _end, path, metro = _removal_game(6405)
        metro.carriages.extend((Carriage(), Carriage()))
        mediator.num_carriages = 2
        self.assertEqual(mediator.available_locomotives, mediator.num_metros - 1)
        self.assertEqual(mediator.available_carriages, 0)

        mediator.remove_path(path)

        self.assertEqual(mediator.metros, [])
        self.assertEqual(mediator.assigned_carriages, 0)
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)
        self.assertEqual(mediator.available_carriages, mediator.num_carriages)


class TestGM06dRemovalTransaction(unittest.TestCase):
    def _loaded_game(self, seed: int):
        mediator, start, end, path, metro = _removal_game(seed)
        metro.carriages.append(Carriage())
        mediator.num_carriages = 2
        aboard = _onboard(mediator, metro, start.shape, "aboard-credited")
        kept = _onboard(mediator, metro, end.shape, "aboard-kept")
        waiting = passenger_for(start, name="waiting")
        end.add_passenger(waiting)
        mediator.passengers.append(waiting)
        for rider in (aboard, kept, waiting):
            mediator.travel_plans[rider] = TravelPlan([Node(end)])
            rider.wait_ms = 777
        _assert_removal_dispatchable(mediator, path)
        return mediator, path

    def test_ordinary_failure_mid_removal_restores_exact_identity(self):
        mediator, path = self._loaded_game(6406)
        before = _footprint(mediator)

        def raising_release(_path):
            raise RuntimeError("release fault")

        mediator.release_color_for_path = raising_release
        try:
            mediator.remove_path(path)
        except RuntimeError:
            pass

        _assert_footprint(self, mediator, before)

    def test_base_exception_failure_rethrows_after_restoration(self):
        mediator, path = self._loaded_game(6407)
        before = _footprint(mediator)
        base_error = KeyboardInterrupt("release base fault")

        def raising_release(_path):
            raise base_error

        mediator.release_color_for_path = raising_release
        try:
            mediator.remove_path(path)
        except BaseException as raised:  # noqa: BLE001 - exact rethrow contract
            self.assertIs(raised, base_error)
        else:
            self.fail("KeyboardInterrupt was not rethrown")

        _assert_footprint(self, mediator, before)

    def test_failed_removal_restores_both_seeded_rng_streams(self):
        mediator, path = self._loaded_game(6408)
        before = _footprint(mediator)

        def rng_consuming_release(_path):
            mediator.context.python_random.random()
            mediator.context.numpy_random.random()
            raise RuntimeError("release rng fault")

        mediator.release_color_for_path = rng_consuming_release
        try:
            mediator.remove_path(path)
        except RuntimeError:
            pass

        self.assertEqual(_rng_state(mediator), before["rng"])
        _assert_footprint(self, mediator, before)

    def test_failure_after_milestone_crossing_credit_restores_progression(self):
        mediator = Mediator(seed=6409)
        mediator.unlocked_num_paths = mediator.num_paths
        mediator.update_path_button_lock_states()
        path, metro = _create_served_path(mediator, [0, 1])
        metro.current_station = path.stations[0]
        metro.position = path.stations[0].position
        rider = _onboard(mediator, metro, path.stations[0].shape, "milestone-rider")
        plan = TravelPlan([Node(path.stations[1])])
        mediator.travel_plans[rider] = plan
        mediator.deliveries = station_unlock_milestones[0] - 1
        mediator.line_credits = 3
        _assert_removal_dispatchable(mediator, path)
        before = _footprint(mediator)
        pending_station = mediator.all_stations[len(mediator.stations)]
        self.assertIsNone(pending_station.unlock_blink_start_time_ms)

        def raising_sweep():
            raise RuntimeError("replan sweep fault")

        mediator.find_travel_plan_for_passengers = raising_sweep
        try:
            mediator.remove_path(path)
        except RuntimeError:
            pass

        self.assertEqual(mediator.deliveries, station_unlock_milestones[0] - 1)
        self.assertEqual(
            mediator._progression.deliveries, station_unlock_milestones[0] - 1
        )
        self.assertEqual(mediator.line_credits, 3)
        self.assertEqual(mediator._progression.line_credits, 3)
        self.assertEqual(_progression_views(mediator), before["progression"])
        self.assertIsNone(pending_station.unlock_blink_start_time_ms)
        self.assertIn(path, mediator.paths)
        self.assertIn(metro, mediator.metros)
        self.assertIs(mediator.path_to_button[path].path, path)
        self.assertIn(rider, metro.passengers)
        self.assertIn(rider, mediator.passengers)
        self.assertIs(mediator.travel_plans.get(rider), plan)
        self.assertFalse(rider.is_at_destination)
        _assert_footprint(self, mediator, before)


if __name__ == "__main__":
    unittest.main()
