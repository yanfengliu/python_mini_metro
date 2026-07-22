"""GM-06d Case 2 contract: queue cancellation.

Encodes the app-experience and mechanism contract from
docs/threads/current/game-maturity/2026-07-21/8/PLAN.md ("Case 2 -
Queue cancellation"): the `can_cancel_unassignment`/`cancel_unassignment`
facades, earliest-queued selection, zero-effect rejections, the live
structured action, and the v1-v5 persisted-document gating that keeps
`cancel_unassignment` live/structured-only. Red at baseline.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path as FsPath
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import recursive_contract
import recursive_playtest
from agent_play import iter_playthrough_observations
from entity.carriage import Carriage
from entity.metro import Metro
from entity.path import Path
from env import MiniMetroEnv
from mediator import Mediator
from recursive_checkpoint import canonical_checkpoint
from test.gm06c_simulation_ui_support import (
    boardable_passenger,
    make_two_station_game,
    onboard_passenger,
    passenger_for,
)

REPO_ROOT = FsPath(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "scripts" / "fixtures"
FLEET_CONTRACT = "explicit_locomotive_assignment_v1"
CARRIAGE_CONTRACT = "explicit_carriage_attachment_v1"
CANCEL_ACTION = {"type": "cancel_unassignment", "path_index": 0}


def _unlock_all_paths(mediator: Mediator) -> None:
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _fresh_path(mediator: Mediator, indices=(0, 1)):
    _unlock_all_paths(mediator)
    path = mediator.create_path_from_station_indices(list(indices))
    if path is None:
        raise AssertionError("test setup could not create a path")
    return path


def _install_metro(mediator: Mediator, path) -> Metro:
    metro = Metro()
    path.add_metro(metro)
    mediator.metros.append(metro)
    return metro


def _fingerprint(mediator: Mediator) -> dict[str, object]:
    metros = list(mediator.metros)
    for path in mediator.paths:
        for metro in path.metros:
            if all(metro is not seen for seen in metros):
                metros.append(metro)
    return {
        "time": mediator.time_ms,
        "steps": mediator.steps,
        "python_rng": mediator.context.python_random.getstate(),
        "numpy_rng": deepcopy(mediator.context.numpy_random.bit_generator.state),
        "terminal": mediator.is_game_over,
        "deliveries": mediator.deliveries,
        "line_credits": mediator.line_credits,
        "available_locomotives": mediator.available_locomotives,
        "available_carriages": mediator.available_carriages,
        "paths": (id(mediator.paths), tuple(id(path) for path in mediator.paths)),
        "global_metros": (
            id(mediator.metros),
            tuple(id(metro) for metro in mediator.metros),
        ),
        "path_metros": tuple(
            (id(path.metros), tuple(id(metro) for metro in path.metros))
            for path in mediator.paths
        ),
        "passengers": (
            id(mediator.passengers),
            tuple(id(passenger) for passenger in mediator.passengers),
        ),
        "plans": (
            id(mediator.travel_plans),
            tuple((id(key), id(value)) for key, value in mediator.travel_plans.items()),
        ),
        "metro_state": tuple(
            (
                id(metro),
                metro.is_unassignment_queued,
                id(metro.passengers),
                tuple(id(passenger) for passenger in metro.passengers),
                id(metro.carriages),
                tuple(id(carriage) for carriage in metro.carriages),
                id(metro._station_service_action),
                metro.stop_time_remaining_ms,
                metro.boarding_progress_ms,
                id(metro.current_station),
                metro.current_segment_idx,
                id(metro.position),
            )
            for metro in metros
        ),
    }


def legacy_inputs(version: int) -> dict[str, object]:
    scenario = json.loads(
        (FIXTURE_ROOT / f"recursive-playtest-v{version}.json").read_text(
            encoding="utf-8"
        )
    )
    inputs = {
        "schemaVersion": version,
        "runId": f"gm06d-legacy-v{version}",
        "sourcePath": f"scripts/fixtures/recursive-playtest-v{version}.json",
        "seed": scenario["seed"],
        "defaultDtMs": scenario["defaultDtMs"],
        "pythonExecutable": sys.executable,
        "pythonHashSeed": "0",
        "operations": deepcopy(scenario["operations"]),
    }
    for field in (
        "environmentRewardContract",
        "overduePassengerThreshold",
        "fleetActionContract",
    ):
        if field in scenario:
            inputs[field] = scenario[field]
    return inputs


def v5_inputs() -> dict[str, object]:
    inputs = legacy_inputs(4)
    inputs["schemaVersion"] = 5
    inputs["runId"] = "gm06d-recorded-v5"
    inputs["sourcePath"] = "recorded-v5.json"
    inputs["carriageActionContract"] = CARRIAGE_CONTRACT
    inputs["defaultDtMs"] = 0
    inputs["operations"] = [
        {
            "name": "create",
            "action": {"type": "create_path", "stations": [0, 1], "loop": False},
            "expectedActionOk": True,
        },
        {
            "name": "assign",
            "action": {"type": "assign_locomotive", "path_index": 0},
            "expectedActionOk": True,
        },
        {
            "name": "cancel",
            "action": dict(CANCEL_ACTION),
            "expectedActionOk": True,
        },
    ]
    return inputs


def assert_drive_preflight_rejects(case: unittest.TestCase, document) -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = FsPath(directory)
        input_path = root / "inputs.json"
        out_dir = root / "out"
        input_path.write_text(json.dumps(document), encoding="utf-8")
        with patch.object(
            recursive_playtest,
            "run_scenario",
            return_value=({}, [], [], {}),
        ) as runner:
            with case.assertRaises(ValueError):
                recursive_playtest.drive_from_file(
                    input_path,
                    out_dir,
                    "must-not-run",
                    recorded_inputs=True,
                )
        runner.assert_not_called()
        case.assertFalse(out_dir.exists())


class ResetCountingEnv(MiniMetroEnv):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset_count = 0

    def reset(self, seed=None):
        self.reset_count += 1
        return super().reset(seed=seed)


class TestGM06dCancelFacades(unittest.TestCase):
    def test_cancel_restores_earliest_queued_metro_in_path_order(self) -> None:
        mediator = Mediator(seed=6500)
        path = _fresh_path(mediator)
        first = _install_metro(mediator, path)
        second = _install_metro(mediator, path)
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        self.assertTrue(first.is_unassignment_queued)
        self.assertTrue(second.is_unassignment_queued)

        self.assertTrue(mediator.can_cancel_unassignment(path))
        self.assertTrue(mediator.cancel_unassignment(path))

        self.assertFalse(first.is_unassignment_queued)
        self.assertTrue(second.is_unassignment_queued)
        self.assertEqual(path.metros, [first, second])
        self.assertEqual(mediator.metros, [first, second])
        self.assertEqual(mediator.queued_locomotives_for_path(path), 1)

        self.assertTrue(mediator.cancel_unassignment(path))
        self.assertFalse(second.is_unassignment_queued)
        self.assertEqual(mediator.queued_locomotives_for_path(path), 0)
        self.assertFalse(mediator.can_cancel_unassignment(path))
        self.assertFalse(mediator.cancel_unassignment(path))
        # Candidate production is restored: the queue facade sees the
        # restored Metros again.
        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))

    def test_cancel_restores_boarding_riders_composition_and_inventory(self) -> None:
        mediator, start, end, path, metro = make_two_station_game(seed=6501)
        metro.carriages.append(Carriage())
        rider = passenger_for(end, name="kept-rider")
        metro.passengers.append(rider)
        mediator.passengers.append(rider)
        metro.is_unassignment_queued = True
        riders_before = tuple(metro.passengers)
        carriages_before = tuple(metro.carriages)
        locomotives_before = mediator.available_locomotives
        carriages_available_before = mediator.available_carriages
        self.assertFalse(mediator.can_board_at_station(metro, start))

        self.assertTrue(mediator.can_cancel_unassignment(path))
        self.assertTrue(mediator.cancel_unassignment(path))

        self.assertFalse(metro.is_unassignment_queued)
        self.assertTrue(mediator.can_board_at_station(metro, start))
        self.assertEqual(tuple(metro.passengers), riders_before)
        self.assertEqual(tuple(metro.carriages), carriages_before)
        self.assertIn(metro, path.metros)
        self.assertIn(metro, mediator.metros)
        self.assertEqual(mediator.available_locomotives, locomotives_before)
        self.assertEqual(mediator.available_carriages, carriages_available_before)
        self.assertIn(rider, mediator.passengers)
        # The restored occupied Metro is a queue candidate again.
        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))


class TestGM06dCancelRejections(unittest.TestCase):
    def assert_zero_effect_rejection(self, mediator: Mediator, target) -> None:
        before = _fingerprint(mediator)
        self.assertFalse(mediator.can_cancel_unassignment(target))
        self.assertFalse(mediator.cancel_unassignment(target))
        self.assertEqual(_fingerprint(mediator), before)

    def test_terminal_game_rejects_with_zero_effects(self) -> None:
        mediator = Mediator(seed=6510)
        path = _fresh_path(mediator)
        _install_metro(mediator, path)
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        mediator.is_game_over = True

        self.assert_zero_effect_rejection(mediator, path)

    def test_inactive_unknown_path_rejects_with_zero_effects(self) -> None:
        mediator = Mediator(seed=6511)
        path = _fresh_path(mediator)
        _install_metro(mediator, path)
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        foreign = Path((10, 20, 30))
        foreign.add_station(mediator.stations[0])
        foreign.add_station(mediator.stations[1])

        self.assert_zero_effect_rejection(mediator, foreign)

    def test_no_queued_metro_rejects_with_zero_effects(self) -> None:
        mediator = Mediator(seed=6512)
        path = _fresh_path(mediator)
        metro = _install_metro(mediator, path)
        self.assertFalse(metro.is_unassignment_queued)

        self.assert_zero_effect_rejection(mediator, path)

    def test_non_canonical_queue_state_rejects_with_zero_effects(self) -> None:
        mediator = Mediator(seed=6513)
        path = _fresh_path(mediator)
        corrupted = _install_metro(mediator, path)
        queued = _install_metro(mediator, path)
        queued.is_unassignment_queued = True
        corrupted.is_unassignment_queued = "corrupt"

        self.assert_zero_effect_rejection(mediator, path)
        self.assertEqual(corrupted.is_unassignment_queued, "corrupt")
        self.assertTrue(queued.is_unassignment_queued)


class TestGM06dCancelStructuredAction(unittest.TestCase):
    def _live_environment(self):
        env = MiniMetroEnv()
        mediator = Mediator(seed=6520)
        path = _fresh_path(mediator)
        self.assertTrue(mediator.assign_locomotive(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        env.mediator = mediator
        return env, mediator, path, path.metros[0]

    def test_path_index_selector_cancels_live_and_tolerates_extras(self) -> None:
        env, mediator, path, metro = self._live_environment()
        self.assertTrue(metro.is_unassignment_queued)

        _, _, _, info = env.step(
            {"type": "cancel_unassignment", "path_index": 0, "ignored": object()},
            dt_ms=0,
        )

        self.assertTrue(info["action_ok"])
        self.assertFalse(metro.is_unassignment_queued)
        self.assertIn(metro, path.metros)
        self.assertIn(metro, mediator.metros)

    def test_path_id_selector_cancels_live(self) -> None:
        env, mediator, path, metro = self._live_environment()

        _, _, _, info = env.step(
            {"type": "cancel_unassignment", "path_id": path.id, "extra": 7},
            dt_ms=0,
        )

        self.assertTrue(info["action_ok"])
        self.assertFalse(metro.is_unassignment_queued)

    def test_selector_validation_requires_exactly_one_selector(self) -> None:
        # regression guard: green at baseline (today every cancel action is
        # rejected as an unknown type; once the action exists, these exact
        # malformed selectors must keep rejecting with zero effects).
        env, mediator, path, metro = self._live_environment()
        invalid = (
            {"type": "cancel_unassignment"},
            {"type": "cancel_unassignment", "path_index": 0, "path_id": path.id},
            {"type": "cancel_unassignment", "path_index": True},
            {"type": "cancel_unassignment", "path_index": -1},
            {"type": "cancel_unassignment", "path_index": 99},
            {"type": "cancel_unassignment", "path_id": ""},
        )
        before = (mediator.time_ms, tuple(mediator.metros))
        for action in invalid:
            with self.subTest(action=action):
                _, _, _, info = env.step(action, dt_ms=0)
                self.assertFalse(info["action_ok"])
                self.assertTrue(metro.is_unassignment_queued)
                self.assertEqual((mediator.time_ms, tuple(mediator.metros)), before)


class TestGM06dPausedCancelReconciliation(unittest.TestCase):
    """Cancelling while paused rebinds the newly-legal boarding action.

    Adversarial-review F-1 regression (cancel direction): restoring the
    queue flag alone left a ``None`` service cache disagreeing with the
    now-unbounded pure oracle, so checkpoint v4 raised on the paused state.
    """

    def test_paused_cancel_rebinds_boarding_and_keeps_checkpoint_valid(self) -> None:
        env = MiniMetroEnv(reward_mode="deliveries")
        mediator, start, end, path, metro = make_two_station_game(seed=6540)
        env.mediator = mediator
        keeper = onboard_passenger(
            mediator, metro, end, name="kept-rider", next_station=end
        )
        boarder = boardable_passenger(mediator, start, end, path, name="boarder")
        metro.is_unassignment_queued = True
        mediator.set_paused(True)
        # The queued parked state is canonical before cancellation.
        self.assertEqual(
            canonical_checkpoint(env, schema_version=4)["schemaVersion"], 4
        )

        self.assertTrue(mediator.can_cancel_unassignment(path))
        self.assertTrue(mediator.cancel_unassignment(path))

        self.assertTrue(mediator.is_paused)
        self.assertFalse(metro.is_unassignment_queued)
        # The newly-legal boarding action binds synchronously, so the
        # paused state stays canonical for checkpoint v4.
        action = metro._station_service_action
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action[0], "board")
        self.assertIs(action[1], boarder)
        self.assertEqual(metro.stop_time_remaining_ms, 500)
        self.assertEqual(
            canonical_checkpoint(env, schema_version=4)["schemaVersion"], 4
        )
        self.assertIn(keeper, metro.passengers)
        # After the unpause tick the bound boarding executes on schedule.
        mediator.set_paused(False)
        mediator.increment_time(500)
        self.assertIn(boarder, metro.passengers)
        self.assertNotIn(boarder, start.passengers)


class TestGM06dCancelPersistedGating(unittest.TestCase):
    def test_v1_through_v4_documents_reject_cancel_before_drive(self) -> None:
        for version in (1, 2, 3, 4):
            candidate = legacy_inputs(version)
            candidate["operations"] = [
                {
                    "name": "incompatible-cancel",
                    "action": dict(CANCEL_ACTION),
                    "expectedActionOk": False,
                }
            ]
            with self.subTest(version=version):
                with self.assertRaises(ValueError):
                    recursive_contract.validate_inputs(candidate)
                assert_drive_preflight_rejects(self, candidate)

    def test_v5_documents_reject_every_cancel_selector_before_drive(self) -> None:
        selectors = (
            {"path_index": 0},
            {"path_id": "Path-process-local"},
            {},
        )
        for selector in selectors:
            candidate = v5_inputs()
            candidate["operations"][2]["action"] = {
                "type": "cancel_unassignment",
                **selector,
            }
            with self.subTest(selector=selector):
                with self.assertRaises(ValueError):
                    recursive_contract.validate_inputs(candidate)
                assert_drive_preflight_rejects(self, candidate)

    def assert_rejected_before_reset(self, record, *, reward="deliveries") -> None:
        env = ResetCountingEnv(reward_mode=reward)
        with self.assertRaises(ValueError):
            list(iter_playthrough_observations(record, env=env))
        self.assertEqual(env.reset_count, 0)

    def test_agent_records_v1_through_v5_reject_cancel_before_reset(self) -> None:
        cases = (
            ("mini-metro-agent-play-v1", "line_credits_delta", None, None, None),
            ("mini-metro-agent-play-v2", "deliveries", None, None, None),
            ("mini-metro-agent-play-v3", "deliveries", 2, None, None),
            ("mini-metro-agent-play-v4", "deliveries", 2, FLEET_CONTRACT, None),
            (
                "mini-metro-agent-play-v5",
                "deliveries",
                2,
                FLEET_CONTRACT,
                CARRIAGE_CONTRACT,
            ),
        )
        valid_prefix = {"type": "create_path", "stations": [0, 1], "loop": False}
        for schema, reward, threshold, fleet, carriage in cases:
            record = SimpleNamespace(
                seed=6531,
                dt_ms=0,
                schema=schema,
                reward_contract=reward,
                overdue_passenger_threshold=threshold,
                fleet_action_contract=fleet,
                carriage_action_contract=carriage,
                actions=[valid_prefix, dict(CANCEL_ACTION)],
            )
            with self.subTest(schema=schema):
                self.assert_rejected_before_reset(record, reward=reward)


if __name__ == "__main__":
    unittest.main()
