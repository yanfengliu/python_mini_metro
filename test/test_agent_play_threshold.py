import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import agent_play
from agent_play import (
    DELIVERIES_REWARD_CONTRACT,
    LINE_CREDITS_REWARD_CONTRACT,
    PlaythroughRecord,
    iter_playthrough_observations,
    replay_playthrough,
    run_agent_playthrough,
)

V1_SCHEMA = "mini-metro-agent-play-v1"
V2_SCHEMA = "mini-metro-agent-play-v2"
V3_SCHEMA = "mini-metro-agent-play-v3"
_MISSING = object()


class NoopAgent:
    def reset(self, observation):
        del observation

    def act(self, observation):
        del observation
        return {"type": "noop"}


class ThresholdMediator:
    def __init__(self, threshold):
        self.overdue_passenger_threshold = threshold
        self.deliveries = 0
        self.line_credits = 0
        self.total_travels_handled = 0
        self.score = 0

    @property
    def max_waiting_passengers(self):
        return self.overdue_passenger_threshold

    @max_waiting_passengers.setter
    def max_waiting_passengers(self, value):
        self.overdue_passenger_threshold = value


class ResetReplacingEnv:
    """Small public-API test double whose reset replaces its mediator."""

    def __init__(
        self,
        dt_ms=None,
        reward_mode=DELIVERIES_REWARD_CONTRACT,
        *,
        reset_threshold=17,
    ):
        self.dt_ms_default = dt_ms
        self.reward_mode = reward_mode
        self.reset_threshold = reset_threshold
        self.reset_count = 0
        self.thresholds_during_step = []
        self.mediator = ThresholdMediator(99)

    def _observation(self, time_ms):
        return {
            "structured": {
                "stations": [],
                "deliveries": self.mediator.deliveries,
                "line_credits": self.mediator.line_credits,
                "score": self.mediator.line_credits,
                "time_ms": time_ms,
            }
        }

    def reset(self, seed=None):
        del seed
        self.reset_count += 1
        self.mediator = ThresholdMediator(self.reset_threshold)
        return self._observation(0)

    def step(self, action, dt_ms=None):
        del action, dt_ms
        self.thresholds_during_step.append(self.mediator.overdue_passenger_threshold)
        return self._observation(1), 0, False, {}


def record(
    *,
    schema=_MISSING,
    threshold=_MISSING,
    reward_contract=_MISSING,
    actions=None,
):
    values = {
        "seed": 7,
        "dt_ms": 3,
        "actions": [{"type": "noop"}] if actions is None else actions,
    }
    if schema is not _MISSING:
        values["schema"] = schema
    if threshold is not _MISSING:
        values["overdue_passenger_threshold"] = threshold
    if reward_contract is not _MISSING:
        values["reward_contract"] = reward_contract
    return SimpleNamespace(**values)


