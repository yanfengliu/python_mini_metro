from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import mediator as mediator_module
from event.convert import convert_pygame_event
from game_session import GameSession
from mediator import Mediator
from path_redraw import PathRedrawGesture


class TestGM05bMouseRedraw(unittest.TestCase):
    def setUp(self) -> None:
        self.mediator = Mediator(seed=1705)
        self.mediator.stations = self.mediator.all_stations[:5]
        self.mediator.unlocked_num_paths = 3
        self.mediator.update_path_button_lock_states()
        self.session = GameSession(self.mediator)

    def dispatch(self, event_type: int, position: object) -> None:
        point = (
            position.to_tuple() if hasattr(position, "to_tuple") else tuple(position)  # type: ignore[arg-type]
        )
        attributes: dict[str, object] = {"pos": point}
        if event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            attributes["button"] = 1
        event = pygame.event.Event(event_type, attributes)
        converted = convert_pygame_event(event, mouse_position=event.pos)
        self.session.dispatch(converted)

    def create_path(self, stations: list[int]):
        path = self.mediator.create_path_from_station_indices(stations)
        self.assertIsNotNone(path)
        assert path is not None
        return path

    def remove_metros(self, path) -> None:
        for metro in tuple(path.metros):
            self.mediator.metros.remove(metro)
        path.metros.clear()

    def arm(self, path) -> None:
        button = self.mediator.path_to_button[path]
        self.dispatch(pygame.MOUSEBUTTONDOWN, button.position)

    def test_real_linear_release_includes_final_station_and_calls_hook_once(
        self,
    ) -> None:
        path = self.create_path([0, 1, 2])
        button = self.mediator.path_to_button[path]
        topology = tuple(path.stations)
        button.show_cross = True
        hook = MagicMock(return_value=True)
        self.mediator.replace_path = hook

        self.arm(path)
        self.assertIs(self.mediator.path_redraw.path, path)
        self.assertFalse(button.show_cross)
        self.assertEqual(tuple(path.stations), topology)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[3].position)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[0].position)
        self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[1].position)

        hook.assert_called_once_with(path, [3, 0, 1], False)
        self.assertIsNone(self.mediator.path_redraw)
        self.assertFalse(self.mediator.is_mouse_down)
        self.assertTrue(all(not item.show_cross for item in self.mediator.path_buttons))

    def test_real_loop_release_dispatches_existing_public_hook(self) -> None:
        path = self.create_path([0, 1])
        hook = MagicMock(return_value=True)
        self.mediator.replace_path = hook

        self.arm(path)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[0].position)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[2].position)
        self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[0].position)

        hook.assert_called_once_with(path, [0, 2], True)
        self.assertIsNone(self.mediator.path_redraw)

    def test_canonical_redraw_preserves_path_and_button_identity(self) -> None:
        path = self.create_path([0, 1, 2])
        self.remove_metros(path)
        button = self.mediator.path_to_button[path]
        path_id = path.id
        original = self.mediator.replace_path

        with patch.object(self.mediator, "replace_path", wraps=original) as hook:
            self.arm(path)
            self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[0].position)
            self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[3].position)
            self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[2].position)

        hook.assert_called_once_with(path, [0, 3, 2], False)
        self.assertEqual(
            path.stations,
            [
                self.mediator.stations[0],
                self.mediator.stations[3],
                self.mediator.stations[2],
            ],
        )
        self.assertEqual(path.id, path_id)
        self.assertIs(self.mediator.path_to_button[path], button)
        self.assertIs(button.path, path)

    def test_zero_station_release_delegates_complete_historical_matrix(self) -> None:
        path_a = self.create_path([0, 1])
        path_b = self.create_path([1, 2])
        button_b = self.mediator.path_to_button[path_b]

        self.arm(path_a)
        self.dispatch(pygame.MOUSEBUTTONUP, button_b.position)
        self.assertIn(path_a, self.mediator.paths)
        self.assertNotIn(path_b, self.mediator.paths)
        self.assertTrue(button_b.show_cross)

        locked = self.mediator.path_buttons[-1]
        purchase = MagicMock(return_value=True)
        self.mediator.try_purchase_path_button = purchase
        self.arm(path_a)
        self.dispatch(pygame.MOUSEBUTTONUP, locked.position)
        purchase.assert_called_once_with(locked)
        self.assertTrue(locked.show_cross)

        speed = self.mediator.speed_buttons[-1]
        apply_speed = MagicMock()
        self.mediator.apply_speed_action = apply_speed
        self.arm(path_a)
        self.dispatch(pygame.MOUSEBUTTONUP, speed.position)
        apply_speed.assert_called_once_with(speed.action)
        self.assertTrue(speed.is_hovered)
        self.assertIsNone(self.mediator.path_redraw)

    def test_captured_station_button_release_cancels_every_button_action(self) -> None:
        path = self.create_path([0, 1])
        locked = self.mediator.path_buttons[-1]
        purchase = MagicMock(return_value=True)
        speed = MagicMock()
        replace = MagicMock(return_value=True)
        self.mediator.try_purchase_path_button = purchase
        self.mediator.apply_speed_action = speed
        self.mediator.replace_path = replace

        for target in (
            self.mediator.path_to_button[path],
            locked,
            self.mediator.speed_buttons[0],
        ):
            with self.subTest(target=target):
                self.arm(path)
                self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[0].position)
                self.dispatch(pygame.MOUSEBUTTONUP, target.position)
                self.assertIn(path, self.mediator.paths)
                self.assertIsNone(self.mediator.path_redraw)
                if hasattr(target, "is_hovered"):
                    self.assertTrue(target.is_hovered)
                else:
                    self.assertTrue(target.show_cross)

        purchase.assert_not_called()
        speed.assert_not_called()
        replace.assert_not_called()

    def test_short_invalid_and_offstation_drafts_cancel_without_hook(self) -> None:
        path = self.create_path([0, 1])
        hook = MagicMock(return_value=True)
        self.mediator.replace_path = hook

        cases = (
            ([0], (-1000, -1000)),
            ([0], self.mediator.stations[0].position),
            ([0, 1, 2, 1], self.mediator.stations[3].position),
        )
        for motions, release in cases:
            with self.subTest(motions=motions, release=release):
                self.arm(path)
                for index in motions:
                    self.dispatch(
                        pygame.MOUSEMOTION, self.mediator.stations[index].position
                    )
                self.dispatch(pygame.MOUSEBUTTONUP, release)
                self.assertIsNone(self.mediator.path_redraw)

        hook.assert_not_called()

    def test_redraw_rejects_structured_and_direct_replacement_until_release(
        self,
    ) -> None:
        path = self.create_path([0, 1, 2])
        self.remove_metros(path)
        topology = tuple(path.stations)
        self.arm(path)

        self.assertFalse(self.mediator.replace_path(path, [0, 2, 1], False))
        self.assertFalse(
            self.mediator.apply_action(
                {"type": "replace_path", "path_id": path.id, "stations": [0, 2, 1]}
            )
        )
        self.assertEqual(tuple(path.stations), topology)
        self.assertIsNotNone(self.mediator.path_redraw)

        self.dispatch(pygame.MOUSEBUTTONUP, (-1000, -1000))
        self.assertTrue(self.mediator.replace_path(path, [0, 2, 1], False))

    def test_repeated_down_does_not_switch_target_or_start_creation(self) -> None:
        path_a = self.create_path([0, 1])
        path_b = self.create_path([1, 2])
        self.arm(path_a)

        self.dispatch(
            pygame.MOUSEBUTTONDOWN,
            self.mediator.path_to_button[path_b].position,
        )
        self.dispatch(pygame.MOUSEBUTTONDOWN, self.mediator.stations[3].position)

        self.assertIs(self.mediator.path_redraw.path, path_a)
        self.assertFalse(self.mediator.is_creating_path)
        self.assertIsNone(self.mediator.path_being_created)

    def test_creation_precedence_clears_malformed_concurrent_redraw(self) -> None:
        path = self.create_path([0, 1])
        self.dispatch(pygame.MOUSEBUTTONDOWN, self.mediator.stations[3].position)
        creating = self.mediator.path_being_created
        self.assertIsNotNone(creating)
        self.mediator.path_redraw = PathRedrawGesture(path)

        self.dispatch(
            pygame.MOUSEBUTTONDOWN,
            self.mediator.path_to_button[path].position,
        )

        self.assertIsNone(self.mediator.path_redraw)
        self.assertTrue(self.mediator.is_creating_path)
        self.assertIs(self.mediator.path_being_created, creating)

    def test_malformed_creation_without_path_clears_redraw_on_release(self) -> None:
        path = self.create_path([0, 1])
        self.arm(path)
        self.mediator.is_creating_path = True
        self.mediator.path_being_created = None

        self.dispatch(pygame.MOUSEBUTTONUP, (-1000, -1000))

        self.assertIsNone(self.mediator.path_redraw)
        self.assertFalse(self.mediator.is_mouse_down)

    def test_locked_assigned_button_and_wrong_type_redraw_fail_closed(self) -> None:
        path = self.create_path([0, 1])
        button = self.mediator.path_to_button[path]
        button.is_locked = True

        self.dispatch(pygame.MOUSEBUTTONDOWN, button.position)
        self.assertIsNone(self.mediator.path_redraw)

        self.mediator.path_redraw = object()  # type: ignore[assignment]
        self.dispatch(pygame.MOUSEBUTTONUP, button.position)
        self.assertIsNone(self.mediator.path_redraw)
        self.assertIn(path, self.mediator.paths)
        self.assertTrue(button.show_cross)

        self.mediator.path_redraw = object()  # type: ignore[assignment]
        self.mediator.is_mouse_down = True
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[2].position)
        self.assertIsNone(self.mediator.path_redraw)
        self.assertIn(path, self.mediator.paths)

    def test_wrong_type_redraw_does_not_strand_active_creation(self) -> None:
        self.dispatch(pygame.MOUSEBUTTONDOWN, self.mediator.stations[0].position)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[1].position)
        self.mediator.path_redraw = object()  # type: ignore[assignment]

        self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[1].position)

        self.assertFalse(self.mediator.is_creating_path)
        self.assertIsNone(self.mediator.path_being_created)
        self.assertIsNone(self.mediator.path_redraw)
        self.assertEqual(self.mediator.paths[0].stations, self.mediator.stations[:2])

    def test_malformed_creation_path_clears_redraw_and_release_fails_closed(
        self,
    ) -> None:
        path = self.create_path([0, 1])
        self.arm(path)
        self.mediator.is_creating_path = False
        self.mediator.path_being_created = object()

        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[2].position)
        self.dispatch(
            pygame.MOUSEBUTTONUP,
            self.mediator.path_to_button[path].position,
        )

        self.assertIsNone(self.mediator.path_redraw)
        self.assertIn(path, self.mediator.paths)

    def test_raised_rebound_hook_clears_gesture_and_hover_in_finally(self) -> None:
        path = self.create_path([0, 1])

        def fail(*_args):
            for button in self.mediator.path_buttons:
                button.show_cross = True
            self.mediator.path_redraw = PathRedrawGesture(path)
            raise RuntimeError("replacement failed")

        self.mediator.replace_path = fail
        self.arm(path)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[0].position)

        with self.assertRaisesRegex(RuntimeError, "replacement failed"):
            self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[2].position)

        self.assertIsNone(self.mediator.path_redraw)
        self.assertFalse(self.mediator.is_mouse_down)
        self.assertTrue(all(not item.show_cross for item in self.mediator.path_buttons))

    def test_preflight_safe_absent_field_and_new_mediator_reset_state(self) -> None:
        path = self.create_path([0, 1])
        self.remove_metros(path)
        del self.mediator.path_redraw

        self.assertTrue(self.mediator.replace_path(path, [0, 1], False))
        self.assertIsNone(Mediator(seed=1706).path_redraw)

    def test_selected_target_remains_exact_after_button_rebinding_and_removal(
        self,
    ) -> None:
        selected = self.create_path([0, 1])
        remaining = self.create_path([1, 2])
        original_button = self.mediator.path_to_button[selected]
        hook = MagicMock(return_value=False)

        self.arm(selected)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[0].position)
        self.mediator.remove_path(selected)
        self.assertIs(original_button.path, remaining)
        self.mediator.replace_path = hook
        self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[2].position)

        hook.assert_called_once_with(selected, [0, 2], False)
        self.assertIn(remaining, self.mediator.paths)
        self.assertIsNone(self.mediator.path_redraw)

    def test_valid_unsafe_redraw_rejects_without_changing_live_topology(self) -> None:
        path = self.create_path([0, 1, 2])
        topology = tuple(path.stations)
        hook = MagicMock(wraps=self.mediator.replace_path)
        self.mediator.replace_path = hook

        self.arm(path)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[1].position)
        self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[2].position)

        hook.assert_called_once_with(path, [1, 2], False)
        self.assertEqual(tuple(path.stations), topology)
        self.assertIsNone(self.mediator.path_redraw)

    def test_real_same_route_redraw_is_successful_topology_noop(self) -> None:
        path = self.create_path([0, 1, 2])
        segment_objects = tuple(path.segments)
        hook = MagicMock(wraps=self.mediator.replace_path)
        self.mediator.replace_path = hook

        self.arm(path)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[0].position)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[1].position)
        self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[2].position)

        hook.assert_called_once_with(path, [0, 1, 2], False)
        self.assertEqual(tuple(path.segments), segment_objects)
        self.assertTrue(
            all(
                before is after for before, after in zip(segment_objects, path.segments)
            )
        )
        self.assertIsNone(self.mediator.path_redraw)

    def test_plain_click_and_historical_bare_up_delete_assigned_lines(self) -> None:
        clicked = self.create_path([0, 1])
        clicked_button = self.mediator.path_to_button[clicked]
        self.dispatch(pygame.MOUSEBUTTONDOWN, clicked_button.position)
        self.dispatch(pygame.MOUSEBUTTONUP, clicked_button.position)
        self.assertNotIn(clicked, self.mediator.paths)

        bare = self.create_path([1, 2])
        self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.path_to_button[bare].position)
        self.assertNotIn(bare, self.mediator.paths)

    def test_unassigned_click_and_station_origin_creation_remain_compatible(
        self,
    ) -> None:
        unassigned = self.mediator.path_buttons[0]
        self.dispatch(pygame.MOUSEBUTTONDOWN, unassigned.position)
        self.assertIsNone(self.mediator.path_redraw)
        self.dispatch(pygame.MOUSEBUTTONUP, unassigned.position)
        self.assertEqual(self.mediator.paths, [])

        self.dispatch(pygame.MOUSEBUTTONDOWN, self.mediator.stations[0].position)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[1].position)
        self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[1].position)
        self.assertEqual(
            self.mediator.paths[0].stations,
            self.mediator.stations[:2],
        )
        self.assertIsNone(self.mediator.path_redraw)

    def test_canonical_failure_rolls_back_after_input_clears_gesture(self) -> None:
        path = self.create_path([0, 1, 2])
        self.remove_metros(path)
        topology = tuple(path.stations)
        graph_builder = MagicMock(side_effect=RuntimeError("graph failure"))

        self.arm(path)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[0].position)
        self.dispatch(pygame.MOUSEMOTION, self.mediator.stations[3].position)
        with (
            patch.object(mediator_module, "build_station_nodes_dict", graph_builder),
            self.assertRaisesRegex(RuntimeError, "graph failure"),
        ):
            self.dispatch(pygame.MOUSEBUTTONUP, self.mediator.stations[2].position)

        self.assertEqual(tuple(path.stations), topology)
        self.assertIsNone(self.mediator.path_redraw)


if __name__ == "__main__":
    unittest.main()
