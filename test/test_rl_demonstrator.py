from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np

from rl.demonstrator import (
    DEMONSTRATION_SEED,
    VERIFIED_DELIVERY_MAX_DECISIONS,
    drag_route_actions,
    pause_resume_action,
    run_delivery_demonstration,
    speed_action,
)
from rl.player_env import PlayerPixelEnv
from rl.privileged_oracle import capture_privileged_snapshot
from rl.protocol import (
    FAST_RENDER_PROFILE,
    ActionKind,
    canonical_to_action_coordinate,
)


class TestDemonstrationActions(unittest.TestCase):
    def setUp(self) -> None:
        positions = ((100, 200), (500, 600), (900, 700))
        stations = [
            SimpleNamespace(position=SimpleNamespace(left=x, top=y))
            for x, y in positions
        ]
        self.env = SimpleNamespace(
            _mediator=SimpleNamespace(
                stations=stations,
                paths=[],
                total_travels_handled=0,
                score=0,
                time_ms=0,
                is_paused=False,
            ),
            task_spec=SimpleNamespace(render_profile=FAST_RENDER_PROFILE),
        )

    def test_drag_route_actions_use_quantized_low_level_player_events(self) -> None:
        actions = drag_route_actions(self.env, [0, 2, 1])

        self.assertEqual(
            [ActionKind(int(action[0])) for action in actions],
            [ActionKind.DOWN, ActionKind.MOTION, ActionKind.MOTION, ActionKind.UP],
        )
        expected_coordinates = [
            canonical_to_action_coordinate(100, 200, FAST_RENDER_PROFILE),
            canonical_to_action_coordinate(900, 700, FAST_RENDER_PROFILE),
            canonical_to_action_coordinate(500, 600, FAST_RENDER_PROFILE),
            canonical_to_action_coordinate(500, 600, FAST_RENDER_PROFILE),
        ]
        self.assertEqual(
            [tuple(int(value) for value in action[1:]) for action in actions],
            expected_coordinates,
        )
        for action in actions:
            self.assertEqual(action.shape, (3,))
            self.assertEqual(action.dtype, np.int64)

    def test_loop_drag_returns_to_the_first_station_before_release(self) -> None:
        actions = drag_route_actions(self.env, [0, 1, 2], loop=True)

        self.assertEqual(
            [ActionKind(int(action[0])) for action in actions],
            [
                ActionKind.DOWN,
                ActionKind.MOTION,
                ActionKind.MOTION,
                ActionKind.MOTION,
                ActionKind.UP,
            ],
        )
        first = canonical_to_action_coordinate(100, 200, FAST_RENDER_PROFILE)
        self.assertEqual(tuple(actions[-2][1:]), first)
        self.assertEqual(tuple(actions[-1][1:]), first)

    def test_route_validation_rejects_ambiguous_or_unreachable_inputs(self) -> None:
        for indices in ([], [0], [0, 0], [0, 3], [0, -1], [0, True]):
            with self.assertRaises((TypeError, ValueError, IndexError)):
                drag_route_actions(self.env, indices)
        with self.assertRaises(TypeError):
            drag_route_actions(self.env, [0, 1], loop=1)  # type: ignore[arg-type]

    def test_pause_and_speed_helpers_emit_protocol_actions(self) -> None:
        self.assertTrue(
            np.array_equal(
                pause_resume_action(),
                np.asarray([ActionKind.SPACE, 0, 0], dtype=np.int64),
            )
        )
        for multiplier, kind in (
            (1, ActionKind.KEY_1),
            (2, ActionKind.KEY_2),
            (4, ActionKind.KEY_3),
        ):
            self.assertTrue(
                np.array_equal(
                    speed_action(multiplier),
                    np.asarray([kind, 0, 0], dtype=np.int64),
                )
            )
        for invalid in (0, 3, True, 1.0):
            with self.assertRaises((TypeError, ValueError)):
                speed_action(invalid)  # type: ignore[arg-type]


class TestDeliveryDemonstration(unittest.TestCase):
    def test_verified_seed_earns_a_delivery_through_only_env_steps(self) -> None:
        env = PlayerPixelEnv(
            max_episode_steps=VERIFIED_DELIVERY_MAX_DECISIONS,
        )
        self.addCleanup(env.close)

        result = run_delivery_demonstration(
            env,
            max_decisions=VERIFIED_DELIVERY_MAX_DECISIONS,
        )

        self.assertEqual(result.metrics["seed"], DEMONSTRATION_SEED)
        self.assertTrue(result.metrics["completed_delivery"])
        self.assertGreaterEqual(result.metrics["deliveries"], 1)
        self.assertFalse(result.metrics["terminated"])
        self.assertFalse(result.metrics["truncated"])
        self.assertLessEqual(
            result.metrics["decisions"], VERIFIED_DELIVERY_MAX_DECISIONS
        )
        self.assertEqual(result.metrics["decisions"], len(result.actions))
        kinds = [ActionKind(int(action[0])) for action in result.actions]
        self.assertEqual(kinds[0], ActionKind.DOWN)
        self.assertIn(ActionKind.MOTION, kinds)
        self.assertIn(ActionKind.UP, kinds)
        route_action_count = len(result.metrics["route_station_indices"]) + 1
        self.assertEqual(
            kinds[route_action_count : route_action_count + 2],
            [ActionKind.DOWN, ActionKind.UP],
        )
        self.assertEqual(
            kinds[route_action_count + 2 : route_action_count + 4],
            [ActionKind.DOWN, ActionKind.UP],
        )
        self.assertTrue(
            all(kind is ActionKind.NOOP for kind in kinds[route_action_count + 4 :])
        )
        self.assertEqual(len(capture_privileged_snapshot(env).path_station_indices), 1)

    def test_verified_demonstration_replays_deterministically(self) -> None:
        first = PlayerPixelEnv(max_episode_steps=VERIFIED_DELIVERY_MAX_DECISIONS)
        second = PlayerPixelEnv(max_episode_steps=VERIFIED_DELIVERY_MAX_DECISIONS)
        self.addCleanup(first.close)
        self.addCleanup(second.close)

        first_result = run_delivery_demonstration(
            first, VERIFIED_DELIVERY_MAX_DECISIONS
        )
        second_result = run_delivery_demonstration(
            second, VERIFIED_DELIVERY_MAX_DECISIONS
        )

        self.assertEqual(first_result.metrics, second_result.metrics)
        self.assertEqual(len(first_result.actions), len(second_result.actions))
        for first_action, second_action in zip(
            first_result.actions, second_result.actions
        ):
            self.assertTrue(np.array_equal(first_action, second_action))


if __name__ == "__main__":
    unittest.main()
