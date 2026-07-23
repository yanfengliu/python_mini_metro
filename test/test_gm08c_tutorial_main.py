"""GM-08c red contract: the main wiring, overlay, and game-over suppression.

The seeded tutorial mediator suppresses its OWN game-over (a per-instance write)
so the sim never freezes; `main.run_game` advances the tutorial each frame and
paints the coaching overlay; and the title "Tutorial" entry appends without
disturbing the prior four rects.
"""

from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import DEFAULT, MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame  # noqa: E402

import main  # noqa: E402
from app_controller import AppScreen  # noqa: E402
from config import screen_height, screen_width  # noqa: E402
from ui.menu_screens import draw_tutorial_overlay, title_layout  # noqa: E402


class TestGM08cTutorialSeed(unittest.TestCase):
    def test_tutorial_mediator_suppresses_game_over(self):
        mediator = main._tutorial_mediator()
        self.assertGreaterEqual(
            mediator.overdue_passenger_threshold,
            10**9,
            "the tutorial instance never reaches game over",
        )
        self.assertEqual(main.TUTORIAL_SEED, 42, "the delivery-friendly probed seed")

    def test_tutorial_game_never_flips_game_over_headless(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        from game_session import GameSession
        from rendering.game_renderer import GameRenderer

        surface = pygame.Surface((screen_width, screen_height))
        mediator = main._tutorial_mediator()
        session = GameSession(mediator, step_observer=GameRenderer())
        session.prepare_layout(surface)
        for _ in range(int(90000 / 16)):  # 90s of no input
            session.advance(16)
        self.assertFalse(
            mediator.is_game_over, "suppressed game-over keeps the sim alive"
        )


class TestGM08cTutorialOverlay(unittest.TestCase):
    def _bytes(self, surface):
        return pygame.image.tobytes(surface, "RGB")

    def test_overlay_is_byte_stable(self):
        a = pygame.Surface((screen_width, screen_height))
        a.fill((10, 10, 10))
        b = a.copy()
        draw_tutorial_overlay(a, "Draw a line.", 1, 7, False)
        draw_tutorial_overlay(b, "Draw a line.", 1, 7, False)
        self.assertEqual(self._bytes(a), self._bytes(b), "same inputs -> same bytes")

    def test_overlay_reflects_its_inputs(self):
        base = pygame.Surface((screen_width, screen_height))
        base.fill((10, 10, 10))
        one = base.copy()
        two = base.copy()
        draw_tutorial_overlay(one, "Draw a line.", 1, 7, False)
        draw_tutorial_overlay(two, "Add a train.", 2, 7, False)
        self.assertNotEqual(self._bytes(one), self._bytes(two), "prompt/ordinal show")


class TestGM08cTitleLayout(unittest.TestCase):
    def test_tutorial_appended_without_moving_prior_rects(self):
        layout = title_layout(screen_width, screen_height)
        for key in ("new_game", "continue", "exit", "settings", "tutorial"):
            self.assertIn(key, layout)
        # Appended below Settings; the prior four are anchored count-independently.
        self.assertGreater(layout["tutorial"].top, layout["settings"].top)
        rects = [layout[k] for k in ("new_game", "continue", "exit", "settings")]
        for i, a in enumerate(rects):
            for b in rects[i + 1 :]:
                self.assertFalse(a.colliderect(b), "prior rects stay disjoint")


def _loop_harness():
    patches = patch.multiple(
        "main",
        pygame=DEFAULT,
        Mediator=DEFAULT,
        GameSession=DEFAULT,
        GameRenderer=DEFAULT,
        convert_pygame_event=DEFAULT,
        read_settings=DEFAULT,
    )
    mocks = patches.start()
    mocks["read_settings"].return_value = SimpleNamespace(
        master_volume=100, sfx_volume=100, fullscreen=False, reduced_motion=False
    )
    pg = mocks["pygame"]
    pg.QUIT = 12
    pg.RESIZABLE = 1
    pg.FULLSCREEN = 2
    pg.SCALED = 4
    window = MagicMock()
    window.get_size.return_value = (screen_width, screen_height)
    pg.display.set_mode.return_value = window
    surface = MagicMock()
    surface.get_size.return_value = (screen_width, screen_height)
    pg.Surface.return_value = surface
    clock = MagicMock()
    clock.tick.return_value = 17
    pg.time.Clock.return_value = clock
    pg.event.get.return_value = []
    mocks["GameSession"].return_value.advance.return_value = SimpleNamespace(alpha=1.0)
    med = mocks["Mediator"].return_value
    med.deliveries = 0
    med.unlocked_num_paths = 1
    med.unlocked_num_stations = 3
    med.is_game_over = False
    med.is_paused = False
    med.all_stations = []
    return patches


class TestGM08cMainWiring(unittest.TestCase):
    def test_run_game_advances_the_tutorial_each_frame(self):
        patches = _loop_harness()
        try:
            # The cold TUTORIAL start really builds the tutorial (MODERATE-3), so
            # the overlay renders; stub the draw on the mock surface.
            with (
                patch("main.AppController.advance_tutorial") as spy,
                patch("main.draw_tutorial_overlay"),
            ):
                main.run_game(max_frames=3, start_state=AppScreen.TUTORIAL)
            self.assertEqual(spy.call_count, 3, "advance_tutorial runs once per frame")
        finally:
            patches.stop()


if __name__ == "__main__":
    unittest.main()
