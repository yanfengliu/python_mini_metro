from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from entity.station import Station
from event.type import MouseEventType
from geometry.circle import Circle
from geometry.point import Point
from path_handle_geometry import build_path_handles_for_state
from rl.protocol import (
    RENDER_PROFILES,
    canonical_to_action_coordinate,
    map_action_coordinate,
)
from test.gm06b_fleet_ui_support import fresh_mediator
from test.gm06c_simulation_ui_support import (
    assert_pairwise_disjoint,
    center_tuple,
    control_group,
    dispatch_mouse,
    point,
    resource_controls,
    shape_radius,
)


def _create_path(mediator, indices=(0, 1)):
    mediator.unlocked_num_paths = len(mediator.path_buttons)
    mediator.update_path_button_lock_states()
    path = mediator.create_path_from_station_indices(list(indices))
    if path is None:
        raise AssertionError("could not construct active route for carriage controls")
    return path


class TestGM06cResourceControlLayout(unittest.TestCase):
    def test_every_stable_slot_has_exact_disjoint_four_control_group(self) -> None:
        mediator = fresh_mediator(seed=117)
        controls = resource_controls(mediator)

        self.assertEqual(len(controls), 4 * len(mediator.path_buttons))
        self.assertEqual(len({id(control) for control in controls}), len(controls))
        for path_button in mediator.path_buttons:
            group = control_group(mediator, path_button)
            self.assertEqual(len(group), 4)
            self.assertTrue(
                all(
                    getattr(control, "path_button", None) is path_button
                    for control in group.values()
                )
            )
        assert_pairwise_disjoint(self, controls)

    def test_bottom_band_has_exact_path_and_resource_rows_clear_of_speed(self) -> None:
        mediator = fresh_mediator(seed=117)
        controls = resource_controls(mediator)

        self.assertEqual(
            {round(button.position.top) for button in mediator.path_buttons},
            {1056},
        )
        self.assertEqual({round(control.position.top) for control in controls}, {1019})
        for control in controls:
            for path_button in mediator.path_buttons:
                locked_text_bottom = (
                    path_button.position.top
                    - shape_radius(path_button)
                    - config.path_button_buy_text_bottom_gap
                )
                self.assertGreater(
                    control.position.top - shape_radius(control),
                    locked_text_bottom,
                )
                self.assertGreater(
                    math.dist(center_tuple(control), center_tuple(path_button)),
                    shape_radius(control) + shape_radius(path_button),
                )
            for speed_button in mediator.speed_buttons:
                self.assertGreater(
                    math.dist(center_tuple(control), center_tuple(speed_button)),
                    shape_radius(control) + shape_radius(speed_button),
                )

    def test_seed_117_profile_roundtrip_hits_exact_controls_and_no_station(
        self,
    ) -> None:
        mediator = fresh_mediator(seed=117)
        controls = resource_controls(mediator)

        for profile in RENDER_PROFILES:
            for control in controls:
                with self.subTest(profile=profile.name, control=repr(control)):
                    center = center_tuple(control)
                    grid = canonical_to_action_coordinate(*center, profile)
                    mapped = map_action_coordinate(*grid, profile)
                    hit = mediator.get_containing_entity(Point(*mapped))
                    self.assertIs(hit, control)
                    self.assertTrue(
                        all(hit is not station for station in mediator.stations)
                    )

    def test_adversarial_maximum_station_center_cannot_steal_quantized_hits(
        self,
    ) -> None:
        mediator = fresh_mediator(seed=117)
        controls = resource_controls(mediator)
        maximum_station_y = round(config.screen_height * 0.9)

        for profile in RENDER_PROFILES:
            for control in controls:
                with self.subTest(profile=profile.name, control=repr(control)):
                    center = center_tuple(control)
                    grid = canonical_to_action_coordinate(*center, profile)
                    mapped = map_action_coordinate(*grid, profile)
                    adversary = Station(
                        Circle(config.station_color, config.station_size),
                        Point(mapped[0], maximum_station_y),
                    )
                    mediator.stations = [adversary]
                    self.assertIs(
                        mediator.get_containing_entity(Point(*mapped)),
                        control,
                    )

    def test_locked_and_unbound_groups_remain_hittable_but_cannot_mutate(self) -> None:
        mediator = fresh_mediator(seed=6340)
        calls = []
        for name in (
            "assign_locomotive",
            "queue_locomotive_unassignment",
            "attach_carriage",
            "detach_carriage",
        ):
            setattr(
                mediator,
                name,
                lambda path, operation=name: calls.append((operation, path)) or True,
            )

        for path_button in mediator.path_buttons:
            self.assertIsNone(path_button.path)
            for control in control_group(mediator, path_button).values():
                self.assertIs(mediator.get_containing_entity(point(control)), control)
                dispatch_mouse(mediator, MouseEventType.MOUSE_DOWN, control)
                dispatch_mouse(mediator, MouseEventType.MOUSE_UP, control)

        self.assertEqual(calls, [])
        self.assertFalse(mediator.is_mouse_down)


