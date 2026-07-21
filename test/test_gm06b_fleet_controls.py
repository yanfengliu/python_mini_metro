from __future__ import annotations

import math
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import (
    fleet_button_radius,
    path_button_buy_text_bottom_gap,
    path_handle_quantization_margin,
    screen_height,
    screen_width,
)
from entity.path import Path
from event.type import MouseEventType
from geometry.point import Point
from path_handles import PathEditSelection, build_path_handles_for_state
from rl.protocol import (
    FAST_RENDER_PROFILE,
    FIDELITY_RENDER_PROFILE,
    canonical_to_action_coordinate,
    map_action_coordinate,
)
from test.gm06b_fleet_ui_support import (
    assert_hover_clear,
    control_pair,
    create_path,
    dispatch_mouse,
    empty_point,
    ensure_one_empty_metro,
    fleet_controls,
    fresh_mediator,
    point,
    shape_radius,
)


class TestGM06bFleetControlOwnershipAndLayout(unittest.TestCase):
    def test_controls_retain_only_path_button_ownership_and_follow_rebinding(
        self,
    ) -> None:
        mediator = fresh_mediator(6210)
        first = create_path(mediator, [0, 1])
        second = create_path(mediator, [1, 2])
        first_button = mediator.path_to_button[first]
        second_button = mediator.path_to_button[second]
        original_controls = fleet_controls(mediator)

        for path_button in mediator.path_buttons:
            assign, unassign = control_pair(mediator, path_button)
            self.assertIs(assign.path_button, path_button)
            self.assertIs(unassign.path_button, path_button)
            for control in (assign, unassign):
                self.assertNotIsInstance(control, Path)
                for value in vars(control).values():
                    self.assertNotIsInstance(value, Path)

        mediator.remove_path(first)

        self.assertIs(mediator.path_to_button[second], first_button)
        self.assertIsNot(mediator.path_to_button[second], second_button)
        self.assertEqual(
            tuple(id(control) for control in fleet_controls(mediator)),
            tuple(id(control) for control in original_controls),
        )
        rebound_assign, _ = control_pair(mediator, first_button)
        hook = MagicMock(return_value=True)
        mediator.assign_locomotive = hook

        dispatch_mouse(mediator, MouseEventType.MOUSE_UP, rebound_assign)

        hook.assert_called_once_with(second)

    def test_every_registered_profile_roundtrip_hits_only_the_exact_control(
        self,
    ) -> None:
        mediator = fresh_mediator(6211)
        create_path(mediator)
        controls = fleet_controls(mediator)

        for control in controls:
            parent = control.path_button
            self.assertLess(control.position.top, parent.position.top)
            self.assertTrue(control.contains(point(control)))
            for profile in (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE):
                with self.subTest(control=id(control), profile=profile.name):
                    center = (
                        int(round(control.position.left)),
                        int(round(control.position.top)),
                    )
                    grid = canonical_to_action_coordinate(*center, profile)
                    mapped = Point(*map_action_coordinate(*grid, profile))
                    self.assertTrue(control.contains(mapped))
                    self.assertFalse(parent.contains(mapped))
                    self.assertTrue(
                        all(
                            other is control or not other.contains(mapped)
                            for other in controls
                        )
                    )
                    self.assertTrue(
                        all(
                            not station.contains(mapped)
                            for station in mediator.stations
                        )
                    )

    def test_locked_purchase_text_clears_both_fleet_controls(self) -> None:
        mediator = fresh_mediator(62111)
        locked = next(button for button in mediator.path_buttons if button.is_locked)
        text_bottom = (
            locked.position.top - shape_radius(locked) - path_button_buy_text_bottom_gap
        )

        for control in control_pair(mediator, locked):
            with self.subTest(operation=control.operation):
                self.assertLessEqual(
                    text_bottom,
                    control.position.top - fleet_button_radius,
                )

    def test_station_precedence_and_handle_obstacles_include_fleet_controls(
        self,
    ) -> None:
        mediator = fresh_mediator(6212)
        path = create_path(mediator)
        controls = fleet_controls(mediator)
        target = control_pair(mediator, mediator.path_to_button[path])[0]
        self.assertIs(mediator.get_containing_entity(point(target)), target)

        station = mediator.stations[0]
        station.position = point(target)
        station.shape.position = station.position
        self.assertIs(mediator.get_containing_entity(point(target)), station)

        parent_x = mediator.path_to_button[path].position.left
        control_y = target.position.top
        for route_station, left in zip(
            path.stations,
            (parent_x - 150, parent_x, parent_x + 150),
        ):
            route_station.position = Point(left, control_y - 55)
            route_station.shape.position = route_station.position
        path.update_segments()
        handles = build_path_handles_for_state(
            mediator,
            path,
            viewport_size=(screen_width, screen_height),
        )

        self.assertGreaterEqual(len(handles), 4)
        for handle in handles:
            for control in controls:
                clearance = (
                    handle.hit_radius
                    + shape_radius(control)
                    + path_handle_quantization_margin
                )
                self.assertGreater(
                    math.dist(handle.center, point(control).to_tuple()),
                    clearance,
                )


