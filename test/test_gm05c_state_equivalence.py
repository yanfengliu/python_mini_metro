from __future__ import annotations

import json
import os
import sys
import unittest

import pygame

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import screen_height, screen_width, station_color, station_size
from entity.passenger import Passenger
from env import MiniMetroEnv
from event.convert import convert_pygame_event
from game_session import GameSession
from geometry.circle import Circle
from geometry.point import Point
from mediator import Mediator
from path_handles import build_path_handles_for_state
from recursive_checkpoint import canonical_checkpoint
from recursive_oracles import reference_errors


def _dispatch(session: GameSession, event_type: int, position: object) -> None:
    point = position.to_tuple() if hasattr(position, "to_tuple") else tuple(position)
    attributes: dict[str, object] = {"pos": point}
    if event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        attributes["button"] = 1
    event = pygame.event.Event(event_type, attributes)
    session.dispatch(convert_pygame_event(event, mouse_position=event.pos))


def _empty_point(mediator: Mediator) -> tuple[int, int]:
    for y in range(160, screen_height - 160, 80):
        for x in range(160, screen_width - 160, 80):
            if mediator.get_containing_entity(Point(x, y)) is None:
                return (x, y)
    raise AssertionError("test viewport has no empty point")


def _create_route(mediator: Mediator, indices: list[int], *, loop: bool = False):
    mediator.stations = mediator.all_stations[:8]
    path = mediator.create_path_from_station_indices(indices, loop=loop)
    if path is None:
        raise AssertionError("test route creation failed")
    return path


def _select(mediator: Mediator, session: GameSession, path) -> None:
    button = mediator.path_to_button[path]
    terminal = _empty_point(mediator)
    _dispatch(session, pygame.MOUSEBUTTONDOWN, button.position)
    _dispatch(session, pygame.MOUSEMOTION, terminal)
    _dispatch(session, pygame.MOUSEBUTTONUP, terminal)


