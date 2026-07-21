from __future__ import annotations

import math
import os
import sys
import unittest

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import screen_height, screen_width
from geometry.point import Point
from path_handles import build_path_handles_for_state
from rl.player_env import PlayerPixelEnv
from rl.protocol import (
    ACTION_LABELS,
    FAST_RENDER_PROFILE,
    FIDELITY_RENDER_PROFILE,
    ActionKind,
    canonical_to_action_coordinate,
    map_action_coordinate,
)

PROTOCOL_FINGERPRINT = (
    "69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f"
)
TASK_FINGERPRINTS = {
    "fast": "719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d",
    "fidelity": "cd713a6891d8e74dab1aac2ded2edc88a727cb2b5b420948c65731d3a0eb3418",
}
ACTION_IDENTITIES = (
    ("NOOP", 0),
    ("MOTION", 1),
    ("DOWN", 2),
    ("UP", 3),
    ("SPACE", 4),
    ("KEY_1", 5),
    ("KEY_2", 6),
    ("KEY_3", 7),
)


def _canonical_position(value: object) -> tuple[float, float]:
    if hasattr(value, "left") and hasattr(value, "top"):
        return (float(value.left), float(value.top))  # type: ignore[union-attr]
    x, y = value  # type: ignore[misc]
    return (float(x), float(y))


def _grid(value: object, profile) -> tuple[int, int]:
    x, y = _canonical_position(value)
    return canonical_to_action_coordinate(round(x), round(y), profile)


def _action(kind: ActionKind, grid: tuple[int, int]) -> np.ndarray:
    return np.asarray([int(kind), *grid], dtype=np.int64)


def _mask_cursor(
    changed: np.ndarray,
    cursor: tuple[int, int],
    profile,
) -> None:
    cursor_x, cursor_y = cursor
    left, top = canonical_to_action_coordinate(
        max(0, cursor_x - 12),
        max(0, cursor_y - 12),
        profile,
    )
    right, bottom = canonical_to_action_coordinate(
        min(screen_width - 1, cursor_x + 42),
        min(screen_height - 1, cursor_y + 52),
        profile,
    )
    padding = 2
    changed[
        max(0, top - padding) : min(profile.height, bottom + padding + 1),
        max(0, left - padding) : min(profile.width, right + padding + 1),
    ] = False


def _changed_outside_cursors(
    before: np.ndarray,
    after: np.ndarray,
    profile,
    *infos: dict[str, object],
) -> np.ndarray:
    if before.shape != profile.observation_shape or after.shape != before.shape:
        raise AssertionError("comparison must use same-profile CHW observations")
    changed = np.any(before != after, axis=0)
    for info in infos:
        _mask_cursor(changed, info["cursor"], profile)  # type: ignore[arg-type]
    return changed


