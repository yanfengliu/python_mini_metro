from __future__ import annotations

import json
import math
import os
import sys
import unittest
from dataclasses import FrozenInstanceError

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.protocol import (
    ACTION_LABELS,
    CANONICAL_HEIGHT,
    CANONICAL_WIDTH,
    DEFAULT_FIXED_TICKS,
    FAST_RENDER_PROFILE,
    FIDELITY_RENDER_PROFILE,
    ActionKind,
    RenderProfile,
    RewardMode,
    TaskSpec,
    canonical_json,
    canonical_to_action_coordinate,
    map_action_coordinate,
    protocol_descriptor,
    protocol_fingerprint,
    resolve_render_profile,
    task_descriptor,
    task_fingerprint,
    validate_fixed_ticks,
)


class TestActionProtocol(unittest.TestCase):
    def test_action_kind_values_are_append_only_player_event_mapping(self) -> None:
        self.assertEqual(
            [(kind.name, kind.value) for kind in ActionKind],
            [
                ("NOOP", 0),
                ("MOTION", 1),
                ("DOWN", 2),
                ("UP", 3),
                ("SPACE", 4),
                ("KEY_1", 5),
                ("KEY_2", 6),
                ("KEY_3", 7),
            ],
        )
        self.assertEqual(
            ACTION_LABELS,
            ("noop", "motion", "down", "up", "space", "1", "2", "3"),
        )

    def test_render_profiles_are_immutable_and_have_stable_shapes(self) -> None:
        self.assertEqual(FAST_RENDER_PROFILE, RenderProfile("fast", 192, 108))
        self.assertEqual(FIDELITY_RENDER_PROFILE, RenderProfile("fidelity", 320, 180))
        self.assertEqual(FAST_RENDER_PROFILE.observation_shape, (3, 108, 192))
        with self.assertRaises(FrozenInstanceError):
            FAST_RENDER_PROFILE.width = 1  # type: ignore[misc]
        for args in (("", 192, 108), ("bad", 1, 108), ("bad", 192, True)):
            with self.assertRaises((TypeError, ValueError)):
                RenderProfile(*args)  # type: ignore[arg-type]

    def test_coordinate_mapping_is_integer_bounded_and_endpoint_exact(self) -> None:
        self.assertEqual((CANONICAL_WIDTH, CANONICAL_HEIGHT), (1920, 1080))
        self.assertEqual(map_action_coordinate(0, 0, FAST_RENDER_PROFILE), (0, 0))
        self.assertEqual(
            map_action_coordinate(191, 107, FAST_RENDER_PROFILE), (1919, 1079)
        )
        midpoint = map_action_coordinate(96, 54, FAST_RENDER_PROFILE)
        self.assertTrue(0 < midpoint[0] < CANONICAL_WIDTH - 1)
        self.assertTrue(0 < midpoint[1] < CANONICAL_HEIGHT - 1)
        self.assertIsInstance(midpoint[0], int)
        self.assertIsInstance(midpoint[1], int)
        for coordinate in ((-1, 0), (192, 0), (0, 108), (True, 0), (1.0, 0)):
            with self.assertRaises((TypeError, ValueError)):
                map_action_coordinate(*coordinate, FAST_RENDER_PROFILE)  # type: ignore[arg-type]

    def test_inverse_coordinate_mapping_is_nearest_and_round_trips_bins(self) -> None:
        self.assertEqual(
            canonical_to_action_coordinate(0, 0, FAST_RENDER_PROFILE), (0, 0)
        )
        self.assertEqual(
            canonical_to_action_coordinate(1919, 1079, FAST_RENDER_PROFILE),
            (191, 107),
        )
        for action_coordinate in ((0, 0), (1, 1), (96, 54), (191, 107)):
            canonical = map_action_coordinate(*action_coordinate, FAST_RENDER_PROFILE)
            self.assertEqual(
                canonical_to_action_coordinate(*canonical, FAST_RENDER_PROFILE),
                action_coordinate,
            )
        for coordinate in ((-1, 0), (1920, 0), (0, 1080), (True, 0), (1.0, 0)):
            with self.assertRaises((TypeError, ValueError)):
                canonical_to_action_coordinate(*coordinate, FAST_RENDER_PROFILE)  # type: ignore[arg-type]


