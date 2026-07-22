from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from env import MiniMetroEnv
from fleet_validation import service_cache_is_canonical
from graph.graph_algo import build_station_nodes_dict
from passenger_capacity import pure_service_action, same_service_action
from test.gm06c_simulation_ui_support import (
    boardable_passenger,
    make_two_station_game,
)
from test.test_gm05a_metro_continuity import _build_network
from test.test_gm06c_carriage_lifecycle import (
    _assert_composition,
    _assert_identities,
    _composition_snapshot,
    _contains_identity,
    _counts,
    _network,
)
from test.test_gm06c_carriage_transactions import (
    _assert_snapshot,
    _carriage_type,
    _management,
    _snapshot,
)
from travel_plan import TravelPlan


def _prime_station_service(test: unittest.TestCase, seed: int):
    mediator, path = _network(seed)
    metro = path.metros[0]
    test.assertTrue(mediator.attach_carriage(path))
    composition = tuple(metro.carriages)
    start, destination = path.stations
    metro.current_station = start
    metro.position = start.position
    boardable_passenger(
        mediator,
        start,
        destination,
        path,
        name=f"lifecycle-cache-{seed}",
    )

    mediator.move_passengers(250)

    test.assertIsNotNone(metro._station_service_action)
    test.assertGreater(metro.stop_time_remaining_ms, 0)
    test.assertGreater(metro.boarding_progress_ms, 0)
    return mediator, path, metro, composition


def _multi_metro_replacement_network(
    test: unittest.TestCase, *, with_waiting_passenger: bool
):
    mediator, stations, target, target_metros = _build_network(metro_count=2)
    other_color = next(
        color for color, in_use in mediator.path_colors.items() if not in_use
    )
    other = Path(other_color)
    other.add_station(stations[3])
    other.add_station(stations[0])
    other_metro = Metro()
    other.add_metro(other_metro)
    mediator.paths.append(other)
    mediator.metros.append(other_metro)
    mediator.path_colors[other_color] = True
    mediator.path_to_color[other] = other_color
    other_button = mediator.path_buttons[1]
    other_button.assign_path(other)
    mediator.path_to_button[other] = other_button

    Carriage = _carriage_type()
    target_metros[0].carriages.append(Carriage())
    target_metros[1].carriages.extend((Carriage(), Carriage()))
    other_metro.carriages.append(Carriage())
    mediator.num_carriages = 8
    owners = (*target_metros, other_metro)

    passenger = None
    if with_waiting_passenger:
        passenger = Passenger(stations[3].shape)
        stations[0].add_passenger(passenger)
        mediator.passengers.append(passenger)
        mediator.travel_plans[passenger] = TravelPlan([])
        test.assertIn(passenger, stations[0].passengers)

    return mediator, target, owners, passenger


def _replacement_service_network(test: unittest.TestCase, seed: int):
    mediator, start, end, path, metro = make_two_station_game(seed=seed)
    rider = boardable_passenger(
        mediator,
        start,
        end,
        path,
        name=f"replacement-service-{seed}",
    )
    mediator.move_passengers(250)
    test.assertIs(metro.current_station, start)
    test.assertIsNotNone(metro._station_service_action)
    return mediator, path, metro, rider


class TestGM06cTopologyCompositionAliasing(unittest.TestCase):
    def test_topology_to_carriage_alias_rejects_noop_and_nonnoop_replacement(self):
        for replacement in ([0, 1], [0, 2, 1]):
            with self.subTest(replacement=replacement):
                mediator, _, path, metros = _build_network(route=(0, 1))
                shared = path.padding_segments
                self.assertEqual(shared, [])
                metros[0].carriages = shared

                self.assertFalse(mediator.replace_path(path, replacement, False))

                self.assertIs(path.padding_segments, shared)
                self.assertIs(metros[0].carriages, shared)
                self.assertEqual(shared, [])


