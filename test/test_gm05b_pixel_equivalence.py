from __future__ import annotations

import os
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from rl.player_env import PlayerPixelEnv
from rl.protocol import (
    FAST_RENDER_PROFILE,
    FIDELITY_RENDER_PROFILE,
    ActionKind,
    canonical_to_action_coordinate,
)


class TestGm05bPlayerPixelRedraw(unittest.TestCase):
    @staticmethod
    def action(kind: ActionKind, coordinate: tuple[int, int]) -> np.ndarray:
        return np.asarray([int(kind), *coordinate], dtype=np.int64)

    @staticmethod
    def grid(position, profile) -> tuple[int, int]:
        return canonical_to_action_coordinate(position.left, position.top, profile)

    @staticmethod
    def assert_step_equal(test, first, second) -> None:
        test.assertTrue(np.array_equal(first[0], second[0]))
        test.assertEqual(first[1:], second[1:])

    def _prepared_pair(self, profile):
        first = PlayerPixelEnv(
            render_mode="rgb_array",
            render_profile=profile,
        )
        second = PlayerPixelEnv(
            render_mode="rgb_array",
            render_profile=profile,
        )
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        first.reset(seed=505)
        second.reset(seed=505)
        mediators = (first._mediator, second._mediator)
        self.assertTrue(all(mediator is not None for mediator in mediators))
        first_mediator, second_mediator = mediators
        assert first_mediator is not None
        assert second_mediator is not None
        first_mediator.set_paused(True)
        second_mediator.set_paused(True)
        first_path = first_mediator.create_path_from_station_indices([0, 1, 2])
        second_path = second_mediator.create_path_from_station_indices([0, 1, 2])
        self.assertIsNotNone(first_path)
        self.assertIsNotNone(second_path)
        assert first_path is not None
        assert second_path is not None
        first._observe()
        second._observe()
        return first, second, first_mediator, second_mediator, first_path, second_path

    def test_fast_and_fidelity_gestures_are_visible_deterministic_and_atomic(
        self,
    ) -> None:
        expected_tasks = {
            "fast": "719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d",
            "fidelity": "cd713a6891d8e74dab1aac2ded2edc88a727cb2b5b420948c65731d3a0eb3418",
        }
        protocol = "69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f"

        for profile in (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE):
            with self.subTest(profile=profile.name):
                (
                    first,
                    second,
                    first_mediator,
                    second_mediator,
                    first_path,
                    second_path,
                ) = self._prepared_pair(profile)
                self.assertEqual(first.protocol_fingerprint, protocol)
                self.assertEqual(first.task_fingerprint, expected_tasks[profile.name])
                self.assertEqual(
                    tuple(first.action_space.nvec),
                    (len(ActionKind), profile.width, profile.height),
                )

                first_button = first_mediator.path_to_button[first_path]
                second_button = second_mediator.path_to_button[second_path]
                targets = (2, 0, 1)
                first_positions = [
                    first_button.position,
                    *(first_mediator.stations[index].position for index in targets),
                ]
                second_positions = [
                    second_button.position,
                    *(second_mediator.stations[index].position for index in targets),
                ]
                first_grids = [
                    self.grid(position, profile) for position in first_positions
                ]
                second_grids = [
                    self.grid(position, profile) for position in second_positions
                ]
                self.assertEqual(first_grids, second_grids)

                with ExitStack() as stack:
                    first_hook = stack.enter_context(
                        patch.object(
                            first_mediator,
                            "replace_path",
                            wraps=first_mediator.replace_path,
                        )
                    )
                    second_hook = stack.enter_context(
                        patch.object(
                            second_mediator,
                            "replace_path",
                            wraps=second_mediator.replace_path,
                        )
                    )

                    hover_first = first.step(
                        self.action(ActionKind.MOTION, first_grids[0])
                    )
                    hover_second = second.step(
                        self.action(ActionKind.MOTION, second_grids[0])
                    )
                    self.assert_step_equal(self, hover_first, hover_second)
                    hover_frame = first.render()
                    assert hover_frame is not None

                    down_first = first.step(
                        self.action(ActionKind.DOWN, first_grids[0])
                    )
                    down_second = second.step(
                        self.action(ActionKind.DOWN, second_grids[0])
                    )
                    self.assert_step_equal(self, down_first, down_second)
                    selected_frame = first.render()
                    assert selected_frame is not None
                    self.assertIsNotNone(first_mediator.path_redraw)

                    cursor_x, cursor_y = down_first[4]["cursor"]
                    changed = np.any(hover_frame != selected_frame, axis=2)
                    changed[
                        max(0, cursor_y - 12) : min(changed.shape[0], cursor_y + 52),
                        max(0, cursor_x - 12) : min(changed.shape[1], cursor_x + 42),
                    ] = False
                    self.assertTrue(
                        np.any(changed),
                        "selected-line feedback must extend beyond the cursor footprint",
                    )

                    for index in (1, 2):
                        first_step = first.step(
                            self.action(ActionKind.MOTION, first_grids[index])
                        )
                        second_step = second.step(
                            self.action(ActionKind.MOTION, second_grids[index])
                        )
                        self.assert_step_equal(self, first_step, second_step)

                    preview_frame = first.render()
                    assert preview_frame is not None
                    station_a = first_mediator.stations[targets[0]].position
                    station_b = first_mediator.stations[targets[1]].position
                    midpoint = (
                        round((station_a.left + station_b.left) / 2),
                        round((station_a.top + station_b.top) / 2),
                    )
                    self.assertEqual(
                        tuple(preview_frame[midpoint[1], midpoint[0]]),
                        tuple(int(channel) for channel in first_path.color),
                    )

                    up_first = first.step(self.action(ActionKind.UP, first_grids[3]))
                    up_second = second.step(self.action(ActionKind.UP, second_grids[3]))
                    self.assert_step_equal(self, up_first, up_second)

                first_hook.assert_called_once_with(first_path, [2, 0, 1], False)
                second_hook.assert_called_once_with(second_path, [2, 0, 1], False)
                self.assertIs(first_mediator.paths[0], first_path)
                self.assertIs(second_mediator.paths[0], second_path)
                self.assertEqual(
                    first_path.stations,
                    [
                        first_mediator.stations[2],
                        first_mediator.stations[0],
                        first_mediator.stations[1],
                    ],
                )
                self.assertIsNone(first_mediator.path_redraw)
                self.assertFalse(first_mediator.is_mouse_down)


if __name__ == "__main__":
    unittest.main()
