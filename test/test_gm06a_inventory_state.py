from __future__ import annotations

import os
import sys
import unittest
from copy import deepcopy
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from env import LINE_CREDITS_DELTA_REWARD_MODE, MiniMetroEnv
from game_session import GameSession
from recursive_checkpoint import canonical_checkpoint, normalize_checkpoint
from test.test_gm05c_state_equivalence import _begin, _select

ARRAY_KEYS = {
    "station_positions",
    "station_shape_types",
    "station_passenger_counts",
    "path_station_indices",
    "path_is_looped",
    "metro_positions",
    "metro_path_indices",
    "passenger_destination_types",
    "passenger_station_indices",
    "passenger_metro_indices",
}


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    tolist = getattr(value, "tolist", None)
    return _plain(tolist()) if callable(tolist) else value


def _environment(schema_version: int = 2) -> MiniMetroEnv:
    reward_mode = (
        LINE_CREDITS_DELTA_REWARD_MODE if schema_version == 1 else "deliveries"
    )
    env = MiniMetroEnv(reward_mode=reward_mode)
    env.reset(seed=6106)
    return env


def _unlock_all_lines(env: MiniMetroEnv) -> None:
    env.mediator.purchased_num_paths = env.mediator.num_paths
    env.mediator.update_unlocked_num_paths()


def _create_line(env: MiniMetroEnv) -> None:
    _, _, _, info = env.step({"type": "create_path", "stations": [0, 1], "loop": False})
    if not info["action_ok"]:
        raise AssertionError("test setup could not create a line")


def _checkpoint_available(checkpoint: dict[str, Any]) -> int:
    total = checkpoint["progression"]["limits"]["num_metros"]
    assigned = len(checkpoint["structured"]["metros"])
    return max(0, total - assigned)


class _FailingTopologyList(list):
    def __init__(self, values: list[Any]) -> None:
        super().__init__(values)
        self.armed = True

    def __setitem__(self, key: Any, value: Any) -> None:
        super().__setitem__(key, value)
        if self.armed and isinstance(key, slice):
            self.armed = False
            raise RuntimeError("topology write fault")


