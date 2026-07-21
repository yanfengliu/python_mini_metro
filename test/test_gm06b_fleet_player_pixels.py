from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np
import pygame

import config
from rl.demonstrator import (
    VERIFIED_DELIVERY_MAX_DECISIONS,
    drag_route_actions,
    run_delivery_demonstration,
)
from rl.player_env import PlayerPixelEnv
from rl.privileged_oracle import capture_privileged_snapshot
from rl.protocol import (
    FAST_RENDER_PROFILE,
    FIDELITY_RENDER_PROFILE,
    ActionKind,
    TaskSpec,
    canonical_to_action_coordinate,
    protocol_fingerprint,
    task_fingerprint,
)
from rl.training import TRAINING_SOURCE_PATHS, compute_training_fingerprint
from test.gm06b_fleet_ui_support import action, control_pair, create_path

PROFILES = (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE)
EXPECTED_PROTOCOL = "69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f"
EXPECTED_FAST_TASK = "719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d"
EXPECTED_FIDELITY_TASK = (
    "cd713a6891d8e74dab1aac2ded2edc88a727cb2b5b420948c65731d3a0eb3418"
)
EXPECTED_LF_TRAINING = (
    "f6fa3ad50bb992152ea0f24dff35603e8e906714cf58c5fcc359ede4af54f65c"
)


def _coordinate(value: Any) -> tuple[int, int]:
    if hasattr(value, "to_tuple"):
        value = value.to_tuple()
    if hasattr(value, "left") and hasattr(value, "top"):
        value = (value.left, value.top)
    left, top = value
    return (int(round(left)), int(round(top)))


def _entry_pair(entry: Any) -> tuple[tuple[int, int], tuple[int, int]]:
    if isinstance(entry, dict):
        assign = entry.get("assign", entry.get("plus"))
        unassign = entry.get("unassign", entry.get("minus"))
    elif hasattr(entry, "assign") and hasattr(entry, "unassign"):
        assign, unassign = entry.assign, entry.unassign
    elif hasattr(entry, "plus") and hasattr(entry, "minus"):
        assign, unassign = entry.plus, entry.minus
    else:
        assign, unassign = entry
    return (_coordinate(assign), _coordinate(unassign))


def _snapshot_fleet_coordinates(snapshot: Any) -> tuple[Any, ...]:
    for name in (
        "fleet_control_positions",
        "fleet_button_positions",
        "path_fleet_control_positions",
    ):
        value = getattr(snapshot, name, None)
        if value is not None:
            entries = (
                tuple(value[index] for index in sorted(value))
                if isinstance(value, dict)
                else tuple(value)
            )
            return tuple(_entry_pair(entry) for entry in entries)
    raise AssertionError(
        "PrivilegedSnapshot needs UUID-free path-indexed real FleetButton coordinates"
    )


def _profile_crop(
    frame: np.ndarray,
    center: tuple[int, int],
    profile: Any,
    *,
    half_extent: int = 56,
) -> np.ndarray:
    left, top = canonical_to_action_coordinate(
        max(0, center[0] - half_extent),
        max(0, center[1] - half_extent),
        profile,
    )
    right, bottom = canonical_to_action_coordinate(
        min(config.screen_width - 1, center[0] + half_extent),
        min(config.screen_height - 1, center[1] + half_extent),
        profile,
    )
    return frame[:, top : bottom + 1, left : right + 1].copy()


def _mask_cursor(
    frame: np.ndarray, cursor: tuple[int, int], profile: Any
) -> np.ndarray:
    result = frame.copy()
    left, top = canonical_to_action_coordinate(
        max(0, cursor[0] - 12), max(0, cursor[1] - 12), profile
    )
    right, bottom = canonical_to_action_coordinate(
        min(config.screen_width - 1, cursor[0] + 42),
        min(config.screen_height - 1, cursor[1] + 52),
        profile,
    )
    result[:, max(0, top - 2) : bottom + 3, max(0, left - 2) : right + 3] = 0
    return result


def _hud_digit_crop(frame: np.ndarray, profile: Any) -> np.ndarray:
    if not pygame.font.get_init():
        pygame.font.init()
    font = pygame.font.Font(None, config.hud_font_size)
    prefix = "Locomotives Available: "
    x, y = config.hud_display_coords
    canonical_left = x + font.size(prefix)[0] - 3
    canonical_right = x + max(font.size(prefix + digit)[0] for digit in "01") + 3
    canonical_top = y + 2 * config.hud_line_spacing
    canonical_bottom = canonical_top + font.get_height()
    left = max(0, math.floor(canonical_left * profile.width / config.screen_width) - 2)
    right = min(
        profile.width,
        math.ceil(canonical_right * profile.width / config.screen_width) + 2,
    )
    top = max(0, math.floor(canonical_top * profile.height / config.screen_height) - 2)
    bottom = min(
        profile.height,
        math.ceil(canonical_bottom * profile.height / config.screen_height) + 2,
    )
    return frame[:, top:bottom, left:right].copy()


