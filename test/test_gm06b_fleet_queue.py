from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.metro import Metro
from entity.passenger import Passenger
from graph.graph_algo import build_station_nodes_dict
from mediator import Mediator


class _RemoveThenRaise(list):
    def remove(self, value) -> None:
        super().remove(value)
        raise RuntimeError("remove fault")


def _unlock_all_paths(mediator: Mediator) -> None:
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _different_shape_indices(mediator: Mediator) -> tuple[int, int]:
    for first, source in enumerate(mediator.stations):
        for second, destination in enumerate(mediator.stations):
            if source.shape.type != destination.shape.type:
                return first, second
    raise AssertionError("test setup requires two station shape types")


def _unserved_path(mediator: Mediator):
    _unlock_all_paths(mediator)
    first, second = _different_shape_indices(mediator)
    path = mediator.create_path_from_station_indices([first, second])
    if path is None:
        raise AssertionError("test setup could not create a path")
    for metro in tuple(path.metros):
        while metro in mediator.metros:
            mediator.metros.remove(metro)
    path.metros.clear()
    return path, first, second


def _install_metro(mediator: Mediator, path) -> Metro:
    metro = Metro()
    path.add_metro(metro)
    mediator.metros.append(metro)
    return metro


def _quiet_simulation(mediator: Mediator) -> None:
    future = 10**9
    mediator.passenger_spawning_step = future
    mediator.passenger_spawning_interval_step = future
    mediator.overdue_passenger_threshold = future
    for station in mediator.stations:
        mediator.station_steps_since_last_spawn[station] = 0
        mediator.station_spawn_interval_steps[station] = future


def _add_waiting_passenger(mediator: Mediator, path) -> Passenger:
    source, destination = path.stations[:2]
    passenger = Passenger(destination.shape)
    source.add_passenger(passenger)
    mediator.passengers.append(passenger)
    mediator.find_travel_plan_for_passengers()
    if passenger not in mediator.travel_plans:
        raise AssertionError("test setup could not route the waiting passenger")
    return passenger


