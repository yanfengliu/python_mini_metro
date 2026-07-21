from __future__ import annotations

import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.passenger import Passenger
from env import MiniMetroEnv
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint
from test.test_gm05a_metro_continuity import _build_network
from travel_plan import TravelPlan


def _carriage_type():
    return importlib.import_module("entity.carriage").Carriage


def _unlock_all_paths(mediator: Mediator) -> None:
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _different_shape_indices(mediator: Mediator) -> tuple[int, int]:
    for first, source in enumerate(mediator.stations):
        for second, destination in enumerate(mediator.stations):
            if source.shape.type != destination.shape.type:
                return first, second
    raise AssertionError("test setup requires two station shape types")


def _network(seed: int):
    mediator = Mediator(seed=seed)
    _unlock_all_paths(mediator)
    first, second = _different_shape_indices(mediator)
    path = mediator.create_path_from_station_indices([first, second])
    if path is None or not mediator.assign_locomotive(path):
        raise AssertionError("test setup could not create an assigned path")
    return mediator, path


def _quiet(mediator: Mediator) -> None:
    future = 10**9
    mediator.passenger_spawning_step = future
    mediator.passenger_spawning_interval_step = future
    mediator.overdue_passenger_threshold = future
    for station in mediator.stations:
        mediator.station_steps_since_last_spawn[station] = 0
        mediator.station_spawn_interval_steps[station] = future


def _as_env(mediator: Mediator) -> MiniMetroEnv:
    env = MiniMetroEnv()
    env.mediator = mediator
    env.last_deliveries = mediator.deliveries
    env.last_line_credits = mediator.line_credits
    return env


def _counts(mediator: Mediator) -> tuple[int, int, int]:
    return (
        mediator.num_carriages,
        mediator.assigned_carriages,
        mediator.available_carriages,
    )


def _assert_identities(test, actual, expected) -> None:
    test.assertEqual(len(actual), len(expected))
    for item, prior in zip(actual, expected):
        test.assertIs(item, prior)


def _contains_identity(collection, item) -> bool:
    return any(candidate is item for candidate in collection)


