"""GM-06d Case 1 contract: occupied-locomotive queued return.

Encodes the app-experience and mechanism contract from
docs/threads/current/game-maturity/2026-07-21/8/PLAN.md ("Case 1 -
Occupied-locomotive queued return") under the D-024 soft-cap rule:
widened occupied selection, service-state preservation, the guaranteed
force-alight drain, oracle-first ordinary unloads, and bounded-travel
settlement. Red at baseline except the marked regression guards.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import passenger_color, passenger_size, station_capacity
from entity.carriage import Carriage
from entity.metro import Metro
from entity.passenger import Passenger
from env import MiniMetroEnv
from geometry.type import ShapeType
from graph.node import Node
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint
from test.gm06c_simulation_ui_support import make_two_station_game, passenger_for
from travel_plan import TravelPlan
from utils import get_shape_from_type


def _offline_rider(name: str) -> Passenger:
    """A rider whose destination shape exists on no station under test."""

    shape = get_shape_from_type(ShapeType.TRIANGLE, passenger_color, passenger_size)
    rider = Passenger(shape)
    rider.id = name
    return rider


def _board(mediator: Mediator, metro: Metro, rider: Passenger) -> Passenger:
    metro.passengers.append(rider)
    mediator.passengers.append(rider)
    return rider


def _unlock_all_paths(mediator: Mediator) -> None:
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _quiet_simulation(mediator: Mediator) -> None:
    future = 10**9
    mediator.passenger_spawning_step = future
    mediator.passenger_spawning_interval_step = future
    mediator.overdue_passenger_threshold = future
    for station in mediator.stations:
        mediator.station_steps_since_last_spawn[station] = 0
        mediator.station_spawn_interval_steps[station] = future


def _fresh_path(mediator: Mediator, indices=(0, 1), loop: bool = False):
    _unlock_all_paths(mediator)
    path = mediator.create_path_from_station_indices(list(indices), loop)
    if path is None:
        raise AssertionError("test setup could not create a path")
    return path


def _install_metro(mediator: Mediator, path) -> Metro:
    metro = Metro()
    path.add_metro(metro)
    mediator.metros.append(metro)
    return metro


def _occupy(mediator: Mediator, path, metro: Metro, count: int) -> None:
    for index in range(count):
        rider = Passenger(path.stations[0].shape)
        rider.id = f"{metro.id}-rider-{index}"
        _board(mediator, metro, rider)


class TestGM06dOccupiedSelection(unittest.TestCase):
    def test_empty_preference_still_selects_empty_over_occupied(self) -> None:
        # regression guard: green at baseline
        mediator = Mediator(seed=6400)
        path = _fresh_path(mediator)
        occupied_first = _install_metro(mediator, path)
        empty_mid = _install_metro(mediator, path)
        occupied_last = _install_metro(mediator, path)
        _occupy(mediator, path, occupied_first, 1)
        _occupy(mediator, path, occupied_last, 1)

        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertFalse(occupied_first.is_unassignment_queued)
        self.assertTrue(empty_mid.is_unassignment_queued)
        self.assertFalse(occupied_last.is_unassignment_queued)
        self.assertEqual(path.metros, [occupied_first, empty_mid, occupied_last])
        self.assertEqual(mediator.metros, [occupied_first, empty_mid, occupied_last])

    def test_only_occupied_metros_selects_fewest_passengers(self) -> None:
        mediator = Mediator(seed=6401)
        path = _fresh_path(mediator)
        two_riders = _install_metro(mediator, path)
        one_rider = _install_metro(mediator, path)
        three_riders = _install_metro(mediator, path)
        _occupy(mediator, path, two_riders, 2)
        _occupy(mediator, path, one_rider, 1)
        _occupy(mediator, path, three_riders, 3)

        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertFalse(two_riders.is_unassignment_queued)
        self.assertTrue(one_rider.is_unassignment_queued)
        self.assertFalse(three_riders.is_unassignment_queued)
        self.assertEqual(path.metros, [two_riders, one_rider, three_riders])
        self.assertEqual(mediator.metros, [two_riders, one_rider, three_riders])
        self.assertEqual(len(one_rider.passengers), 1)

    def test_occupied_tie_breaks_by_latest_path_order(self) -> None:
        mediator = Mediator(seed=6402)
        path = _fresh_path(mediator)
        early_tie = _install_metro(mediator, path)
        heavier = _install_metro(mediator, path)
        late_tie = _install_metro(mediator, path)
        _occupy(mediator, path, early_tie, 1)
        _occupy(mediator, path, heavier, 2)
        _occupy(mediator, path, late_tie, 1)

        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertFalse(early_tie.is_unassignment_queued)
        self.assertFalse(heavier.is_unassignment_queued)
        self.assertTrue(late_tie.is_unassignment_queued)
        self.assertIn(late_tie, path.metros)
        self.assertIn(late_tie, mediator.metros)


class TestGM06dOccupiedQueueServiceState(unittest.TestCase):
    def test_occupied_queue_preserves_in_progress_unload_state(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6410)
        rider = passenger_for(start, name="in-progress-unload")
        _board(mediator, metro, rider)
        mediator.move_passengers(250)
        action = metro._station_service_action
        self.assertIsNotNone(action)
        assert action is not None
        self.assertIs(action[1], rider)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (250, 250),
        )

        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertTrue(metro.is_unassignment_queued)
        self.assertIn(metro, path.metros)
        self.assertIn(metro, mediator.metros)
        preserved = metro._station_service_action
        self.assertIsNotNone(preserved)
        assert preserved is not None
        self.assertEqual(preserved[0], action[0])
        self.assertIs(preserved[1], rider)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (250, 250),
        )
        self.assertFalse(mediator.can_board_at_station(metro, start))

        mediator.move_passengers(250)
        self.assertTrue(rider.is_at_destination)
        self.assertNotIn(rider, mediator.passengers)
        self.assertEqual(mediator.deliveries, 1)

        mediator.increment_time(0)
        self.assertNotIn(metro, path.metros)
        self.assertNotIn(metro, mediator.metros)
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)

    def test_empty_fast_path_still_clears_and_detaches_immediately(self) -> None:
        # regression guard: green at baseline
        mediator, start, end, path, metro = make_two_station_game(seed=6411)
        waiting = passenger_for(end, name="waiting-boarder")
        start.add_passenger(waiting)
        mediator.passengers.append(waiting)
        plan = TravelPlan([Node(end)])
        plan.next_path = path
        mediator.travel_plans[waiting] = plan
        mediator.move_passengers(250)
        self.assertIsNotNone(metro._station_service_action)
        self.assertEqual(metro.boarding_progress_ms, 250)

        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertNotIn(metro, path.metros)
        self.assertNotIn(metro, mediator.metros)
        self.assertIsNone(metro._station_service_action)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (0, 0),
        )
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)
        self.assertIn(waiting, start.passengers)


class TestGM06dGuaranteedDrain(unittest.TestCase):
    def _drained_setup(self):
        mediator, start, end, path, metro = make_two_station_game(seed=6420)
        metro.carriages.append(Carriage())
        waiting = []
        for index in range(station_capacity):
            passenger = passenger_for(end, name=f"waiting-{index}")
            start.add_passenger(passenger)
            mediator.passengers.append(passenger)
            waiting.append(passenger)

        no_plan = _board(mediator, metro, _offline_rider("no-plan"))
        no_plan.wait_ms = 777

        off_line = _board(mediator, metro, _offline_rider("off-line-plan"))
        off_line.wait_ms = 777
        offline_shape = get_shape_from_type(
            ShapeType.CROSS, passenger_color, passenger_size
        )
        from entity.station import Station
        from geometry.point import Point

        foreign_station = Station(offline_shape, Point(2000, 2000))
        off_plan = TravelPlan([Node(foreign_station)])
        mediator.travel_plans[off_line] = off_plan

        blocked = _board(mediator, metro, _offline_rider("blocked-transfer"))
        blocked.wait_ms = 777
        blocked_plan = TravelPlan([Node(start)])
        mediator.travel_plans[blocked] = blocked_plan

        metro.is_unassignment_queued = True
        riders = (no_plan, off_line, blocked)
        plans = (off_plan, blocked_plan)
        return mediator, start, path, metro, waiting, riders, plans

    def test_drain_alights_all_matching_riders_one_batch_and_settles(self) -> None:
        (
            mediator,
            start,
            path,
            metro,
            waiting,
            riders,
            plans,
        ) = self._drained_setup()
        no_plan, off_line, blocked = riders
        off_plan, blocked_plan = plans
        self.assertEqual(len(start.passengers), station_capacity)
        self.assertFalse(start.has_room())

        mediator.increment_time(0)

        # One atomic batch, appended in exact metro holder order, with the
        # D-024 overflow permission above station_capacity.
        self.assertEqual(metro.passengers, [])
        self.assertEqual(start.passengers, [*waiting, no_plan, off_line, blocked])
        self.assertGreater(len(start.passengers), station_capacity)
        for rider in riders:
            self.assertIn(rider, mediator.passengers)
            self.assertFalse(rider.is_at_destination)
            self.assertEqual(rider.wait_ms, 0)
        # The stale plans are cleared; any surviving entry must be fresh.
        self.assertIsNot(mediator.travel_plans.get(off_line), off_plan)
        self.assertIsNot(mediator.travel_plans.get(blocked), blocked_plan)

        # The queued stop-override never fabricates a service action.
        self.assertIsNone(metro._station_service_action)

        # The emptied Metro settles the same tick and refunds its consist
        # through the derived counts.
        self.assertNotIn(metro, path.metros)
        self.assertNotIn(metro, mediator.metros)
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)
        self.assertEqual(mediator.assigned_carriages, 0)
        self.assertEqual(mediator.available_carriages, mediator.num_carriages)

    def test_ordinary_destination_unload_still_runs_timed_first(self) -> None:
        # regression guard: green at baseline
        mediator, start, end, path, metro = make_two_station_game(seed=6421)
        rider_dest = passenger_for(start, name="dest-unload")
        _board(mediator, metro, rider_dest)
        rider_stuck = _board(mediator, metro, _offline_rider("stuck"))
        metro.is_unassignment_queued = True

        mediator.increment_time(0)

        # The executable destination unload is served through the normal
        # timed path, never force-alighted instantly, and no drain fires
        # while the oracle still resolves an executable action.
        action = metro._station_service_action
        self.assertIsNotNone(action)
        assert action is not None
        self.assertIs(action[1], rider_dest)
        self.assertIn("destination", str(action[0]).lower())
        self.assertEqual(metro.stop_time_remaining_ms, 500)
        self.assertEqual(metro.passengers, [rider_dest, rider_stuck])
        self.assertNotIn(rider_dest, start.passengers)
        self.assertNotIn(rider_stuck, start.passengers)
        self.assertIn(metro, mediator.metros)

    def test_drain_fires_after_ordinary_unload_completes_same_tick(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6422)
        rider_dest = passenger_for(start, name="dest-unload")
        _board(mediator, metro, rider_dest)
        rider_stuck = _board(mediator, metro, _offline_rider("stuck"))
        metro.is_unassignment_queued = True
        mediator.increment_time(0)

        mediator.increment_time(500)

        self.assertTrue(rider_dest.is_at_destination)
        self.assertNotIn(rider_dest, mediator.passengers)
        self.assertEqual(mediator.deliveries, 1)
        self.assertEqual(metro.passengers, [])
        self.assertIn(rider_stuck, start.passengers)
        self.assertIn(rider_stuck, mediator.passengers)
        self.assertFalse(rider_stuck.is_at_destination)
        self.assertNotIn(metro, path.metros)
        self.assertNotIn(metro, mediator.metros)
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)


class TestGM06dBoundedReturn(unittest.TestCase):
    def test_occupied_queued_return_completes_on_small_loop(self) -> None:
        mediator = Mediator(seed=6430)
        _quiet_simulation(mediator)
        path = _fresh_path(mediator, (0, 1, 2), loop=True)
        self.assertTrue(path.is_looped)
        self.assertTrue(mediator.assign_locomotive(path))
        metro = path.metros[0]
        rider = Passenger(path.stations[1].shape)
        rider.id = "loop-rider"
        _board(mediator, metro, rider)

        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        self.assertTrue(metro.is_unassignment_queued)

        settled_after = None
        for tick in range(3000):
            mediator.increment_time(250)
            if all(candidate is not metro for candidate in mediator.metros):
                settled_after = tick
                break

        self.assertIsNotNone(
            settled_after,
            "queued occupied return never settled within bounded travel",
        )
        self.assertTrue(all(candidate is not metro for candidate in path.metros))
        self.assertEqual(metro.passengers, [])
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)
        # The rider is conserved: delivered as a genuine delivery or waiting
        # at a real station, never deleted or frozen aboard.
        delivered = rider.is_at_destination
        waiting_somewhere = any(
            rider in station.passengers for station in mediator.stations
        )
        self.assertTrue(delivered or waiting_somewhere)
        if delivered:
            self.assertNotIn(rider, mediator.passengers)
        else:
            self.assertIn(rider, mediator.passengers)


class TestGM06dPausedQueueReconciliation(unittest.TestCase):
    """Queueing an occupied at-station Metro reconciles its service cache.

    Adversarial-review F-1 regression (queue direction): the preserved
    mid-BOARD cache must not disagree with the queue-gated pure oracle
    while paused, so fleet queries stay truthful, cancellation stays
    possible, and checkpoint v4 accepts the legitimately-reached state.
    """

    def _paused_occupied_mid_board_environment(self):
        # Reviewer probe: seed 0, dt 250 — a three-station line with one
        # locomotive reaches an occupied mid-BOARD stop after 14 noops.
        env = MiniMetroEnv(reward_mode="deliveries")
        env.reset(seed=0)
        for action in (
            {"type": "create_path", "stations": [0, 1, 2], "loop": False},
            {"type": "assign_locomotive", "path_index": 0},
            *({"type": "noop"} for _ in range(14)),
            {"type": "pause"},
        ):
            _, _, _, info = env.step(action, dt_ms=250)
            self.assertTrue(info["action_ok"])
        mediator = env.mediator
        metro = mediator.metros[0]
        cache = metro._station_service_action
        self.assertTrue(mediator.is_paused)
        self.assertIsNotNone(metro.current_station)
        self.assertIsNotNone(cache)
        assert cache is not None
        self.assertEqual(cache[0], "board")
        self.assertTrue(metro.passengers)
        self.assertTrue(
            0 < metro.boarding_progress_ms < metro.boarding_time_per_passenger_ms
        )
        return env, mediator, mediator.paths[0], metro

    def test_paused_queue_of_occupied_mid_board_metro_stays_canonical(self) -> None:
        env, mediator, path, metro = self._paused_occupied_mid_board_environment()

        _, _, _, info = env.step(
            {"type": "unassign_locomotive", "path_index": 0}, dt_ms=250
        )

        self.assertTrue(info["action_ok"])
        self.assertTrue(metro.is_unassignment_queued)
        self.assertIn(metro, path.metros)
        self.assertIn(metro, mediator.metros)
        # The now-illegal BOARD binding is dropped so the cache equals the
        # queue-gated pure oracle even while paused.
        self.assertIsNone(metro._station_service_action)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (0, 0)
        )
        checkpoint = canonical_checkpoint(env, schema_version=4)
        self.assertEqual(checkpoint["schemaVersion"], 4)
        self.assertEqual(mediator.queued_locomotives_for_path(path), 1)
        # Cancellation works while still paused and rebinds the again-legal
        # boarding action synchronously.
        self.assertTrue(mediator.is_paused)
        self.assertTrue(mediator.can_cancel_unassignment(path))
        self.assertTrue(mediator.cancel_unassignment(path))
        self.assertFalse(metro.is_unassignment_queued)
        rebound = metro._station_service_action
        self.assertIsNotNone(rebound)
        assert rebound is not None
        self.assertEqual(rebound[0], "board")
        checkpoint = canonical_checkpoint(env, schema_version=4)
        self.assertEqual(checkpoint["schemaVersion"], 4)


class TestGM06dTerminalTickDrainGate(unittest.TestCase):
    """The forced-alight drain never moves riders once the game is over."""

    def test_game_over_flipping_tick_leaves_queued_metro_riders_untouched(
        self,
    ) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6440)
        rider_dest = passenger_for(start, name="dest-unload")
        _board(mediator, metro, rider_dest)
        rider_stuck = _board(mediator, metro, _offline_rider("stuck"))
        metro.is_unassignment_queued = True
        mediator.increment_time(0)
        # The ordinary destination unload is mid-service, so the pre-flow
        # drain seam stays quiet at the start of the flipping tick.
        self.assertIsNotNone(metro._station_service_action)
        self.assertEqual(metro.stop_time_remaining_ms, 500)
        overdue = passenger_for(start, name="overdue")
        end.add_passenger(overdue)
        mediator.passengers.append(overdue)
        overdue.wait_ms = mediator.passenger_max_wait_time_ms
        mediator.overdue_passenger_threshold = 1

        mediator.increment_time(500)

        self.assertTrue(mediator.is_game_over)
        # The in-flight ordinary unload still completes on the terminal tick.
        self.assertTrue(rider_dest.is_at_destination)
        self.assertEqual(mediator.deliveries, 1)
        # The post-flow drain is gated on game over: no rider moves after
        # the game ends, and the still-occupied Metro never settles.
        self.assertEqual(metro.passengers, [rider_stuck])
        self.assertNotIn(rider_stuck, start.passengers)
        self.assertIn(rider_stuck, mediator.passengers)
        self.assertIn(metro, path.metros)
        self.assertIn(metro, mediator.metros)


if __name__ == "__main__":
    unittest.main()
