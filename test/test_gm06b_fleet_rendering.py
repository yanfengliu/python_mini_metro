from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path as FilesystemPath

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import config
from config import screen_color, screen_height, screen_width
from rendering.game_renderer import GameRenderer
from test.gm06b_fleet_ui_support import (
    control_pair,
    create_path,
    crop_bytes,
    fresh_mediator,
    point,
)


def _surface() -> pygame.Surface:
    result = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA, 32)
    result.fill(screen_color)
    return result


def _render(renderer: GameRenderer, mediator) -> pygame.Surface:
    result = _surface()
    renderer.draw(result, mediator, alpha=1.0)
    return result


def _clear_path_fleet(mediator, path) -> None:
    owned = {id(metro) for metro in path.metros}
    path.metros[:] = []
    mediator.metros[:] = [metro for metro in mediator.metros if id(metro) not in owned]


def _render_state(mediator) -> tuple[object, ...]:
    return (
        tuple(id(path) for path in mediator.paths),
        tuple(id(metro) for metro in mediator.metros),
        tuple(
            (
                id(metro),
                bool(getattr(metro, "is_unassignment_queued", False)),
                point(metro).to_tuple(),
                id(metro.current_segment),
                metro.current_segment_idx,
            )
            for metro in mediator.metros
        ),
        tuple(
            (
                id(button),
                point(button).to_tuple(),
                bool(getattr(button, "is_hovered", False)),
                bool(getattr(button, "show_cross", False)),
            )
            for button in mediator.buttons
        ),
        mediator.available_locomotives,
    )


class TestGM06bFleetButtonRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.mediator = fresh_mediator(6230)
        self.path = create_path(self.mediator)
        _clear_path_fleet(self.mediator, self.path)
        self.mediator.num_metros = 4
        self.path_button = self.mediator.path_to_button[self.path]
        self.assign, self.unassign = control_pair(self.mediator, self.path_button)
        self.renderer = GameRenderer()

    def _assign_many(self, count: int) -> None:
        for _ in range(count):
            self.assertTrue(self.mediator.assign_locomotive(self.path))

    def _unassign_crop(self) -> bytes:
        return crop_bytes(_render(self.renderer, self.mediator), self.unassign)

    def test_multi_queue_badge_is_orthogonal_to_minus_enable_and_hover(self) -> None:
        self._assign_many(3)
        enabled = self._unassign_crop()
        self.unassign.on_hover()
        enabled_hover = self._unassign_crop()
        self.assertNotEqual(enabled_hover, enabled)
        self.unassign.on_exit()

        self.assertTrue(self.mediator.queue_locomotive_unassignment(self.path))
        one_queue = self._unassign_crop()
        self.assertNotEqual(one_queue, enabled)
        self.unassign.on_hover()
        one_queue_hover = self._unassign_crop()
        self.assertNotEqual(one_queue_hover, one_queue)
        self.unassign.on_exit()

        self.assertTrue(self.mediator.queue_locomotive_unassignment(self.path))
        two_queues = self._unassign_crop()
        self.assertNotEqual(two_queues, one_queue)
        self.assertTrue(self.mediator.queue_locomotive_unassignment(self.path))
        disabled_queued = self._unassign_crop()
        self.assertNotEqual(disabled_queued, two_queues)

        self.unassign.on_hover()
        disabled_hover_attempt = self._unassign_crop()
        self.assertEqual(disabled_hover_attempt, disabled_queued)
        self.assertFalse(self.mediator.queue_locomotive_unassignment(self.path))

    def test_assignment_and_immediate_detachment_recompute_control_state(self) -> None:
        enabled_plus = crop_bytes(
            _render(self.renderer, self.mediator),
            self.assign,
        )
        self.mediator.num_metros = 1
        self.assertTrue(self.mediator.assign_locomotive(self.path))
        assigned_plus = crop_bytes(_render(self.renderer, self.mediator), self.assign)
        self.assertNotEqual(assigned_plus, enabled_plus)

        metro = self.path.metros[0]
        station = self.path.stations[0]
        metro.current_station = station
        metro.position = station.position
        self.assertTrue(self.mediator.queue_locomotive_unassignment(self.path))
        self.assertNotIn(metro, self.path.metros)
        self.assertNotIn(metro, self.mediator.metros)
        returned_plus = crop_bytes(_render(self.renderer, self.mediator), self.assign)
        self.assertEqual(returned_plus, enabled_plus)

    def test_locked_and_empty_slots_render_disabled_and_cannot_mutate(self) -> None:
        empty_button = next(
            button for button in self.mediator.path_buttons if button.path is None
        )
        empty_assign, empty_unassign = control_pair(self.mediator, empty_button)
        before = (
            tuple(id(metro) for metro in self.mediator.metros),
            tuple(id(path) for path in self.mediator.paths),
            self.mediator.available_locomotives,
        )
        empty_enabled = {
            crop_bytes(_render(self.renderer, self.mediator), empty_assign),
            crop_bytes(_render(self.renderer, self.mediator), empty_unassign),
        }
        empty_assign.on_hover()
        empty_unassign.on_hover()
        empty_hover = {
            crop_bytes(_render(self.renderer, self.mediator), empty_assign),
            crop_bytes(_render(self.renderer, self.mediator), empty_unassign),
        }

        self.assertEqual(empty_hover, empty_enabled)
        self.assertEqual(
            (
                tuple(id(metro) for metro in self.mediator.metros),
                tuple(id(path) for path in self.mediator.paths),
                self.mediator.available_locomotives,
            ),
            before,
        )


class TestGM06bQueuedMarkerAndPurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_queued_metro_marker_is_config_owned_visible_and_render_pure(self) -> None:
        mediator = fresh_mediator(6240)
        path = create_path(mediator)
        _clear_path_fleet(mediator, path)
        self.assertTrue(mediator.assign_locomotive(path))
        metro = path.metros[0]
        renderer = GameRenderer()
        config_names = tuple(name.lower() for name in dir(config))
        self.assertTrue(
            any(
                "metro" in name and "queue" in name and "color" in name
                for name in config_names
            )
        )
        self.assertTrue(
            any(
                "metro" in name and "queue" in name and "width" in name
                for name in config_names
            )
        )

        metro.is_unassignment_queued = False
        ordinary = crop_bytes(_render(renderer, mediator), metro, half_width=50)
        metro.is_unassignment_queued = True
        before = _render_state(mediator)
        queued_surface = _render(renderer, mediator)
        queued = crop_bytes(queued_surface, metro, half_width=50)
        second_surface = _render(renderer, mediator)

        self.assertNotEqual(queued, ordinary)
        self.assertEqual(
            pygame.image.tobytes(queued_surface, "RGBA"),
            pygame.image.tobytes(second_surface, "RGBA"),
        )
        self.assertEqual(_render_state(mediator), before)
        self.assertEqual(renderer.network_renderer.cache_entry_count, 1)
        self.assertEqual(renderer.network_renderer.cache_rebuild_count, 1)

    def test_ui_production_files_retain_selected_physical_line_boundaries(self) -> None:
        source = FilesystemPath(__file__).resolve().parents[1] / "src"
        below_500 = (
            source / "fleet_input.py",
            source / "input_coordinator.py",
            source / "rendering" / "game_renderer.py",
            source / "ui" / "fleet_button.py",
            source / "entity" / "metro.py",
            source / "rl" / "privileged_oracle.py",
            source / "rl" / "demonstrator.py",
        )
        for path in below_500:
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertLess(len(path.read_text(encoding="utf-8").splitlines()), 500)
        mediator = source / "mediator.py"
        self.assertLess(len(mediator.read_text(encoding="utf-8").splitlines()), 1_000)


if __name__ == "__main__":
    unittest.main()
