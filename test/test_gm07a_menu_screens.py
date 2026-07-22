"""GM-07a red contract: deterministic title/pause-menu chrome in ui.menu_screens."""

from __future__ import annotations

import importlib
import os
import sys
import unittest
from copy import deepcopy

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_color, screen_height, screen_width
from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint
from rendering.game_renderer import GameRenderer

_TITLE_KEYS = ("new_game", "exit")
_PAUSE_KEYS = ("resume", "restart", "exit_to_title")


def _module_symbol(testcase: unittest.TestCase, symbol: str):
    try:
        module = importlib.import_module("ui.menu_screens")
    except ModuleNotFoundError as error:
        testcase.fail(f"GM-07a product module is missing: ui.menu_screens ({error})")
    value = getattr(module, symbol, None)
    testcase.assertIsNotNone(
        value, f"GM-07a product symbol is missing: ui.menu_screens.{symbol}"
    )
    return value


def _fresh_surface() -> pygame.Surface:
    surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA, 32)
    surface.fill(screen_color)
    return surface


def _bytes(surface: pygame.Surface) -> bytes:
    return pygame.image.tobytes(surface, "RGBA")


def _region_bytes(surface: pygame.Surface, rect) -> bytes:
    return _bytes(surface.subsurface(pygame.Rect(rect)).copy())


def _rng_state(mediator):
    return (
        mediator.context.python_random.getstate(),
        deepcopy(mediator.context.numpy_random.bit_generator.state),
    )


class TestGM07aMenuScreens(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def _layout(self, layout_name: str, keys: tuple[str, ...]):
        layout_fn = _module_symbol(self, layout_name)
        layout = layout_fn(screen_width, screen_height)
        for key in keys:
            self.assertIn(key, layout, f"{layout_name} must expose the {key!r} rect")
        return layout

    def test_layout_rects_are_deterministic_disjoint_and_inside_the_screen(self):
        for layout_name, keys in (
            ("title_layout", _TITLE_KEYS),
            ("pause_menu_layout", _PAUSE_KEYS),
        ):
            with self.subTest(layout=layout_name):
                first = self._layout(layout_name, keys)
                second = self._layout(layout_name, keys)
                rects = [pygame.Rect(first[key]) for key in keys]
                for key, rect in zip(keys, rects):
                    self.assertGreater(rect.width, 0)
                    self.assertGreater(rect.height, 0)
                    self.assertGreaterEqual(rect.left, 0)
                    self.assertGreaterEqual(rect.top, 0)
                    self.assertLessEqual(rect.right, screen_width)
                    self.assertLessEqual(rect.bottom, screen_height)
                    self.assertTrue(rect.collidepoint(rect.center))
                    self.assertEqual(
                        pygame.Rect(second[key]),
                        rect,
                        "hit-test rects must be deterministic across calls",
                    )
                for index, rect in enumerate(rects):
                    for other in rects[index + 1 :]:
                        self.assertFalse(
                            rect.colliderect(other),
                            "menu hit targets must not overlap",
                        )

    def _assert_deterministic_chrome(
        self, draw_name: str, layout_name: str, keys: tuple[str, ...]
    ) -> pygame.Surface:
        draw = _module_symbol(self, draw_name)
        layout = self._layout(layout_name, keys)
        blank = _fresh_surface()
        first = _fresh_surface()
        draw(first)
        second = _fresh_surface()
        draw(second)
        self.assertEqual(
            _bytes(first), _bytes(second), "repeated draws must be byte-identical"
        )
        self.assertNotEqual(
            _bytes(first), _bytes(blank), "the screen must paint visible chrome"
        )
        draw(first)
        self.assertEqual(
            _bytes(first),
            _bytes(second),
            "redrawing over existing chrome must stay byte-stable",
        )
        for key in keys:
            self.assertNotEqual(
                _region_bytes(first, layout[key]),
                _region_bytes(blank, layout[key]),
                f"the {key!r} control must paint non-background pixels in its rect",
            )
        return first

    def test_title_screen_draws_deterministic_button_chrome(self):
        self._assert_deterministic_chrome(
            "draw_title_screen", "title_layout", _TITLE_KEYS
        )

    def test_pause_menu_draws_deterministic_chrome_distinct_from_title(self):
        pause = self._assert_deterministic_chrome(
            "draw_pause_menu", "pause_menu_layout", _PAUSE_KEYS
        )
        title = _fresh_surface()
        _module_symbol(self, "draw_title_screen")(title)
        self.assertNotEqual(
            _bytes(pause),
            _bytes(title),
            "pause menu and title screens must be distinguishable",
        )

    def test_menu_chrome_composes_over_a_frozen_gameplay_frame_without_mutation(self):
        draw_pause_menu = _module_symbol(self, "draw_pause_menu")
        draw_title_screen = _module_symbol(self, "draw_title_screen")
        env = MiniMetroEnv(dt_ms=17)
        env.reset(seed=7300)
        mediator = env.mediator
        self.assertIsNotNone(mediator.create_path_from_station_indices([0, 1]))
        renderer = GameRenderer()
        gameplay = _fresh_surface()
        renderer.draw(gameplay, mediator, alpha=1.0)
        frozen = _bytes(gameplay)
        checkpoint_before = canonical_checkpoint(env)
        rng_before = _rng_state(mediator)

        composed = gameplay.copy()
        draw_pause_menu(composed)
        self.assertEqual(
            _bytes(gameplay),
            frozen,
            "menu chrome must only touch the surface it was given",
        )
        self.assertNotEqual(
            _bytes(composed), frozen, "menu chrome must paint above the frozen frame"
        )

        titled = gameplay.copy()
        draw_title_screen(titled)
        self.assertEqual(_bytes(gameplay), frozen)
        self.assertNotEqual(_bytes(titled), frozen)

        self.assertEqual(
            canonical_checkpoint(env),
            checkpoint_before,
            "menu drawing must not mutate gameplay state",
        )
        self.assertEqual(
            _rng_state(mediator), rng_before, "menu drawing must not consume game RNG"
        )

        replay = _fresh_surface()
        renderer.draw(replay, mediator, alpha=1.0)
        self.assertEqual(
            _bytes(replay),
            frozen,
            "gameplay bytes under the menu must stay reproducible",
        )


if __name__ == "__main__":
    unittest.main()
