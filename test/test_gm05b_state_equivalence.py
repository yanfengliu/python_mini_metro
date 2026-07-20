from __future__ import annotations

import json
import os
import sys
import unittest

import pygame

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from config import screen_color, screen_height, screen_width
from env import MiniMetroEnv
from event.convert import convert_pygame_event
from game_session import GameSession
from recursive_checkpoint import canonical_checkpoint
from recursive_oracles import reference_errors
from rendering.game_renderer import GameRenderer


def _dispatch(session: GameSession, event_type: int, position) -> None:
    point = position.to_tuple() if hasattr(position, "to_tuple") else tuple(position)
    attributes = {"pos": point}
    if event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        attributes["button"] = 1
    event = pygame.event.Event(event_type, attributes)
    session.dispatch(convert_pygame_event(event, mouse_position=event.pos))


def _frame(mediator, renderer: GameRenderer | None = None) -> bytes:
    renderer = renderer or GameRenderer()
    surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA, 32)
    surface.fill(screen_color)
    renderer.draw(surface, mediator, alpha=1.0)
    return pygame.image.tobytes(surface, "RGBA")


def _create_route(env: MiniMetroEnv):
    path = env.mediator.create_path_from_station_indices([0, 1, 2])
    if path is None:
        raise AssertionError("test route creation failed")
    return path


class TestGM05bStateEquivalence(unittest.TestCase):
    def test_active_gesture_is_rendered_but_absent_from_every_canonical_surface(
        self,
    ) -> None:
        env = MiniMetroEnv()
        env.reset(seed=1707)
        path = _create_route(env)
        session = GameSession(env.mediator)
        renderer = GameRenderer()
        baseline = canonical_checkpoint(env)
        baseline_observation = env.observe()
        baseline_pixels = _frame(env.mediator, renderer)

        button = env.mediator.path_to_button[path]
        _dispatch(session, pygame.MOUSEBUTTONDOWN, button.position)
        _dispatch(session, pygame.MOUSEMOTION, env.mediator.stations[2].position)
        _dispatch(session, pygame.MOUSEMOTION, env.mediator.stations[0].position)

        active = canonical_checkpoint(env)
        active_observation = env.observe()
        active_pixels = _frame(env.mediator, renderer)
        self.assertEqual(active, baseline)
        self.assertEqual(
            active_observation["structured"], baseline_observation["structured"]
        )
        for name, expected in baseline_observation["arrays"].items():
            actual = active_observation["arrays"][name]
            if isinstance(expected, list):
                self.assertEqual(len(actual), len(expected))
                for actual_item, expected_item in zip(actual, expected):
                    self.assertTrue((actual_item == expected_item).all())
            else:
                self.assertTrue((actual == expected).all())
        self.assertEqual(reference_errors(active), [])
        self.assertNotEqual(active_pixels, baseline_pixels)
        self.assertNotIn("path_redraw", json.dumps(active, sort_keys=True))
        self.assertEqual(active["rng"], baseline["rng"])

    def test_completed_manual_and_structured_replacements_are_canonically_equal(
        self,
    ) -> None:
        manual = MiniMetroEnv()
        structured = MiniMetroEnv()
        manual.reset(seed=1708)
        structured.reset(seed=1708)
        manual_path = _create_route(manual)
        structured_path = _create_route(structured)
        session = GameSession(manual.mediator)

        button = manual.mediator.path_to_button[manual_path]
        _dispatch(session, pygame.MOUSEBUTTONDOWN, button.position)
        _dispatch(session, pygame.MOUSEMOTION, manual.mediator.stations[2].position)
        _dispatch(session, pygame.MOUSEMOTION, manual.mediator.stations[0].position)
        _dispatch(session, pygame.MOUSEBUTTONUP, manual.mediator.stations[1].position)
        self.assertTrue(structured.mediator.replace_path(structured_path, [2, 0, 1]))

        manual_checkpoint = canonical_checkpoint(manual)
        structured_checkpoint = canonical_checkpoint(structured)
        self.assertEqual(manual_checkpoint, structured_checkpoint)
        self.assertEqual(reference_errors(manual_checkpoint), [])
        self.assertIsNone(manual.mediator.path_redraw)
        self.assertFalse(manual.mediator.is_mouse_down)

    def test_cancellation_and_environment_reset_clear_the_active_draft(self) -> None:
        env = MiniMetroEnv()
        env.reset(seed=1709)
        path = _create_route(env)
        baseline = canonical_checkpoint(env)
        session = GameSession(env.mediator)
        button = env.mediator.path_to_button[path]

        _dispatch(session, pygame.MOUSEBUTTONDOWN, button.position)
        _dispatch(session, pygame.MOUSEMOTION, env.mediator.stations[2].position)
        _dispatch(session, pygame.MOUSEBUTTONUP, (-1000, -1000))

        self.assertEqual(canonical_checkpoint(env), baseline)
        self.assertIsNone(env.mediator.path_redraw)
        self.assertFalse(env.mediator.is_mouse_down)

        _dispatch(session, pygame.MOUSEBUTTONDOWN, button.position)
        self.assertIsNotNone(env.mediator.path_redraw)
        previous_mediator = env.mediator
        env.reset(seed=1710)
        self.assertIsNot(env.mediator, previous_mediator)
        self.assertIsNone(env.mediator.path_redraw)
        self.assertFalse(env.mediator.is_mouse_down)


if __name__ == "__main__":
    unittest.main()
