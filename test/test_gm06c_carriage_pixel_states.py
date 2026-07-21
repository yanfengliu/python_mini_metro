from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np

import config
from geometry.point import Point
from rendering.layout import build_visual_path, project_metro_pose
from rl.demonstrator import drag_route_actions
from rl.player_env import PlayerPixelEnv
from rl.privileged_oracle import capture_privileged_snapshot
from rl.protocol import (
    FAST_RENDER_PROFILE,
    FIDELITY_RENDER_PROFILE,
    ActionKind,
    canonical_to_action_coordinate,
)
from test.gm06c_simulation_ui_support import action, carriage_spacing, product_symbol
from test.test_gm06c_carriage_pixels import (
    _click,
    _control_pairs,
    _hud_crop,
    _mask_pointer,
    _mask_pointers,
    _profile_crop,
)

PROFILES = (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE)


def _control_crop(frame, center, cursor, profile):
    return _profile_crop(
        _mask_pointer(frame, cursor, profile),
        center,
        profile,
        half_extent=32,
    )


def _exclusive_body_crop(frame, center, all_centers, profile):
    pixel_centers = tuple(
        canonical_to_action_coordinate(
            round(candidate[0]),
            round(candidate[1]),
            profile,
        )
        for candidate in all_centers
    )
    target = canonical_to_action_coordinate(
        round(center[0]),
        round(center[1]),
        profile,
    )
    others = tuple(candidate for candidate in pixel_centers if candidate != target)
    nearest = min(
        (math.dist(target, candidate) for candidate in others),
        default=12.0,
    )
    half_extent = max(2, int(nearest / 2))
    left = max(0, target[0] - half_extent)
    right = min(profile.width - 1, target[0] + half_extent)
    top = max(0, target[1] - half_extent)
    bottom = min(profile.height - 1, target[1] + half_extent)
    result = frame[:, top : bottom + 1, left : right + 1].copy()
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            target_distance = (x - target[0]) ** 2 + (y - target[1]) ** 2
            if any(
                target_distance >= (x - other[0]) ** 2 + (y - other[1]) ** 2
                for other in others
            ):
                result[:, y - top, x - left] = 0
    return result


