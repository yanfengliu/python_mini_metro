from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.passenger import Passenger
from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint
from test.test_gm06c_carriage_inventory import (
    _assert_identities,
    _carriage_type,
    _management_type,
    _network,
)
from test.test_gm06c_carriage_transactions import (
    _assert_snapshot,
    _full_graph,
    _snapshot,
)


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _interaction_state(host):
    return (
        host.is_mouse_down,
        host.is_creating_path,
        host.path_being_created,
        host.path_redraw,
        host.path_edit_selection,
        tuple((button, getattr(button, "is_hovered", None)) for button in host.buttons),
    )


class TestGM06cDeterministicTargetSelection(unittest.TestCase):
    def test_attach_uses_fewest_then_earliest_exact_owner(self) -> None:
        mediator, path = _network(61501, metro_count=3)
        mediator.num_carriages = 10
        first, second, last = path.metros
        lists = tuple(metro.carriages for metro in path.metros)
        manager = _management_type()()
        reconcile = MagicMock(side_effect=AssertionError("moving reconciliation"))

        attached = []
        for expected_owner in (first, second):
            candidate = _carriage_type()()
            factory = MagicMock(return_value=candidate)
            getter = MagicMock(return_value=factory)
            self.assertTrue(
                manager.attach(
                    mediator,
                    path,
                    get_carriage_factory=getter,
                    reconcile_station_service=reconcile,
                )
            )
            getter.assert_called_once_with()
            factory.assert_called_once_with()
            self.assertIs(expected_owner.carriages[-1], candidate)
            attached.append(candidate)

        self.assertEqual([len(metro.carriages) for metro in path.metros], [1, 1, 0])
        self.assertIs(first.carriages[0], attached[0])
        self.assertIs(second.carriages[0], attached[1])
        self.assertEqual(last.carriages, [])
        for metro, original in zip(path.metros, lists, strict=True):
            self.assertIs(metro.carriages, original)
        reconcile.assert_not_called()

    def test_detach_uses_most_then_latest_and_removes_exact_tail(self) -> None:
        mediator, path = _network(61502, metro_count=3)
        mediator.num_carriages = 10
        Carriage = _carriage_type()
        first, second, last = path.metros
        first.carriages.extend(Carriage() for _ in range(2))
        second.carriages.extend(Carriage() for _ in range(3))
        last.carriages.extend(Carriage() for _ in range(3))
        lists = tuple(metro.carriages for metro in path.metros)
        before = tuple(tuple(metro.carriages) for metro in path.metros)
        second_tail = second.carriages[-1]
        last_tail = last.carriages[-1]
        manager = _management_type()()
        reconcile = MagicMock(side_effect=AssertionError("moving reconciliation"))

        self.assertTrue(
            manager.detach(mediator, path, reconcile_station_service=reconcile)
        )
        _assert_identities(self, first.carriages, before[0])
        _assert_identities(self, second.carriages, before[1])
        _assert_identities(self, last.carriages, before[2][:-1])
        self.assertTrue(all(item is not last_tail for item in last.carriages))

        self.assertTrue(
            manager.detach(mediator, path, reconcile_station_service=reconcile)
        )
        _assert_identities(self, first.carriages, before[0])
        _assert_identities(self, second.carriages, before[1][:-1])
        _assert_identities(self, last.carriages, before[2][:-1])
        self.assertTrue(all(item is not second_tail for item in second.carriages))
        self.assertEqual([len(metro.carriages) for metro in path.metros], [2, 2, 2])
        for metro, original in zip(path.metros, lists, strict=True):
            self.assertIs(metro.carriages, original)
        self.assertEqual(
            (
                mediator.num_carriages,
                mediator.assigned_carriages,
                mediator.available_carriages,
            ),
            (10, 6, 4),
        )
        reconcile.assert_not_called()


