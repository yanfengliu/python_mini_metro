from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


class TestHeadlessRender(unittest.TestCase):
    def test_fresh_process_renders_repeatably_without_display_or_uuid_allocations(self):
        source_root = Path(__file__).resolve().parents[1] / "src"
        script = textwrap.dedent(
            """
            import importlib
            from contextlib import ExitStack
            from unittest.mock import patch

            import pygame

            from config import screen_color
            from mediator import Mediator
            from rendering.game_renderer import GameRenderer

            assert pygame.display.get_surface() is None
            mediator = Mediator()
            renderer = GameRenderer()
            assert renderer.resources.font_count == 0
            assert not pygame.font.get_init()

            first = pygame.Surface((640, 360), pygame.SRCALPHA, 32)
            second = pygame.Surface((640, 360), pygame.SRCALPHA, 32)
            modules = (
                "entity.metro",
                "entity.padding_segment",
                "entity.passenger",
                "entity.path",
                "entity.path_segment",
                "entity.segment",
                "entity.station",
                "geometry.circle",
                "geometry.line",
                "geometry.polygon",
                "geometry.rect",
                "geometry.shape",
                "graph.node",
            )
            with ExitStack() as stack:
                for module_name in modules:
                    module = importlib.import_module(module_name)
                    stack.enter_context(
                        patch.object(
                            module,
                            "uuid",
                            side_effect=AssertionError(
                                f"render allocated an identity in {module_name}"
                            ),
                        )
                    )
                first.fill(screen_color)
                renderer.draw(first, mediator, alpha=1.0)
                second.fill(screen_color)
                renderer.draw(second, mediator, alpha=1.0)

            assert pygame.display.get_surface() is None
            assert pygame.image.tobytes(first, "RGBA") == pygame.image.tobytes(
                second, "RGBA"
            )
            print("HEADLESS_OK")
            """
        )
        env = os.environ.copy()
        env["SDL_VIDEODRIVER"] = "dummy"
        env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        env["PYTHONPATH"] = str(source_root)

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            check=False,
            env=env,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("HEADLESS_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
