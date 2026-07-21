from __future__ import annotations

import os
import sys
import unittest
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
    canonical_to_action_coordinate,
)
from test.gm06c_simulation_ui_support import action, require_attribute

PROFILES = (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE)
EXPECTED_INFO_KEYS = {
    "protocol_fingerprint",
    "task_fingerprint",
    "reward_mode",
    "render_profile",
    "decision",
    "cursor",
    "pointer_down",
    "termination_reason",
}


def _coordinate(value: Any) -> tuple[int, int]:
    if hasattr(value, "to_tuple"):
        value = value.to_tuple()
    if hasattr(value, "left") and hasattr(value, "top"):
        value = (value.left, value.top)
    left, top = value
    return (int(round(float(left))), int(round(float(top))))


def _pair(entry: Any, first: str, second: str):
    if isinstance(entry, dict):
        left = entry.get(first, entry.get("plus"))
        right = entry.get(second, entry.get("minus"))
    elif hasattr(entry, first) and hasattr(entry, second):
        left, right = getattr(entry, first), getattr(entry, second)
    elif hasattr(entry, "plus") and hasattr(entry, "minus"):
        left, right = entry.plus, entry.minus
    else:
        left, right = entry
    return (_coordinate(left), _coordinate(right))


def _control_pairs(snapshot: Any, field: str, first: str, second: str):
    entries = require_attribute(_AssertionProxy(), snapshot, field)
    if isinstance(entries, dict):
        entries = tuple(entries[index] for index in sorted(entries))
    return tuple(_pair(entry, first, second) for entry in entries)


class _AssertionProxy:
    """Tiny assertion adapter for helper use outside a TestCase instance."""

    @staticmethod
    def assertTrue(value, message):
        if not value:
            raise AssertionError(message)

    @staticmethod
    def assertIsNotNone(value, message):
        if value is None:
            raise AssertionError(message)