def _begin(mediator: Mediator, session: GameSession, path, kind: str, slot=None):
    matches = [
        handle
        for handle in build_path_handles_for_state(
            mediator,
            path,
            viewport_size=(screen_width, screen_height),
        )
        if handle.kind == kind and (slot is None or handle.slot == slot)
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one {kind} handle at {slot}, got {matches!r}")
    _dispatch(session, pygame.MOUSEMOTION, matches[0].center)
    _dispatch(session, pygame.MOUSEBUTTONDOWN, matches[0].center)
    return matches[0]


def _assert_observation_equal(
    test: unittest.TestCase,
    actual: dict[str, object],
    expected: dict[str, object],
) -> None:
    test.assertEqual(actual["structured"], expected["structured"])
    actual_arrays = actual["arrays"]
    expected_arrays = expected["arrays"]
    test.assertEqual(set(actual_arrays), set(expected_arrays))
    for name, expected_value in expected_arrays.items():
        actual_value = actual_arrays[name]
        if isinstance(expected_value, list):
            test.assertEqual(len(actual_value), len(expected_value))
            for actual_item, expected_item in zip(actual_value, expected_value):
                test.assertTrue((actual_item == expected_item).all())
        else:
            test.assertTrue((actual_value == expected_value).all())


class TestGM05cStateEquivalence(unittest.TestCase):
    def test_idle_selection_and_active_edit_are_absent_from_canonical_state(
        self,
    ) -> None:
        env = MiniMetroEnv()
        env.reset(seed=5051)
        mediator = env.mediator
        path = _create_route(mediator, [0, 1, 2])
        session = GameSession(mediator)
        baseline = canonical_checkpoint(env)
        baseline_observation = env.observe()

        _select(mediator, session, path)
        selected = canonical_checkpoint(env)
        selected_observation = env.observe()
        self.assertEqual(selected, baseline)
        _assert_observation_equal(self, selected_observation, baseline_observation)
        self.assertNotIn("path_edit_selection", json.dumps(selected, sort_keys=True))
        self.assertEqual(reference_errors(selected), [])

        _begin(mediator, session, path, "end")
        active = canonical_checkpoint(env)
        active_observation = env.observe()
        self.assertEqual(active, baseline)
        _assert_observation_equal(self, active_observation, baseline_observation)
        self.assertNotIn("handle_edit", json.dumps(active, sort_keys=True))
        self.assertEqual(active["rng"], baseline["rng"])
        self.assertEqual(reference_errors(active), [])

    def test_manual_endpoint_and_loop_insert_match_structured_replacement(self) -> None:
        cases = (
            ("start-extend", [0, 1, 2], False, "start", None, 3, [3, 0, 1, 2]),
            ("endpoint", [0, 1, 2], False, "end", None, 3, [0, 1, 2, 3]),
            ("start-shorten", [0, 1, 2], False, "start", None, 1, [1, 2]),
            ("end-shorten", [0, 1, 2], False, "end", None, 1, [0, 1]),
            ("loop-close", [0, 1, 2], True, "insert", 3, 3, [0, 1, 2, 3]),
        )
        for name, source, loop, kind, slot, target, expected in cases:
            with self.subTest(name=name):
                manual_env = MiniMetroEnv()
                structured_env = MiniMetroEnv()
                manual_env.reset(seed=5052)
                structured_env.reset(seed=5052)
                manual = manual_env.mediator
                structured = structured_env.mediator
                if name == "start-shorten":
                    manual.num_metros = 0
                    structured.num_metros = 0
                manual_path = _create_route(manual, source, loop=loop)
                structured_path = _create_route(structured, source, loop=loop)
                session = GameSession(manual)

                _select(manual, session, manual_path)
                _begin(manual, session, manual_path, kind, slot)
                _dispatch(
                    session,
                    pygame.MOUSEBUTTONUP,
                    manual.stations[target].position,
                )
                self.assertTrue(
                    structured.replace_path(structured_path, expected, loop=loop)
                )

                manual_checkpoint = canonical_checkpoint(manual_env)
                structured_checkpoint = canonical_checkpoint(structured_env)
                self.assertEqual(manual_checkpoint, structured_checkpoint)
                self.assertEqual(reference_errors(manual_checkpoint), [])

    def test_real_game_over_transition_clears_every_handle_gesture_reference(
        self,
    ) -> None:
        mediator = Mediator(seed=5053)
        path = _create_route(mediator, [0, 1, 2])
        session = GameSession(mediator)
        _select(mediator, session, path)
        _begin(mediator, session, path, "end")
        self.assertIsNotNone(mediator.path_redraw)
        self.assertIsNotNone(mediator.path_redraw.handle_edit)

        passenger = Passenger(Circle(station_color, station_size))
        mediator.stations[0].add_passenger(passenger)
        mediator.passenger_max_wait_time_ms = 1
        mediator.overdue_passenger_threshold = 1
        mediator.update_waiting_and_game_over(1)

        self.assertTrue(mediator.is_game_over)
        self.assertFalse(mediator.is_mouse_down)
        self.assertIsNone(mediator.path_redraw)
        self.assertIsNone(mediator.path_edit_selection)
        self.assertTrue(all(not button.show_cross for button in mediator.path_buttons))
        self.assertTrue(all(not button.is_hovered for button in mediator.speed_buttons))

    def test_reset_and_path_loss_release_idle_selection(self) -> None:
        mediator = Mediator(seed=5054)
        path = _create_route(mediator, [0, 1, 2])
        session = GameSession(mediator)
        _select(mediator, session, path)
        self.assertIsNotNone(mediator.path_edit_selection)

        mediator.paths.remove(path)
        # A harmless pointer move is enough to reconcile an exact-path loss.
        _dispatch(session, pygame.MOUSEMOTION, _empty_point(mediator))
        self.assertIsNone(mediator.path_edit_selection)

        replacement = Mediator(seed=5054)
        self.assertIsNone(replacement.path_edit_selection)
        self.assertIsNone(replacement.path_redraw)
        self.assertFalse(replacement.is_mouse_down)


if __name__ == "__main__":
    unittest.main()
