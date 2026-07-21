from __future__ import annotations

import os
import sys
import unittest
from contextlib import ExitStack
from dataclasses import replace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import input_coordinator as input_coordinator_module
import mediator as mediator_module
import path_handles as path_handles_module
from config import screen_height, screen_width
from event.convert import convert_pygame_event
from game_session import GameSession
from geometry.point import Point
from mediator import Mediator
from path_handles import build_path_handles_for_state
from path_redraw import PathRedrawGesture


def _position_tuple(position: object) -> tuple[float, float]:
    if hasattr(position, "to_tuple"):
        return tuple(position.to_tuple())  # type: ignore[no-any-return,union-attr]
    return tuple(position)  # type: ignore[arg-type,return-value]


class _InputHarness:
    def __init__(self, seed: int) -> None:
        self.mediator = Mediator(seed=seed)
        self.mediator.stations = self.mediator.all_stations[:8]
        self.mediator.unlocked_num_paths = 3
        self.mediator.update_path_button_lock_states()
        self.session = GameSession(self.mediator)

    def dispatch(self, event_type: int, position: object) -> None:
        attributes: dict[str, object] = {"pos": _position_tuple(position)}
        if event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            attributes["button"] = 1
        event = pygame.event.Event(event_type, attributes)
        converted = convert_pygame_event(event, mouse_position=event.pos)
        self.session.dispatch(converted)

    def create_path(self, indices: list[int], *, loop: bool = False):
        path = self.mediator.create_path_from_station_indices(indices, loop=loop)
        if path is None:
            raise AssertionError(f"could not create test path {indices}, loop={loop}")
        return path

    def empty_point(self) -> Point:
        for y in range(160, screen_height - 160, 80):
            for x in range(160, screen_width - 160, 80):
                point = Point(x, y)
                if self.mediator.get_containing_entity(point) is None:
                    return point
        raise AssertionError("test viewport has no empty point")

    def handles(self, path) -> tuple[object, ...]:
        return tuple(
            build_path_handles_for_state(
                self.mediator,
                path,
                viewport_size=(screen_width, screen_height),
            )
        )

    def handle(self, path, kind: str, slot: int | None = None):
        matches = [
            handle
            for handle in self.handles(path)
            if handle.kind == kind and (slot is None or handle.slot == slot)
        ]
        if len(matches) != 1:
            raise AssertionError(
                f"expected one {kind} handle at slot {slot}, got {matches!r}"
            )
        return matches[0]

    def arm(self, path) -> None:
        button = self.mediator.path_to_button[path]
        self.dispatch(pygame.MOUSEBUTTONDOWN, button.position)

    def selected_path(self):
        selection = self.mediator.path_edit_selection
        return None if selection is None else selection.path_ref()

    def select(
        self,
        path,
        *,
        motions: tuple[object, ...] = (),
        release: object | None = None,
    ) -> Point | object:
        terminal = self.empty_point() if release is None else release
        self.arm(path)
        for position in motions:
            self.dispatch(pygame.MOUSEMOTION, position)
        self.dispatch(pygame.MOUSEMOTION, terminal)
        self.dispatch(pygame.MOUSEBUTTONUP, terminal)
        return terminal

    def begin_handle(self, path, kind: str, slot: int | None = None):
        handle = self.handle(path, kind, slot)
        self.dispatch(pygame.MOUSEMOTION, handle.center)
        self.dispatch(pygame.MOUSEBUTTONDOWN, handle.center)
        return handle

    def release(self, position: object, *, with_motion: bool = True) -> None:
        if with_motion:
            self.dispatch(pygame.MOUSEMOTION, position)
        self.dispatch(pygame.MOUSEBUTTONUP, position)