class TestGM06cResourceControlInput(unittest.TestCase):
    def test_release_target_matrix_dispatches_each_of_four_operations(self) -> None:
        mediator = fresh_mediator(seed=6341)
        path = _create_path(mediator)
        path_button = mediator.path_to_button[path]
        group = control_group(mediator, path_button)
        facade_by_operation = {
            "assign_locomotive": "assign_locomotive",
            "unassign_locomotive": "queue_locomotive_unassignment",
            "attach_carriage": "attach_carriage",
            "detach_carriage": "detach_carriage",
        }

        for source_name, source in group.items():
            for target_name, target in group.items():
                with self.subTest(source=source_name, target=target_name):
                    calls = []
                    for operation, facade in facade_by_operation.items():
                        setattr(
                            mediator,
                            facade,
                            lambda selected, value=operation: (
                                calls.append((value, selected)) or True
                            ),
                        )
                    dispatch_mouse(mediator, MouseEventType.MOUSE_DOWN, source)
                    dispatch_mouse(mediator, MouseEventType.MOUSE_UP, target)
                    self.assertEqual(calls, [(target_name, path)])
                    self.assertFalse(mediator.is_mouse_down)

    def test_carriage_facade_exception_propagates_and_finally_clears_input(
        self,
    ) -> None:
        mediator = fresh_mediator(seed=6342)
        path = _create_path(mediator)
        group = control_group(mediator, mediator.path_to_button[path])
        attach = group["attach_carriage"]
        for button in mediator.buttons:
            if hasattr(button, "is_hovered"):
                button.is_hovered = True

        def raising(_path):
            raise RuntimeError("carriage facade failed")

        mediator.attach_carriage = raising
        dispatch_mouse(mediator, MouseEventType.MOUSE_DOWN, attach)
        with self.assertRaisesRegex(RuntimeError, "carriage facade failed"):
            dispatch_mouse(mediator, MouseEventType.MOUSE_UP, attach)

        self.assertFalse(mediator.is_mouse_down)
        self.assertIsNone(mediator.path_redraw)
        self.assertIsNone(mediator.path_edit_selection)
        for button in mediator.buttons:
            if hasattr(button, "is_hovered"):
                self.assertFalse(button.is_hovered)
            if hasattr(button, "show_cross"):
                self.assertFalse(button.show_cross)

    def test_route_handles_keep_quantization_clearance_from_every_resource_control(
        self,
    ) -> None:
        mediator = fresh_mediator(seed=6343)
        path = _create_path(mediator, (0, 1, 2))
        handles = build_path_handles_for_state(
            mediator,
            path,
            viewport_size=(config.screen_width, config.screen_height),
        )

        self.assertGreater(len(handles), 0)
        for handle in handles:
            for control in resource_controls(mediator):
                self.assertGreater(
                    math.dist(handle.center, center_tuple(control)),
                    handle.hit_radius
                    + shape_radius(control)
                    + config.path_handle_quantization_margin,
                )


if __name__ == "__main__":
    unittest.main()