class TestGM06cRetirementClearsLatentStationService(unittest.TestCase):
    def test_immediate_fleet_return_clears_nonempty_cache_and_timing(self):
        mediator, path, metro, composition = _prime_station_service(self, 61900)

        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertFalse(_contains_identity(path.metros, metro))
        self.assertFalse(_contains_identity(mediator.metros, metro))
        _assert_identities(self, metro.carriages, composition)
        self.assertEqual(_counts(mediator), (2, 0, 2))
        self.assertIsNone(metro._station_service_action)
        self.assertEqual(metro.stop_time_remaining_ms, 0)
        self.assertEqual(metro.boarding_progress_ms, 0)

    def test_successful_line_removal_clears_nonempty_cache_and_timing(self):
        mediator, path, metro, composition = _prime_station_service(self, 61901)

        mediator.remove_path(path)

        self.assertTrue(all(candidate is not metro for candidate in mediator.metros))
        self.assertTrue(any(candidate is metro for candidate in path.metros))
        _assert_identities(self, metro.carriages, composition)
        self.assertIsNone(metro._station_service_action)
        self.assertEqual(metro.stop_time_remaining_ms, 0)
        self.assertEqual(metro.boarding_progress_ms, 0)

    def test_reset_clears_nonempty_cache_and_timing_on_retired_graph(self):
        mediator, _, metro, composition = _prime_station_service(self, 61902)
        env = MiniMetroEnv()
        env.mediator = mediator
        env.last_deliveries = mediator.deliveries
        env.last_line_credits = mediator.line_credits

        env.reset(seed=61903)

        self.assertIsNot(env.mediator, mediator)
        self.assertTrue(
            all(candidate is not metro for candidate in env.mediator.metros)
        )
        _assert_identities(self, metro.carriages, composition)
        self.assertIsNone(metro._station_service_action)
        self.assertEqual(metro.stop_time_remaining_ms, 0)
        self.assertEqual(metro.boarding_progress_ms, 0)


class TestGM06cNonemptyServiceRollback(unittest.TestCase):
    def test_reconciliation_failure_restores_live_cache_and_fraction(self):
        for operation in ("attach", "detach"):
            for error in (
                RuntimeError("reconciliation fault"),
                KeyboardInterrupt("reconciliation base fault"),
            ):
                with self.subTest(operation=operation, error=type(error).__name__):
                    self._assert_reconciliation_rollback(operation, error)

    def _assert_reconciliation_rollback(self, operation, error) -> None:
        mediator, path, metro, _ = _prime_station_service(
            self, 61910 + len(operation) + len(type(error).__name__)
        )
        before = _snapshot(mediator)
        before_action = metro._station_service_action
        before_timing = (
            metro.stop_time_remaining_ms,
            metro.boarding_progress_ms,
        )

        def fail_reconciliation(selected):
            self.assertIs(selected, metro)
            selected._station_service_action = None
            selected.stop_time_remaining_ms = 0
            selected.boarding_progress_ms = 0
            raise error

        reconcile = MagicMock(side_effect=fail_reconciliation)
        candidate = _carriage_type()()

        def invoke():
            if operation == "attach":
                return _management().attach(
                    mediator,
                    path,
                    get_carriage_factory=lambda: lambda: candidate,
                    reconcile_station_service=reconcile,
                )
            return _management().detach(
                mediator,
                path,
                reconcile_station_service=reconcile,
            )

        if isinstance(error, Exception):
            self.assertFalse(invoke())
        else:
            try:
                invoke()
            except BaseException as raised:
                self.assertIs(raised, error)
            else:
                self.fail(f"{type(error).__name__} was not raised")

        reconcile.assert_called_once_with(metro)
        _assert_snapshot(self, mediator, before)
        self.assertIs(metro._station_service_action, before_action)
        self.assertEqual(
            (
                metro.stop_time_remaining_ms,
                metro.boarding_progress_ms,
            ),
            before_timing,
        )


class TestGM06cMalformedLineRemoval(unittest.TestCase):
    def test_preexisting_composition_corruption_fails_before_line_mutation(self):
        mediator, path = _network(61920)
        metro = path.metros[0]
        self.assertTrue(mediator.attach_carriage(path))
        metro.carriages.append(metro.carriages[0])
        before = _snapshot(mediator)
        button = mediator.path_to_button[path]
        color = mediator.path_to_color[path]
        color_state = mediator.path_colors[color]

        try:
            result = mediator.remove_path(path)
        except ValueError:
            pass
        else:
            self.assertIsNone(result)

        _assert_snapshot(self, mediator, before)
        self.assertIs(mediator.path_to_button[path], button)
        self.assertIs(button.path, path)
        self.assertEqual(mediator.path_to_color[path], color)
        self.assertIs(mediator.path_colors[color], color_state)