class TestGM06bPrivilegedFleetCoordinates(unittest.TestCase):
    def test_snapshot_coordinates_are_uuid_free_path_indexed_and_follow_rebinding(
        self,
    ) -> None:
        env = PlayerPixelEnv(max_episode_steps=20)
        self.addCleanup(env.close)
        env.reset(seed=6250)
        mediator = env._mediator
        assert mediator is not None
        mediator.unlocked_num_paths = 3
        mediator.update_path_button_lock_states()
        first = create_path(mediator, [0, 1])
        second = create_path(mediator, [1, 2])
        first_snapshot = capture_privileged_snapshot(env)
        positions = _snapshot_fleet_coordinates(first_snapshot)

        self.assertEqual(len(positions), 2)
        for index, path in enumerate((first, second)):
            assign, unassign = control_pair(mediator, mediator.path_to_button[path])
            self.assertEqual(
                positions[index],
                (_coordinate(assign.position), _coordinate(unassign.position)),
            )
        self.assertNotIn("Path-", repr(positions))
        self.assertNotIn("Metro-", repr(positions))

        old_second = positions[1]
        mediator.remove_path(first)
        rebound = _snapshot_fleet_coordinates(capture_privileged_snapshot(env))
        assign, unassign = control_pair(mediator, mediator.path_to_button[second])
        self.assertEqual(
            rebound,
            ((_coordinate(assign.position), _coordinate(unassign.position)),),
        )
        self.assertNotEqual(rebound[0], old_second)