class TestGM06cWholeConsistLifecycle(unittest.TestCase):
    def test_immediate_return_refunds_consist_only_after_exact_owner_removal(
        self,
    ) -> None:
        mediator, path = _network(60801)
        metro = path.metros[0]
        self.assertTrue(mediator.attach_carriage(path))
        self.assertTrue(mediator.attach_carriage(path))
        retained = tuple(metro.carriages)
        metro.current_station = path.stations[0]
        self.assertEqual(_counts(mediator), (2, 2, 0))

        self.assertTrue(mediator.queue_locomotive_unassignment(path))

        self.assertFalse(_contains_identity(path.metros, metro))
        self.assertFalse(_contains_identity(mediator.metros, metro))
        _assert_identities(self, metro.carriages, retained)
        self.assertEqual(_counts(mediator), (2, 0, 2))
        self.assertIsNone(metro._station_service_action)

    def test_moving_queue_keeps_consist_assigned_until_real_station_settlement(
        self,
    ) -> None:
        mediator, path = _network(60802)
        _quiet(mediator)
        metro = path.metros[0]
        self.assertTrue(mediator.attach_carriage(path))
        carriage = metro.carriages[0]
        self.assertEqual(_counts(mediator), (2, 1, 1))

        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        self.assertTrue(_contains_identity(mediator.metros, metro))
        self.assertTrue(any(item is carriage for item in metro.carriages))
        self.assertEqual(_counts(mediator), (2, 1, 1))

        metro.position = metro.current_segment.segment_end
        mediator.increment_time(1)

        self.assertFalse(_contains_identity(path.metros, metro))
        self.assertFalse(_contains_identity(mediator.metros, metro))
        self.assertIs(metro.carriages[0], carriage)
        self.assertEqual(_counts(mediator), (2, 0, 2))
        self.assertIsNone(metro._station_service_action)
        self.assertEqual(metro.stop_time_remaining_ms, 0)
        self.assertEqual(metro.boarding_progress_ms, 0)

    def test_corruption_after_queue_fails_closed_and_leaves_pending_owner(self) -> None:
        mediator, path = _network(60803)
        _quiet(mediator)
        metro = path.metros[0]
        self.assertTrue(mediator.attach_carriage(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        metro.carriages.append(metro.carriages[0])
        malformed = tuple(metro.carriages)
        metro.position = metro.current_segment.segment_end

        mediator.increment_time(1)

        self.assertTrue(_contains_identity(path.metros, metro))
        self.assertTrue(_contains_identity(mediator.metros, metro))
        self.assertTrue(metro.is_unassignment_queued)
        _assert_identities(self, metro.carriages, malformed)
        self.assertFalse(mediator.can_attach_carriage(path))
        self.assertFalse(mediator.can_detach_carriage(path))

    def test_malformed_composition_rejects_queue_before_intent(self) -> None:
        mediator, path = _network(60804)
        metro = path.metros[0]
        carriage = _carriage_type()()
        metro.carriages[:] = [carriage, carriage]

        self.assertFalse(mediator.can_queue_locomotive_unassignment(path))
        self.assertFalse(mediator.queue_locomotive_unassignment(path))
        self.assertFalse(metro.is_unassignment_queued)

    def test_successful_line_removal_refunds_and_retires_retained_composition(
        self,
    ) -> None:
        mediator, path = _network(60805)
        metro = path.metros[0]
        self.assertTrue(mediator.attach_carriage(path))
        self.assertTrue(mediator.attach_carriage(path))
        retired = tuple(metro.carriages)
        self.assertEqual(_counts(mediator), (2, 2, 0))

        mediator.remove_path(path)

        self.assertFalse(_contains_identity(mediator.paths, path))
        self.assertFalse(_contains_identity(mediator.metros, metro))
        self.assertTrue(_contains_identity(path.metros, metro))
        _assert_identities(self, metro.carriages, retired)
        self.assertEqual(_counts(mediator), (2, 0, 2))
        self.assertIsNone(metro._station_service_action)

        _unlock_all_paths(mediator)
        recreated = mediator.create_path_from_station_indices([0, 1])
        if recreated is None or not mediator.assign_locomotive(recreated):
            raise AssertionError("test setup could not recreate a served line")
        self.assertTrue(mediator.attach_carriage(recreated))
        replacement = recreated.metros[0].carriages[0]
        for old in retired:
            self.assertIsNot(replacement, old)
            self.assertNotEqual(replacement.id, old.id)

    def test_late_line_removal_failure_is_explicitly_malformed_until_gm06d(
        self,
    ) -> None:
        mediator, path = _network(60806)
        metro = path.metros[0]
        self.assertTrue(mediator.attach_carriage(path))
        retained = tuple(metro.carriages)
        mediator.invalidate_travel_plans_for_path = MagicMock(
            side_effect=RuntimeError("late removal fault")
        )

        with self.assertRaisesRegex(RuntimeError, "late removal fault"):
            mediator.remove_path(path)

        self.assertTrue(_contains_identity(mediator.paths, path))
        self.assertTrue(_contains_identity(path.metros, metro))
        self.assertFalse(_contains_identity(mediator.metros, metro))
        _assert_identities(self, metro.carriages, retained)
        self.assertEqual(mediator.assigned_carriages, 0)
        self.assertEqual(mediator.available_carriages, mediator.num_carriages)
        self.assertFalse(mediator.can_attach_carriage(path))
        self.assertFalse(mediator.can_detach_carriage(path))
        with self.assertRaises(ValueError):
            canonical_checkpoint(_as_env(mediator))

    def test_attached_consist_owner_remove_failures_rollback_immediate_and_delayed(
        self,
    ) -> None:
        for timing in ("immediate", "delayed"):
            for owner in ("path", "global"):
                for error in (RuntimeError("owner removal"), KeyboardInterrupt()):
                    with self.subTest(
                        timing=timing, owner=owner, error=type(error).__name__
                    ):
                        mediator, path = _network(60820 + len(timing) + len(owner))
                        _quiet(mediator)
                        metro = path.metros[0]
                        self.assertTrue(mediator.attach_carriage(path))
                        calls = MagicMock()
                        if timing == "immediate":
                            metro.current_station = path.stations[0]
                            metro.position = metro.current_station.position
                        else:
                            self.assertTrue(
                                mediator.queue_locomotive_unassignment(path)
                            )
                        before = _composition_snapshot(metro)
                        before["queue"] = True

                        def corrupt_composition() -> None:
                            calls()
                            metro.carriages = [*metro.carriages, _carriage_type()()]
                            metro._base_capacity += 4
                            metro.stop_time_remaining_ms = 777
                            metro.boarding_progress_ms = 123
                            metro._station_service_action = ("board", object())

                        if owner == "path":
                            path.metros = _RemoveThenRaise(
                                path.metros, corrupt_composition, error
                            )
                            owner_list = path.metros
                        else:
                            mediator.metros = _RemoveThenRaise(
                                mediator.metros, corrupt_composition, error
                            )
                            owner_list = mediator.metros

                        def invoke() -> None:
                            if timing == "immediate":
                                mediator.queue_locomotive_unassignment(path)
                            else:
                                metro.position = metro.current_segment.segment_end
                                mediator.increment_time(1)

                        if isinstance(error, Exception):
                            invoke()
                        else:
                            try:
                                invoke()
                            except BaseException as raised:
                                self.assertIs(raised, error)
                            else:
                                self.fail("injected BaseException was not raised")
                        calls.assert_called_once_with()
                        self.assertIs(
                            path.metros if owner == "path" else mediator.metros,
                            owner_list,
                        )
                        self.assertTrue(_contains_identity(path.metros, metro))
                        self.assertTrue(_contains_identity(mediator.metros, metro))
                        self.assertTrue(metro.is_unassignment_queued)
                        _assert_composition(self, metro, before)
                        self.assertEqual(_counts(mediator), (2, 1, 1))


def _composition_snapshot(metro) -> dict[str, object]:
    return {
        "list": metro.carriages,
        "items": tuple(metro.carriages),
        "base": metro._base_capacity,
        "capacity": metro.capacity,
        "passenger_list": metro.passengers,
        "passengers": tuple(metro.passengers),
        "queue": metro.is_unassignment_queued,
        "service": metro._station_service_action,
        "stop": metro.stop_time_remaining_ms,
        "progress": metro.boarding_progress_ms,
    }


def _assert_composition(test: unittest.TestCase, metro, before) -> None:
    test.assertIs(metro.carriages, before["list"])
    _assert_identities(test, metro.carriages, before["items"])
    test.assertEqual(metro._base_capacity, before["base"])
    test.assertEqual(metro.capacity, before["capacity"])
    test.assertIs(metro.passengers, before["passenger_list"])
    _assert_identities(test, metro.passengers, before["passengers"])
    test.assertIs(metro.is_unassignment_queued, before["queue"])
    test.assertIs(metro._station_service_action, before["service"])
    test.assertEqual(metro.stop_time_remaining_ms, before["stop"])
    test.assertEqual(metro.boarding_progress_ms, before["progress"])


class _FailingSlice(list):
    def __init__(self, values) -> None:
        super().__init__(values)
        self.armed = True

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if isinstance(key, slice) and self.armed:
            self.armed = False
            raise RuntimeError("late topology fault")


class _RemoveThenRaise(list):
    def __init__(self, values, callback, error) -> None:
        super().__init__(values)
        self.callback, self.error, self.armed = callback, error, True

    def _after(self) -> None:
        if self.armed:
            self.armed = False
            self.callback()
            raise self.error

    def pop(self, index=-1):
        value = super().pop(index)
        self._after()
        return value

    def remove(self, value) -> None:
        index = next(
            index for index, candidate in enumerate(self) if candidate is value
        )
        self.pop(index)

    def __delitem__(self, key) -> None:
        super().__delitem__(key)
        self._after()

    def __setitem__(self, key, value) -> None:
        super().__setitem__(key, value)
        if isinstance(key, slice) and len(self) == 0:
            self._after()


class TestGM06cRouteReplacementComposition(unittest.TestCase):
    def _composed_network(self):
        mediator, stations, path, metros = _build_network()
        mediator.num_carriages = 4
        for _ in range(3):
            self.assertTrue(mediator.attach_carriage(path))
        metro = metros[0]
        metro._station_service_action = None
        return mediator, stations, path, metro

    def test_success_rejection_and_semantic_noop_preserve_exact_composition(
        self,
    ) -> None:
        mediator, _, path, metro = self._composed_network()
        before = _composition_snapshot(metro)

        self.assertTrue(mediator.replace_path(path, [0, 1, 2], False))
        _assert_composition(self, metro, before)
        self.assertTrue(mediator.replace_path(path, [0, 1, 3, 2], False))
        _assert_composition(self, metro, before)
        self.assertFalse(mediator.replace_path(path, [0, 3, 2], False))
        _assert_composition(self, metro, before)

    def test_otherwise_valid_shared_empty_carriage_list_rejects_semantic_noop(
        self,
    ) -> None:
        mediator, _, path, metros = _build_network(metro_count=2)
        shared = []
        metros[0].carriages = shared
        metros[1].carriages = shared

        self.assertFalse(mediator.replace_path(path, [0, 1, 2], False))

        self.assertIs(metros[0].carriages, shared)
        self.assertIs(metros[1].carriages, shared)
        self.assertEqual(len(shared), 0)

    def test_callback_mutate_then_return_or_raise_restores_composition(self) -> None:
        for raises in (False, True):
            with self.subTest(raises=raises):
                mediator, stations, path, metro = self._composed_network()
                passenger = Passenger(stations[-1].shape)
                stations[0].add_passenger(passenger)
                mediator.passengers.append(passenger)
                mediator.travel_plans[passenger] = TravelPlan([])
                before = _composition_snapshot(metro)

                def mutate(*_args) -> None:
                    metro.carriages = [*metro.carriages, _carriage_type()()]
                    metro.passengers = [passenger]
                    metro._base_capacity += 4
                    metro.is_unassignment_queued = True
                    metro.stop_time_remaining_ms = 777
                    metro.boarding_progress_ms = 123
                    metro._station_service_action = ("boarding", passenger)
                    if raises:
                        raise RuntimeError("replan mutation")

                mediator._replan_passenger_at_station = mutate
                if raises:
                    with self.assertRaisesRegex(RuntimeError, "replan mutation"):
                        mediator.replace_path(path, [0, 1, 3, 2], False)
                else:
                    try:
                        result = mediator.replace_path(path, [0, 1, 3, 2], False)
                    except (RuntimeError, ValueError):
                        pass
                    else:
                        self.assertFalse(result)

                _assert_composition(self, metro, before)

    def test_late_topology_rollback_restores_carriage_list_and_capacity(self) -> None:
        mediator, _, path, metro = self._composed_network()
        path.stations = _FailingSlice(path.stations)
        failing = path.stations
        before = _composition_snapshot(metro)

        with self.assertRaisesRegex(RuntimeError, "late topology fault"):
            mediator.replace_path(path, [0, 1, 3, 2], False)

        self.assertIs(path.stations, failing)
        _assert_composition(self, metro, before)


if __name__ == "__main__":
    unittest.main()
