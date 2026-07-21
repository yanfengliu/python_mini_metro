from __future__ import annotations

import math
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pygame

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config  # noqa: E402
from env import MiniMetroEnv  # noqa: E402
from path_handles import (  # noqa: E402
    build_path_handles_for_state,
    hit_test_path_handles,
)
from recursive_checkpoint import canonical_checkpoint  # noqa: E402
from rendering.game_renderer import GameRenderer, LazyRenderResources  # noqa: E402
from rl.player_env import PlayerPixelEnv  # noqa: E402
from rl.protocol import (  # noqa: E402
    FAST_RENDER_PROFILE,
    FIDELITY_RENDER_PROFILE,
    ActionKind,
    canonical_to_action_coordinate,
    map_action_coordinate,
)

OLD_HUD_EXCLUSION = (0, 0, 700, 140)
NEW_HUD_EXCLUSION = (0, 0, 840, 250)
PROFILES = (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE)


class _RecordingFont:
    def __init__(self, owner: _RecordingResources) -> None:
        self.owner = owner

    def render(self, text, antialias, color):
        del antialias, color
        self.owner.text.append(text)
        surface = pygame.Surface((max(1, len(text)), 1), pygame.SRCALPHA, 32)
        self.owner.labels[id(surface)] = text
        return surface


class _RecordingResources:
    def __init__(self) -> None:
        self.text: list[str] = []
        self.labels: dict[int, str] = {}

    def font(self, name, size):
        del name, size
        return _RecordingFont(self)


class _RecordingSurface:
    def __init__(self) -> None:
        self.blits: list[tuple[pygame.Surface, tuple[int, int]]] = []

    def blit(self, source, destination):
        self.blits.append((source, destination))
        return destination


class _Point:
    def __init__(self, left: float, top: float) -> None:
        self.left = left
        self.top = top


class _Station:
    def __init__(self, name: str, left: float, top: float) -> None:
        self.id = name
        self.position = _Point(left, top)
        self.size = 30


class _PathStub:
    def __init__(self, name: str, points, *, loop: bool = False) -> None:
        self.id = name
        self.color = (30, 110, 210)
        self.stations = [
            _Station(f"{name}-{index}", left, top)
            for index, (left, top) in enumerate(points)
        ]
        self.is_looped = loop


def _state_for(path: _PathStub):
    return SimpleNamespace(
        paths=[path],
        stations=list(path.stations),
        path_buttons=[],
        speed_buttons=[],
        buttons=[],
    )


def _descriptor_keys(handles) -> tuple[tuple[str, int], ...]:
    return tuple((handle.kind, handle.slot) for handle in handles)


def _rect_distance(point, rect) -> float:
    left, top, right, bottom = rect
    x = min(max(point[0], left), right)
    y = min(max(point[1], top), bottom)
    return math.hypot(point[0] - x, point[1] - y)


def _grid(position, profile) -> tuple[int, int]:
    return canonical_to_action_coordinate(
        round(float(position.left)), round(float(position.top)), profile
    )


def _action(kind: ActionKind, grid: tuple[int, int] = (0, 0)) -> np.ndarray:
    return np.asarray([int(kind), *grid], dtype=np.int64)


def _cursor_bounds(cursor: tuple[int, int], profile) -> tuple[int, int, int, int]:
    cursor_x, cursor_y = cursor
    left, top = canonical_to_action_coordinate(
        max(0, cursor_x - 12), max(0, cursor_y - 12), profile
    )
    right, bottom = canonical_to_action_coordinate(
        min(config.screen_width - 1, cursor_x + 42),
        min(config.screen_height - 1, cursor_y + 52),
        profile,
    )
    padding = 2
    return (
        max(0, left - padding),
        max(0, top - padding),
        min(profile.width, right + padding + 1),
        min(profile.height, bottom + padding + 1),
    )


def _mask_cursors(frame: np.ndarray, profile, infos) -> np.ndarray:
    masked = frame.copy()
    for info in infos:
        left, top, right, bottom = _cursor_bounds(info["cursor"], profile)
        masked[:, top:bottom, left:right] = 0
    return masked


def _digit_crop(profile, font) -> tuple[slice, slice]:
    prefix = "Locomotives Available: "
    x, y = config.hud_display_coords
    top = y + 2 * config.hud_line_spacing
    left = x + font.size(prefix)[0] - 3
    right = x + max(font.size(prefix + digit)[0] for digit in ("3", "4")) + 3
    bottom = top + font.get_height()
    scale_x = profile.width / config.screen_width
    scale_y = profile.height / config.screen_height
    output_left = max(0, math.floor(left * scale_x) - 2)
    output_top = max(0, math.floor(top * scale_y) - 2)
    output_right = min(profile.width, math.ceil(right * scale_x) + 2)
    output_bottom = min(profile.height, math.ceil(bottom * scale_y) + 2)
    return (slice(output_top, output_bottom), slice(output_left, output_right))


