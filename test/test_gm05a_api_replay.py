import inspect
import json
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path as FilePath
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.path import Path
from env import MiniMetroEnv
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint
from recursive_oracles import reference_errors


class Action(dict):
    pass


class ActionType(str):
    pass


class IntSubclass(int):
    pass


class ListSubclass(list):
    pass


class StrSubclass(str):
    pass


class TestGM05aApiReplay(unittest.TestCase):
    def assert_observation_topology_agrees(self, observation):
        structured = observation["structured"]
        arrays = observation["arrays"]
        station_indices = structured["index"]["station_id_to_index"]
        expected_paths = [
            [station_indices[station_id] for station_id in path["station_ids"]]
            for path in structured["paths"]
        ]

        self.assertEqual(
            [values.tolist() for values in arrays["path_station_indices"]],
            expected_paths,
        )
        self.assertEqual(
            arrays["path_is_looped"].tolist(),
            [int(path["is_looped"]) for path in structured["paths"]],
        )

    def build_env_with_path(self, *, seed, stations, loop=False):
        env = MiniMetroEnv()
        env.reset(seed=seed)
        path = env.mediator.create_path_from_station_indices(stations, loop=loop)
        self.assertIsNotNone(path)
        return env, path

    def test_exact_replace_facade_and_private_replanner_signatures(self):
        expected = {
            "replace_path": "(self, path: 'Path', station_indices: 'List[int]', loop: 'bool' = False) -> 'bool'",
            "replace_path_by_id": "(self, path_id: 'str', station_indices: 'List[int]', loop: 'bool' = False) -> 'bool'",
            "replace_path_by_index": "(self, path_index: 'int', station_indices: 'List[int]', loop: 'bool' = False) -> 'bool'",
            "_replan_passenger_at_station": "(self, passenger: 'Passenger', station: 'Station', station_nodes_dict: 'Dict[Station, Node]') -> 'None'",
        }

        actual = {
            name: str(inspect.signature(member))
            for name in expected
            if callable(member := getattr(Mediator, name, None))
        }
        self.assertEqual(actual, expected)
        self.assertFalse(hasattr(Mediator, "replan_passenger_at_station"))

    def test_structured_subclasses_extras_and_dynamic_selector_dispatch(self):
        mediator = Mediator(seed=3)
        by_id = MagicMock(return_value=True)
        mediator.replace_path_by_id = by_id

        self.assertTrue(
            mediator.apply_action(
                Action(
                    type=ActionType("replace_path"),
                    path_id="line-id",
                    stations=[0, 1],
                    loop=True,
                    ignored={"future": "field"},
                )
            )
        )
        by_id.assert_called_once_with("line-id", [0, 1], True)

        by_index = MagicMock(return_value=True)
        mediator.replace_path_by_index = by_index
        self.assertTrue(
            mediator.apply_action(
                Action(type=ActionType("replace_path"), path_index=0, stations=[1, 2])
            )
        )
        by_index.assert_called_once_with(0, [1, 2], False)

    def test_structured_selector_presence_is_exact_xor_even_for_none(self):
        mediator = Mediator(seed=5)
        by_id = MagicMock(return_value=True)
        by_index = MagicMock(return_value=True)
        mediator.replace_path_by_id = by_id
        mediator.replace_path_by_index = by_index
        invalid = (
            {"type": "replace_path", "stations": [0, 1]},
            {
                "type": "replace_path",
                "path_id": "line-id",
                "path_index": 0,
                "stations": [0, 1],
            },
            {
                "type": "replace_path",
                "path_id": None,
                "path_index": 0,
                "stations": [0, 1],
            },
            {
                "type": "replace_path",
                "path_id": "line-id",
                "path_index": None,
                "stations": [0, 1],
            },
            {"type": "replace_path", "path_id": None, "stations": [0, 1]},
        )

        for action in invalid:
            with self.subTest(action=action):
                self.assertFalse(mediator.apply_action(action))
                by_id.assert_not_called()
                by_index.assert_not_called()

        self.assertTrue(
            mediator.apply_action(
                {"type": "replace_path", "path_id": "line-id", "stations": [0, 1]}
            )
        )
        by_id.assert_called_once_with("line-id", [0, 1], False)

    def test_structured_payload_requires_exact_types_and_active_bounds(self):
        mediator = Mediator(seed=7)
        by_id = MagicMock(return_value=True)
        by_index = MagicMock(return_value=True)
        mediator.replace_path_by_id = by_id
        mediator.replace_path_by_index = by_index
        station_count = len(mediator.stations)
        invalid = (
            {
                "type": "replace_path",
                "path_id": StrSubclass("line-id"),
                "stations": [0, 1],
            },
            {"type": "replace_path", "path_id": "", "stations": [0, 1]},
            {
                "type": "replace_path",
                "path_index": IntSubclass(0),
                "stations": [0, 1],
            },
            {"type": "replace_path", "path_index": True, "stations": [0, 1]},
            {
                "type": "replace_path",
                "path_index": 0,
                "stations": ListSubclass([0, 1]),
            },
            {"type": "replace_path", "path_index": 0, "stations": (0, 1)},
            {"type": "replace_path", "path_index": 0, "stations": [0]},
            {"type": "replace_path", "path_index": 0, "stations": [0, True]},
            {
                "type": "replace_path",
                "path_index": 0,
                "stations": [0, IntSubclass(1)],
            },
            {"type": "replace_path", "path_index": 0, "stations": [-1, 1]},
            {
                "type": "replace_path",
                "path_index": 0,
                "stations": [0, station_count],
            },
            {
                "type": "replace_path",
                "path_index": 0,
                "stations": [0, 1],
                "loop": 1,
            },
        )

        for action in invalid:
            with self.subTest(action=action):
                self.assertFalse(mediator.apply_action(action))
                by_id.assert_not_called()
                by_index.assert_not_called()

        self.assertTrue(
            mediator.apply_action(
                {
                    "type": "replace_path",
                    "path_index": 0,
                    "stations": [0, station_count - 1],
                    "loop": False,
                }
            )
        )
        by_index.assert_called_once_with(0, [0, station_count - 1], False)

    def test_selector_wrappers_fail_closed_and_resolve_replace_hook_late(self):
        mediator = Mediator(seed=11)
        path = mediator.create_path_from_station_indices([0, 1, 2])
        self.assertIsNotNone(path)
        by_id = getattr(mediator, "replace_path_by_id", None)
        by_index = getattr(mediator, "replace_path_by_index", None)
        self.assertTrue(callable(by_id))
        self.assertTrue(callable(by_index))

        first_hook = MagicMock(return_value=True)
        mediator.replace_path = first_hook
        self.assertTrue(by_id(path.id, [0, 1, 2], True))
        first_hook.assert_called_once_with(path, [0, 1, 2], True)

        second_hook = MagicMock(return_value=True)
        mediator.replace_path = second_hook
        self.assertTrue(by_index(0, [0, 1, 2]))
        second_hook.assert_called_once_with(path, [0, 1, 2], False)

        for invalid in (None, "", StrSubclass(path.id), 1):
            with self.subTest(path_id=invalid):
                self.assertFalse(by_id(invalid, [0, 1]))
        for invalid in (False, IntSubclass(0), -1, 1):
            with self.subTest(path_index=invalid):
                self.assertFalse(by_index(invalid, [0, 1]))

        duplicate = Path(path.color)
        duplicate.id = path.id
        duplicate.add_station(mediator.stations[0])
        duplicate.add_station(mediator.stations[1])
        mediator.paths = [path, duplicate]
        mediator.replace_path = MagicMock(return_value=True)
        self.assertFalse(by_id(path.id, [0, 1]))
        mediator.replace_path.assert_not_called()

        mediator.paths = [path, path]
        self.assertFalse(by_index(0, [0, 1]))
        mediator.replace_path.assert_not_called()

    def test_rejected_structured_action_does_not_advance_default_time(self):
        env = MiniMetroEnv(dt_ms=41)
        env.reset(seed=13)
        before = canonical_checkpoint(env)
        replacement = MagicMock(return_value=False)
        env.mediator.replace_path_by_index = replacement

        observation, reward, done, info = env.step(
            {
                "type": "replace_path",
                "path_index": 0,
                "stations": [0, 1],
                "loop": False,
            }
        )

        self.assertFalse(info["action_ok"])
        replacement.assert_called_once_with(0, [0, 1], False)
        self.assertEqual(reward, 0)
        self.assertFalse(done)
        self.assertEqual(canonical_checkpoint(env, observation), before)

    def test_successful_linear_and_loop_actions_preserve_id_and_observation_contract(
        self,
    ):
        cases = (
            (17, [0, 1], False, [0, 1, 2], False, "path_id"),
            (19, [0, 1, 0], True, [0, 1, 2, 0], True, "path_index"),
        )
        for seed, created, created_loop, replacement, loop, selector in cases:
            with self.subTest(loop=loop, selector=selector):
                env, path = self.build_env_with_path(
                    seed=seed, stations=created, loop=created_loop
                )
                path_id = path.id
                paths = env.mediator.paths
                checkpoint_keys = set(canonical_checkpoint(env))
                action = {
                    "type": "replace_path",
                    selector: path_id if selector == "path_id" else 0,
                    "stations": replacement,
                    "loop": loop,
                }

                observation, reward, done, info = env.step(action, dt_ms=0)

                self.assertTrue(info["action_ok"])
                self.assertEqual(reward, 0)
                self.assertFalse(done)
                self.assertIs(env.mediator.paths, paths)
                self.assertIs(env.mediator.paths[0], path)
                self.assertEqual(path.id, path_id)
                normalized = replacement[:-1] if loop else replacement
                self.assertEqual(
                    path.stations,
                    [env.mediator.stations[index] for index in normalized],
                )
                self.assertEqual(path.is_looped, loop)
                self.assertEqual(observation["structured"]["paths"][0]["id"], path_id)
                self.assert_observation_topology_agrees(observation)
                checkpoint = canonical_checkpoint(env, observation)
                self.assertEqual(set(checkpoint), checkpoint_keys)
                self.assertEqual(checkpoint["schemaVersion"], 2)
                self.assertEqual(reference_errors(checkpoint), [])

    def test_rejected_linear_and_loop_actions_preserve_checkpoint_and_arrays(self):
        cases = (
            (23, [0, 1, 2], False, [0, 1, 1, 2], False, "path_id"),
            (
                29,
                [0, 1, 2, 0],
                True,
                [0, 1, 3, 1, 2, 0],
                True,
                "path_index",
            ),
        )
        for seed, created, created_loop, replacement, loop, selector in cases:
            with self.subTest(loop=loop, selector=selector):
                env, path = self.build_env_with_path(
                    seed=seed, stations=created, loop=created_loop
                )
                self.assertTrue(callable(getattr(env.mediator, "replace_path", None)))
                paths = env.mediator.paths
                before = canonical_checkpoint(env)
                action = {
                    "type": "replace_path",
                    selector: path.id if selector == "path_id" else 0,
                    "stations": replacement,
                    "loop": loop,
                }

                observation, reward, done, info = env.step(action, dt_ms=97)

                self.assertFalse(info["action_ok"])
                self.assertEqual(reward, 0)
                self.assertFalse(done)
                self.assertIs(env.mediator.paths, paths)
                self.assertIs(env.mediator.paths[0], path)
                self.assert_observation_topology_agrees(observation)
                checkpoint = canonical_checkpoint(env, observation)
                self.assertEqual(checkpoint, before)
                self.assertEqual(reference_errors(checkpoint), [])

    def test_fresh_process_recursive_replay_is_exact_and_oracle_clean(self):
        repo_root = FilePath(__file__).resolve().parents[1]
        source_root = repo_root / "src"
        script = textwrap.dedent(
            """
            import json
            from recursive_playtest import run_scenario

            scenario = {
                "schemaVersion": 2,
                "seed": 31,
                "defaultDtMs": 0,
                "environmentRewardContract": "deliveries",
                "operations": [
                    {
                        "name": "create-linear",
                        "action": {
                            "type": "create_path",
                            "stations": [0, 1],
                            "loop": False,
                        },
                        "expectedActionOk": True,
                        "dtMs": 0,
                    },
                    {
                        "name": "replace-linear",
                        "action": {
                            "type": "replace_path",
                            "path_index": 0,
                            "stations": [0, 1, 2],
                            "loop": False,
                        },
                        "expectedActionOk": True,
                        "dtMs": 0,
                    },
                    {
                        "name": "reject-duplicate",
                        "action": {
                            "type": "replace_path",
                            "path_index": 0,
                            "stations": [0, 1, 1, 2],
                            "loop": False,
                        },
                        "expectedActionOk": False,
                        "dtMs": 97,
                    },
                ],
            }
            _, transcript, findings, _ = run_scenario(
                scenario,
                run_id="gm05a-fresh",
                source_path="gm05a-inline",
            )
            payload = {
                "action_ok": [row["actionOk"] for row in transcript],
                "checkpoints": [row["checkpoint"] for row in transcript],
                "findings": findings,
            }
            print("GM05A_RESULT=" + json.dumps(payload, sort_keys=True))
            """
        )
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = "31"
        environment["SDL_VIDEODRIVER"] = "dummy"
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(source_root), environment.get("PYTHONPATH")])
        )

        payloads = []
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=repo_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            line = next(
                (
                    item.removeprefix("GM05A_RESULT=")
                    for item in result.stdout.splitlines()
                    if item.startswith("GM05A_RESULT=")
                ),
                None,
            )
            self.assertIsNotNone(line, result.stdout)
            payloads.append(json.loads(line))

        self.assertEqual(payloads[0], payloads[1])
        self.assertEqual(payloads[0]["action_ok"], [True, True, False])
        self.assertEqual(payloads[0]["findings"], [])


if __name__ == "__main__":
    unittest.main()