def _profile_crop(
    frame: np.ndarray,
    center: tuple[int, int],
    profile: Any,
    *,
    half_extent: int,
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


def _hud_crop(frame: np.ndarray, profile: Any) -> np.ndarray:
    canonical_center = (420, 110)
    return _profile_crop(
        frame,
        canonical_center,
        profile,
        half_extent=230,
    )


def _mask_pointer(frame: np.ndarray, cursor: tuple[int, int], profile: Any):
    return _mask_pointers(frame, (cursor,), profile)


def _mask_pointers(
    frame: np.ndarray,
    cursors: tuple[tuple[int, int], ...],
    profile: Any,
):
    result = frame.copy()
    for cursor in cursors:
        left, top = canonical_to_action_coordinate(
            max(0, cursor[0] - 2),
            max(0, cursor[1] - 2),
            profile,
        )
        right, bottom = canonical_to_action_coordinate(
            min(config.screen_width - 1, cursor[0] + 32),
            min(config.screen_height - 1, cursor[1] + 42),
            profile,
        )
        result[:, top : bottom + 1, left : right + 1] = 0
    return result


def _all_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _all_strings(key)
            yield from _all_strings(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _all_strings(item)


def _click(env: PlayerPixelEnv, center: tuple[int, int], profile: Any):
    grid = canonical_to_action_coordinate(*center, profile)
    env.step(action(ActionKind.DOWN, grid))
    env.step(action(ActionKind.UP, grid))
    return env.step(action(ActionKind.MOTION, (0, 0)))


class TestGM06cPrivilegedCarriageFields(unittest.TestCase):
    def test_snapshot_preserves_locomotive_pairs_and_adds_uuid_free_carriage_state(
        self,
    ) -> None:
        env = PlayerPixelEnv(fixed_ticks=1, max_episode_steps=30)
        self.addCleanup(env.close)
        _frame, info = env.reset(seed=6360)
        self.assertEqual(set(info), EXPECTED_INFO_KEYS)
        self.assertEqual(
            tuple(env.action_space.nvec),
            (len(ActionKind), FAST_RENDER_PROFILE.width, FAST_RENDER_PROFILE.height),
        )
        initial = capture_privileged_snapshot(env)
        self.assertEqual(require_attribute(self, initial, "carriages_total"), 2)
        self.assertEqual(require_attribute(self, initial, "carriages_assigned"), 0)
        self.assertEqual(require_attribute(self, initial, "carriages_available"), 2)

        for route_action in drag_route_actions(env, (0, 1)):
            env.step(route_action)
        routed = capture_privileged_snapshot(env)
        locomotive = _control_pairs(
            routed,
            "fleet_control_positions",
            "assign",
            "unassign",
        )
        carriages = _control_pairs(
            routed,
            "carriage_control_positions",
            "attach",
            "detach",
        )

        self.assertEqual(len(locomotive), 1)
        self.assertEqual(len(carriages), 1)
        self.assertNotEqual(locomotive, carriages)
        raw_controls = (
            routed.fleet_control_positions,
            routed.carriage_control_positions,
        )
        strings = tuple(_all_strings(raw_controls))
        for prefix in ("Path-", "Metro-", "Carriage-"):
            self.assertFalse(
                any(prefix in value for value in strings),
                f"privileged control coordinate keys/values leaked {prefix}",
            )

        profile = env.task_spec.render_profile
        _click(env, locomotive[0][0], profile)
        _click(env, carriages[0][0], profile)
        attached = capture_privileged_snapshot(env)

        self.assertEqual(require_attribute(self, attached, "carriages_total"), 2)
        self.assertEqual(require_attribute(self, attached, "carriages_assigned"), 1)
        self.assertEqual(require_attribute(self, attached, "carriages_available"), 1)
        mediator = env._mediator
        assert mediator is not None
        self.assertEqual(len(mediator.paths[0].metros[0].carriages), 1)


class TestGM06cCarriagePlayerPixels(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_fast_and_fidelity_pixels_cover_control_states_hud_and_live_bodies(
        self,
    ) -> None:
        for profile in PROFILES:
            with self.subTest(profile=profile.name):
                env = PlayerPixelEnv(
                    render_profile=profile,
                    fixed_ticks=1,
                    max_episode_steps=80,
                )
                try:
                    env.reset(seed=117)
                    for route_action in drag_route_actions(env, (0, 1)):
                        env.step(route_action)
                    env.step(action(ActionKind.SPACE))
                    snapshot = capture_privileged_snapshot(env)
                    locomotive = _control_pairs(
                        snapshot,
                        "fleet_control_positions",
                        "assign",
                        "unassign",
                    )[0]
                    carriage = _control_pairs(
                        snapshot,
                        "carriage_control_positions",
                        "attach",
                        "detach",
                    )[0]
                    station_center = snapshot.station_positions[0]

                    disabled, *_, disabled_info = env.step(
                        action(ActionKind.MOTION, (0, 0))
                    )
                    assigned, *_, assigned_info = _click(env, locomotive[0], profile)
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(
                                _mask_pointer(
                                    disabled,
                                    disabled_info["cursor"],
                                    profile,
                                ),
                                carriage[0],
                                profile,
                                half_extent=32,
                            ),
                            _profile_crop(
                                _mask_pointer(
                                    assigned,
                                    assigned_info["cursor"],
                                    profile,
                                ),
                                carriage[0],
                                profile,
                                half_extent=32,
                            ),
                        )
                    )

                    hover, *_, hover_info = env.step(
                        action(
                            ActionKind.MOTION,
                            canonical_to_action_coordinate(*carriage[0], profile),
                        )
                    )
                    shared_cursors = (
                        assigned_info["cursor"],
                        hover_info["cursor"],
                    )
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(
                                _mask_pointers(
                                    assigned,
                                    shared_cursors,
                                    profile,
                                ),
                                carriage[0],
                                profile,
                                half_extent=32,
                            ),
                            _profile_crop(
                                _mask_pointers(hover, shared_cursors, profile),
                                carriage[0],
                                profile,
                                half_extent=32,
                            ),
                        )
                    )

                    one, *_, one_info = _click(env, carriage[0], profile)
                    one_snapshot = capture_privileged_snapshot(env)
                    self.assertEqual(one_snapshot.carriages_available, 1)
                    self.assertEqual(one_snapshot.carriages_assigned, 1)
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(
                                assigned,
                                station_center,
                                profile,
                                half_extent=170,
                            ),
                            _profile_crop(
                                one,
                                station_center,
                                profile,
                                half_extent=170,
                            ),
                        )
                    )
                    self.assertFalse(
                        np.array_equal(
                            _hud_crop(assigned, profile), _hud_crop(one, profile)
                        )
                    )

                    zero, *_, zero_info = _click(env, carriage[0], profile)
                    zero_snapshot = capture_privileged_snapshot(env)
                    self.assertEqual(zero_snapshot.carriages_available, 0)
                    self.assertEqual(zero_snapshot.carriages_assigned, 2)
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(
                                _mask_pointer(one, one_info["cursor"], profile),
                                carriage[0],
                                profile,
                                half_extent=32,
                            ),
                            _profile_crop(
                                _mask_pointer(zero, zero_info["cursor"], profile),
                                carriage[0],
                                profile,
                                half_extent=32,
                            ),
                        )
                    )

                    detached, *_ = _click(env, carriage[1], profile)
                    detached_snapshot = capture_privileged_snapshot(env)
                    self.assertEqual(detached_snapshot.carriages_available, 1)
                    self.assertEqual(detached_snapshot.carriages_assigned, 1)
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(
                                zero,
                                station_center,
                                profile,
                                half_extent=170,
                            ),
                            _profile_crop(
                                detached,
                                station_center,
                                profile,
                                half_extent=170,
                            ),
                        )
                    )
                finally:
                    env.close()