class TestGM06AInventoryState(unittest.TestCase):
    def assert_fleet(
        self,
        env: MiniMetroEnv,
        *,
        total: int,
        assigned: int,
        available: int,
        observation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        observation = env.observe() if observation is None else observation
        self.assertEqual(set(observation["arrays"]), ARRAY_KEYS)
        self.assertNotIn("fleet", observation["arrays"])
        self.assertIn("fleet", observation["structured"], "structured fleet is missing")
        self.assertEqual(
            observation["structured"]["fleet"],
            {
                "locomotives_total": total,
                "locomotives_assigned": assigned,
                "locomotives_available": available,
            },
        )
        self.assertEqual(len(observation["structured"]["metros"]), assigned)
        self.assertEqual(env.mediator.num_metros, total)
        self.assertEqual(len(env.mediator.metros), assigned)
        self.assertEqual(env.mediator.available_locomotives, available)
        return observation

    def test_structured_fleet_tracks_create_exhaust_remove_and_reset(self) -> None:
        env = _environment()
        self.assert_fleet(env, total=4, assigned=0, available=4)
        _unlock_all_lines(env)

        for assigned in range(1, 5):
            _create_line(env)
            self.assert_fleet(
                env,
                total=4,
                assigned=assigned,
                available=4 - assigned,
            )

        self.assertTrue(env.mediator.remove_path_by_index(0))
        self.assert_fleet(env, total=4, assigned=3, available=1)
        reset_observation = env.reset(seed=6106)
        self.assert_fleet(
            env,
            total=4,
            assigned=0,
            available=4,
            observation=reset_observation,
        )

    def test_structured_fleet_clamps_direct_cap_changes(self) -> None:
        env = _environment()
        _unlock_all_lines(env)
        _create_line(env)
        _create_line(env)

        for total, available in ((0, 0), (1, 0), (2, 0), (3, 1)):
            env.mediator.num_metros = total
            self.assert_fleet(
                env,
                total=total,
                assigned=2,
                available=available,
            )

    def _assert_checkpoint_reconstruction(self, schema_version: int) -> None:
        env = _environment(schema_version)
        _create_line(env)
        checkpoint = canonical_checkpoint(env, schema_version=schema_version)
        recorded = deepcopy(checkpoint)
        normalized = normalize_checkpoint(checkpoint)

        self.assertEqual(checkpoint, recorded)
        self.assertEqual(_checkpoint_available(checkpoint), 3)
        self.assertEqual(_checkpoint_available(normalized), 3)
        self.assertNotIn("fleet", checkpoint["structured"])
        self.assertNotIn("fleet", normalized["structured"])
        self.assert_fleet(env, total=4, assigned=1, available=3)

    def test_checkpoint_v1_reconstructs_without_a_new_field(self) -> None:
        self._assert_checkpoint_reconstruction(1)

    def test_checkpoint_v2_reconstructs_without_a_new_field(self) -> None:
        self._assert_checkpoint_reconstruction(2)

    def _assert_overcap_checkpoint(self, schema_version: int) -> None:
        env = _environment(schema_version)
        _unlock_all_lines(env)
        _create_line(env)
        _create_line(env)
        env.mediator.num_metros = 0

        for assigned in (2, 1, 0):
            checkpoint = canonical_checkpoint(env, schema_version=schema_version)
            self.assertEqual(len(checkpoint["structured"]["metros"]), assigned)
            self.assertEqual(_checkpoint_available(checkpoint), 0)
            self.assert_fleet(env, total=0, assigned=assigned, available=0)
            if assigned:
                self.assertTrue(env.mediator.remove_path_by_index(0))

    def test_checkpoint_v1_clamps_overcap_removals(self) -> None:
        self._assert_overcap_checkpoint(1)

    def test_checkpoint_v2_clamps_overcap_removals(self) -> None:
        self._assert_overcap_checkpoint(2)

    def _assert_detached_checkpoint(self, schema_version: int) -> None:
        env = _environment(schema_version)
        _create_line(env)
        path = env.mediator.paths[0]
        metro = path.metros[0]
        env.mediator.metros.clear()

        checkpoint = canonical_checkpoint(env, schema_version=schema_version)
        self.assertIn(metro, path.metros)
        self.assertEqual(len(env.mediator.metros), 0)
        self.assertEqual(len(checkpoint["structured"]["metros"]), 0)
        self.assertEqual(len(checkpoint["metroMotion"]), 1)
        self.assertEqual(checkpoint["topology"]["paths"][0]["metro_indices"], [0])
        self.assertEqual(_checkpoint_available(checkpoint), 4)
        self.assert_fleet(env, total=4, assigned=0, available=4)

    def test_checkpoint_v1_uses_global_assignment_for_a_detached_metro(self) -> None:
        self._assert_detached_checkpoint(1)

    def test_checkpoint_v2_uses_global_assignment_for_a_detached_metro(self) -> None:
        self._assert_detached_checkpoint(2)

    def test_observation_and_checkpoint_reads_are_pure(self) -> None:
        env = _environment()
        _create_line(env)
        before = canonical_checkpoint(env)
        observation = env.observe()
        structured_before = deepcopy(observation["structured"])
        arrays_before = _plain(observation["arrays"])

        self.assert_fleet(
            env,
            total=4,
            assigned=1,
            available=3,
            observation=observation,
        )
        canonical_checkpoint(env, observation)
        normalize_checkpoint(before)
        self.assertEqual(observation["structured"], structured_before)
        self.assertEqual(_plain(observation["arrays"]), arrays_before)
        self.assertEqual(canonical_checkpoint(env), before)

    def test_available_property_rejects_assignment_and_deletion(self) -> None:
        env = _environment()
        before = canonical_checkpoint(env)
        observation_before = _plain(env.observe())

        with self.assertRaises(AttributeError):
            env.mediator.available_locomotives = 99
        with self.assertRaises(AttributeError):
            del env.mediator.available_locomotives

        self.assertEqual(canonical_checkpoint(env), before)
        self.assertEqual(_plain(env.observe()), observation_before)
        self.assert_fleet(env, total=4, assigned=0, available=4)

    def test_manual_and_structured_creation_expose_the_same_fleet(self) -> None:
        manual = _environment()
        structured = _environment()
        host = manual.mediator
        host.start_path_on_station(host.stations[0])
        host.add_station_to_path(host.stations[1])
        host.end_path_on_station(host.stations[2])
        _, _, _, info = structured.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False}
        )

        self.assertTrue(info["action_ok"])
        self.assertEqual(canonical_checkpoint(manual), canonical_checkpoint(structured))
        self.assert_fleet(manual, total=4, assigned=1, available=3)
        self.assert_fleet(structured, total=4, assigned=1, available=3)

    def test_successful_public_replacement_preserves_the_fleet_surface(self) -> None:
        env = _environment()
        _, _, _, info = env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False}
        )
        self.assertTrue(info["action_ok"])
        path = env.mediator.paths[0]
        identities = tuple(env.mediator.metros)

        self.assertTrue(env.mediator.replace_path(path, [2, 0, 1]))

        self.assertEqual(tuple(env.mediator.metros), identities)
        self.assert_fleet(env, total=4, assigned=1, available=3)

    def test_rejected_public_replacement_preserves_the_fleet_surface(self) -> None:
        env = _environment()
        _, _, _, info = env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False}
        )
        self.assertTrue(info["action_ok"])
        path = env.mediator.paths[0]
        identities = tuple(env.mediator.metros)
        before = canonical_checkpoint(env)

        self.assertFalse(env.mediator.replace_path(path, [0]))

        self.assertEqual(canonical_checkpoint(env), before)
        self.assertEqual(tuple(env.mediator.metros), identities)
        self.assert_fleet(env, total=4, assigned=1, available=3)

    def test_rolled_back_public_replacement_preserves_the_fleet_surface(self) -> None:
        env = _environment()
        env.mediator.stations = env.mediator.all_stations[:4]
        _, _, _, info = env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False}
        )
        self.assertTrue(info["action_ok"])
        path = env.mediator.paths[0]
        path.stations = _FailingTopologyList(path.stations)
        identities = tuple(env.mediator.metros)
        before = canonical_checkpoint(env)

        with self.assertRaisesRegex(RuntimeError, "topology write fault"):
            env.mediator.replace_path(path, [0, 1, 3, 2])

        self.assertEqual(canonical_checkpoint(env), before)
        self.assertEqual(tuple(env.mediator.metros), identities)
        self.assert_fleet(env, total=4, assigned=1, available=3)

    def test_redraw_selection_and_handle_edit_preserve_the_fleet_surface(self) -> None:
        env = _environment()
        env.mediator.stations = env.mediator.all_stations[:8]
        path = env.mediator.create_path_from_station_indices([0, 1, 2])
        if path is None:
            raise AssertionError("test setup could not create a route")
        session = GameSession(env.mediator)
        identities = tuple(env.mediator.metros)
        before = canonical_checkpoint(env)

        _select(env.mediator, session, path)
        selected = env.observe()
        self.assertEqual(canonical_checkpoint(env), before)
        _begin(env.mediator, session, path, "end")
        editing = env.observe()

        self.assertEqual(canonical_checkpoint(env), before)
        self.assertEqual(tuple(env.mediator.metros), identities)
        for observation in (selected, editing):
            self.assert_fleet(
                env,
                total=4,
                assigned=1,
                available=3,
                observation=observation,
            )

    def test_rejected_pause_and_terminal_operations_preserve_fleet(self) -> None:
        env = _environment()
        _create_line(env)
        identities = tuple(env.mediator.metros)

        rejected, _, _, rejected_info = env.step(
            {"type": "remove_path", "path_index": 99}
        )
        paused, _, _, paused_info = env.step({"type": "pause"})
        env.mediator.is_game_over = True
        terminal_before = canonical_checkpoint(env)
        terminal, _, done, terminal_info = env.step({"type": "noop"})

        self.assertFalse(rejected_info["action_ok"])
        self.assertTrue(paused_info["action_ok"])
        self.assertTrue(done)
        self.assertFalse(terminal_info["action_ok"])
        self.assertEqual(canonical_checkpoint(env), terminal_before)
        self.assertEqual(tuple(env.mediator.metros), identities)
        for observation in (rejected, paused, terminal):
            self.assert_fleet(
                env,
                total=4,
                assigned=1,
                available=3,
                observation=observation,
            )


if __name__ == "__main__":
    unittest.main()