class TestGM06bFleetReleaseMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.mediator = fresh_mediator(6220)
        self.path = create_path(self.mediator)
        ensure_one_empty_metro(self.mediator, self.path)
        self.path_button = self.mediator.path_to_button[self.path]
        self.assign, self.unassign = control_pair(self.mediator, self.path_button)

    def test_direct_bare_and_cross_control_release_use_release_target(self) -> None:
        assign_hook = MagicMock(return_value=True)
        unassign_hook = MagicMock(return_value=True)
        self.mediator.assign_locomotive = assign_hook
        self.mediator.queue_locomotive_unassignment = unassign_hook

        dispatch_mouse(self.mediator, MouseEventType.MOUSE_DOWN, self.assign)
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, self.assign)
        assign_hook.assert_called_once_with(self.path)
        unassign_hook.assert_not_called()

        assign_hook.reset_mock()
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, self.assign)
        assign_hook.assert_called_once_with(self.path)

        assign_hook.reset_mock()
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_DOWN, self.assign)
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, self.unassign)
        assign_hook.assert_not_called()
        unassign_hook.assert_called_once_with(self.path)
        self.assertFalse(self.mediator.is_mouse_down)

    def test_zero_station_redraw_release_invokes_fleet_target(self) -> None:
        hook = MagicMock(return_value=True)
        self.mediator.assign_locomotive = hook

        dispatch_mouse(self.mediator, MouseEventType.MOUSE_DOWN, self.path_button)
        self.assertIsNotNone(self.mediator.path_redraw)
        self.assertEqual(tuple(self.mediator.path_redraw.stations), ())
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, self.assign)

        hook.assert_called_once_with(self.path)
        self.assertIsNone(self.mediator.path_redraw)
        self.assertIsNone(self.mediator.path_edit_selection)
        self.assertFalse(self.mediator.is_mouse_down)
        assert_hover_clear(self, self.mediator.buttons)

    def test_full_redraw_release_over_control_is_consumed(self) -> None:
        assign_hook = MagicMock(return_value=True)
        unassign_hook = MagicMock(return_value=True)
        self.mediator.assign_locomotive = assign_hook
        self.mediator.queue_locomotive_unassignment = unassign_hook
        original_stations = tuple(self.path.stations)

        dispatch_mouse(self.mediator, MouseEventType.MOUSE_DOWN, self.path_button)
        dispatch_mouse(
            self.mediator,
            MouseEventType.MOUSE_MOTION,
            self.mediator.stations[0],
        )
        self.assertGreater(len(self.mediator.path_redraw.stations), 0)
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, self.assign)

        assign_hook.assert_not_called()
        unassign_hook.assert_not_called()
        self.assertEqual(tuple(self.path.stations), original_stations)
        self.assertIsNone(self.mediator.path_redraw)
        self.assertFalse(self.mediator.is_mouse_down)

    def test_captured_handle_release_over_control_is_consumed(self) -> None:
        assign_hook = MagicMock(return_value=True)
        unassign_hook = MagicMock(return_value=True)
        self.mediator.assign_locomotive = assign_hook
        self.mediator.queue_locomotive_unassignment = unassign_hook

        dispatch_mouse(self.mediator, MouseEventType.MOUSE_DOWN, self.path_button)
        terminal = empty_point(self.mediator)
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_MOTION, terminal)
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, terminal)
        self.assertIsNotNone(self.mediator.path_edit_selection)
        handles = build_path_handles_for_state(
            self.mediator,
            self.path,
            viewport_size=(screen_width, screen_height),
        )
        self.assertGreater(len(handles), 0)
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_DOWN, handles[0].center)
        self.assertIsNotNone(self.mediator.path_redraw)
        self.assertIsNotNone(self.mediator.path_redraw.handle_edit)
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, self.unassign)

        assign_hook.assert_not_called()
        unassign_hook.assert_not_called()
        self.assertIsNone(self.mediator.path_redraw)
        self.assertIsNone(self.mediator.path_edit_selection)
        self.assertFalse(self.mediator.is_mouse_down)

    def test_false_and_raising_facades_always_clear_transient_and_hover_state(
        self,
    ) -> None:
        for name, result in (("false", False), ("raise", RuntimeError("fleet failed"))):
            with self.subTest(name=name):
                self.mediator.path_edit_selection = PathEditSelection(self.path)
                self.mediator.path_redraw = None
                for button in self.mediator.buttons:
                    button.on_hover()
                hook = MagicMock(
                    side_effect=result if isinstance(result, Exception) else None,
                    return_value=result if not isinstance(result, Exception) else None,
                )
                self.mediator.assign_locomotive = hook

                if isinstance(result, Exception):
                    with self.assertRaisesRegex(RuntimeError, "fleet failed"):
                        dispatch_mouse(
                            self.mediator, MouseEventType.MOUSE_UP, self.assign
                        )
                else:
                    dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, self.assign)

                hook.assert_called_once_with(self.path)
                self.assertIsNone(self.mediator.path_redraw)
                self.assertIsNone(self.mediator.path_edit_selection)
                self.assertFalse(self.mediator.is_mouse_down)
                assert_hover_clear(self, self.mediator.buttons)

    def test_manual_and_structured_controls_call_the_same_public_facades(self) -> None:
        assign_hook = MagicMock(return_value=True)
        unassign_hook = MagicMock(return_value=True)
        self.mediator.assign_locomotive = assign_hook
        self.mediator.queue_locomotive_unassignment = unassign_hook

        dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, self.assign)
        self.assertTrue(
            self.mediator.apply_action({"type": "assign_locomotive", "path_index": 0})
        )
        dispatch_mouse(self.mediator, MouseEventType.MOUSE_UP, self.unassign)
        self.assertTrue(
            self.mediator.apply_action({"type": "unassign_locomotive", "path_index": 0})
        )

        self.assertEqual(assign_hook.call_args_list[0].args, (self.path,))
        self.assertEqual(assign_hook.call_args_list[1].args, (self.path,))
        self.assertEqual(unassign_hook.call_args_list[0].args, (self.path,))
        self.assertEqual(unassign_hook.call_args_list[1].args, (self.path,))


if __name__ == "__main__":
    unittest.main()