class TestTaskSpec(unittest.TestCase):
    def test_defaults_and_validators_are_explicit(self) -> None:
        spec = TaskSpec()
        self.assertEqual(spec.render_profile, FAST_RENDER_PROFILE)
        self.assertEqual(spec.fixed_ticks, DEFAULT_FIXED_TICKS)
        self.assertEqual(spec.reward_mode, RewardMode.DELIVERIES)
        self.assertEqual(spec.max_episode_steps, 36_000)
        self.assertEqual(validate_fixed_ticks(1), 1)
        for value in (0, -1, True, 1.5, "6"):
            with self.assertRaises((TypeError, ValueError)):
                validate_fixed_ticks(value)  # type: ignore[arg-type]
        self.assertEqual(
            TaskSpec(reward_mode="display_score_delta").reward_mode,
            RewardMode.DISPLAY_SCORE_DELTA,
        )
        with self.assertRaises(ValueError):
            TaskSpec(reward_mode="unknown")  # type: ignore[arg-type]
        self.assertIs(resolve_render_profile("fast"), FAST_RENDER_PROFILE)
        self.assertIs(
            resolve_render_profile(FIDELITY_RENDER_PROFILE),
            FIDELITY_RENDER_PROFILE,
        )
        for profile in (
            "unknown",
            RenderProfile("custom", 64, 64),
            RenderProfile("fast", 64, 64),
        ):
            with self.assertRaises((TypeError, ValueError)):
                TaskSpec(render_profile=profile)  # type: ignore[arg-type]
        for value in (0, -1, True, 1.5, "36000"):
            with self.assertRaises((TypeError, ValueError)):
                TaskSpec(max_episode_steps=value)  # type: ignore[arg-type]

    def test_task_descriptor_defines_spaces_and_episode_semantics(self) -> None:
        spec = TaskSpec(
            render_profile=FIDELITY_RENDER_PROFILE,
            fixed_ticks=3,
            reward_mode=RewardMode.DISPLAY_SCORE_DELTA,
            max_episode_steps=900,
        )
        descriptor = task_descriptor(spec)

        self.assertEqual(descriptor["action_space"]["nvec"], [8, 320, 180])
        self.assertEqual(descriptor["observation_space"]["shape"], [3, 180, 320])
        self.assertEqual(descriptor["observation_space"]["dtype"], "uint8")
        self.assertEqual(descriptor["observation_space"]["bounds"], [0, 255])
        self.assertEqual(descriptor["observation_space"]["channel_order"], "CHW")
        self.assertEqual(descriptor["fixed_ticks"], 3)
        self.assertEqual(descriptor["reward_mode"], "display_score_delta")
        self.assertEqual(descriptor["episode"]["max_episode_steps"], 900)
        self.assertEqual(descriptor["episode"]["terminated_when"], "game_over")
        self.assertEqual(
            descriptor["episode"]["truncated_when"],
            "configured_horizon_reached_without_game_over",
        )

    def test_protocol_descriptor_records_cursor_and_control_semantics(self) -> None:
        descriptor = protocol_descriptor()

        self.assertEqual(descriptor["canonical_viewport"], [1920, 1080])
        self.assertEqual(
            [entry["label"] for entry in descriptor["actions"]["kinds"]],
            list(ACTION_LABELS),
        )
        self.assertEqual(
            descriptor["actions"]["coordinate_mapping"]["method"],
            "nearest_endpoint_integer",
        )
        cursor = descriptor["cursor"]
        self.assertTrue(cursor["included_in_observation"])
        self.assertEqual(cursor["initial_canonical_position"], [960, 540])
        self.assertEqual(cursor["moves_on"], ["motion", "down", "up"])
        self.assertEqual(cursor["pressed_state"], "down_until_up")
        self.assertEqual(cursor["shape"]["polygon_offsets"][0], [0, 0])
        self.assertEqual(cursor["shape"]["outline_width"], 3)
        self.assertEqual(cursor["pressed_marker"]["radius"], 7)
        self.assertEqual(
            cursor["composite_order"],
            "after_game_frame_before_profile_resize",
        )
        transition = descriptor["transition"]
        self.assertEqual(
            transition["action_order"],
            "pointer_motion_if_changed_then_action_event_then_fixed_ticks",
        )
        self.assertEqual(transition["max_raw_events_per_action"], 2)
        self.assertEqual(
            descriptor["info"]["policy_boundary"],
            "pixels_only_info_contains_no_live_game_state",
        )
        self.assertEqual(
            descriptor["info"]["terminal_metrics_available"],
            "after_last_action_only",
        )


class TestProtocolFingerprints(unittest.TestCase):
    def test_canonical_json_is_compact_sorted_and_rejects_non_finite_values(
        self,
    ) -> None:
        first = canonical_json({"z": 1, "a": {"y": 2, "x": 3}})
        second = canonical_json({"a": {"x": 3, "y": 2}, "z": 1})
        self.assertEqual(first, second)
        self.assertEqual(first, '{"a":{"x":3,"y":2},"z":1}')
        self.assertEqual(json.loads(first), {"a": {"x": 3, "y": 2}, "z": 1})
        with self.assertRaises(ValueError):
            canonical_json({"bad": math.nan})

    def test_protocol_and_task_fingerprints_are_stable_and_sensitive(self) -> None:
        protocol_hash = protocol_fingerprint()
        default_hash = task_fingerprint(TaskSpec())
        self.assertRegex(protocol_hash, r"^[0-9a-f]{64}$")
        self.assertRegex(default_hash, r"^[0-9a-f]{64}$")
        self.assertEqual(protocol_hash, protocol_fingerprint())
        self.assertEqual(default_hash, task_fingerprint(TaskSpec()))
        self.assertNotEqual(
            default_hash,
            task_fingerprint(TaskSpec(render_profile=FIDELITY_RENDER_PROFILE)),
        )
        self.assertNotEqual(default_hash, task_fingerprint(TaskSpec(fixed_ticks=3)))
        self.assertNotEqual(
            default_hash,
            task_fingerprint(TaskSpec(reward_mode=RewardMode.DISPLAY_SCORE_DELTA)),
        )
        self.assertNotEqual(
            default_hash,
            task_fingerprint(TaskSpec(max_episode_steps=10_000)),
        )


if __name__ == "__main__":
    unittest.main()