class TestGM06cCarriageMinusAndQueuePixels(unittest.TestCase):
    def test_minus_disabled_enabled_hover_and_queued_disable_are_visible(self) -> None:
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
                    _click(env, locomotive[0], profile)
                    disabled, *_, disabled_info = env.step(
                        action(ActionKind.MOTION, (0, 0))
                    )

                    enabled, *_, enabled_info = _click(env, carriage[0], profile)

                    self.assertFalse(
                        np.array_equal(
                            _control_crop(
                                disabled,
                                carriage[1],
                                disabled_info["cursor"],
                                profile,
                            ),
                            _control_crop(
                                enabled,
                                carriage[1],
                                enabled_info["cursor"],
                                profile,
                            ),
                        )
                    )

                    hover, *_, hover_info = env.step(
                        action(
                            ActionKind.MOTION,
                            canonical_to_action_coordinate(*carriage[1], profile),
                        )
                    )
                    shared_cursors = (
                        enabled_info["cursor"],
                        hover_info["cursor"],
                    )
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(
                                _mask_pointers(enabled, shared_cursors, profile),
                                carriage[1],
                                profile,
                                half_extent=32,
                            ),
                            _profile_crop(
                                _mask_pointers(hover, shared_cursors, profile),
                                carriage[1],
                                profile,
                                half_extent=32,
                            ),
                        )
                    )

                    mediator = env._mediator
                    assert mediator is not None
                    path = mediator.paths[0]
                    metro = path.metros[0]
                    segment = metro.current_segment
                    metro.current_station = None
                    metro.position = Point(
                        (segment.segment_start.left + segment.segment_end.left) / 2,
                        (segment.segment_start.top + segment.segment_end.top) / 2,
                    )
                    ordinary, *_, ordinary_info = env.step(
                        action(ActionKind.MOTION, (0, 0))
                    )
                    visual = build_visual_path(
                        path,
                        float(path.path_order),
                        config.path_order_shift,
                    )
                    head = project_metro_pose(path, metro, visual)
                    layout = product_symbol(
                        self,
                        "rendering.consist_layout",
                        "consist_layout",
                    )
                    tails = layout(visual, head, 1, carriage_spacing(self))
                    body_centers = (head.position, tails[0].position)
                    queued, *_, queued_info = _click(env, locomotive[1], profile)
                    self.assertTrue(metro.is_unassignment_queued)
                    self.assertEqual(len(metro.carriages), 1)
                    queued_snapshot = capture_privileged_snapshot(env)
                    self.assertEqual(queued_snapshot.carriages_assigned, 1)
                    self.assertEqual(queued_snapshot.carriages_available, 1)

                    body_cursors = (
                        ordinary_info["cursor"],
                        queued_info["cursor"],
                    )
                    profile_centers = tuple(
                        canonical_to_action_coordinate(
                            round(center[0]),
                            round(center[1]),
                            profile,
                        )
                        for center in body_centers
                    )
                    self.assertEqual(len(set(profile_centers)), len(body_centers))
                    ordinary_bodies = _mask_pointers(
                        ordinary,
                        body_cursors,
                        profile,
                    )
                    queued_bodies = _mask_pointers(
                        queued,
                        body_cursors,
                        profile,
                    )
                    for center in body_centers:
                        canonical_center = tuple(round(value) for value in center)
                        with self.subTest(
                            profile=profile.name,
                            body=canonical_center,
                        ):
                            self.assertFalse(
                                np.array_equal(
                                    _exclusive_body_crop(
                                        ordinary_bodies,
                                        center,
                                        body_centers,
                                        profile,
                                    ),
                                    _exclusive_body_crop(
                                        queued_bodies,
                                        center,
                                        body_centers,
                                        profile,
                                    ),
                                )
                            )

                    for center in carriage:
                        with self.subTest(profile=profile.name, center=center):
                            self.assertFalse(
                                np.array_equal(
                                    _control_crop(
                                        enabled,
                                        center,
                                        enabled_info["cursor"],
                                        profile,
                                    ),
                                    _control_crop(
                                        queued,
                                        center,
                                        queued_info["cursor"],
                                        profile,
                                    ),
                                )
                            )

                    before = (
                        tuple(metro.carriages),
                        queued_snapshot.carriages_assigned,
                        queued_snapshot.carriages_available,
                    )
                    _click(env, carriage[0], profile)
                    _click(env, carriage[1], profile)
                    after_snapshot = capture_privileged_snapshot(env)
                    self.assertEqual(
                        (
                            tuple(metro.carriages),
                            after_snapshot.carriages_assigned,
                            after_snapshot.carriages_available,
                        ),
                        before,
                    )
                finally:
                    env.close()

    def test_zero_hud_distinct_glyphs_and_profile_caches_are_observable(self) -> None:
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
                    _click(env, locomotive[0], profile)
                    one, *_, one_info = _click(env, carriage[0], profile)
                    one_snapshot = capture_privileged_snapshot(env)
                    self.assertEqual(one_snapshot.carriages_available, 1)

                    glyph_frame = _mask_pointer(one, one_info["cursor"], profile)
                    self.assertFalse(
                        np.array_equal(
                            _profile_crop(
                                glyph_frame,
                                carriage[0],
                                profile,
                                half_extent=10,
                            ),
                            _profile_crop(
                                glyph_frame,
                                carriage[1],
                                profile,
                                half_extent=10,
                            ),
                        )
                    )

                    zero, *_, zero_info = _click(env, carriage[0], profile)
                    zero_snapshot = capture_privileged_snapshot(env)
                    self.assertEqual(zero_snapshot.carriages_available, 0)
                    hud_cursors = (one_info["cursor"], zero_info["cursor"])
                    self.assertFalse(
                        np.array_equal(
                            _hud_crop(
                                _mask_pointers(one, hud_cursors, profile),
                                profile,
                            ),
                            _hud_crop(
                                _mask_pointers(zero, hud_cursors, profile),
                                profile,
                            ),
                        )
                    )

                    renderer = env._renderer
                    mediator = env._mediator
                    assert renderer is not None
                    assert mediator is not None
                    network = renderer.network_renderer
                    before = (
                        network.cache_entry_count,
                        network.cache_rebuild_count,
                        tuple(network._cache_layouts),
                        network.preview_cache_entry_count,
                        network.preview_cache_rebuild_count,
                        network._preview_cache_layout,
                        renderer.resources.font_count,
                        tuple(renderer.interpolator._previous.items()),
                        tuple(renderer.interpolator._current.items()),
                    )
                    env.step(action(ActionKind.MOTION, (0, 0)))
                    env.step(action(ActionKind.MOTION, (0, 0)))
                    after = (
                        network.cache_entry_count,
                        network.cache_rebuild_count,
                        tuple(network._cache_layouts),
                        network.preview_cache_entry_count,
                        network.preview_cache_rebuild_count,
                        network._preview_cache_layout,
                        renderer.resources.font_count,
                        tuple(renderer.interpolator._previous.items()),
                        tuple(renderer.interpolator._current.items()),
                    )
                    self.assertEqual(after, before)
                    self.assertLessEqual(
                        network.cache_entry_count,
                        int(bool(mediator.paths)),
                    )
                    self.assertLessEqual(
                        len(network._cache_layouts),
                        len(mediator.paths),
                    )
                    self.assertLessEqual(
                        network.preview_cache_entry_count,
                        int(mediator.path_redraw is not None),
                    )
                    self.assertLessEqual(
                        int(network._preview_cache_layout is not None),
                        int(mediator.path_redraw is not None),
                    )
                    self.assertLessEqual(
                        len(renderer.interpolator._current),
                        len(mediator.metros),
                    )
                    self.assertLessEqual(
                        len(renderer.interpolator._previous),
                        len(mediator.metros),
                    )
                finally:
                    env.close()


if __name__ == "__main__":
    unittest.main()