class TestGM06cGlobalReplacementConservation(unittest.TestCase):
    def test_success_preserves_same_path_and_other_path_compositions(self):
        mediator, target, owners, _ = _multi_metro_replacement_network(
            self, with_waiting_passenger=False
        )
        before = tuple(_composition_snapshot(metro) for metro in owners)

        self.assertTrue(mediator.replace_path(target, [0, 1, 3, 2], False))

        for metro, state in zip(owners, before, strict=True):
            _assert_composition(self, metro, state)

    def test_callback_inventory_and_carriage_intrinsic_drift_always_restores(self):
        for raises in (False, True):
            with self.subTest(raises=raises):
                mediator, target, owners, passenger = _multi_metro_replacement_network(
                    self, with_waiting_passenger=True
                )
                self.assertIsNotNone(passenger)
                before = _snapshot(mediator)
                carriages = tuple(
                    carriage for metro in owners for carriage in metro.carriages
                )

                def mutate(*_args) -> None:
                    mediator.num_carriages += 9
                    for index, carriage in enumerate(carriages, 1):
                        carriage.id += f"-drift-{index}"
                        carriage._capacity += index
                        carriage.shape = object()
                    if raises:
                        raise RuntimeError("intrinsic replacement drift")

                mediator._replan_passenger_at_station = mutate
                if raises:
                    with self.assertRaisesRegex(
                        RuntimeError, "intrinsic replacement drift"
                    ):
                        mediator.replace_path(target, [0, 1, 3, 2], False)
                else:
                    try:
                        mediator.replace_path(target, [0, 1, 3, 2], False)
                    except ValueError:
                        pass

                _assert_snapshot(self, mediator, before)

    def test_callback_drift_restores_same_path_and_other_path_compositions(self):
        mediator, target, owners, passenger = _multi_metro_replacement_network(
            self, with_waiting_passenger=True
        )
        self.assertIsNotNone(passenger)
        before = tuple(_composition_snapshot(metro) for metro in owners)
        calls = MagicMock()

        def mutate(*_args) -> None:
            calls()
            for metro in owners[1:]:
                metro.carriages = [*metro.carriages, _carriage_type()()]
                metro.passengers = list(metro.passengers)
                metro._base_capacity += 4
                metro.is_unassignment_queued = True
                metro.stop_time_remaining_ms = 777
                metro.boarding_progress_ms = 123
                metro._station_service_action = ("board", passenger)

        mediator._replan_passenger_at_station = mutate
        try:
            result = mediator.replace_path(target, [0, 1, 3, 2], False)
        except (RuntimeError, ValueError):
            result = False

        self.assertFalse(result)
        calls.assert_called_once_with()
        for metro, state in zip(owners, before, strict=True):
            _assert_composition(self, metro, state)


class TestGM06cReplacementServiceReconciliation(unittest.TestCase):
    def test_success_reconciles_after_waiting_replans_and_publishes_exact_cache(self):
        mediator, path, metro, rider = _replacement_service_network(self, 61930)
        events = []
        original_replan = mediator._replan_passenger_at_station
        original_reconcile = mediator._reconcile_station_service

        def replan(passenger, station, graph):
            events.append(("replan", passenger))
            return original_replan(passenger, station, graph)

        def reconcile(candidate):
            events.append(("reconcile", candidate))
            return original_reconcile(candidate)

        mediator._replan_passenger_at_station = replan
        mediator._reconcile_station_service = reconcile

        self.assertTrue(mediator.replace_path(path, [1, 0], False))

        self.assertEqual(events, [("replan", rider), ("reconcile", metro)])
        graph = build_station_nodes_dict(mediator.stations, mediator.paths)
        expected = pure_service_action(mediator, metro, metro.current_station, graph)
        self.assertTrue(same_service_action(metro._station_service_action, expected))
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms),
            (250, 250),
        )

    def test_reconciliation_exception_rolls_back_topology_plans_and_cache(self):
        for error in (
            RuntimeError("replacement reconciliation fault"),
            KeyboardInterrupt("replacement reconciliation base fault"),
        ):
            with self.subTest(error=type(error).__name__):
                mediator, path, metro, _ = _replacement_service_network(
                    self, 61931 + len(type(error).__name__)
                )
                before = _snapshot(mediator)

                def fail_reconciliation(candidate):
                    self.assertIs(candidate, metro)
                    candidate._station_service_action = None
                    candidate.stop_time_remaining_ms = 0
                    candidate.boarding_progress_ms = 0
                    raise error

                mediator._reconcile_station_service = fail_reconciliation
                with self.assertRaises(type(error)) as raised:
                    mediator.replace_path(path, [1, 0], False)
                self.assertIs(raised.exception, error)
                _assert_snapshot(self, mediator, before)