class TestGM06cCarriageDemonstrator(unittest.TestCase):
    def test_verified_budget_grows_by_only_two_low_level_decisions(self) -> None:
        self.assertEqual(VERIFIED_DELIVERY_MAX_DECISIONS, 122)

    def test_early_delivery_cannot_bypass_required_carriage_setup(self) -> None:
        env = PlayerPixelEnv(fixed_ticks=320, max_episode_steps=30)
        self.addCleanup(env.close)
        env.reset(seed=0)
        station_count = len(capture_privileged_snapshot(env).station_positions)
        route_count = len(drag_route_actions(env, tuple(range(station_count))))

        result = run_delivery_demonstration(env, route_count + 4)
        snapshot = capture_privileged_snapshot(env)

        self.assertTrue(result.metrics["completed_delivery"])
        self.assertEqual(len(result.actions), route_count + 4)
        self.assertEqual(require_attribute(self, snapshot, "carriages_assigned"), 1)
        self.assertEqual(require_attribute(self, snapshot, "carriages_available"), 1)

    def test_demonstrator_attaches_one_real_carriage_before_noops(self) -> None:
        env = PlayerPixelEnv(fixed_ticks=1, max_episode_steps=30)
        self.addCleanup(env.close)
        env.reset(seed=0)
        station_count = len(capture_privileged_snapshot(env).station_positions)
        route_count = len(drag_route_actions(env, tuple(range(station_count))))
        result = run_delivery_demonstration(env, route_count + 4)
        snapshot = capture_privileged_snapshot(env)
        carriage_pairs = _control_pairs(
            snapshot,
            "carriage_control_positions",
            "attach",
            "detach",
        )
        attach_grid = canonical_to_action_coordinate(
            *carriage_pairs[0][0],
            env.task_spec.render_profile,
        )

        self.assertEqual(
            tuple(result.actions[route_count + 2]),
            (ActionKind.DOWN.value, *attach_grid),
        )
        self.assertEqual(
            tuple(result.actions[route_count + 3]),
            (ActionKind.UP.value, *attach_grid),
        )
        self.assertEqual(require_attribute(self, snapshot, "carriages_assigned"), 1)
        self.assertEqual(require_attribute(self, snapshot, "carriages_available"), 1)
        mediator = env._mediator
        assert mediator is not None
        self.assertEqual(len(mediator.paths), 1)
        self.assertEqual(len(mediator.paths[0].metros), 1)
        self.assertEqual(len(mediator.paths[0].metros[0].carriages), 1)

    def test_verified_delivery_keeps_attachment_and_uses_only_noops_after_setup(
        self,
    ) -> None:
        env = PlayerPixelEnv(max_episode_steps=VERIFIED_DELIVERY_MAX_DECISIONS)
        self.addCleanup(env.close)
        env.reset(seed=0)
        station_count = len(capture_privileged_snapshot(env).station_positions)
        route_count = len(drag_route_actions(env, tuple(range(station_count))))

        result = run_delivery_demonstration(env, VERIFIED_DELIVERY_MAX_DECISIONS)
        snapshot = capture_privileged_snapshot(env)

        self.assertTrue(result.metrics["completed_delivery"])
        self.assertGreaterEqual(result.metrics["deliveries"], 1)
        self.assertEqual(require_attribute(self, snapshot, "carriages_assigned"), 1)
        self.assertEqual(require_attribute(self, snapshot, "carriages_available"), 1)
        for demonstrated in result.actions[route_count + 4 :]:
            self.assertEqual(int(demonstrated[0]), ActionKind.NOOP.value)


if __name__ == "__main__":
    unittest.main()