class TestGM05cPixelEquivalence(unittest.TestCase):
    def _prepared_env(self, profile, seed: int):
        env = PlayerPixelEnv(render_profile=profile)
        self.addCleanup(env.close)
        env.reset(seed=seed)
        mediator = env._mediator
        self.assertIsNotNone(mediator)
        assert mediator is not None
        mediator.stations = mediator.all_stations[:6]
        mediator.unlocked_num_paths = 3
        mediator.update_path_button_lock_states()
        mediator.set_paused(True)
        path = mediator.create_path_from_station_indices([0, 1, 2])
        self.assertIsNotNone(path)
        assert path is not None
        env._observe()
        return env, mediator, path

    def _prepared_pair(self, profile, seed: int):
        return (
            self._prepared_env(profile, seed),
            self._prepared_env(profile, seed),
        )

    @staticmethod
    def _handles(mediator, path) -> tuple[object, ...]:
        return tuple(
            build_path_handles_for_state(
                mediator,
                path,
                viewport_size=(screen_width, screen_height),
            )
        )

    def _handle(self, mediator, path, kind: str):
        matches = [item for item in self._handles(mediator, path) if item.kind == kind]
        self.assertGreater(len(matches), 0)
        return matches[-1]

    def _reachable_empty(self, mediator, profile, avoid=()):
        for action_y in range(8, profile.height - 8, 8):
            for action_x in range(8, profile.width - 8, 8):
                canonical = map_action_coordinate(action_x, action_y, profile)
                point = Point(*canonical)
                if mediator.get_containing_entity(point) is not None:
                    continue
                if any(
                    math.hypot(canonical[0] - center[0], canonical[1] - center[1]) < 160
                    for center in avoid
                ):
                    continue
                return (action_x, action_y), canonical
        raise AssertionError("registered profile has no reachable empty target")

    def assert_step_equal(self, first, second) -> None:
        self.assertTrue(np.array_equal(first[0], second[0]))
        self.assertEqual(first[1:], second[1:])

    def test_registered_profiles_keep_exact_identities_and_reach_every_handle(
        self,
    ) -> None:
        for profile in (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE):
            with self.subTest(profile=profile.name):
                env, mediator, path = self._prepared_env(profile, seed=510)
                handles = self._handles(mediator, path)

                self.assertEqual(env.protocol_fingerprint, PROTOCOL_FINGERPRINT)
                self.assertEqual(env.task_fingerprint, TASK_FINGERPRINTS[profile.name])
                self.assertEqual(
                    [(kind.name, kind.value) for kind in ActionKind],
                    list(ACTION_IDENTITIES),
                )
                self.assertEqual(
                    ACTION_LABELS,
                    ("noop", "motion", "down", "up", "space", "1", "2", "3"),
                )
                self.assertEqual(
                    tuple(env.action_space.nvec),
                    (len(ActionKind), profile.width, profile.height),
                )
                self.assertEqual(env.observation_space.shape, profile.observation_shape)
                self.assertGreaterEqual(len(handles), 4)

                for handle in handles:
                    with self.subTest(kind=handle.kind, slot=handle.slot):
                        center_x, center_y = handle.center
                        action_grid = canonical_to_action_coordinate(
                            round(center_x),
                            round(center_y),
                            profile,
                        )
                        mapped = map_action_coordinate(*action_grid, profile)
                        error = math.hypot(
                            mapped[0] - center_x,
                            mapped[1] - center_y,
                        )
                        self.assertLessEqual(error, handle.hit_radius)
                        self.assertIsNone(
                            mediator.get_containing_entity(Point(*mapped)),
                            "round-tripped handle must remain outside live entities",
                        )

    def test_selected_markers_are_visible_in_actual_chw_step_observation(self) -> None:
        for profile in (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE):
            with self.subTest(profile=profile.name):
                selected, control = self._prepared_pair(profile, seed=511)
                selected_env, selected_mediator, selected_path = selected
                control_env, control_mediator, _ = control
                handle = self._handle(selected_mediator, selected_path, "end")
                handle_center = _canonical_position(handle.center)
                empty_grid, _ = self._reachable_empty(
                    selected_mediator,
                    profile,
                    avoid=(handle_center,),
                )
                button_grid = _grid(
                    selected_mediator.path_to_button[selected_path].position,
                    profile,
                )

                selected_env.step(_action(ActionKind.DOWN, button_grid))
                selected_result = selected_env.step(_action(ActionKind.UP, empty_grid))
                control_env.step(_action(ActionKind.DOWN, empty_grid))
                control_result = control_env.step(_action(ActionKind.UP, empty_grid))

                self.assertIs(
                    selected_mediator.path_edit_selection.path_ref(),
                    selected_path,
                )
                self.assertIsNone(control_mediator.path_edit_selection)
                self.assertEqual(selected_result[1:], control_result[1:])
                changed = _changed_outside_cursors(
                    control_result[0],
                    selected_result[0],
                    profile,
                    selected_result[4],
                )
                self.assertTrue(
                    np.any(changed),
                    "selected handles must survive profile scaling beyond the cursor",
                )
                center_x, center_y = _grid(handle.center, profile)
                radius = max(
                    2,
                    math.ceil(handle.hit_radius * profile.width / screen_width) + 2,
                )
                self.assertTrue(
                    np.any(
                        changed[
                            max(0, center_y - radius) : center_y + radius + 1,
                            max(0, center_x - radius) : center_x + radius + 1,
                        ]
                    ),
                    "the selected marker must remain visible near its canonical center",
                )

    def test_seeded_twins_complete_two_phase_shortening_with_visible_removal(
        self,
    ) -> None:
        for profile in (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE):
            with self.subTest(profile=profile.name):
                first, second = self._prepared_pair(profile, seed=512)
                first_env, first_mediator, first_path = first
                second_env, second_mediator, second_path = second
                first_handle = self._handle(first_mediator, first_path, "end")
                second_handle = self._handle(second_mediator, second_path, "end")
                self.assertEqual(
                    (
                        first_handle.kind,
                        first_handle.slot,
                        first_handle.anchor,
                        first_handle.center,
                        first_handle.hit_radius,
                    ),
                    (
                        second_handle.kind,
                        second_handle.slot,
                        second_handle.anchor,
                        second_handle.center,
                        second_handle.hit_radius,
                    ),
                )
                centers = (_canonical_position(first_handle.center),)
                empty_grid, _ = self._reachable_empty(
                    first_mediator,
                    profile,
                    avoid=centers,
                )
                button_grid = _grid(
                    first_mediator.path_to_button[first_path].position,
                    profile,
                )
                handle_grid = _grid(first_handle.center, profile)
                adjacent_grid = _grid(first_mediator.stations[1].position, profile)
                actions = (
                    _action(ActionKind.DOWN, button_grid),
                    _action(ActionKind.UP, empty_grid),
                    _action(ActionKind.DOWN, handle_grid),
                    _action(ActionKind.MOTION, adjacent_grid),
                    _action(ActionKind.UP, adjacent_grid),
                )
                results = []

                for action in actions:
                    first_result = first_env.step(action)
                    second_result = second_env.step(action)
                    self.assert_step_equal(first_result, second_result)
                    results.append(first_result)

                self.assertIsNone(first_mediator.path_edit_selection)
                self.assertIsNone(first_mediator.path_redraw)
                self.assertFalse(first_mediator.is_mouse_down)
                self.assertEqual(
                    first_path.stations,
                    first_mediator.stations[:2],
                )
                self.assertEqual(
                    second_path.stations,
                    second_mediator.stations[:2],
                )
                down_result = results[2]
                shortening_result = results[3]
                changed = _changed_outside_cursors(
                    down_result[0],
                    shortening_result[0],
                    profile,
                    down_result[4],
                    shortening_result[4],
                )
                edge_grids = (
                    _grid(first_mediator.stations[1].position, profile),
                    _grid(first_mediator.stations[2].position, profile),
                )
                xs = [value[0] for value in edge_grids]
                ys = [value[1] for value in edge_grids]
                padding = 5
                edge_changed = changed[
                    max(0, min(ys) - padding) : min(
                        profile.height, max(ys) + padding + 1
                    ),
                    max(0, min(xs) - padding) : min(
                        profile.width, max(xs) + padding + 1
                    ),
                ]
                self.assertTrue(
                    np.any(edge_changed),
                    "shortening removal feedback must survive in the CHW terminal edge",
                )


if __name__ == "__main__":
    unittest.main()
