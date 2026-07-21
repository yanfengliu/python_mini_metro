from __future__ import annotations

import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import metro_capacity
from entity.metro import Metro
from entity.passenger import Passenger
from env import MiniMetroEnv
from mediator import Mediator


def _carriage_type():
    return importlib.import_module("entity.carriage").Carriage


def _management_type():
    return importlib.import_module("carriage_management").CarriageManagement


def _assert_identities(test, actual, expected) -> None:
    test.assertEqual(len(actual), len(expected))
    for item, prior in zip(actual, expected):
        test.assertIs(item, prior)


def _unlock_all_paths(mediator: Mediator) -> None:
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _assigned_path(mediator: Mediator, indices=(0, 1), metro_count: int = 1):
    _unlock_all_paths(mediator)
    mediator.num_metros = max(mediator.num_metros, metro_count)
    path = mediator.create_path_from_station_indices(list(indices))
    if path is None:
        raise AssertionError("test setup could not create a path")
    for _ in range(metro_count):
        if not mediator.assign_locomotive(path):
            raise AssertionError("test setup could not assign a locomotive")
    return path


def _different_shape_indices(mediator: Mediator) -> tuple[int, int]:
    for first, source in enumerate(mediator.stations):
        for second, destination in enumerate(mediator.stations):
            if source.shape.type != destination.shape.type:
                return first, second
    raise AssertionError("test setup requires two station shape types")


def _network(seed: int, metro_count: int = 1):
    mediator = Mediator(seed=seed)
    first, second = _different_shape_indices(mediator)
    path = _assigned_path(mediator, (first, second), metro_count)
    return mediator, path


