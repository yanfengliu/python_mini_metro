"""GM-07c red contract: three-button title chrome and the failure notice.

Deterministic-pixel tests (``_fresh_surface``/``_bytes``/``_region_bytes`` from
``test_gm07a_menu_screens``) pin the lockstep ``menu_screens`` edits: the title
layout gains a ``continue`` rect between ``new_game`` and ``exit`` (deterministic,
pairwise-disjoint, on-screen); ``draw_title_screen`` receives whether Continue is
available and paints its button only then, byte-stably; and a new public
``draw_notice`` text primitive renders deterministically. A green guard confirms
the pause-menu layout is undisturbed by the third title button.
"""

from __future__ import annotations

import importlib
import inspect
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_color, screen_height, screen_width

_TITLE_KEYS = ("new_game", "continue", "exit")
_PAUSE_KEYS = ("resume", "restart", "exit_to_title")


def _module_symbol(testcase, symbol):
    try:
        module = importlib.import_module("ui.menu_screens")
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        testcase.fail(f"GM-07c product module is missing: ui.menu_screens ({error})")
    value = getattr(module, symbol, None)
    testcase.assertIsNotNone(
        value, f"GM-07c product symbol is missing: ui.menu_screens.{symbol}"
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


class TestGM07cTitleMenuScreens(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def _layout(self, layout_name: str, keys: tuple[str, ...]):
        layout = _module_symbol(self, layout_name)(screen_width, screen_height)
        for key in keys:
            self.assertIn(key, layout, f"{layout_name} must expose the {key!r} rect")
        return layout

    def _require_continue_param(self, draw) -> None:
        parameters = inspect.signature(draw).parameters
        self.assertIn(
            "continue_available",
            parameters,
            "draw_title_screen must receive whether Continue is available",
        )

    def test_title_layout_has_three_disjoint_onscreen_buttons(self):
        first = self._layout("title_layout", _TITLE_KEYS)
        second = self._layout("title_layout", _TITLE_KEYS)
        rects = [pygame.Rect(first[key]) for key in _TITLE_KEYS]
        for key, rect in zip(_TITLE_KEYS, rects):
            self.assertGreater(rect.width, 0)
            self.assertGreater(rect.height, 0)
            self.assertGreaterEqual(rect.left, 0)
            self.assertGreaterEqual(rect.top, 0)
            self.assertLessEqual(rect.right, screen_width)
            self.assertLessEqual(rect.bottom, screen_height)
            self.assertEqual(
                pygame.Rect(second[key]), rect, "title layout must be deterministic"
            )
        for index, rect in enumerate(rects):
            for other in rects[index + 1 :]:
                self.assertFalse(
                    rect.colliderect(other), "title hit targets must not overlap"
                )

    def test_continue_button_paints_only_when_available(self):
        draw = _module_symbol(self, "draw_title_screen")
        self._require_continue_param(draw)
        layout = self._layout("title_layout", _TITLE_KEYS)
        blank = _fresh_surface()

        without = _fresh_surface()
        draw(without, continue_available=False)
        available = _fresh_surface()
        draw(available, continue_available=True)

        for key in ("new_game", "exit"):
            self.assertNotEqual(
                _region_bytes(without, layout[key]),
                _region_bytes(blank, layout[key]),
                f"the {key!r} control must always paint",
            )
            self.assertNotEqual(
                _region_bytes(available, layout[key]),
                _region_bytes(blank, layout[key]),
                f"the {key!r} control must always paint",
            )
        self.assertEqual(
            _region_bytes(without, layout["continue"]),
            _region_bytes(blank, layout["continue"]),
            "an unavailable Continue must leave its rect unpainted",
        )
        self.assertNotEqual(
            _region_bytes(available, layout["continue"]),
            _region_bytes(blank, layout["continue"]),
            "an available Continue must paint its button",
        )

    def test_title_screen_is_byte_stable_for_each_continue_flag(self):
        draw = _module_symbol(self, "draw_title_screen")
        self._require_continue_param(draw)
        for available in (False, True):
            with self.subTest(continue_available=available):
                first = _fresh_surface()
                draw(first, continue_available=available)
                second = _fresh_surface()
                draw(second, continue_available=available)
                self.assertEqual(
                    _bytes(first), _bytes(second), "repeated draws must be identical"
                )
                draw(first, continue_available=available)
                self.assertEqual(
                    _bytes(first),
                    _bytes(second),
                    "redrawing over existing chrome must stay byte-stable",
                )

    def test_notice_primitive_is_deterministic_and_byte_stable(self):
        draw_notice = _module_symbol(self, "draw_notice")
        message = "Could not load the saved game."
        blank = _fresh_surface()
        first = _fresh_surface()
        draw_notice(first, message)
        second = _fresh_surface()
        draw_notice(second, message)
        self.assertEqual(
            _bytes(first), _bytes(second), "repeated notice draws must be identical"
        )
        self.assertNotEqual(
            _bytes(first), _bytes(blank), "the notice must paint visible text"
        )
        draw_notice(first, message)
        self.assertEqual(
            _bytes(first), _bytes(second), "redrawing the notice must stay byte-stable"
        )

    def test_pause_menu_layout_still_exposes_three_disjoint_controls(self):
        # regression guard: green at baseline
        layout = self._layout("pause_menu_layout", _PAUSE_KEYS)
        rects = [pygame.Rect(layout[key]) for key in _PAUSE_KEYS]
        for index, rect in enumerate(rects):
            self.assertGreater(rect.width, 0)
            self.assertGreater(rect.height, 0)
            self.assertLessEqual(rect.right, screen_width)
            self.assertLessEqual(rect.bottom, screen_height)
            for other in rects[index + 1 :]:
                self.assertFalse(
                    rect.colliderect(other), "pause-menu targets must not overlap"
                )


if __name__ == "__main__":
    unittest.main()