class TestGM05cHandleInput(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = _InputHarness(2500)

    def reset_harness(self, seed: int = 2500) -> _InputHarness:
        self.harness = _InputHarness(seed)
        return self.harness

    def assert_clear(self, harness: _InputHarness | None = None) -> None:
        h = harness or self.harness
        self.assertFalse(h.mediator.is_mouse_down)
        self.assertIsNone(h.mediator.path_redraw)
        self.assertIsNone(h.mediator.path_edit_selection)
        self.assertTrue(
            all(not button.show_cross for button in h.mediator.path_buttons)
        )
        self.assertTrue(
            all(not button.is_hovered for button in h.mediator.speed_buttons)
        )

    def test_empty_release_selects_exact_path_after_zero_valid_or_invalid_samples(
        self,
    ) -> None:
        for name, indices in (
            ("zero", ()),
            ("valid", (0, 1)),
            ("invalid", (0, 1, 2, 1)),
        ):
            with self.subTest(name=name):
                h = self.reset_harness()
                path = h.create_path([0, 1, 2])
                hook = MagicMock(return_value=True)
                h.mediator.replace_path = hook

                h.select(
                    path,
                    motions=tuple(
                        h.mediator.stations[index].position for index in indices
                    ),
                )

                self.assertIs(h.selected_path(), path)
                self.assertIsNone(h.mediator.path_redraw)
                self.assertFalse(h.mediator.is_mouse_down)
                self.assertGreater(len(h.handles(path)), 0)
                hook.assert_not_called()

    def test_fresh_handle_down_and_release_clear_before_exactly_one_hook(self) -> None:
        h = self.harness
        path = h.create_path([0, 1, 2])
        calls: list[tuple[object, list[int], bool]] = []

        def observe(target, indices, loop):
            self.assertIsNone(h.mediator.path_redraw)
            self.assertIsNone(h.mediator.path_edit_selection)
            self.assertFalse(h.mediator.is_mouse_down)
            self.assertTrue(
                all(not button.show_cross for button in h.mediator.path_buttons)
            )
            self.assertTrue(
                all(not button.is_hovered for button in h.mediator.speed_buttons)
            )
            calls.append((target, indices, loop))
            return True

        hook = MagicMock(side_effect=observe)
        h.mediator.replace_path = hook
        h.select(path)
        handle = h.begin_handle(path, "end")

        self.assertIsNone(h.mediator.path_edit_selection)
        self.assertTrue(h.mediator.is_mouse_down)
        self.assertIsNotNone(h.mediator.path_redraw)
        edit = h.mediator.path_redraw.handle_edit
        self.assertIsNotNone(edit)
        self.assertIs(edit.path, path)
        self.assertEqual(edit.kind, handle.kind)

        h.release(h.mediator.stations[3].position)

        hook.assert_called_once_with(path, [0, 1, 2, 3], False)
        self.assertEqual(calls, [(path, [0, 1, 2, 3], False)])
        self.assert_clear()

    def test_both_endpoint_extensions_and_one_step_shortenings(self) -> None:
        cases = (
            ("start-extend", "start", 3, [3, 0, 1, 2]),
            ("end-extend", "end", 3, [0, 1, 2, 3]),
            ("start-shorten", "start", 1, [1, 2]),
            ("end-shorten", "end", 1, [0, 1]),
        )
        for name, kind, release_index, expected in cases:
            with self.subTest(name=name):
                h = self.reset_harness()
                path = h.create_path([0, 1, 2])
                hook = MagicMock(return_value=True)
                h.mediator.replace_path = hook
                h.select(path)
                h.begin_handle(path, kind)
                h.release(h.mediator.stations[release_index].position)

                hook.assert_called_once_with(path, expected, False)
                self.assert_clear(h)

    def test_linear_and_loop_insertions_use_canonical_slots(self) -> None:
        cases = (
            ("linear", [0, 1, 2], False, 1, 3, [0, 3, 1, 2]),
            ("loop-edge", [0, 1, 2], True, 1, 3, [0, 3, 1, 2]),
            ("loop-close", [0, 1, 2], True, 3, 3, [0, 1, 2, 3]),
            ("two-station-loop", [0, 1], True, 1, 2, [0, 2, 1]),
        )
        for name, source, loop, slot, release_index, expected in cases:
            with self.subTest(name=name):
                h = self.reset_harness()
                path = h.create_path(source, loop=loop)
                inserts = [item for item in h.handles(path) if item.kind == "insert"]
                if name == "two-station-loop":
                    self.assertEqual(len(inserts), 1)
                    self.assertEqual(inserts[0].slot, 1)
                hook = MagicMock(return_value=True)
                h.mediator.replace_path = hook
                h.select(path)
                h.begin_handle(path, "insert", slot)
                h.release(h.mediator.stations[release_index].position)

                hook.assert_called_once_with(path, expected, loop)
                self.assert_clear(h)

    def test_release_event_target_wins_over_last_motion_target(self) -> None:
        h = self.harness
        path = h.create_path([0, 1, 2])
        hook = MagicMock(return_value=True)
        h.mediator.replace_path = hook
        h.select(path)
        h.begin_handle(path, "end")
        h.dispatch(pygame.MOUSEMOTION, h.mediator.stations[3].position)
        h.release(h.mediator.stations[4].position, with_motion=False)

        hook.assert_called_once_with(path, [0, 1, 2, 4], False)
        self.assert_clear()

    def test_invalid_release_targets_cancel(self) -> None:
        for name, target in (
            ("same-route", lambda h: h.mediator.stations[2].position),
            ("offstation", lambda h: h.empty_point()),
            ("offscreen", lambda _h: (-1000, -1000)),
        ):
            with self.subTest(name=name):
                h = self.reset_harness()
                path = h.create_path([0, 1, 2])
                topology = tuple(path.stations)
                hook = MagicMock(return_value=True)
                h.mediator.replace_path = hook
                h.select(path)
                h.begin_handle(path, "start")
                h.release(target(h))

                hook.assert_not_called()
                self.assertEqual(tuple(path.stations), topology)
                self.assert_clear(h)

    def test_button_targets_cancel_without_release_matrix_actions(self) -> None:
        h = self.harness
        path = h.create_path([0, 1, 2])
        assigned = h.mediator.path_to_button[path]
        locked = h.mediator.path_buttons[-1]
        speed = h.mediator.speed_buttons[-1]
        remove = MagicMock()
        purchase = MagicMock(return_value=True)
        apply_speed = MagicMock()
        replace_hook = MagicMock(return_value=True)
        h.mediator.remove_path = remove
        h.mediator.try_purchase_path_button = purchase
        h.mediator.apply_speed_action = apply_speed
        h.mediator.replace_path = replace_hook

        for target in (assigned, locked, speed):
            with self.subTest(target=type(target).__name__):
                h.select(path)
                h.begin_handle(path, "end")
                h.release(target.position)
                self.assert_clear(h)

        remove.assert_not_called()
        purchase.assert_not_called()
        apply_speed.assert_not_called()
        replace_hook.assert_not_called()

    def test_ambiguous_handle_down_is_consumed_before_button_release(self) -> None:
        h = self.harness
        path = h.create_path([0, 1, 2])
        h.select(path)
        descriptor = h.handle(path, "insert", 1)
        remove = MagicMock()
        hook = MagicMock(return_value=True)
        h.mediator.remove_path = remove
        h.mediator.replace_path = hook

        with ExitStack() as stack:
            for module in (
                path_handles_module,
                input_coordinator_module,
                mediator_module,
            ):
                stack.enter_context(
                    patch.object(
                        module,
                        "build_path_handles_for_state",
                        return_value=(descriptor, descriptor),
                        create=True,
                    )
                )
            h.dispatch(pygame.MOUSEMOTION, descriptor.center)
            h.dispatch(pygame.MOUSEBUTTONDOWN, descriptor.center)
            self.assertTrue(h.mediator.is_mouse_down)
            self.assertIsNone(h.mediator.path_edit_selection)
            self.assertIsNotNone(h.mediator.path_redraw)
            h.release(h.mediator.path_to_button[path].position)

        remove.assert_not_called()
        hook.assert_not_called()
        self.assertIn(path, h.mediator.paths)
        self.assert_clear()

    def test_stale_or_malformed_edit_fails_closed(self) -> None:
        for name in ("removed", "mutated", "malformed"):
            with self.subTest(name=name):
                h = self.reset_harness()
                path = h.create_path([0, 1, 2])
                hook = MagicMock(return_value=True)
                h.mediator.replace_path = hook
                h.select(path)
                h.begin_handle(path, "end")
                if name == "removed":
                    h.mediator.paths.remove(path)
                elif name == "mutated":
                    path.stations.append(h.mediator.stations[4])
                    path.update_segments()
                else:
                    h.mediator.path_redraw = replace(
                        h.mediator.path_redraw,
                        handle_edit=object(),
                    )
                h.release(h.mediator.stations[3].position)

                hook.assert_not_called()
                self.assert_clear(h)

    def test_broader_canonical_rejection_still_gets_one_clean_public_call(self) -> None:
        h = self.harness
        path = h.create_path([0, 1, 2])
        malformed_other = h.create_path([4, 5])
        topology = tuple(path.stations)
        original = h.mediator.replace_path
        h.select(path)
        h.begin_handle(path, "end")
        malformed_other.id = ""

        with patch.object(h.mediator, "replace_path", wraps=original) as hook:
            h.release(h.mediator.stations[3].position)

        hook.assert_called_once_with(path, [0, 1, 2, 3], False)
        self.assertEqual(tuple(path.stations), topology)
        self.assert_clear()

    def test_raised_rebound_hook_cannot_restore_transient_references(self) -> None:
        h = self.harness
        path = h.create_path([0, 1, 2])

        def fail(*_args):
            self.assertIsNone(h.mediator.path_redraw)
            self.assertIsNone(h.mediator.path_edit_selection)
            self.assertFalse(h.mediator.is_mouse_down)
            h.mediator.path_redraw = PathRedrawGesture(path)
            h.mediator.path_edit_selection = object()
            h.mediator.is_mouse_down = True
            for button in h.mediator.path_buttons:
                button.show_cross = True
            for button in h.mediator.speed_buttons:
                button.is_hovered = True
            raise RuntimeError("rebound hook failed")

        hook = MagicMock(side_effect=fail)
        h.mediator.replace_path = hook
        h.select(path)
        h.begin_handle(path, "end")

        with self.assertRaisesRegex(RuntimeError, "rebound hook failed"):
            h.release(h.mediator.stations[3].position)

        hook.assert_called_once_with(path, [0, 1, 2, 3], False)
        self.assert_clear()

    def test_full_redraw_and_click_or_bare_release_remain_compatible(self) -> None:
        h = self.harness
        path = h.create_path([0, 1, 2])
        crossing = h.handle(path, "insert", 1)
        hook = MagicMock(return_value=True)
        h.mediator.replace_path = hook

        h.arm(path)
        h.dispatch(pygame.MOUSEMOTION, h.mediator.stations[0].position)
        h.dispatch(pygame.MOUSEMOTION, crossing.center)
        self.assertIsNone(h.mediator.path_redraw.handle_edit)
        h.release(h.mediator.stations[2].position)

        hook.assert_called_once_with(path, [0, 2], False)
        self.assert_clear()

        clicked = h.create_path([1, 2])
        clicked_button = h.mediator.path_to_button[clicked]
        h.dispatch(pygame.MOUSEBUTTONDOWN, clicked_button.position)
        h.dispatch(pygame.MOUSEBUTTONUP, clicked_button.position)
        self.assertNotIn(clicked, h.mediator.paths)

        bare = h.create_path([2, 3])
        h.dispatch(pygame.MOUSEBUTTONUP, h.mediator.path_to_button[bare].position)
        self.assertNotIn(bare, h.mediator.paths)

    def test_dense_station_samples_and_final_jump_select_the_same_path(self) -> None:
        cases = (
            (374, 2, Point(840, 950)),
            (11, 1, Point(840, 850)),
        )
        for seed, crossing_index, terminal in cases:
            with self.subTest(seed=seed):
                dense = _InputHarness(seed)
                jump = _InputHarness(seed)
                dense_path = dense.create_path([0, 2])
                jump_path = jump.create_path([0, 2])
                dense_hook = MagicMock(return_value=True)
                jump_hook = MagicMock(return_value=True)
                dense.mediator.replace_path = dense_hook
                jump.mediator.replace_path = jump_hook
                self.assertIsNone(dense.mediator.get_containing_entity(terminal))

                dense.select(
                    dense_path,
                    motions=(dense.mediator.stations[crossing_index].position,),
                    release=terminal,
                )
                jump.select(jump_path, release=terminal)

                self.assertIs(dense.selected_path(), dense_path)
                self.assertIs(jump.selected_path(), jump_path)
                dense_hook.assert_not_called()
                jump_hook.assert_not_called()

    def test_dense_handle_samples_and_final_jump_select_the_same_path(self) -> None:
        for seed in (0, 43):
            with self.subTest(seed=seed):
                dense = _InputHarness(seed)
                jump = _InputHarness(seed)
                dense_path = dense.create_path([0, 1, 2])
                jump_path = jump.create_path([0, 1, 2])
                crossing = dense.handle(dense_path, "insert", 1)
                terminal = dense.empty_point()
                dense_hook = MagicMock(return_value=True)
                jump_hook = MagicMock(return_value=True)
                dense.mediator.replace_path = dense_hook
                jump.mediator.replace_path = jump_hook

                dense.select(
                    dense_path,
                    motions=(crossing.center,),
                    release=terminal,
                )
                jump.select(jump_path, release=terminal)

                self.assertIs(dense.selected_path(), dense_path)
                self.assertIs(jump.selected_path(), jump_path)
                self.assertIsNone(dense.mediator.path_redraw)
                self.assertIsNone(jump.mediator.path_redraw)
                dense_hook.assert_not_called()
                jump_hook.assert_not_called()


if __name__ == "__main__":
    unittest.main()