class TestGM06bFleetQueue(unittest.TestCase):
    def assert_conserved(self, mediator: Mediator) -> None:
        total = mediator.num_metros
        assigned = len(mediator.metros)
        self.assertEqual(
            mediator.available_locomotives,
            max(0, total - assigned),
        )
        if assigned <= total:
            self.assertEqual(mediator.available_locomotives + assigned, total)

        global_ids = [id(metro) for metro in mediator.metros]
        self.assertEqual(len(global_ids), len(set(global_ids)))
        owners = [metro for path in mediator.paths for metro in path.metros]
        self.assertEqual({id(metro) for metro in owners}, set(global_ids))
        self.assertEqual(len({id(metro) for metro in owners}), len(owners))

    def test_reverse_order_candidate_skips_occupied_and_queues_last_empty(self) -> None:
        mediator = Mediator(seed=6300)
        path, _, _ = _unserved_path(mediator)
        first = _install_metro(mediator, path)
        second = _install_metro(mediator, path)
        occupied_last = _install_metro(mediator, path)
        rider = _add_waiting_passenger(mediator, path)
        path.stations[0].move_passenger(rider, occupied_last)

        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertFalse(getattr(first, "is_unassignment_queued", False))
        self.assertTrue(second.is_unassignment_queued)
        self.assertFalse(getattr(occupied_last, "is_unassignment_queued", False))
        self.assertEqual(path.metros, [first, second, occupied_last])
        self.assertEqual(mediator.metros, [first, second, occupied_last])

    def test_repeated_requests_queue_distinct_candidates_and_never_cancel_prior_queue(
        self,
    ) -> None:
        mediator = Mediator(seed=6301)
        path, _, _ = _unserved_path(mediator)
        first = _install_metro(mediator, path)
        second = _install_metro(mediator, path)

        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        self.assertFalse(mediator.queue_locomotive_unassignment(path))

        self.assertTrue(first.is_unassignment_queued)
        self.assertTrue(second.is_unassignment_queued)
        self.assertEqual(path.metros, [first, second])
        self.assertEqual(mediator.metros, [first, second])

    def test_fresh_segment_start_coordinate_queues_without_immediate_detachment(
        self,
    ) -> None:
        mediator = Mediator(seed=6302)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        self.assertIsNone(metro.current_station)
        self.assertEqual(metro.position, path.segments[0].segment_start)

        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertTrue(metro.is_unassignment_queued)
        self.assertIn(metro, path.metros)
        self.assertIn(metro, mediator.metros)
        self.assertEqual(mediator.available_locomotives, mediator.num_metros - 1)

    def test_exact_owned_current_station_detaches_immediately(self) -> None:
        mediator = Mediator(seed=6303)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        metro.current_station = path.stations[0]

        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertNotIn(metro, path.metros)
        self.assertNotIn(metro, mediator.metros)
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)
        self.assert_conserved(mediator)

    def test_moving_queue_forces_first_real_stop_and_then_detaches(self) -> None:
        mediator = Mediator(seed=6304)
        _quiet_simulation(mediator)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        destination = path.stations[1]

        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        metro.position = metro.current_segment.segment_end
        mediator.increment_time(1)

        self.assertIs(metro.current_station, destination)
        self.assertTrue(metro.just_arrived_and_stopped)
        self.assertNotIn(metro, path.metros)
        self.assertNotIn(metro, mediator.metros)
        self.assert_conserved(mediator)

    def test_queued_metro_crosses_padding_without_a_synthetic_stop(self) -> None:
        mediator = Mediator(seed=63041)
        _quiet_simulation(mediator)
        _unlock_all_paths(mediator)
        path = mediator.create_path_from_station_indices([0, 1, 2])
        if path is None:
            raise AssertionError("test setup could not create a three-station path")
        metro = _install_metro(mediator, path)
        padding = path.segments[1]
        metro.current_segment_idx = 1
        metro.current_segment = padding
        metro.position = padding.segment_end
        metro.current_station = None

        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        self.assertFalse(mediator.should_stop_at_next_station(metro, {}))
        mediator.increment_time(1)

        self.assertIsNone(metro.current_station)
        self.assertFalse(metro.just_arrived_and_stopped)
        self.assertIs(metro.current_segment, path.segments[2])
        self.assertTrue(mediator.should_stop_at_next_station(metro, {}))
        self.assertIn(metro, mediator.metros)

    def test_nonmutating_boarding_query_returns_no_candidate_for_queued_metro(
        self,
    ) -> None:
        mediator = Mediator(seed=6305)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        passenger = _add_waiting_passenger(mediator, path)
        metro.is_unassignment_queued = True
        graph = build_station_nodes_dict(mediator.stations, mediator.paths)

        candidates = mediator.get_boarding_candidates_for_metro(
            metro,
            path.stations[0],
            graph,
            mutate_travel_plans=False,
        )

        self.assertEqual(candidates, [])
        self.assertIn(passenger, path.stations[0].passengers)
        self.assertEqual(metro.passengers, [])

    def test_mutating_boarding_query_is_empty_and_does_not_replace_travel_plan(
        self,
    ) -> None:
        mediator = Mediator(seed=6306)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        passenger = _add_waiting_passenger(mediator, path)
        original_plan = mediator.travel_plans[passenger]
        original_nodes = tuple(original_plan.node_path)
        metro.is_unassignment_queued = True
        graph = build_station_nodes_dict(mediator.stations, mediator.paths)

        candidates = mediator.get_boarding_candidates_for_metro(
            metro,
            path.stations[0],
            graph,
            mutate_travel_plans=True,
        )

        self.assertEqual(candidates, [])
        self.assertIs(mediator.travel_plans[passenger], original_plan)
        self.assertEqual(tuple(original_plan.node_path), original_nodes)

    def test_queued_metro_has_no_boarding_permission_or_boarding_dwell(self) -> None:
        mediator = Mediator(seed=6307)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        _add_waiting_passenger(mediator, path)
        station = path.stations[0]
        metro.current_station = station
        metro.is_unassignment_queued = True
        graph = build_station_nodes_dict(mediator.stations, mediator.paths)

        self.assertFalse(mediator.can_board_at_station(metro, station))
        mediator.start_station_stop_if_needed(metro, station, graph)
        self.assertEqual(metro.stop_time_remaining_ms, 0)
        self.assertEqual(metro.boarding_progress_ms, 0)

    def test_passenger_flow_never_boards_waiting_rider_into_queued_metro(self) -> None:
        mediator = Mediator(seed=6308)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        passenger = _add_waiting_passenger(mediator, path)
        station = path.stations[0]
        metro.current_station = station
        metro.is_unassignment_queued = True

        mediator.move_passengers(metro.boarding_time_per_passenger_ms)

        self.assertIn(passenger, station.passengers)
        self.assertNotIn(passenger, metro.passengers)
        self.assertEqual(metro.stop_time_remaining_ms, 0)
        self.assertEqual(metro.boarding_progress_ms, 0)

    def test_terminal_producing_tick_finishes_empty_arrival_settlement_once(
        self,
    ) -> None:
        mediator = Mediator(seed=6309)
        _quiet_simulation(mediator)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        waiting = _add_waiting_passenger(mediator, path)
        waiting.wait_ms = mediator.passenger_max_wait_time_ms
        mediator.overdue_passenger_threshold = 1

        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        metro.position = metro.current_segment.segment_end
        mediator.increment_time(1)

        self.assertTrue(mediator.is_game_over)
        self.assertNotIn(metro, path.metros)
        self.assertNotIn(metro, mediator.metros)
        frozen = (mediator.time_ms, mediator.steps, tuple(mediator.metros))
        mediator.increment_time(1000)
        self.assertEqual(
            (mediator.time_ms, mediator.steps, tuple(mediator.metros)),
            frozen,
        )

    def test_paused_request_is_accepted_but_moving_queue_does_not_advance(self) -> None:
        mediator = Mediator(seed=6310)
        _quiet_simulation(mediator)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        before = metro.position.to_tuple()
        mediator.is_paused = True

        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        mediator.increment_time(1000)

        self.assertEqual(metro.position.to_tuple(), before)
        self.assertTrue(metro.is_unassignment_queued)
        self.assertIn(metro, path.metros)
        self.assertIn(metro, mediator.metros)

    def test_terminal_request_rejects_without_queue_or_collection_effects(self) -> None:
        mediator = Mediator(seed=6311)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        mediator.is_game_over = True
        path_before = tuple(path.metros)
        global_before = tuple(mediator.metros)

        self.assertFalse(mediator.queue_locomotive_unassignment(path))

        self.assertFalse(getattr(metro, "is_unassignment_queued", False))
        self.assertEqual(tuple(path.metros), path_before)
        self.assertEqual(tuple(mediator.metros), global_before)

    def test_malformed_candidate_ownership_rejects_without_creating_queue_intent(
        self,
    ) -> None:
        for kind in ("missing-global", "duplicate-global"):
            with self.subTest(kind=kind):
                mediator = Mediator(seed=6312)
                path, _, _ = _unserved_path(mediator)
                metro = _install_metro(mediator, path)
                if kind == "missing-global":
                    mediator.metros.clear()
                else:
                    mediator.metros.append(metro)

                self.assertFalse(mediator.queue_locomotive_unassignment(path))
                self.assertFalse(getattr(metro, "is_unassignment_queued", False))

    def test_path_replacement_success_and_rejection_preserve_pending_exact_identity(
        self,
    ) -> None:
        mediator = Mediator(seed=6313)
        path, first, second = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        third = next(
            index
            for index in range(len(mediator.stations))
            if index not in {first, second}
        )
        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertTrue(mediator.replace_path(path, [first, second, third]))
        self.assertIs(path.metros[0], metro)
        self.assertIs(mediator.metros[0], metro)
        self.assertTrue(metro.is_unassignment_queued)

        self.assertFalse(mediator.replace_path(path, [first, third]))
        self.assertIs(path.metros[0], metro)
        self.assertIs(mediator.metros[0], metro)
        self.assertTrue(metro.is_unassignment_queued)

    def test_removing_line_with_empty_pending_metro_returns_global_inventory(
        self,
    ) -> None:
        mediator = Mediator(seed=6314)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        mediator.remove_path(path)

        self.assertNotIn(path, mediator.paths)
        self.assertNotIn(metro, mediator.metros)
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)
        self.assert_conserved(mediator)

    def test_over_cap_immediate_returns_preserve_clamp_until_deficit_clears(
        self,
    ) -> None:
        mediator = Mediator(seed=6315)
        path, _, _ = _unserved_path(mediator)
        metros = [_install_metro(mediator, path) for _ in range(3)]
        for metro in metros:
            metro.current_station = path.stations[0]
        mediator.num_metros = 1
        observed = []

        for _ in range(3):
            self.assertTrue(mediator.queue_locomotive_unassignment(path))
            observed.append(
                (
                    len(mediator.metros),
                    mediator.available_locomotives,
                )
            )
            self.assert_conserved(mediator)

        self.assertEqual(observed, [(2, 0), (1, 0), (0, 1)])

    def test_immediate_detachment_failure_restores_both_collection_objects_and_stays_pending(
        self,
    ) -> None:
        for failing_owner in ("path", "global"):
            with self.subTest(failing_owner=failing_owner):
                mediator = Mediator(seed=6316)
                path, _, _ = _unserved_path(mediator)
                metro = _install_metro(mediator, path)
                metro.current_station = path.stations[0]
                if failing_owner == "path":
                    path.metros = _RemoveThenRaise(path.metros)
                else:
                    mediator.metros = _RemoveThenRaise(mediator.metros)
                path_collection = path.metros
                global_collection = mediator.metros

                try:
                    result = mediator.queue_locomotive_unassignment(path)
                except RuntimeError:
                    result = True

                self.assertTrue(result)
                self.assertIs(path.metros, path_collection)
                self.assertIs(mediator.metros, global_collection)
                self.assertEqual(path.metros, [metro])
                self.assertEqual(mediator.metros, [metro])
                self.assertTrue(metro.is_unassignment_queued)
                self.assert_conserved(mediator)

    def test_rider_injected_after_queue_force_alights_and_settles(self) -> None:
        mediator = Mediator(seed=6317)
        _quiet_simulation(mediator)
        path, _, _ = _unserved_path(mediator)
        metro = _install_metro(mediator, path)
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        rider = Passenger(path.stations[0].shape)
        metro.add_passenger(rider)
        mediator.passengers.append(rider)
        rider.wait_ms = 777
        metro.position = metro.current_segment.segment_end

        mediator.increment_time(1)

        # GM-06d Case 1: the planless rider force-alights at the real-station
        # stop (D-024 overflow-permitted, plan cleared, wait reset) and the
        # emptied metro settles the same tick instead of freezing the rider.
        arrival = path.stations[1]
        self.assertEqual(metro.passengers, [])
        self.assertIn(rider, arrival.passengers)
        self.assertIn(rider, mediator.passengers)
        self.assertNotIn(rider, mediator.travel_plans)
        self.assertEqual(rider.wait_ms, 0)
        self.assertFalse(rider.is_at_destination)
        self.assertNotIn(metro, path.metros)
        self.assertNotIn(metro, mediator.metros)
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)
        self.assert_conserved(mediator)


if __name__ == "__main__":
    unittest.main()