class TestGM06cMalformedServiceCachePreflight(unittest.TestCase):
    def _cache_network(self, seed: int):
        mediator, start, end, path, metro = make_two_station_game(seed=seed)
        self.assertTrue(mediator.attach_carriage(path))
        first = boardable_passenger(
            mediator, start, end, path, name=f"cache-first-{seed}"
        )
        mediator._reconcile_station_service(metro)
        self.assertTrue(mediator.can_attach_carriage(path))
        self.assertTrue(mediator.can_detach_carriage(path))
        return mediator, start, end, path, metro, first

    def test_bound_cache_malformed_states_reject_queries_and_actions_exactly(self):
        # Structurally malformed caches -- a bound action off-station, an
        # unknown kind, or a broken boarding timer -- still fail the carriage
        # preflight exactly and leave the graph untouched. (A merely stale but
        # well-formed cache is legitimate GM-07b state, not malformed: see
        # test_stale_but_structural_cache_permits_attach_and_reconciles.)
        for case in ("moving", "nonexact-kind", "wrong-timer"):
            with self.subTest(case=case):
                mediator, start, end, path, metro, first = self._cache_network(
                    61940 + len(case)
                )
                if case == "moving":
                    metro.current_station = None
                elif case == "nonexact-kind":
                    metro._station_service_action = ("boarding", first)
                else:
                    metro.stop_time_remaining_ms -= 1
                before = _snapshot(mediator)

                self.assertFalse(mediator.can_attach_carriage(path))
                self.assertFalse(mediator.can_detach_carriage(path))
                self.assertFalse(mediator.attach_carriage(path))
                self.assertFalse(mediator.detach_carriage(path))
                _assert_snapshot(self, mediator, before)

    def test_stale_but_structural_cache_permits_attach_and_reconciles(self):
        # A well-formed bound cache that merely disagrees with the re-derivable
        # oracle is legitimate GM-07b state, not corruption: a live rider held
        # elsewhere ('wrong-holder', the reachable same-tick sibling-board
        # shape) or a non-preferred boarding candidate ('wrong-oracle'). The
        # carriage preflight tolerates it exactly as the checkpoint verifier
        # does, and the transaction reconciles the touched metro back to the
        # strict oracle -- so the op succeeds instead of silently no-opping.
        nodes = build_station_nodes_dict
        for case in ("wrong-holder", "wrong-oracle"):
            with self.subTest(case=case):
                mediator, start, end, path, metro, first = self._cache_network(
                    61940 + len(case)
                )
                if case == "wrong-holder":
                    passenger = boardable_passenger(
                        mediator, end, start, path, name="wrong-holder"
                    )
                else:
                    passenger = boardable_passenger(
                        mediator, start, end, path, name="wrong-oracle"
                    )
                metro._station_service_action = ("board", passenger)
                self.assertFalse(
                    same_service_action(
                        metro._station_service_action,
                        pure_service_action(
                            mediator,
                            metro,
                            metro.current_station,
                            nodes(mediator.stations, mediator.paths),
                        ),
                    )
                )

                self.assertTrue(mediator.can_attach_carriage(path))
                self.assertTrue(mediator.can_detach_carriage(path))
                self.assertTrue(mediator.attach_carriage(path))
                # The touched metro was reconciled to the strict oracle.
                self.assertTrue(
                    service_cache_is_canonical(mediator, metro, allow_unbound=False)
                )

    def test_zero_timer_real_station_fixture_can_bind_during_first_mutation(self):
        mediator, start, end, path, metro = make_two_station_game(seed=61960)
        self.assertTrue(mediator.attach_carriage(path))
        rider = boardable_passenger(
            mediator, start, end, path, name="pre-reconciliation-fixture"
        )
        self.assertIsNone(metro._station_service_action)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (0, 0)
        )

        self.assertTrue(mediator.can_attach_carriage(path))
        self.assertTrue(mediator.can_detach_carriage(path))
        self.assertTrue(mediator.attach_carriage(path))

        self.assertEqual(metro._station_service_action, ("board", rider))
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (500, 0)
        )


if __name__ == "__main__":
    unittest.main()