class TestGM06cQueryAndActionPurity(unittest.TestCase):
    def test_positive_queries_are_repeatable_and_preserve_full_fingerprint(self):
        host, paths, _, _ = _full_graph(61511)
        before = _snapshot(host)

        for _ in range(2):
            self.assertTrue(host.can_attach_carriage(paths[0]))
            self.assertTrue(host.can_detach_carriage(paths[0]))
            _assert_snapshot(self, host, before)

    def test_every_malformed_live_selector_preserves_graph_pointer_and_observation(
        self,
    ) -> None:
        host, paths, _, _ = _full_graph(61512)
        env = MiniMetroEnv()
        env.mediator = host
        env.last_deliveries = host.deliveries
        env.last_line_credits = host.line_credits
        path = paths[0]
        invalid = (
            {"type": "attach_carriage"},
            {"type": "attach_carriage", "path_index": True},
            {"type": "attach_carriage", "path_index": -1},
            {"type": "attach_carriage", "path_index": len(paths)},
            {"type": "attach_carriage", "path_index": 0.0},
            {"type": "attach_carriage", "path_id": None},
            {"type": "attach_carriage", "path_id": True},
            {"type": "attach_carriage", "path_id": "missing-path"},
            {"type": "attach_carriage", "path_index": 0, "path_id": path.id},
            {"type": "detach_carriage"},
            {"type": "detach_carriage", "path_index": True},
            {"type": "detach_carriage", "path_index": -1},
            {"type": "detach_carriage", "path_index": len(paths)},
            {"type": "detach_carriage", "path_index": "0"},
            {"type": "detach_carriage", "path_id": None},
            {"type": "detach_carriage", "path_id": 7},
            {"type": "detach_carriage", "path_id": "missing-path"},
            {"type": "detach_carriage", "path_index": 0, "path_id": path.id},
            {"type": "detach_carriage", "path_id": ""},
        )

        for action in invalid:
            before = _snapshot(host)
            interaction = _interaction_state(host)
            observation = _jsonable(env.observe())
            checkpoint = canonical_checkpoint(env, schema_version=4)
            counters = (env.last_deliveries, env.last_line_credits)
            with self.subTest(action=action):
                current, _, _, info = env.step(action, dt_ms=1_000)
                self.assertFalse(info["action_ok"])
                _assert_snapshot(self, host, before)
                self.assertEqual(_interaction_state(host), interaction)
                self.assertEqual(_jsonable(current), observation)
                self.assertEqual(
                    canonical_checkpoint(env, schema_version=4), checkpoint
                )
                self.assertEqual((env.last_deliveries, env.last_line_credits), counters)

    def test_every_inapplicable_target_preserves_negative_query_and_action_state(
        self,
    ) -> None:
        cases = (
            ("duplicate-path-id", "attach"),
            ("creating", "attach"),
            ("terminal", "attach"),
            ("queued-attach", "attach"),
            ("queued-detach", "detach"),
            ("capacity-unsafe", "detach"),
            ("exhausted", "attach"),
            ("no-locomotive", "detach"),
        )

        for index, (name, operation) in enumerate(cases):
            with self.subTest(name=name):
                host, paths, metros, _ = _full_graph(61520 + index)
                path = paths[0]
                if name == "duplicate-path-id":
                    paths[1].id = path.id
                elif name == "creating":
                    path.is_being_created = True
                elif name == "terminal":
                    host.is_game_over = True
                elif name.startswith("queued"):
                    metros[0].is_unassignment_queued = True
                elif name == "capacity-unsafe":
                    for _ in range(13):
                        passenger = Passenger(path.stations[0].shape)
                        metros[0].passengers.append(passenger)
                        host.passengers.append(passenger)
                elif name == "exhausted":
                    host.num_carriages = 4
                else:
                    path.metros.remove(metros[0])
                    host.metros.remove(metros[0])

                env = MiniMetroEnv()
                env.mediator = host
                env.last_deliveries = host.deliveries
                env.last_line_credits = host.line_credits
                action = {"type": f"{operation}_carriage", "path_index": 0}
                query = (
                    host.can_attach_carriage
                    if operation == "attach"
                    else host.can_detach_carriage
                )
                before = _snapshot(host)
                interaction = _interaction_state(host)
                observation = _jsonable(env.observe())
                checkpoint = (
                    None
                    if name in {"duplicate-path-id", "capacity-unsafe"}
                    else canonical_checkpoint(env, schema_version=4)
                )
                counters = (env.last_deliveries, env.last_line_credits)

                self.assertFalse(query(path))
                _assert_snapshot(self, host, before)
                current, _, _, info = env.step(action, dt_ms=1_000)

                self.assertFalse(info["action_ok"])
                _assert_snapshot(self, host, before)
                self.assertEqual(_interaction_state(host), interaction)
                self.assertEqual(_jsonable(current), observation)
                if checkpoint is not None:
                    self.assertEqual(
                        canonical_checkpoint(env, schema_version=4), checkpoint
                    )
                self.assertEqual((env.last_deliveries, env.last_line_credits), counters)


if __name__ == "__main__":
    unittest.main()