def _expected_hud_frame(count: int, profile, font) -> np.ndarray:
    canonical = pygame.Surface(
        (config.screen_width, config.screen_height), pygame.SRCALPHA, 32
    )
    canonical.fill(config.screen_color)
    x, y = config.hud_display_coords
    rendered = font.render(f"Locomotives Available: {count}", True, (0, 0, 0))
    canonical.blit(rendered, (x, y + 2 * config.hud_line_spacing))
    scaled = pygame.Surface((profile.width, profile.height), pygame.SRCALPHA, 32)
    pygame.transform.smoothscale(canonical, scaled.get_size(), scaled)
    whc = pygame.surfarray.array3d(scaled)
    return np.ascontiguousarray(whc.transpose(2, 1, 0), dtype=np.uint8)


class TestGM06aInventoryRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_hud_third_line_uses_property_complete_legacy_then_zero(self) -> None:
        cases = (
            SimpleNamespace(
                deliveries=23,
                line_credits=4,
                available_locomotives=7,
                num_metros=4,
                metros=[object()],
            ),
            SimpleNamespace(
                deliveries=23, line_credits=4, num_metros=4, metros=[object()]
            ),
            SimpleNamespace(deliveries=23, line_credits=4, num_metros=4),
        )
        expected_counts = (7, 3, 0)
        observed = []

        for state in cases:
            resources = _RecordingResources()
            surface = _RecordingSurface()
            GameRenderer(resources=resources)._draw_hud(surface, state)
            observed.append(
                (
                    resources.text,
                    [destination for _, destination in surface.blits],
                )
            )

        self.assertEqual(
            observed,
            [
                (
                    [
                        "Passengers Delivered: 23",
                        "Line Credits: 4",
                        f"Locomotives Available: {count}",
                        "Carriages Available: 0",
                    ],
                    [(20, 20), (20, 70), (20, 120), (20, 170)],
                )
                for count in expected_counts
            ],
        )

    def test_bundled_font_exhaustive_count_envelope_uses_exact_blocker(self) -> None:
        self.assertEqual(config.path_handle_hud_exclusion, NEW_HUD_EXCLUSION)
        resources = LazyRenderResources()
        font = resources.font(config.font_name, config.hud_font_size)
        self.assertIs(font, resources.font("ignored-by-renderer", config.hud_font_size))
        self.assertEqual(resources.font_count, 1)
        x, y = config.hud_display_coords
        blocker = pygame.Rect(0, 0, 840, 250)

        for count in range(1000):
            with self.subTest(count=count):
                for label, row in (
                    (f"Locomotives Available: {count}", 2),
                    (f"Carriages Available: {count}", 3),
                ):
                    rendered = font.render(label, True, (0, 0, 0))
                    rect = rendered.get_rect(
                        topleft=(x, y + row * config.hud_line_spacing)
                    )
                    self.assertTrue(blocker.contains(rect), rect)

    def test_old_and_new_blockers_preserve_every_descriptor_round_trip(self) -> None:
        paths = (
            _PathStub("line", ((100, 100), (320, 100), (560, 150), (780, 100))),
            _PathStub(
                "loop", ((100, 80), (360, 80), (700, 140), (500, 360)), loop=True
            ),
        )

        for path in paths:
            state = _state_for(path)
            expected = (
                {("insert", slot) for slot in range(1, len(path.stations) + 1)}
                if path.is_looped
                else {
                    ("start", 0),
                    ("end", len(path.stations)),
                    *(("insert", slot) for slot in range(1, len(path.stations))),
                }
            )
            with patch.object(config, "path_handle_hud_exclusion", OLD_HUD_EXCLUSION):
                old_handles = build_path_handles_for_state(
                    state,
                    path,
                    viewport_size=(config.screen_width, config.screen_height),
                )
            with patch.object(config, "path_handle_hud_exclusion", NEW_HUD_EXCLUSION):
                new_handles = build_path_handles_for_state(
                    state,
                    path,
                    viewport_size=(config.screen_width, config.screen_height),
                )

            self.assertEqual(set(_descriptor_keys(old_handles)), expected)
            self.assertEqual(set(_descriptor_keys(new_handles)), expected)
            self.assertEqual(len(old_handles), len(expected))
            self.assertEqual(len(new_handles), len(expected))
            for handle in new_handles:
                self.assertGreater(
                    _rect_distance(handle.center, NEW_HUD_EXCLUSION),
                    handle.hit_radius + config.path_handle_quantization_margin,
                )
                for profile in PROFILES:
                    grid = canonical_to_action_coordinate(
                        round(handle.center[0]), round(handle.center[1]), profile
                    )
                    mapped = map_action_coordinate(*grid, profile)
                    self.assertGreater(
                        _rect_distance(mapped, NEW_HUD_EXCLUSION), handle.hit_radius
                    )
                    hit = hit_test_path_handles(new_handles, mapped)
                    self.assertFalse(hit.ambiguous)
                    self.assertIs(hit.handle, handle)

    def test_repeated_render_is_pure_cache_bounded_and_source_stays_small(self) -> None:
        env = MiniMetroEnv(dt_ms=17)
        env.reset(seed=606)
        mediator = env.mediator
        path = mediator.create_path_from_station_indices([0, 1, 2])
        self.assertIsNotNone(path)
        self.assertTrue(mediator.assign_locomotive(path))
        mediator.prepare_layout(config.screen_width, config.screen_height)
        renderer = GameRenderer()
        before = canonical_checkpoint(env)

        rendered = []
        for _ in range(2):
            surface = pygame.Surface(
                (config.screen_width, config.screen_height), pygame.SRCALPHA, 32
            )
            surface.fill(config.screen_color)
            renderer.draw(surface, mediator, alpha=1.0)
            rendered.append(pygame.image.tobytes(surface, "RGBA"))

        self.assertEqual(rendered[0], rendered[1])
        self.assertEqual(canonical_checkpoint(env), before)
        self.assertEqual(renderer.resources.font_count, 1)
        self.assertEqual(renderer.network_renderer.cache_entry_count, 1)
        self.assertEqual(renderer.network_renderer.cache_rebuild_count, 1)
        self.assertEqual(renderer.network_renderer.preview_cache_entry_count, 0)
        self.assertEqual(renderer.network_renderer.preview_cache_rebuild_count, 0)
        self.assertEqual(vars(renderer.path_handle_renderer), {})
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "rendering"
            / "game_renderer.py"
        )
        self.assertLess(len(source.read_text(encoding="utf-8").splitlines()), 500)

    def test_low_level_player_actions_show_exact_glyph_4_to_3_to_4(self) -> None:
        resources = LazyRenderResources()
        font = resources.font(config.font_name, config.hud_font_size)

        for profile in PROFILES:
            with self.subTest(profile=profile.name):
                env = PlayerPixelEnv(
                    render_profile=profile, fixed_ticks=1, max_episode_steps=20
                )
                try:
                    env.reset(seed=606)
                    mediator = env._mediator
                    self.assertIsNotNone(mediator)
                    assert mediator is not None
                    fresh = env.step(_action(ActionKind.NOOP))
                    first_grid = _grid(mediator.stations[0].position, profile)
                    second_grid = _grid(mediator.stations[1].position, profile)
                    env.step(_action(ActionKind.DOWN, first_grid))
                    env.step(_action(ActionKind.MOTION, second_grid))
                    env.step(_action(ActionKind.UP, second_grid))
                    self.assertEqual(
                        (len(mediator.paths), len(mediator.metros)), (1, 0)
                    )
                    route = mediator.paths[0]
                    plus = next(
                        button
                        for button in mediator.fleet_buttons
                        if button.operation == "assign"
                        and button.path_button is mediator.path_to_button[route]
                    )
                    plus_grid = _grid(plus.position, profile)
                    env.step(_action(ActionKind.DOWN, plus_grid))
                    assigned = env.step(_action(ActionKind.UP, plus_grid))
                    self.assertEqual(
                        (len(mediator.paths), len(mediator.metros)), (1, 1)
                    )
                    button_grid = _grid(
                        mediator.path_to_button[route].position, profile
                    )
                    env.step(_action(ActionKind.DOWN, button_grid))
                    removed = env.step(_action(ActionKind.UP, button_grid))
                    self.assertEqual(
                        (len(mediator.paths), len(mediator.metros)), (0, 0)
                    )

                    infos = (fresh[4], assigned[4], removed[4])
                    frames = tuple(
                        _mask_cursors(result[0], profile, infos)
                        for result in (fresh, assigned, removed)
                    )
                    rows, columns = _digit_crop(profile, font)
                    crops = tuple(frame[:, rows, columns] for frame in frames)
                    expected_four = _expected_hud_frame(4, profile, font)[
                        :, rows, columns
                    ]
                    expected_three = _expected_hud_frame(3, profile, font)[
                        :, rows, columns
                    ]

                    self.assertFalse(np.array_equal(expected_four, expected_three))
                    self.assertTrue(np.array_equal(crops[0], expected_four))
                    self.assertTrue(np.array_equal(crops[1], expected_three))
                    self.assertTrue(np.array_equal(crops[2], expected_four))
                    self.assertTrue(np.array_equal(crops[0], crops[2]))
                    self.assertFalse(np.array_equal(crops[0], crops[1]))
                finally:
                    env.close()


if __name__ == "__main__":
    unittest.main()