class TestAgentPlayThresholdPersistence(unittest.TestCase):
    def test_public_schema_aliases_keep_v1_immutable_and_advance_current_to_v3(self):
        self.assertEqual(agent_play.PLAYTHROUGH_RECORD_SCHEMA_V1, V1_SCHEMA)
        self.assertEqual(agent_play.PLAYTHROUGH_RECORD_SCHEMA_V2, V2_SCHEMA)
        self.assertEqual(agent_play.PLAYTHROUGH_RECORD_SCHEMA_V3, V3_SCHEMA)
        self.assertEqual(agent_play.LEGACY_PLAYTHROUGH_RECORD_SCHEMA, V1_SCHEMA)
        self.assertEqual(agent_play.PLAYTHROUGH_RECORD_SCHEMA, V3_SCHEMA)

    def test_literal_v1_v2_and_v3_identifiers_remain_supported(self):
        cases = (
            (
                V1_SCHEMA,
                LINE_CREDITS_REWARD_CONTRACT,
                _MISSING,
                1,
            ),
            (V2_SCHEMA, DELIVERIES_REWARD_CONTRACT, _MISSING, 1),
            (V3_SCHEMA, DELIVERIES_REWARD_CONTRACT, 4, 4),
        )
        for schema, reward_contract, threshold, expected in cases:
            with self.subTest(schema=schema):
                env = ResetReplacingEnv()
                replay_record = record(
                    schema=schema,
                    reward_contract=reward_contract,
                    threshold=threshold,
                )

                observations = list(
                    iter_playthrough_observations(replay_record, env=env)
                )

                self.assertEqual(len(observations), 2)
                self.assertEqual(env.mediator.overdue_passenger_threshold, expected)
                self.assertEqual(env.thresholds_during_step, [expected])

    def test_schema_less_v1_and_literal_v2_reconstruct_threshold_one(self):
        historical_records = (
            record(),
            record(
                schema=V1_SCHEMA,
                reward_contract=LINE_CREDITS_REWARD_CONTRACT,
            ),
            record(
                schema=V2_SCHEMA,
                reward_contract=DELIVERIES_REWARD_CONTRACT,
            ),
        )
        for replay_record in historical_records:
            with self.subTest(schema=getattr(replay_record, "schema", None)):
                env = ResetReplacingEnv()
                observations = iter_playthrough_observations(replay_record, env=env)

                next(observations)
                self.assertEqual(env.reset_count, 1)
                self.assertEqual(env.mediator.overdue_passenger_threshold, 1)
                list(observations)
                self.assertEqual(env.thresholds_during_step, [1])

    def test_new_capture_records_post_reset_default_and_explicit_thresholds(self):
        for threshold in (2, 5):
            with self.subTest(threshold=threshold):
                env = ResetReplacingEnv(reset_threshold=threshold)

                _, captured = run_agent_playthrough(
                    agent=NoopAgent(),
                    env=env,
                    seed=11,
                    max_steps=0,
                )

                self.assertEqual(captured.schema, V3_SCHEMA)
                self.assertEqual(captured.overdue_passenger_threshold, threshold)

    def test_v3_replay_applies_threshold_after_supplied_environment_reset(self):
        env = ResetReplacingEnv(reset_threshold=19)
        replay_record = record(
            schema=V3_SCHEMA,
            reward_contract=DELIVERIES_REWARD_CONTRACT,
            threshold=6,
        )
        observations = iter_playthrough_observations(replay_record, env=env)

        next(observations)

        self.assertEqual(env.reset_count, 1)
        self.assertEqual(env.mediator.overdue_passenger_threshold, 6)
        list(observations)
        self.assertEqual(env.thresholds_during_step, [6])

    def test_v3_replay_supports_a_zero_argument_environment_factory(self):
        created = []

        def zero_argument_factory():
            env = ResetReplacingEnv(reset_threshold=23)
            created.append(env)
            return env

        replay_record = record(
            schema=V3_SCHEMA,
            reward_contract=DELIVERIES_REWARD_CONTRACT,
            threshold=8,
        )

        with patch.object(agent_play, "MiniMetroEnv", zero_argument_factory):
            replay_playthrough(replay_record)

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].reset_count, 1)
        self.assertEqual(created[0].mediator.overdue_passenger_threshold, 8)
        self.assertEqual(created[0].thresholds_during_step, [8])

    def test_v3_threshold_is_required_and_strictly_positive_non_boolean_integer(self):
        invalid_values = (_MISSING, True, False, 0, -1, 1.5, "2", None)
        for invalid in invalid_values:
            with self.subTest(threshold=invalid):
                env = ResetReplacingEnv()
                replay_record = record(
                    schema=V3_SCHEMA,
                    reward_contract=DELIVERIES_REWARD_CONTRACT,
                    threshold=invalid,
                    actions=[],
                )

                with self.assertRaisesRegex(ValueError, "overdue.*threshold"):
                    list(iter_playthrough_observations(replay_record, env=env))

                self.assertEqual(env.reset_count, 0)

        dataclass_record = PlaythroughRecord(
            seed=7,
            dt_ms=3,
            actions=[],
            schema=V3_SCHEMA,
            reward_contract=DELIVERIES_REWARD_CONTRACT,
        )
        env = ResetReplacingEnv()
        with self.assertRaisesRegex(ValueError, "overdue.*threshold"):
            list(iter_playthrough_observations(dataclass_record, env=env))
        self.assertEqual(env.reset_count, 0)

    def test_capture_and_replay_fail_closed_without_a_threshold_control(self):
        class ThresholdBlindEnv(ResetReplacingEnv):
            def reset(self, seed=None):
                del seed
                self.reset_count += 1
                self.mediator = SimpleNamespace(
                    deliveries=0,
                    line_credits=0,
                    total_travels_handled=0,
                    score=0,
                )
                return self._observation(0)

        capture_env = ThresholdBlindEnv()
        with self.assertRaisesRegex(ValueError, "does not expose"):
            run_agent_playthrough(
                agent=NoopAgent(),
                env=capture_env,
                seed=11,
                max_steps=0,
            )
        self.assertEqual(capture_env.reset_count, 1)

        replay_env = ThresholdBlindEnv()
        replay_record = record(
            schema=V3_SCHEMA,
            reward_contract=DELIVERIES_REWARD_CONTRACT,
            threshold=2,
            actions=[],
        )
        with self.assertRaisesRegex(ValueError, "does not expose"):
            list(iter_playthrough_observations(replay_record, env=replay_env))
        self.assertEqual(replay_env.reset_count, 1)


if __name__ == "__main__":
    unittest.main()
