from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import mediator as mediator_module
from entity.metro import Metro
from env import MiniMetroEnv
from mediator import Mediator


class _AppendFailureList(list):
    def __init__(self, values, *, mutate: bool) -> None:
        super().__init__(values)
        self.mutate = mutate

    def append(self, value) -> None:
        if self.mutate:
            super().append(value)
        raise RuntimeError("global append fault")


class _RemoveAfterMutationList(list):
    def remove(self, value) -> None:
        super().remove(value)
        raise RuntimeError("global removal fault")


def _unlock_all_paths(mediator: Mediator) -> None:
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _create_path(mediator: Mediator, indices: list[int]):
    path = mediator.create_path_from_station_indices(indices)
    if path is None:
        raise AssertionError(f"path creation failed for {indices!r}")
    return path


def _begin_path(mediator: Mediator):
    mediator.start_path_on_station(mediator.stations[0])
    mediator.add_station_to_path(mediator.stations[1])
    path = mediator.path_being_created
    if path is None:
        raise AssertionError("path draft was not installed")
    return path


def _add_metro(mediator: Mediator, path):
    metro = Metro()
    path.add_metro(metro)
    mediator.metros.append(metro)
    return metro


class TestGM06aLocomotiveInventory(unittest.TestCase):
    def assertFleet(self, mediator: Mediator, expected: tuple[int, int, int]) -> None:
        self.assertEqual(
            (mediator.num_metros, len(mediator.metros), mediator.available_locomotives),
            expected,
        )

    def assertValidOwnership(self, mediator: Mediator) -> None:
        owners = {}
        for path in mediator.paths:
            for metro in path.metros:
                self.assertNotIn(id(metro), owners)
                owners[id(metro)] = path
                self.assertEqual(metro.path_id, path.id)
        global_ids = [id(metro) for metro in mediator.metros]
        self.assertEqual(len(global_ids), len(set(global_ids)))
        self.assertEqual(set(global_ids), set(owners))
        self.assertEqual(
            mediator.available_locomotives + len(mediator.metros),
            mediator.num_metros,
        )

    def test_fresh_and_reset_are_four_unassigned_without_metro_construction(self):
        factory = MagicMock(side_effect=AssertionError("constructed unassigned Metro"))
        with patch.object(mediator_module, "Metro", factory):
            env = MiniMetroEnv()
            first = env.mediator
            env.reset(seed=17)
            reset = env.mediator

        factory.assert_not_called()
        self.assertIsNot(first, reset)
        self.assertFleet(first, (4, 0, 4))
        self.assertFleet(reset, (4, 0, 4))
        self.assertNotIn("_available_locomotives", first.__dict__)
        self.assertNotIn("_available_locomotives", reset.__dict__)

    def test_sequential_create_exhaust_remove_and_recreate_uses_fresh_identity(self):
        mediator = Mediator(seed=1)
        _unlock_all_paths(mediator)
        mediator.num_metros = 2

        first = _create_path(mediator, [0, 1])
        first_metro = first.metros[0]
        self.assertFleet(mediator, (2, 1, 1))
        second = _create_path(mediator, [1, 2])
        self.assertFleet(mediator, (2, 2, 0))
        unserved = _create_path(mediator, [0, 2])
        self.assertEqual(unserved.metros, [])
        self.assertFleet(mediator, (2, 2, 0))

        mediator.remove_path(first)
        self.assertFleet(mediator, (2, 1, 1))
        recreated = _create_path(mediator, [0, 1])
        self.assertEqual(len(recreated.metros), 1)
        self.assertIsNot(recreated.metros[0], first_metro)
        self.assertNotEqual(recreated.metros[0].id, first_metro.id)
        self.assertIn(second.metros[0], mediator.metros)
        self.assertFleet(mediator, (2, 2, 0))

    def test_direct_cap_writes_clamp_and_recover_without_ejecting_assignments(self):
        mediator = Mediator(seed=2)
        _unlock_all_paths(mediator)
        mediator.num_metros = 2
        path = _create_path(mediator, [0, 1])
        _add_metro(mediator, path)
        identities = tuple(mediator.metros)

        observed = []
        for total in (0, 1, 2, 3):
            mediator.num_metros = total
            self.assertEqual(tuple(mediator.metros), identities)
            observed.append(
                (total, len(mediator.metros), mediator.available_locomotives)
            )
        self.assertEqual(
            observed,
            [(0, 2, 0), (1, 2, 0), (2, 2, 0), (3, 2, 1)],
        )

        recovered = _create_path(mediator, [1, 2])
        self.assertEqual(len(recovered.metros), 1)
        self.assertEqual(tuple(mediator.metros[:2]), identities)
        self.assertFleet(mediator, (3, 3, 0))

    def test_valid_gameplay_ownership_and_conservation_include_unserved_paths(self):
        mediator = Mediator(seed=3)
        _unlock_all_paths(mediator)
        mediator.num_metros = 2
        _create_path(mediator, [0, 1])
        _create_path(mediator, [1, 2])
        unserved = _create_path(mediator, [0, 2])

        self.assertEqual(unserved.metros, [])
        self.assertValidOwnership(mediator)

    def test_exhausted_finish_never_resolves_late_metro_factory(self):
        mediator = Mediator(seed=4)
        _unlock_all_paths(mediator)
        mediator.num_metros = 0
        factory = MagicMock(side_effect=AssertionError("factory resolved at cap"))

        with patch.object(mediator_module, "Metro", factory):
            path = _create_path(mediator, [0, 1])

        factory.assert_not_called()
        self.assertEqual(path.metros, [])
        self.assertFleet(mediator, (0, 0, 0))

    def test_factory_failure_leaves_inventory_available(self):
        mediator = Mediator(seed=5)
        mediator.num_metros = 1
        path = _begin_path(mediator)

        with patch.object(mediator_module, "Metro", side_effect=LookupError("factory")):
            with self.assertRaisesRegex(LookupError, "factory"):
                mediator.finish_path_creation()

        self.assertIs(mediator.path_being_created, path)
        self.assertEqual(path.metros, [])
        self.assertFleet(mediator, (1, 0, 1))

    def test_route_add_failure_leaves_inventory_available(self):
        mediator = Mediator(seed=6)
        mediator.num_metros = 1
        path = _begin_path(mediator)
        path.add_metro = MagicMock(side_effect=RuntimeError("route add"))

        with self.assertRaisesRegex(RuntimeError, "route add"):
            mediator.finish_path_creation()

        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])
        self.assertFleet(mediator, (1, 0, 1))

    def test_global_append_failure_before_mutation_leaves_inventory_available(self):
        mediator = Mediator(seed=7)
        mediator.num_metros = 1
        path = _begin_path(mediator)
        mediator.metros = _AppendFailureList([], mutate=False)

        with self.assertRaisesRegex(RuntimeError, "global append fault"):
            mediator.finish_path_creation()

        self.assertEqual(len(path.metros), 1)
        self.assertEqual(mediator.metros, [])
        self.assertFleet(mediator, (1, 0, 1))

    def test_global_append_then_raise_consumes_available_inventory(self):
        mediator = Mediator(seed=8)
        mediator.num_metros = 1
        path = _begin_path(mediator)
        mediator.metros = _AppendFailureList([], mutate=True)

        with self.assertRaisesRegex(RuntimeError, "global append fault"):
            mediator.finish_path_creation()

        self.assertIs(path.metros[0], mediator.metros[0])
        self.assertFleet(mediator, (1, 1, 0))

    def test_button_assignment_failure_keeps_installed_identity_consumed(self):
        mediator = Mediator(seed=9)
        mediator.num_metros = 1
        path = _begin_path(mediator)
        mediator.assign_paths_to_buttons = MagicMock(
            side_effect=RuntimeError("button assignment")
        )

        with self.assertRaisesRegex(RuntimeError, "button assignment"):
            mediator.finish_path_creation()

        self.assertIsNone(mediator.path_being_created)
        self.assertIs(path.metros[0], mediator.metros[0])
        self.assertFleet(mediator, (1, 1, 0))

    def test_removal_failure_before_global_effect_preserves_assignment(self):
        mediator = Mediator(seed=10)
        mediator.num_metros = 1
        path = _create_path(mediator, [0, 1])
        mediator.path_to_button[path].remove_path = MagicMock(
            side_effect=RuntimeError("button clear")
        )

        with self.assertRaisesRegex(RuntimeError, "button clear"):
            mediator.remove_path(path)

        self.assertIn(path, mediator.paths)
        self.assertFleet(mediator, (1, 1, 0))

    def test_partial_removal_in_valid_state_refunds_actual_global_effect(self):
        mediator = Mediator(seed=11)
        mediator.num_metros = 2
        path = _create_path(mediator, [0, 1])
        _add_metro(mediator, path)
        mediator.metros = _RemoveAfterMutationList(mediator.metros)

        with self.assertRaisesRegex(RuntimeError, "global removal fault"):
            mediator.remove_path(path)

        self.assertIn(path, mediator.paths)
        self.assertEqual(len(path.metros), 2)
        self.assertFleet(mediator, (2, 1, 1))

    def test_partial_over_cap_removals_clear_deficit_without_false_refund(self):
        mediator = Mediator(seed=12)
        mediator.num_metros = 2
        path = _create_path(mediator, [0, 1])
        _add_metro(mediator, path)
        mediator.num_metros = 0
        mediator.metros = _RemoveAfterMutationList(mediator.metros)
        self.assertFleet(mediator, (0, 2, 0))

        with self.assertRaisesRegex(RuntimeError, "global removal fault"):
            mediator.remove_path(path)
        self.assertFleet(mediator, (0, 1, 0))

        with self.assertRaisesRegex(RuntimeError, "global removal fault"):
            mediator.remove_path(path)
        self.assertFleet(mediator, (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
