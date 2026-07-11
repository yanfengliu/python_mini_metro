from __future__ import annotations

import os
import random
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np
import pygame
from gymnasium.utils.env_checker import check_env

from entity.passenger import Passenger
from event.type import MouseEventType
from geometry.point import Point
from rl.player_env import PlayerPixelEnv
from rl.privileged_oracle import capture_privileged_snapshot
from rl.protocol import (
    CURSOR_FILL_COLOR,
    CURSOR_OUTLINE_COLOR,
    CURSOR_PRESSED_MARKER_COLOR,
    FAST_RENDER_PROFILE,
    FIDELITY_RENDER_PROFILE,
    ActionKind,
    RewardMode,
    TaskSpec,
    canonical_to_action_coordinate,
    map_action_coordinate,
)


class TestPlayerPixelEnv(unittest.TestCase):
    def setUp(self) -> None:
        self.env = PlayerPixelEnv(render_mode="rgb_array", max_episode_steps=20)

    def tearDown(self) -> None:
        self.env.close()

    @staticmethod
    def action(kind: ActionKind, x: int = 0, y: int = 0) -> np.ndarray:
        return np.asarray([kind.value, x, y], dtype=np.int64)

    def test_gymnasium_contract_spaces_and_headless_render(self) -> None:
        observation, info = self.env.reset(seed=42)

        self.assertEqual(observation.shape, (3, 108, 192))
        self.assertEqual(observation.dtype, np.uint8)
        self.assertTrue(observation.flags.c_contiguous)
        self.assertTrue(self.env.observation_space.contains(observation))
        self.assertEqual(tuple(self.env.action_space.nvec), (8, 192, 108))
        self.assertEqual(info["decision"], 0)
        self.assertNotIn("stations", info)
        for hidden_key in (
            "seed",
            "deliveries",
            "display_score",
            "simulation_time_ms",
        ):
            self.assertNotIn(hidden_key, info)
        self.assertIsNone(pygame.display.get_surface())

        faster = PlayerPixelEnv(fixed_ticks=3, max_episode_steps=2)
        self.addCleanup(faster.close)
        self.assertEqual(faster.metadata["render_fps"], 20.0)
        self.assertEqual(self.env.metadata["render_fps"], 10.0)

        frame = self.env.render()
        assert frame is not None
        self.assertEqual(frame.shape, (1080, 1920, 3))
        self.assertEqual(frame.dtype, np.uint8)
        self.assertIsNone(pygame.display.get_surface())

    def test_environment_passes_gymnasium_checker(self) -> None:
        check_env(self.env, skip_render_check=False)

    def test_action_validation_rejects_fractional_boolean_and_out_of_range_values(
        self,
    ) -> None:
        self.env.reset(seed=42)
        for action in (
            np.asarray([0.5, 0, 0]),
            np.asarray([True, False, False]),
            [0, True, 0],
            np.asarray([8, 0, 0], dtype=np.int64),
            np.asarray([0, 192, 0], dtype=np.int64),
            np.asarray([0, 0], dtype=np.int64),
        ):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    self.env.step(action)

    def test_exact_ticks_pause_resume_and_horizon(self) -> None:
        self.env.close()
        self.env = PlayerPixelEnv(max_episode_steps=3)
        self.env.reset(seed=10)
        self.assertEqual(capture_privileged_snapshot(self.env).simulation_time_ms, 0)

        _, _, terminated, truncated, first = self.env.step(self.action(ActionKind.NOOP))
        self.assertFalse(terminated)
        self.assertFalse(truncated)
        self.assertNotIn("game_episode", first)
        self.assertEqual(capture_privileged_snapshot(self.env).simulation_time_ms, 100)

        self.env.step(self.action(ActionKind.SPACE))
        paused = capture_privileged_snapshot(self.env)
        self.assertEqual(paused.simulation_time_ms, 100)
        self.assertTrue(paused.is_paused)

        _, _, terminated, truncated, resumed = self.env.step(
            self.action(ActionKind.SPACE)
        )
        self.assertFalse(terminated)
        self.assertTrue(truncated)
        self.assertEqual(resumed["game_episode"]["simulation_time_ms"], 200)
        self.assertEqual(resumed["game_episode"]["seed"], 10)
        with self.assertRaisesRegex(RuntimeError, "reset"):
            self.env.step(self.action(ActionKind.NOOP))

    def test_game_over_terminates_and_takes_precedence_over_horizon(self) -> None:
        self.env.close()
        self.env = PlayerPixelEnv(max_episode_steps=1)
        self.env.reset(seed=14)
        mediator = self.env._mediator
        assert mediator is not None
        passenger = Passenger(mediator.stations[1].shape)
        passenger.wait_ms = mediator.passenger_max_wait_time_ms - 1
        mediator.stations[0].add_passenger(passenger)

        _, _, terminated, truncated, info = self.env.step(self.action(ActionKind.NOOP))

        self.assertTrue(terminated)
        self.assertFalse(truncated)
        self.assertEqual(info["termination_reason"], "game_over")
        self.assertEqual(info["game_episode"]["seed"], 14)
        with self.assertRaisesRegex(RuntimeError, "reset"):
            self.env.step(self.action(ActionKind.NOOP))

    def test_mouse_actions_dispatch_exact_player_event_sequence(self) -> None:
        self.env.reset(seed=15)
        session = self.env._session
        assert session is not None
        down_grid = (17, 23)
        up_grid = (41, 57)
        down_position = map_action_coordinate(*down_grid, FAST_RENDER_PROFILE)
        up_position = map_action_coordinate(*up_grid, FAST_RENDER_PROFILE)

        with patch.object(session, "dispatch", wraps=session.dispatch) as dispatch:
            self.env.step(self.action(ActionKind.DOWN, *down_grid))
            down_events = [call.args[0] for call in dispatch.call_args_list]
            self.assertEqual(
                [event.event_type for event in down_events],
                [MouseEventType.MOUSE_MOTION, MouseEventType.MOUSE_DOWN],
            )
            self.assertEqual(
                [event.position.to_tuple() for event in down_events],
                [down_position, down_position],
            )

            dispatch.reset_mock()
            self.env.step(self.action(ActionKind.DOWN, *down_grid))
            dispatch.assert_not_called()

            self.env.step(self.action(ActionKind.UP, *up_grid))
            up_events = [call.args[0] for call in dispatch.call_args_list]
            self.assertEqual(
                [event.event_type for event in up_events],
                [MouseEventType.MOUSE_MOTION, MouseEventType.MOUSE_UP],
            )
            self.assertEqual(
                [event.position.to_tuple() for event in up_events],
                [up_position, up_position],
            )

    def test_low_level_station_drag_creates_route(self) -> None:
        self.env.close()
        self.env = PlayerPixelEnv(max_episode_steps=50)
        self.env.reset(seed=11)
        station_a, station_b = capture_privileged_snapshot(self.env).station_positions[
            :2
        ]
        a = canonical_to_action_coordinate(
            *station_a,
            FAST_RENDER_PROFILE,
        )
        b = canonical_to_action_coordinate(
            *station_b,
            FAST_RENDER_PROFILE,
        )

        self.env.step(self.action(ActionKind.DOWN, *a))
        self.env.step(self.action(ActionKind.MOTION, *b))
        self.env.step(self.action(ActionKind.UP, *b))

        snapshot = capture_privileged_snapshot(self.env)
        self.assertEqual(snapshot.path_station_indices, ((0, 1),))

    def test_pointer_state_and_cursor_are_observable(self) -> None:
        before, _ = self.env.reset(seed=12)

        pressed, _, _, _, down_info = self.env.step(self.action(ActionKind.DOWN, 0, 0))
        _, _, _, _, duplicate_info = self.env.step(self.action(ActionKind.DOWN, 0, 0))
        _, _, _, _, up_info = self.env.step(self.action(ActionKind.UP, 0, 0))

        self.assertFalse(np.array_equal(before, pressed))
        self.assertTrue(down_info["pointer_down"])
        self.assertTrue(duplicate_info["pointer_down"])
        self.assertFalse(up_info["pointer_down"])

    def test_cursor_pixels_profiles_and_future_content_are_observable(self) -> None:
        before, info = self.env.reset(seed=16)
        frame = self.env.render()
        assert frame is not None
        cursor_x, cursor_y = info["cursor"]
        self.assertEqual(
            tuple(frame[cursor_y, cursor_x]),
            CURSOR_OUTLINE_COLOR,
        )
        self.assertEqual(
            tuple(frame[cursor_y + 12, cursor_x + 8]),
            CURSOR_FILL_COLOR,
        )

        cursor_grid = canonical_to_action_coordinate(
            cursor_x,
            cursor_y,
            FAST_RENDER_PROFILE,
        )
        _, _, _, _, pressed_info = self.env.step(
            self.action(ActionKind.DOWN, *cursor_grid)
        )
        pressed_frame = self.env.render()
        assert pressed_frame is not None
        pressed_x, pressed_y = pressed_info["cursor"]
        self.assertEqual(
            tuple(pressed_frame[pressed_y + 4, pressed_x + 8]),
            CURSOR_PRESSED_MARKER_COLOR,
        )

        mediator = self.env._mediator
        assert mediator is not None
        future_station = mediator.all_stations[len(mediator.stations)]
        future_position = Point(1600, 800)
        future_station.position = future_position
        future_station.shape.position = future_position
        mediator.stations.append(future_station)
        with_future_content = self.env._observe()
        self.assertFalse(np.array_equal(before, with_future_content))

        fidelity = PlayerPixelEnv(
            render_profile=FIDELITY_RENDER_PROFILE,
            max_episode_steps=2,
        )
        self.addCleanup(fidelity.close)
        fidelity_observation, _ = fidelity.reset(seed=16)
        self.assertEqual(fidelity_observation.shape, (3, 180, 320))
        self.assertEqual(tuple(fidelity.action_space.nvec), (8, 320, 180))

    def test_environment_defaults_match_the_versioned_task_spec(self) -> None:
        default_env = PlayerPixelEnv()
        self.addCleanup(default_env.close)

        self.assertEqual(default_env.task_spec, TaskSpec())

    def test_delivery_and_display_score_reward_modes(self) -> None:
        self.env.reset(seed=13)
        mediator = self.env._mediator
        assert mediator is not None
        mediator.total_travels_handled += 3
        mediator.score += 2
        _, reward, _, _, info = self.env.step(self.action(ActionKind.NOOP))
        self.assertEqual(reward, 3.0)
        self.assertNotIn("deliveries_delta", info)
        self.assertNotIn("display_score_delta", info)

        score_env = PlayerPixelEnv(
            reward_mode=RewardMode.DISPLAY_SCORE_DELTA,
            max_episode_steps=5,
        )
        self.addCleanup(score_env.close)
        score_env.reset(seed=13)
        score_mediator = score_env._mediator
        assert score_mediator is not None
        score_mediator.total_travels_handled += 3
        score_mediator.score += 2
        _, score_reward, _, _, _ = score_env.step(self.action(ActionKind.NOOP))
        self.assertEqual(score_reward, 2.0)

    def test_seeded_and_interleaved_environments_are_isolated(self) -> None:
        host_python_state = random.getstate()
        host_numpy_state = np.random.get_state()
        first = PlayerPixelEnv(max_episode_steps=10)
        second = PlayerPixelEnv(max_episode_steps=10)
        reference = PlayerPixelEnv(max_episode_steps=10)
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        self.addCleanup(reference.close)

        first_observation, _ = first.reset(seed=101)
        second.reset(seed=202)
        reference_observation, _ = reference.reset(seed=101)
        self.assertTrue(np.array_equal(first_observation, reference_observation))

        actions = [
            self.action(ActionKind.NOOP),
            self.action(ActionKind.MOTION, 30, 40),
            self.action(ActionKind.NOOP),
        ]
        for action in actions:
            first_step = first.step(action)
            second.step(self.action(ActionKind.NOOP))
            reference_step = reference.step(action)
            self.assertTrue(np.array_equal(first_step[0], reference_step[0]))
            self.assertEqual(first_step[1:], reference_step[1:])

        self.assertEqual(random.getstate(), host_python_state)
        current_numpy_state = np.random.get_state()
        self.assertEqual(current_numpy_state[0], host_numpy_state[0])
        self.assertTrue(np.array_equal(current_numpy_state[1], host_numpy_state[1]))
        self.assertEqual(current_numpy_state[2:], host_numpy_state[2:])

    def test_close_is_idempotent_and_does_not_break_another_environment(self) -> None:
        other = PlayerPixelEnv(max_episode_steps=3)
        self.addCleanup(other.close)
        other.reset(seed=9)
        self.env.reset(seed=8)

        self.env.close()
        self.env.close()
        observation, *_ = other.step(self.action(ActionKind.NOOP))

        self.assertTrue(other.observation_space.contains(observation))


if __name__ == "__main__":
    unittest.main()
