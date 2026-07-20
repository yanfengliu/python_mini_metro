from __future__ import annotations

import gc
import importlib
import os
import sys
import unittest
import weakref
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_color
from entity.path import Path
from geometry.circle import Circle
from geometry.point import Point
from path_redraw import PathRedrawGesture
from rendering.game_renderer import GameRenderer
from rendering.layout import (
    VisualPath,
    build_preview_visual_path,
    build_visual_path,
)
from rendering.network_renderer import NetworkRenderer, NetworkStyle
from ui.path_button import (
    INVALID_OUTLINE_COLOR,
    SELECTED_OUTLINE_COLOR,
    PathButton,
)


class StationStub:
    def __init__(self, station_id: str, x: float, y: float) -> None:
        self.id = station_id
        self.position = Point(x, y)


class GestureStub:
    def __init__(
        self,
        path: Path,
        stations: list[StationStub],
        *,
        loop: bool = False,
        temp_point: Point | None = None,
        invalid: bool = False,
    ) -> None:
        self.path = path
        self.stations = stations
        self.loop = loop
        self.temp_point = temp_point
        self.invalid = invalid


def build_path(
    stations: list[StationStub],
    *,
    color: tuple[int, int, int] = (20, 100, 210),
    loop: bool = False,
) -> Path:
    path = Path(color)
    path.stations[:] = stations
    path.is_looped = loop
    path.update_segments()
    return path


def surface_bytes(surface: pygame.Surface) -> bytes:
    return pygame.image.tobytes(surface, "RGBA")


class RecordingNetworkRenderer:
    def __init__(self, log: list[str], target: Path) -> None:
        self.log = log
        self.target = target
        self.preview_kwargs: dict[str, object] | None = None

    def draw(self, surface, paths):
        del surface
        self.log.append("network")
        self.assert_exact_paths(paths)
        return (VisualPath(self.target.id, self.target.color, 1.5, False, ()),)

    def assert_exact_paths(self, paths) -> None:
        if len(paths) != 1 or paths[0] is not self.target:
            raise AssertionError("renderer did not preserve exact live path identity")

    def draw_preview(self, surface, **kwargs):
        del surface
        self.log.append("preview")
        self.preview_kwargs = kwargs


class RecordingEntity:
    def __init__(self, label: str, log: list[str]) -> None:
        self.label = label
        self.log = log

    def draw(self, surface, **kwargs) -> None:
        del surface, kwargs
        self.log.append(self.label)


class RecordingPathButton(RecordingEntity):
    def __init__(self, label: str, log: list[str], path: Path) -> None:
        super().__init__(label, log)
        self.path = path
        self.is_locked = False
        self.show_cross = True
        self.observed_kwargs: dict[str, object] | None = None

    def draw(self, surface, **kwargs) -> None:
        del surface
        self.observed_kwargs = kwargs
        self.log.append(self.label)


