from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import mediator as mediator_module
from entity.metro import Metro
from geometry.point import Point
from mediator import Mediator


class _AppendThenRaise(list):
    def append(self, value) -> None:
        super().append(value)
        raise RuntimeError("append fault")


class _SubstitutingAppend(list):
    def append(self, value) -> None:
        super().append(Metro())


class _RebindingGlobalAppend(list):
    def __init__(self, mediator: Mediator, values=()) -> None:
        super().__init__(values)
        self.mediator = mediator

    def append(self, value) -> None:
        self.mediator.metros = [value]
        raise RuntimeError("global rebound fault")


def _unlock_all_paths(mediator: Mediator) -> None:
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _create_path(mediator: Mediator, indices=(0, 1)):
    _unlock_all_paths(mediator)
    path = mediator.create_path_from_station_indices(list(indices))
    if path is None:
        raise AssertionError("test setup could not create a path")
    return path


def _strip_transitional_assignment(mediator: Mediator, path) -> None:
    for metro in tuple(path.metros):
        while metro in mediator.metros:
            mediator.metros.remove(metro)
    path.metros.clear()


def _unserved_path(mediator: Mediator, indices=(0, 1)):
    path = _create_path(mediator, indices)
    _strip_transitional_assignment(mediator, path)
    return path


