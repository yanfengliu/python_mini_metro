from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from entity.path import Path
from event.type import MouseEventType
from test.gm06b_fleet_ui_support import create_path, fresh_mediator
from test.gm06c_render_state_support import render_state_signature
from test.gm06c_simulation_ui_support import (
    control_group,
    dispatch_mouse,
    require_attribute,
    resource_controls,
    shape_radius,
)


def _assert_input_clear(testcase: unittest.TestCase, mediator) -> None:
    testcase.assertFalse(mediator.is_mouse_down)
    testcase.assertIsNone(mediator.path_redraw)
    testcase.assertIsNone(mediator.path_edit_selection)
    for button in mediator.buttons:
        if hasattr(button, "is_hovered"):
            testcase.assertFalse(button.is_hovered)
        if hasattr(button, "show_cross"):
            testcase.assertFalse(button.show_cross)


class TestGM06cCarriageControlOwnership(unittest.TestCase):
    def test_controls_retain_only_stable_path_button_and_follow_rebinding(self) -> None:
        mediator = fresh_mediator(6390)
        mediator.unlocked_num_paths = len(mediator.path_buttons)
        mediator.update_path_button_lock_states()
        first = create_path(mediator, [0, 1])
        second = create_path(mediator, [1, 2])
        first_button = mediator.path_to_button[first]
        second_button = mediator.path_to_button[second]
        original_controls = tuple(resource_controls(mediator))

        for path_button in mediator.path_buttons:
            group = control_group(mediator, path_button)
            for operation in ("attach_carriage", "detach_carriage"):
                control = group[operation]
                self.assertIs(control.path_button, path_button)
                self.assertFalse(hasattr(control, "path"))
                self.assertNotIsInstance(control, Path)
                for value in vars(control).values():
                    self.assertNotIsInstance(value, Path)

        mediator.remove_path(first)

        self.assertIs(mediator.path_to_button[second], first_button)
        self.assertIsNot(mediator.path_to_button[second], second_button)
        self.assertEqual(
            tuple(id(control) for control in resource_controls(mediator)),
            tuple(id(control) for control in original_controls),
        )
        rebound_attach = control_group(mediator, first_button)["attach_carriage"]
        calls = []
        mediator.attach_carriage = lambda selected: calls.append(selected) or True

        dispatch_mouse(mediator, MouseEventType.MOUSE_UP, rebound_attach)

        self.assertEqual(calls, [second])
        _assert_input_clear(self, mediator)

    def test_detach_false_and_raise_are_consumed_with_finally_cleanup(self) -> None:
        mediator = fresh_mediator(6391)
        path = create_path(mediator)
        detach = control_group(mediator, mediator.path_to_button[path])[
            "detach_carriage"
        ]
        calls = []
        mediator.detach_carriage = lambda selected: calls.append(selected) or False
        for button in mediator.buttons:
            if hasattr(button, "is_hovered"):
                button.is_hovered = True

        dispatch_mouse(mediator, MouseEventType.MOUSE_DOWN, detach)
        dispatch_mouse(mediator, MouseEventType.MOUSE_UP, detach)

        self.assertEqual(calls, [path])
        _assert_input_clear(self, mediator)

        def raising(_selected):
            raise RuntimeError("detach failed")

        mediator.detach_carriage = raising
        for button in mediator.buttons:
            if hasattr(button, "is_hovered"):
                button.is_hovered = True
        dispatch_mouse(mediator, MouseEventType.MOUSE_DOWN, detach)
        with self.assertRaisesRegex(RuntimeError, "detach failed"):
            dispatch_mouse(mediator, MouseEventType.MOUSE_UP, detach)
        _assert_input_clear(self, mediator)

    def test_queued_consist_disables_both_carriage_controls_and_mutation(self) -> None:
        mediator = fresh_mediator(6392)
        path = create_path(mediator)
        self.assertTrue(mediator.assign_locomotive(path))
        attach = require_attribute(self, mediator, "attach_carriage")
        can_attach = require_attribute(self, mediator, "can_attach_carriage")
        can_detach = require_attribute(self, mediator, "can_detach_carriage")
        self.assertTrue(attach(path))
        metro = path.metros[0]
        before = (
            tuple(metro.carriages),
            mediator.assigned_carriages,
            mediator.available_carriages,
        )
        metro.is_unassignment_queued = True
        group = control_group(mediator, mediator.path_to_button[path])

        self.assertFalse(can_attach(path))
        self.assertFalse(can_detach(path))
        for operation in ("attach_carriage", "detach_carriage"):
            control = group[operation]
            enabled = getattr(control, "_is_enabled", None)
            self.assertTrue(callable(enabled))
            self.assertFalse(enabled(mediator, path))
            dispatch_mouse(mediator, MouseEventType.MOUSE_UP, control)

        self.assertEqual(
            (
                tuple(metro.carriages),
                mediator.assigned_carriages,
                mediator.available_carriages,
            ),
            before,
        )


class TestGM06cControlBandBoundaries(unittest.TestCase):
    def test_canonical_surface_satisfies_full_reserved_band_inequalities(self) -> None:
        mediator = fresh_mediator(6393)
        mediator.prepare_layout(config.screen_width, config.screen_height)
        station_safe_bottom = (
            config.screen_height * 0.9
            + config.station_size
            + config.path_handle_quantization_margin
        )

        for control in resource_controls(mediator):
            self.assertGreater(
                control.position.top - shape_radius(control),
                station_safe_bottom,
            )
            self.assertLessEqual(
                control.position.top + shape_radius(control),
                config.screen_height,
            )

    def test_unsatisfiable_supported_surface_fails_atomically(self) -> None:
        mediator = fresh_mediator(6394)
        before = render_state_signature(mediator)

        with self.assertRaises(ValueError):
            mediator.prepare_layout(800, 600)

        self.assertEqual(render_state_signature(mediator), before)


if __name__ == "__main__":
    unittest.main()