class TestGM06bFleetPlayerPixels(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_real_fast_and_fidelity_actions_expose_controls_queue_marker_and_refund(
        self,
    ) -> None:
        for profile in PROFILES:
            with self.subTest(profile=profile.name):
                env = PlayerPixelEnv(
                    render_profile=profile,
                    fixed_ticks=1,
                    max_episode_steps=100,
                )
                try:
                    env.reset(seed=6251)
                    for route_action in drag_route_actions(env, (0, 1)):
                        env.step(route_action)
                    mediator = env._mediator
                    assert mediator is not None
                    path = mediator.paths[0]
                    positions = _snapshot_fleet_coordinates(
                        capture_privileged_snapshot(env)
                    )
                    plus, minus = positions[0]
                    plus_grid = canonical_to_action_coordinate(*plus, profile)
                    minus_grid = canonical_to_action_coordinate(*minus, profile)

                    env.step(action(ActionKind.SPACE))
                    away, *_, away_info = env.step(action(ActionKind.MOTION, (0, 0)))
                    plus_hover, *_, plus_hover_info = env.step(
                        action(ActionKind.MOTION, plus_grid)
                    )
                    masked_away = _mask_cursor(away, away_info["cursor"], profile)
                    masked_hover = _mask_cursor(
                        plus_hover, plus_hover_info["cursor"], profile
                    )
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(masked_away, plus, profile),
                            _profile_crop(masked_hover, plus, profile),
                        )
                    )

                    env.step(action(ActionKind.DOWN, plus_grid))
                    env.step(action(ActionKind.UP, plus_grid))
                    ordinary, *_ = env.step(action(ActionKind.MOTION, (0, 0)))
                    self.assertEqual(len(path.metros), 1)
                    metro = path.metros[0]
                    self.assertFalse(metro.is_unassignment_queued)
                    ordinary_marker = _profile_crop(
                        ordinary, _coordinate(metro.position), profile
                    )

                    minus_hover, *_, minus_hover_info = env.step(
                        action(ActionKind.MOTION, minus_grid)
                    )
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(
                                _mask_cursor(ordinary, (0, 0), profile),
                                minus,
                                profile,
                            ),
                            _profile_crop(
                                _mask_cursor(
                                    minus_hover,
                                    minus_hover_info["cursor"],
                                    profile,
                                ),
                                minus,
                                profile,
                            ),
                        )
                    )
                    env.step(action(ActionKind.DOWN, minus_grid))
                    env.step(action(ActionKind.UP, minus_grid))
                    queued, *_ = env.step(action(ActionKind.MOTION, (0, 0)))
                    self.assertTrue(metro.is_unassignment_queued)
                    queued_marker = _profile_crop(
                        queued, _coordinate(metro.position), profile
                    )
                    self.assertFalse(np.array_equal(queued_marker, ordinary_marker))
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(queued, minus, profile),
                            _profile_crop(ordinary, minus, profile),
                        )
                    )

                    for _ in range(3):
                        env.step(action(ActionKind.DOWN, plus_grid))
                        env.step(action(ActionKind.UP, plus_grid))
                    exhausted, *_ = env.step(action(ActionKind.MOTION, (0, 0)))
                    self.assertEqual(mediator.available_locomotives, 0)
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(exhausted, plus, profile),
                            _profile_crop(ordinary, plus, profile),
                        )
                    )

                    candidate = next(
                        item
                        for item in reversed(path.metros)
                        if not item.is_unassignment_queued
                    )
                    station = path.stations[0]
                    candidate.current_station = station
                    candidate.position = station.position
                    before_refund = _hud_digit_crop(exhausted, profile)
                    env.step(action(ActionKind.DOWN, minus_grid))
                    env.step(action(ActionKind.UP, minus_grid))
                    refunded, *_ = env.step(action(ActionKind.MOTION, (0, 0)))
                    self.assertNotIn(candidate, path.metros)
                    self.assertEqual(mediator.available_locomotives, 1)
                    self.assertFalse(
                        np.array_equal(
                            before_refund, _hud_digit_crop(refunded, profile)
                        )
                    )
                finally:
                    env.close()

    def test_player_protocol_info_actions_and_task_identities_remain_exact(
        self,
    ) -> None:
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
        self.assertEqual(protocol_fingerprint(), EXPECTED_PROTOCOL)
        self.assertEqual(task_fingerprint(), EXPECTED_FAST_TASK)
        self.assertEqual(
            task_fingerprint(TaskSpec(render_profile=FIDELITY_RENDER_PROFILE)),
            EXPECTED_FIDELITY_TASK,
        )
        env = PlayerPixelEnv(max_episode_steps=2)
        self.addCleanup(env.close)
        _, info = env.reset(seed=6252)
        self.assertEqual(
            set(info),
            {
                "protocol_fingerprint",
                "task_fingerprint",
                "reward_mode",
                "render_profile",
                "decision",
                "cursor",
                "pointer_down",
                "termination_reason",
            },
        )
        self.assertNotIn("fleet", info)
        self.assertEqual(tuple(env.action_space.nvec), (8, 192, 108))

    def test_canonical_lf_training_sources_retain_exact_fingerprint(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            for relative in TRAINING_SOURCE_PATHS:
                target = checkout / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                # Freeze source identity through one checkout-independent text policy.
                target.write_bytes(
                    (root / relative)
                    .read_bytes()
                    .replace(bytes((13, 10)), bytes((10,)))
                )

            self.assertEqual(
                compute_training_fingerprint(checkout),
                EXPECTED_LF_TRAINING,
            )

            eol_variant = checkout / "src/rl/training.py"
            canonical_bytes = eol_variant.read_bytes()
            self.assertIn(bytes((10,)), canonical_bytes)
            eol_variant.write_bytes(
                canonical_bytes.replace(bytes((10,)), bytes((13, 10)))
            )
            self.assertNotEqual(
                compute_training_fingerprint(checkout),
                EXPECTED_LF_TRAINING,
            )


class TestGM06bDeliveryDemonstrator(unittest.TestCase):
    def test_demonstrator_clicks_real_quantized_plus_then_only_waits(self) -> None:
        env = PlayerPixelEnv(max_episode_steps=VERIFIED_DELIVERY_MAX_DECISIONS)
        self.addCleanup(env.close)
        result = run_delivery_demonstration(env, VERIFIED_DELIVERY_MAX_DECISIONS)
        route_action_count = len(result.metrics["route_station_indices"]) + 1
        kinds = [ActionKind(int(item[0])) for item in result.actions]

        self.assertEqual(
            kinds[route_action_count : route_action_count + 2],
            [ActionKind.DOWN, ActionKind.UP],
        )
        self.assertTrue(
            all(kind is ActionKind.NOOP for kind in kinds[route_action_count + 2 :])
        )
        plus, _ = _snapshot_fleet_coordinates(capture_privileged_snapshot(env))[0]
        expected = canonical_to_action_coordinate(*plus, env.task_spec.render_profile)
        self.assertEqual(
            tuple(int(value) for value in result.actions[route_action_count][1:]),
            expected,
        )
        self.assertEqual(
            tuple(int(value) for value in result.actions[route_action_count + 1][1:]),
            expected,
        )
        self.assertTrue(result.metrics["completed_delivery"])
        self.assertGreaterEqual(result.metrics["deliveries"], 1)
        mediator = env._mediator
        assert mediator is not None
        self.assertGreaterEqual(len(mediator.metros), 1)


if __name__ == "__main__":
    unittest.main()