class TestGM05bPreviewRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.style = NetworkStyle(
            lane_spacing=10,
            stroke_width=8,
            halo_width=14,
            supersample=2,
        )
        self.stations = [
            StationStub("A", 35, 40),
            StationStub("B", 130, 45),
            StationStub("C", 155, 140),
        ]

    def test_preview_layout_matches_committed_geometry_without_mutation(self) -> None:
        cases = (
            (self.stations, False, -0.5),
            (self.stations, True, 1.0),
            (list(reversed(self.stations)), False, 1.5),
            (list(reversed(self.stations)), True, -1.5),
        )
        for stations, loop, order in cases:
            with self.subTest(loop=loop, order=order, reversed=stations[0].id == "C"):
                path = build_path(stations, loop=loop)
                before = tuple((item.id, item.position.to_tuple()) for item in stations)

                expected = build_visual_path(path, order, self.style.lane_spacing)
                actual = build_preview_visual_path(
                    path_id=path.id,
                    color=path.color,
                    stations=stations,
                    order=order,
                    lane_spacing=self.style.lane_spacing,
                    loop=loop,
                    temp_point=stations[-1].position,
                )

                self.assertEqual(actual, expected)
                self.assertEqual(
                    tuple((item.id, item.position.to_tuple()) for item in stations),
                    before,
                )

    def test_isolated_preview_pixels_match_committed_candidate(self) -> None:
        for loop, order in ((False, -0.5), (True, 1.5)):
            with self.subTest(loop=loop, order=order):
                candidate = build_path(list(reversed(self.stations)), loop=loop)
                committed = pygame.Surface((220, 180), pygame.SRCALPHA, 32)
                preview = pygame.Surface((220, 180), pygame.SRCALPHA, 32)
                repeated = pygame.Surface((220, 180), pygame.SRCALPHA, 32)
                committed_renderer = NetworkRenderer(self.style)
                preview_renderer = NetworkRenderer(self.style)

                committed_renderer.draw(committed, [candidate], orders=[order])
                kwargs = dict(
                    path_id=candidate.id,
                    color=candidate.color,
                    stations=candidate.stations,
                    order=order,
                    loop=loop,
                    temp_point=None,
                    invalid=False,
                )
                preview_renderer.draw_preview(preview, **kwargs)
                preview_renderer.draw_preview(repeated, **kwargs)

                self.assertEqual(surface_bytes(preview), surface_bytes(committed))
                self.assertEqual(surface_bytes(repeated), surface_bytes(preview))
                self.assertEqual(preview_renderer.preview_cache_rebuild_count, 1)

    def test_isolated_preview_matches_selected_shared_lane_layout(self) -> None:
        shared = self.stations[:2]
        other = build_path(shared, color=(210, 40, 40))
        selected = build_path(self.stations, color=(20, 100, 210))
        layouts = NetworkRenderer(self.style).draw(
            pygame.Surface((220, 180), pygame.SRCALPHA, 32),
            [other, selected],
        )
        selected_layout = layouts[1]
        committed = pygame.Surface((220, 180), pygame.SRCALPHA, 32)
        preview = pygame.Surface((220, 180), pygame.SRCALPHA, 32)

        NetworkRenderer(self.style).draw(
            committed, [selected], orders=[selected_layout.order]
        )
        NetworkRenderer(self.style).draw_preview(
            preview,
            path_id=selected.id,
            color=selected.color,
            stations=selected.stations,
            order=selected_layout.order,
            loop=False,
            temp_point=None,
            invalid=False,
        )

        self.assertEqual(selected_layout.order, 0.5)
        self.assertEqual(surface_bytes(preview), surface_bytes(committed))

    def test_dynamic_preview_extends_same_geometry_without_gameplay_segments(
        self,
    ) -> None:
        temp_point = Point(195, 115)
        preview = build_preview_visual_path(
            path_id="preview",
            color=(20, 100, 210),
            stations=self.stations[:2],
            order=0.5,
            lane_spacing=self.style.lane_spacing,
            loop=False,
            temp_point=temp_point,
        )
        committed = build_path([*self.stations[:2], StationStub("pointer", 195, 115)])
        expected = build_visual_path(committed, 0.5, self.style.lane_spacing)

        self.assertEqual(
            tuple(
                (segment.kind, segment.start, segment.end)
                for segment in preview.segments
            ),
            tuple(
                (segment.kind, segment.start, segment.end)
                for segment in expected.segments
            ),
        )
        self.assertIsNone(preview.segments[-1].end_station_id)

    def test_old_network_overlay_intentionally_differs_at_crossing(self) -> None:
        horizontal = build_path(
            [StationStub("L", 25, 90), StationStub("R", 195, 90)],
            color=(200, 30, 30),
        )
        vertical_stations = [StationStub("T", 110, 15), StationStub("D", 110, 165)]
        vertical = build_path(vertical_stations, color=(30, 60, 210))
        globally_composited = pygame.Surface((220, 180), pygame.SRCALPHA, 32)
        overlay = pygame.Surface((220, 180), pygame.SRCALPHA, 32)

        NetworkRenderer(self.style).draw(
            globally_composited,
            [horizontal, vertical],
            orders=[0, 0],
        )
        overlay_renderer = NetworkRenderer(self.style)
        overlay_renderer.draw(overlay, [horizontal], orders=[0])
        overlay_renderer.draw_preview(
            overlay,
            path_id=vertical.id,
            color=vertical.color,
            stations=vertical_stations,
            order=0,
            loop=False,
            temp_point=None,
            invalid=False,
        )

        self.assertNotEqual(surface_bytes(overlay), surface_bytes(globally_composited))
        self.assertEqual(overlay.get_at((105, 90))[:3], screen_color)

    def test_preview_cache_is_bounded_exact_and_retains_no_gameplay_objects(
        self,
    ) -> None:
        renderer = NetworkRenderer(self.style)
        surface = pygame.Surface((220, 180), pygame.SRCALPHA, 32)
        stations = [StationStub("A", 30, 30), StationStub("B", 120, 60)]
        path = build_path(stations)
        gesture = GestureStub(path, stations, temp_point=Point(180, 140))
        path_ref = weakref.ref(path)
        station_ref = weakref.ref(stations[0])
        gesture_ref = weakref.ref(gesture)

        kwargs = dict(
            path_id=path.id,
            color=path.color,
            stations=gesture.stations,
            order=0.5,
            loop=False,
            temp_point=gesture.temp_point,
            invalid=False,
        )
        renderer.draw_preview(surface, **kwargs)
        renderer.draw_preview(surface, **kwargs)
        self.assertEqual(renderer.preview_cache_entry_count, 1)
        self.assertEqual(renderer.preview_cache_rebuild_count, 1)
        self.assertEqual(renderer.cache_rebuild_count, 0)
        assert renderer._preview_cache_surface is not None
        self.assertLess(
            renderer._preview_cache_surface.get_width(), surface.get_width()
        )
        self.assertLess(
            renderer._preview_cache_surface.get_height(), surface.get_height()
        )

        renderer.draw_preview(surface, **{**kwargs, "temp_point": Point(175, 130)})
        renderer.draw_preview(surface, **{**kwargs, "invalid": True})
        self.assertEqual(renderer.preview_cache_entry_count, 1)
        self.assertEqual(renderer.preview_cache_rebuild_count, 3)
        self.assertEqual(renderer.cache_rebuild_count, 0)

        del kwargs
        del gesture
        del path
        del stations
        gc.collect()
        self.assertIsNone(path_ref())
        self.assertIsNone(station_ref())
        self.assertIsNone(gesture_ref())

    def test_static_cache_distinguishes_topology_change_from_same_route_noop(
        self,
    ) -> None:
        network = NetworkRenderer(self.style)
        renderer = GameRenderer(network_renderer=network)
        surface = pygame.Surface((220, 180), pygame.SRCALPHA, 32)
        path = build_path(self.stations[:2])
        state = SimpleNamespace(
            paths=[path],
            path_redraw=PathRedrawGesture(path),
            stations=[],
            metros=[],
            buttons=[],
            path_buttons=[],
            speed_buttons=[],
            time_ms=0,
            is_game_over=False,
        )

        with patch.object(renderer, "_draw_hud"):
            renderer.draw(surface, state)
            state.path_redraw = state.path_redraw.enter_station(self.stations[0])
            renderer.draw(surface, state)
            state.path_redraw = state.path_redraw.enter_station(self.stations[1])
            renderer.draw(surface, state)
            state.path_redraw = state.path_redraw.move_to(Point(180, 150))
            renderer.draw(surface, state)
            state.path_redraw = state.path_redraw.enter_station(self.stations[2])
            renderer.draw(surface, state)
            state.path_redraw = state.path_redraw.enter_station(self.stations[1])
            self.assertTrue(state.path_redraw.invalid)
            renderer.draw(surface, state)
            path.update_segments()
            renderer.draw(surface, state)
            self.assertEqual(network.cache_rebuild_count, 1)

            state.path_redraw = None
            renderer.draw(surface, state)
            self.assertEqual(network.preview_cache_entry_count, 0)

        path.stations.append(self.stations[2])
        path.update_segments()
        with patch.object(renderer, "_draw_hud"):
            renderer.draw(surface, state)
        self.assertEqual(network.cache_rebuild_count, 2)

    def test_game_renderer_draws_preview_below_entities_at_live_path_order(
        self,
    ) -> None:
        log: list[str] = []
        path = build_path(self.stations[:2])
        network = RecordingNetworkRenderer(log, path)
        renderer = GameRenderer(network_renderer=network)
        button = RecordingPathButton("button", log, path)
        gesture = GestureStub(
            path,
            self.stations,
            temp_point=Point(190, 150),
            invalid=True,
        )
        state = SimpleNamespace(
            paths=[path],
            path_redraw=gesture,
            stations=[RecordingEntity("station", log)],
            metros=[],
            buttons=[button],
            path_buttons=[button],
            speed_buttons=[],
            time_ms=0,
            deliveries=0,
            line_credits=0,
            is_game_over=False,
        )
        surface = pygame.Surface((220, 180), pygame.SRCALPHA, 32)

        with patch.object(
            renderer, "_draw_hud", side_effect=lambda *_: log.append("hud")
        ):
            renderer.draw(surface, state)

        self.assertEqual(log, ["network", "preview", "station", "button", "hud"])
        assert network.preview_kwargs is not None
        self.assertIs(network.preview_kwargs["stations"], gesture.stations)
        self.assertEqual(network.preview_kwargs["order"], 1.5)
        self.assertTrue(network.preview_kwargs["invalid"])
        assert button.observed_kwargs is not None
        self.assertTrue(button.observed_kwargs["is_selected"])
        self.assertTrue(button.observed_kwargs["is_invalid"])

    def test_selected_and_invalid_button_feedback_suppresses_cross_observationally(
        self,
    ) -> None:
        path = build_path(self.stations[:2], color=(35, 120, 220))
        button = PathButton(Circle((180, 180, 180), 30), Point(60, 60))
        button.assign_path(path)
        button.show_cross = True

        def render(*, selected: bool, invalid: bool = False) -> pygame.Surface:
            surface = pygame.Surface((120, 120), pygame.SRCALPHA, 32)
            button.draw(surface, is_selected=selected, is_invalid=invalid)
            return surface

        normal = render(selected=False)
        selected = render(selected=True)
        invalid = render(selected=True, invalid=True)

        self.assertEqual(normal.get_at((60, 60))[:3], (0, 0, 0))
        self.assertEqual(selected.get_at((60, 60))[:3], path.color)
        self.assertEqual(selected.get_at((94, 60))[:3], SELECTED_OUTLINE_COLOR)
        self.assertEqual(invalid.get_at((94, 60))[:3], INVALID_OUTLINE_COLOR)
        self.assertNotEqual(surface_bytes(selected), surface_bytes(invalid))
        self.assertTrue(button.show_cross)

    def test_active_preview_headless_render_allocates_no_entity_identity(self) -> None:
        from mediator import Mediator

        state = Mediator(seed=73)
        path = state.create_path_from_station_indices([0, 1], loop=False)
        assert path is not None
        state.path_redraw = GestureStub(
            path,
            list(state.stations[:3]),
            temp_point=Point(500, 400),
        )
        state.prepare_layout(640, 360)
        renderer = GameRenderer()
        surface = pygame.Surface((640, 360), pygame.SRCALPHA, 32)
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
                            f"preview render allocated an identity in {module_name}"
                        ),
                    )
                )
            renderer.draw(surface, state)

        self.assertIsNone(pygame.display.get_surface())


if __name__ == "__main__":
    unittest.main()
