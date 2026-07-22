"""GM-07d red contract: the game-over best indicator and isolation extension.

Deterministic-pixel tests (``_fresh_surface``/``_bytes`` from
``test_gm07c_menu_screens``) pin a new public ``menu_screens`` primitive that
paints a compact "new best" indicator only for an ``is_best`` result and stays
byte-stable. A second class extends the GM-07b persistence-isolation scan: it
requires ``highscores`` to be named in the forbidden save-module set and
re-runs the AST scan so no headless surface (``env``/``agent_play``/
``recursive_*``/``rl``) imports the leaderboard or any save module.

Absent product surfaces become clean FAILUREs (never ERRORs) through the
``require_attribute`` guards.
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_color, screen_height, screen_width

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"


def _module_symbol(testcase, symbol):
    try:
        module = importlib.import_module("ui.menu_screens")
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        testcase.fail(f"GM-07d product module is missing: ui.menu_screens ({error})")
    value = getattr(module, symbol, None)
    testcase.assertIsNotNone(
        value, f"GM-07d product symbol is missing: ui.menu_screens.{symbol}"
    )
    return value


def _fresh_surface() -> pygame.Surface:
    surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA, 32)
    surface.fill(screen_color)
    return surface


def _bytes(surface: pygame.Surface) -> bytes:
    return pygame.image.tobytes(surface, "RGBA")


class TestGM07dBestIndicator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_best_indicator_paints_only_for_a_best_result(self):
        draw = _module_symbol(self, "draw_best_indicator")
        blank = _fresh_surface()

        best = _fresh_surface()
        draw(best, SimpleNamespace(rank=1, is_best=True))
        self.assertNotEqual(
            _bytes(best), _bytes(blank), "a new best must paint a visible indicator"
        )

        not_best = _fresh_surface()
        draw(not_best, SimpleNamespace(rank=2, is_best=False))
        self.assertEqual(
            _bytes(not_best),
            _bytes(blank),
            "a non-best result must leave the surface untouched",
        )

        absent = _fresh_surface()
        draw(absent, None)
        self.assertEqual(
            _bytes(absent), _bytes(blank), "an absent result must paint nothing"
        )

    def test_best_indicator_is_byte_stable(self):
        draw = _module_symbol(self, "draw_best_indicator")
        best = SimpleNamespace(rank=1, is_best=True)
        first = _fresh_surface()
        draw(first, best)
        second = _fresh_surface()
        draw(second, best)
        self.assertEqual(_bytes(first), _bytes(second), "repeated draws are identical")
        draw(first, best)
        self.assertEqual(
            _bytes(first), _bytes(second), "redrawing over the indicator stays stable"
        )


class TestGM07dPersistenceIsolation(unittest.TestCase):
    def _forbidden_names(self):
        module = None
        for name in (
            "test.test_gm07b_save_determinism",
            "test_gm07b_save_determinism",
        ):
            try:
                module = importlib.import_module(name)
                break
            except ModuleNotFoundError:
                continue
        self.assertIsNotNone(module, "cannot import the GM-07b isolation scan module")
        names = getattr(module, "SAVE_MODULE_NAMES", None)
        self.assertIsNotNone(names, "GM-07b SAVE_MODULE_NAMES is missing")
        return set(names)

    def test_highscores_is_named_in_the_forbidden_save_module_set(self):
        self.assertIn(
            "highscores",
            self._forbidden_names(),
            "the GM-07b isolation scan must forbid the highscores module too",
        )

    def test_runtime_surfaces_import_no_highscores_or_save_module(self):
        # regression guard: green at baseline (no headless surface imports the
        # leaderboard or any save module).
        forbidden = {
            "save_game",
            "save_schema",
            "save_load",
            "save_schema_records",
            "highscores",
        }
        targets = [
            SRC_ROOT / "env.py",
            SRC_ROOT / "agent_play.py",
            SRC_ROOT / "recursive_playtest.py",
            SRC_ROOT / "recursive_checkpoint.py",
            *sorted((SRC_ROOT / "rl").glob("*.py")),
        ]
        self.assertGreater(len(targets), 4)
        for target in targets:
            tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    self.assertNotIn(
                        name.split(".")[0],
                        forbidden,
                        f"{target.relative_to(REPO_ROOT)} imports {name}",
                    )


if __name__ == "__main__":
    unittest.main()