class TestGM06cCarriageEntityAndCapacity(unittest.TestCase):
    def test_carriage_defaults_are_unique_attached_only_entities(self) -> None:
        Carriage = _carriage_type()

        first = Carriage()
        second = Carriage()

        self.assertIsInstance(first.id, str)
        self.assertTrue(first.id)
        self.assertNotEqual(first.id, second.id)
        self.assertIsNot(first, second)
        self.assertEqual(first.capacity, 6)
        self.assertIs(type(first.capacity), int)
        self.assertGreater(first.capacity, 0)
        self.assertIsNotNone(first.shape)
        self.assertFalse(hasattr(first, "passengers"))
        with self.assertRaises((AttributeError, TypeError, ValueError)):
            first.capacity = first.capacity + 1

    def test_each_metro_owns_a_distinct_empty_composition_and_derived_capacity(
        self,
    ) -> None:
        first = Metro()
        second = Metro()

        self.assertIsInstance(first.carriages, list)
        self.assertIsInstance(second.carriages, list)
        self.assertIsNot(first.carriages, second.carriages)
        self.assertEqual(first.carriages, [])
        self.assertEqual(second.carriages, [])
        self.assertEqual(first._base_capacity, metro_capacity)
        self.assertEqual(first.capacity, metro_capacity)

        carriage = _carriage_type()()
        first.carriages.append(carriage)
        self.assertEqual(first.capacity, metro_capacity + carriage.capacity)
        self.assertEqual(second.capacity, metro_capacity)

    def test_capacity_write_is_total_atomic_and_detachment_never_edits_base(
        self,
    ) -> None:
        empty = Metro()
        empty.capacity = 0
        self.assertEqual(empty.carriages, [])
        self.assertEqual((empty._base_capacity, empty.capacity), (0, 0))

        metro = Metro()
        carriage = _carriage_type()()
        metro.carriages.append(carriage)

        metro.capacity = carriage.capacity
        self.assertEqual(metro.capacity, carriage.capacity)
        self.assertEqual(metro._base_capacity, 0)

        before = (
            metro._base_capacity,
            metro.capacity,
            metro.carriages,
            tuple(metro.carriages),
        )
        for invalid in (
            True,
            False,
            -1,
            None,
            float(carriage.capacity),
            "15",
            carriage.capacity - 1,
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises((TypeError, ValueError)):
                    metro.capacity = invalid
                self.assertEqual((metro._base_capacity, metro.capacity), before[:2])
                self.assertIs(metro.carriages, before[2])
                _assert_identities(self, metro.carriages, before[3])

        metro.carriages.pop()
        self.assertEqual(metro._base_capacity, 0)
        self.assertEqual(metro.capacity, 0)

    def test_capacity_write_cannot_overfill_current_passengers(self) -> None:
        metro = Metro()
        metro.passengers.extend(object() for _ in range(metro_capacity))
        before = (metro._base_capacity, metro.capacity, tuple(metro.passengers))

        with self.assertRaises((TypeError, ValueError)):
            metro.capacity = metro_capacity - 1

        self.assertEqual(
            (metro._base_capacity, metro.capacity, tuple(metro.passengers)), before
        )
        metro.capacity = metro_capacity
        self.assertEqual(metro.capacity, metro_capacity)


class TestGM06cCarriageInventory(unittest.TestCase):
    def assert_inventory(
        self, mediator: Mediator, expected: tuple[int, int, int]
    ) -> None:
        self.assertEqual(
            (
                mediator.num_carriages,
                mediator.assigned_carriages,
                mediator.available_carriages,
            ),
            expected,
        )

    def test_fresh_and_reset_have_two_fungible_units_and_no_object_pool(self) -> None:
        env = MiniMetroEnv()
        first = env.mediator
        path = _assigned_path(first)
        self.assertTrue(first.attach_carriage(path))
        retired_metro = path.metros[0]
        retired_carriage = retired_metro.carriages[0]
        env.reset(seed=60601)
        reset = env.mediator

        self.assertIsNot(first, reset)
        self.assert_inventory(first, (2, 1, 1))
        self.assert_inventory(reset, (2, 0, 2))
        self.assertFalse(hasattr(first, "carriages"))
        self.assertFalse(hasattr(first, "_available_carriages"))
        self.assertFalse(hasattr(reset, "carriages"))
        self.assertTrue(all(metro is not retired_metro for metro in reset.metros))
        self.assertTrue(
            all(
                carriage is not retired_carriage
                for metro in reset.metros
                for carriage in metro.carriages
            )
        )

        with self.assertRaises(AttributeError):
            reset.assigned_carriages = 1
        with self.assertRaises(AttributeError):
            reset.available_carriages = 1

    def test_assignment_is_derived_from_canonical_global_metro_order(self) -> None:
        mediator = Mediator(seed=60602)
        path = _assigned_path(mediator, metro_count=2)
        Carriage = _carriage_type()
        first, second = path.metros
        first.carriages.extend((Carriage(), Carriage()))
        second.carriages.append(Carriage())
        mediator.num_carriages = 4

        self.assert_inventory(mediator, (4, 3, 1))
        self.assertEqual(first.capacity, metro_capacity + 12)
        self.assertEqual(second.capacity, metro_capacity + 6)

        detached_global = mediator.metros.pop()
        self.assertIs(detached_global, second)
        self.assertTrue(any(candidate is second for candidate in path.metros))
        self.assert_inventory(mediator, (4, 2, 2))

    def test_direct_total_writes_clamp_and_recover_without_deleting_attachments(
        self,
    ) -> None:
        mediator = Mediator(seed=60603)
        path = _assigned_path(mediator)
        metro = path.metros[0]
        identities = (_carriage_type()(), _carriage_type()())
        metro.carriages.extend(identities)

        observed = []
        for total in (0, 1, 2, 3):
            mediator.num_carriages = total
            observed.append(
                (
                    total,
                    mediator.assigned_carriages,
                    mediator.available_carriages,
                )
            )
            _assert_identities(self, metro.carriages, identities)

        self.assertEqual(observed, [(0, 2, 0), (1, 2, 0), (2, 2, 0), (3, 2, 1)])
        self.assertEqual(mediator.available_carriages, 1)

    def test_canonical_compositions_never_share_list_identity_or_carriage_identity(
        self,
    ) -> None:
        mediator = Mediator(seed=60604)
        path = _assigned_path(mediator, metro_count=2)

        self.assertTrue(mediator.attach_carriage(path))
        self.assertTrue(mediator.attach_carriage(path))

        first, second = path.metros
        self.assertIsNot(first.carriages, second.carriages)
        flattened = [
            carriage for metro in mediator.metros for carriage in metro.carriages
        ]
        self.assertEqual(len(flattened), 2)
        for index, carriage in enumerate(flattened):
            for other in flattened[index + 1 :]:
                self.assertIsNot(carriage, other)
        self.assertEqual(len({carriage.id for carriage in flattened}), 2)
        self.assert_inventory(mediator, (2, 2, 0))


class TestGM06cDeterministicTransactions(unittest.TestCase):
    def assert_inventory(
        self, mediator: Mediator, expected: tuple[int, int, int]
    ) -> None:
        self.assertEqual(
            (
                mediator.num_carriages,
                mediator.assigned_carriages,
                mediator.available_carriages,
            ),
            expected,
        )

    def test_mixed_candidates_choose_eligible_extrema_and_preserve_exact_lists(
        self,
    ) -> None:
        mediator, path = _network(60701, metro_count=3)
        first, queued, last = path.metros
        Carriage = _carriage_type()
        first.carriages.extend(Carriage() for _ in range(3))
        queued.is_unassignment_queued = True
        last.carriages.append(Carriage())
        for _ in range(19):
            passenger = Passenger(path.stations[0].shape)
            first.passengers.append(passenger)
            mediator.passengers.append(passenger)
        mediator.num_carriages = 6
        manager = _management_type()()

        expected = Carriage()
        factory = MagicMock(return_value=expected)
        getter = MagicMock(return_value=factory)
        target_list = last.carriages
        prefix = tuple(target_list)
        self.assertTrue(
            manager.attach(
                mediator,
                path,
                get_carriage_factory=getter,
                reconcile_station_service=MagicMock(),
            )
        )
        getter.assert_called_once_with()
        factory.assert_called_once_with()
        self.assertIs(last.carriages, target_list)
        self.assertEqual(len(last.carriages), len(prefix) + 1)
        for actual, prior in zip(last.carriages, prefix):
            self.assertIs(actual, prior)
        self.assertIs(last.carriages[-1], expected)
        self.assertEqual((len(first.carriages), len(queued.carriages)), (3, 0))
        self.assert_inventory(mediator, (6, 5, 1))

        self.assertTrue(
            manager.detach(mediator, path, reconcile_station_service=MagicMock())
        )
        self.assertIs(last.carriages, target_list)
        self.assertEqual(len(last.carriages), len(prefix))
        for actual, prior in zip(last.carriages, prefix):
            self.assertIs(actual, prior)
        self.assertTrue(all(carriage is not expected for carriage in last.carriages))
        self.assertEqual(len(first.carriages), 3)
        self.assert_inventory(mediator, (6, 4, 2))

    def test_empty_exhausted_and_safe_over_cap_boundaries(self) -> None:
        mediator, path = _network(60706)
        manager = _management_type()()
        reconcile = MagicMock()
        getter = MagicMock(side_effect=AssertionError("factory resolved"))

        self.assertFalse(
            manager.detach(mediator, path, reconcile_station_service=reconcile)
        )
        mediator.num_carriages = 0
        self.assertFalse(
            manager.attach(
                mediator,
                path,
                get_carriage_factory=getter,
                reconcile_station_service=reconcile,
            )
        )
        getter.assert_not_called()
        reconcile.assert_not_called()

        carriage = _carriage_type()()
        metro = path.metros[0]
        carriage_list = metro.carriages
        carriage_list.append(carriage)
        self.assert_inventory(mediator, (0, 1, 0))
        self.assertTrue(
            manager.detach(mediator, path, reconcile_station_service=reconcile)
        )
        self.assertIs(metro.carriages, carriage_list)
        self.assertEqual(len(metro.carriages), 0)
        self.assert_inventory(mediator, (0, 0, 0))

    def test_occupied_attach_is_allowed_and_detach_is_capacity_safe(self) -> None:
        mediator, path = _network(60702)
        metro = path.metros[0]
        first = Passenger(path.stations[0].shape)
        metro.passengers.append(first)
        mediator.passengers.append(first)

        self.assertTrue(mediator.attach_carriage(path))
        while len(metro.passengers) < 7:
            passenger = Passenger(path.stations[0].shape)
            metro.passengers.append(passenger)
            mediator.passengers.append(passenger)

        before = tuple(metro.carriages)
        self.assertFalse(mediator.can_detach_carriage(path))
        self.assertFalse(mediator.detach_carriage(path))
        _assert_identities(self, metro.carriages, before)

        removed = metro.passengers.pop()
        mediator.passengers.remove(removed)
        self.assertTrue(mediator.can_detach_carriage(path))
        self.assertTrue(mediator.detach_carriage(path))
        self.assertEqual(metro.capacity, 6)
        self.assertEqual(len(metro.passengers), 6)

    def test_explicit_detach_retires_identity_and_next_attach_is_fresh(self) -> None:
        mediator, path = _network(60707)
        metro = path.metros[0]
        self.assertTrue(mediator.attach_carriage(path))
        retired = metro.carriages[-1]
        retired_id = retired.id

        self.assertTrue(mediator.detach_carriage(path))
        self.assertTrue(
            all(
                candidate is not retired
                for owner in mediator.metros
                for candidate in owner.carriages
            )
        )
        self.assertTrue(mediator.attach_carriage(path))

        replacement = metro.carriages[-1]
        self.assertIsNot(replacement, retired)
        self.assertNotEqual(replacement.id, retired_id)

    def test_paused_is_immediate_terminal_and_queued_are_rejected(self) -> None:
        mediator, path = _network(60703)
        metro = path.metros[0]
        mediator.is_paused = True

        self.assertTrue(mediator.attach_carriage(path))
        self.assertTrue(mediator.detach_carriage(path))
        metro.is_unassignment_queued = True
        self.assertFalse(mediator.attach_carriage(path))
        self.assertFalse(mediator.detach_carriage(path))
        metro.is_unassignment_queued = False
        mediator.is_game_over = True
        self.assertFalse(mediator.attach_carriage(path))
        self.assertFalse(mediator.detach_carriage(path))

    def test_live_selectors_ignore_extras_but_reject_ambiguous_or_wrong_types(
        self,
    ) -> None:
        env = MiniMetroEnv()
        env.mediator = mediator = _network(60704)[0]
        path = mediator.paths[0]

        self.assertTrue(
            mediator.apply_action(
                {"type": "attach_carriage", "path_index": 0, "ignored": object()}
            )
        )
        self.assertTrue(
            mediator.apply_action(
                {"type": "detach_carriage", "path_id": path.id, "ignored": object()}
            )
        )

        invalid = (
            {"type": "attach_carriage"},
            {"type": "attach_carriage", "path_index": True},
            {"type": "attach_carriage", "path_index": -1},
            {"type": "attach_carriage", "path_index": 0, "path_id": path.id},
            {"type": "detach_carriage", "path_id": ""},
        )
        before = (mediator.time_ms, tuple(path.metros[0].carriages))
        for action in invalid:
            with self.subTest(action=action):
                _, _, _, info = env.step(action, dt_ms=1_000)
                self.assertFalse(info["action_ok"])
                self.assertEqual(
                    (mediator.time_ms, tuple(path.metros[0].carriages)), before
                )

    def test_duplicate_path_id_and_detached_target_reject_without_factory(self) -> None:
        mediator, path = _network(60705)
        _unlock_all_paths(mediator)
        second = mediator.create_path_from_station_indices([1, 2])
        if second is None:
            raise AssertionError("test setup could not create a second path")
        second.id = path.id
        manager = _management_type()()
        getter = MagicMock(side_effect=AssertionError("factory resolved"))
        reconcile = MagicMock(side_effect=AssertionError("reconciled"))

        self.assertFalse(
            manager.attach(
                mediator,
                path,
                get_carriage_factory=getter,
                reconcile_station_service=reconcile,
            )
        )
        getter.assert_not_called()
        reconcile.assert_not_called()
        self.assertFalse(
            mediator.apply_action({"type": "attach_carriage", "path_id": path.id})
        )

        second.id = f"{second.id}-unique"
        mediator.paths.remove(path)
        self.assertFalse(
            manager.attach(
                mediator,
                path,
                get_carriage_factory=getter,
                reconcile_station_service=reconcile,
            )
        )
        getter.assert_not_called()
        reconcile.assert_not_called()
        self.assertFalse(mediator.attach_carriage(path))


if __name__ == "__main__":
    unittest.main()