class TestGM06bFleetAssignment(unittest.TestCase):
    def assert_conserved(self, mediator: Mediator) -> None:
        assigned = len(mediator.metros)
        total = mediator.num_metros
        self.assertEqual(
            mediator.available_locomotives,
            max(0, total - assigned),
        )
        if assigned <= total:
            self.assertEqual(mediator.available_locomotives + assigned, total)

        owners: dict[int, object] = {}
        for path in mediator.paths:
            for metro in path.metros:
                self.assertNotIn(id(metro), owners)
                owners[id(metro)] = path
                self.assertEqual(metro.path_id, path.id)
        self.assertEqual(
            {id(metro) for metro in mediator.metros},
            set(owners),
        )
        self.assertEqual(
            len({id(metro) for metro in mediator.metros}),
            len(mediator.metros),
        )

    def invoke_failure(self, callback) -> None:
        try:
            result = callback()
        except AttributeError:
            raise
        except Exception:
            return
        self.assertFalse(result, "a failed transaction must not report success")

    def test_new_metro_starts_with_no_unassignment_request(self) -> None:
        metro = Metro()

        self.assertIs(metro.is_unassignment_queued, False)

    def test_completed_path_is_unserved_until_explicit_assignment(self) -> None:
        mediator = Mediator(seed=6200)
        path = _create_path(mediator)

        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])
        self.assertEqual(mediator.available_locomotives, mediator.num_metros)

    def test_assignment_installs_one_fresh_exact_identity_in_both_owner_lists(
        self,
    ) -> None:
        mediator = Mediator(seed=6201)
        path = _unserved_path(mediator)
        path_collection = path.metros
        global_collection = mediator.metros
        created = Metro()

        with patch.object(mediator_module, "Metro", return_value=created) as factory:
            self.assertTrue(mediator.assign_locomotive(path))

        factory.assert_called_once_with()
        self.assertIs(path.metros, path_collection)
        self.assertIs(mediator.metros, global_collection)
        self.assertEqual(path.metros, [created])
        self.assertEqual(mediator.metros, [created])
        self.assertIs(path.metros[0], mediator.metros[0])
        self.assertIs(created.current_segment, path.segments[0])
        self.assertIsNone(created.current_station)
        self.assertEqual(created.position, path.segments[0].segment_start)
        self.assert_conserved(mediator)

    def test_multiple_assignments_append_without_reordering_existing_identities(
        self,
    ) -> None:
        mediator = Mediator(seed=6202)
        mediator.num_metros = 3
        path = _unserved_path(mediator)
        expected = []

        for _ in range(3):
            created = Metro()
            expected.append(created)
            with patch.object(mediator_module, "Metro", return_value=created):
                self.assertTrue(mediator.assign_locomotive(path))
            self.assertEqual(path.metros, expected)
            self.assertEqual(mediator.metros, expected)
            self.assert_conserved(mediator)

        self.assertFalse(mediator.assign_locomotive(path))
        self.assertEqual(path.metros, expected)
        self.assertEqual(mediator.metros, expected)

    def test_exhausted_and_over_cap_assignment_reject_before_factory_resolution(
        self,
    ) -> None:
        for total in (1, 0, -1):
            with self.subTest(total=total):
                mediator = Mediator(seed=6203)
                path = _unserved_path(mediator)
                existing = Metro()
                path.add_metro(existing)
                mediator.metros.append(existing)
                mediator.num_metros = total
                before = (tuple(path.metros), tuple(mediator.metros))
                factory = MagicMock(side_effect=AssertionError("factory resolved"))

                with patch.object(mediator_module, "Metro", factory):
                    self.assertFalse(mediator.assign_locomotive(path))

                factory.assert_not_called()
                self.assertEqual((tuple(path.metros), tuple(mediator.metros)), before)
                self.assert_conserved(mediator)

    def test_detached_creating_and_malformed_targets_reject_without_factory(
        self,
    ) -> None:
        cases = []

        detached_mediator = Mediator(seed=6204)
        detached = _unserved_path(detached_mediator)
        detached_mediator.paths.remove(detached)
        cases.append(("detached", detached_mediator, detached))

        creating_mediator = Mediator(seed=6205)
        _unlock_all_paths(creating_mediator)
        creating_mediator.start_path_on_station(creating_mediator.stations[0])
        creating_mediator.add_station_to_path(creating_mediator.stations[1])
        creating = creating_mediator.path_being_created
        self.assertIsNotNone(creating)
        cases.append(("creating", creating_mediator, creating))

        malformed_mediator = Mediator(seed=6206)
        malformed = _unserved_path(malformed_mediator)
        owned = Metro()
        malformed.add_metro(owned)
        malformed_mediator.metros[:] = [owned, owned]
        cases.append(("duplicate-global", malformed_mediator, malformed))

        for name, mediator, target in cases:
            with self.subTest(name=name):
                path_before = tuple(target.metros)
                global_before = tuple(mediator.metros)
                factory = MagicMock(side_effect=AssertionError("factory resolved"))
                with patch.object(mediator_module, "Metro", factory):
                    self.assertFalse(mediator.assign_locomotive(target))
                factory.assert_not_called()
                self.assertEqual(tuple(target.metros), path_before)
                self.assertEqual(tuple(mediator.metros), global_before)

    def test_malformed_geometry_rejects_before_factory_resolution(self) -> None:
        malformed_segments = (
            [object()],
            [
                SimpleNamespace(
                    segment_start=Point(1, 1),
                    segment_end=Point(2, 2),
                    start_station=None,
                    end_station=None,
                )
            ],
        )

        for index, segments in enumerate(malformed_segments):
            with self.subTest(index=index):
                mediator = Mediator(seed=6218 + index)
                path = _unserved_path(mediator)
                path.segments = segments
                path_before = tuple(path.metros)
                global_before = tuple(mediator.metros)
                factory = MagicMock(side_effect=AssertionError("factory resolved"))

                with patch.object(mediator_module, "Metro", factory):
                    self.assertFalse(mediator.assign_locomotive(path))

                factory.assert_not_called()
                self.assertEqual(tuple(path.metros), path_before)
                self.assertEqual(tuple(mediator.metros), global_before)

    def test_factory_exception_leaves_original_collections_and_inventory_untouched(
        self,
    ) -> None:
        mediator = Mediator(seed=6207)
        path = _unserved_path(mediator)
        path_collection = path.metros
        global_collection = mediator.metros

        with patch.object(
            mediator_module, "Metro", side_effect=RuntimeError("factory")
        ):
            self.invoke_failure(lambda: mediator.assign_locomotive(path))

        self.assertIs(path.metros, path_collection)
        self.assertIs(mediator.metros, global_collection)
        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])
        self.assert_conserved(mediator)

    def test_path_append_then_raise_restores_original_collection_object_and_contents(
        self,
    ) -> None:
        mediator = Mediator(seed=6208)
        path = _unserved_path(mediator)
        path.metros = _AppendThenRaise([])
        path_collection = path.metros
        global_collection = mediator.metros

        self.invoke_failure(lambda: mediator.assign_locomotive(path))

        self.assertIs(path.metros, path_collection)
        self.assertIs(mediator.metros, global_collection)
        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])
        self.assert_conserved(mediator)

    def test_global_append_then_raise_rolls_back_both_owner_lists(self) -> None:
        mediator = Mediator(seed=6209)
        path = _unserved_path(mediator)
        mediator.metros = _AppendThenRaise([])
        path_collection = path.metros
        global_collection = mediator.metros

        self.invoke_failure(lambda: mediator.assign_locomotive(path))

        self.assertIs(path.metros, path_collection)
        self.assertIs(mediator.metros, global_collection)
        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])
        self.assert_conserved(mediator)

    def test_callback_collection_rebinding_is_restored_before_exception_propagates(
        self,
    ) -> None:
        mediator = Mediator(seed=6210)
        path = _unserved_path(mediator)
        original_add = path.add_metro
        path_collection = path.metros
        global_collection = mediator.metros

        def rebound_add(metro) -> None:
            original_add(metro)
            path.metros = list(path.metros)
            raise RuntimeError("path rebound fault")

        path.add_metro = rebound_add
        self.invoke_failure(lambda: mediator.assign_locomotive(path))

        self.assertIs(path.metros, path_collection)
        self.assertIs(mediator.metros, global_collection)
        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])

        path.add_metro = original_add
        mediator.metros = _RebindingGlobalAppend(mediator)
        global_collection = mediator.metros
        self.invoke_failure(lambda: mediator.assign_locomotive(path))
        self.assertIs(path.metros, path_collection)
        self.assertIs(mediator.metros, global_collection)
        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])
        self.assert_conserved(mediator)

    def test_postcondition_substitution_rolls_back_without_accepting_wrong_identity(
        self,
    ) -> None:
        mediator = Mediator(seed=6211)
        path = _unserved_path(mediator)
        mediator.metros = _SubstitutingAppend([])
        path_collection = path.metros
        global_collection = mediator.metros

        self.invoke_failure(lambda: mediator.assign_locomotive(path))

        self.assertIs(path.metros, path_collection)
        self.assertIs(mediator.metros, global_collection)
        self.assertEqual(path.metros, [])
        self.assertEqual(mediator.metros, [])
        self.assert_conserved(mediator)


if __name__ == "__main__":
    unittest.main()
