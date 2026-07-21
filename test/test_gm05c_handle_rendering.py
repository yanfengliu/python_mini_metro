from __future__ import annotations

import gc
import importlib
import os
import sys
import unittest
import weakref
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

import config
from config import path_order_shift, screen_color
from entity.path import Path
from geometry.point import Point
from path_redraw import PathRedrawGesture
from rendering.game_renderer import GameRenderer
from rendering.layout import build_visual_path
from rendering.network_renderer import (
    INVALID_PREVIEW_COLOR,
    NetworkRenderer,
    NetworkStyle,
)
from rendering.path_handle_renderer import removal_on_layout
from ui.path_button import INVALID_OUTLINE_COLOR


class StationStub:
    def __init__(
        self,
        station_id: str,
        x: float,
        y: float,
        log: list[str] | None = None,
    ) -> None:
        self.id = station_id
        self.position = Point(x, y)
        self.log = log

    def draw(self, surface, **kwargs) -> None:
        del surface, kwargs
        if self.log is not None:
            self.log.append("station")


class RecordingEntity:
    def __init__(self, label: str, log: list[str]) -> None:
        self.label = label
        self.log = log

    def draw(self, surface, **kwargs) -> None:
        del surface, kwargs
        self.log.append(self.label)


class RecordingNetworkRenderer:
    def __init__(self, log: list[str], path: Path) -> None:
        self.log = log
        self.path = path

    def draw(self, surface, paths):
        del surface
        self.log.append("network")
        if tuple(paths) != (self.path,):
            raise AssertionError("renderer received a different path")
        return (build_visual_path(self.path, 0.0, path_order_shift),)

    def clear_preview_cache(self) -> None:
        pass


class RecordingHandleRenderer:
    def __init__(self, log: list[str] | None = None) -> None:
        self.log = log
        self.leaders: tuple[object, ...] = ()
        self.markers: tuple[object, ...] = ()

    def draw_leaders(self, surface, handles) -> None:
        del surface
        self.leaders = tuple(handles)
        if self.log is not None:
            self.log.append("leaders")

    def draw_markers(self, surface, handles, *, selected=None, invalid=False) -> None:
        del surface, selected, invalid
        self.markers = tuple(handles)
        if self.log is not None:
            self.log.append("markers")

    def draw_shortening_removal(
        self, surface, segment, *, color, invalid=False
    ) -> None:
        del surface, segment, color, invalid


def path_handles_module():
    return importlib.import_module("path_handles")


def path_handle_renderer():
    module = importlib.import_module("rendering.path_handle_renderer")
    return module.PathHandleRenderer()


def build_path(
    stations: list[StationStub],
    *,
    color: tuple[int, int, int] = (30, 90, 220),
    loop: bool = False,
) -> Path:
    path = Path(color)
    path.stations[:] = stations
    path.is_looped = loop
    path.update_segments()
    return path


def make_state(
    paths: list[Path],
    stations: list[StationStub],
    *,
    selection=None,
    metros=(),
    buttons=(),
):
    return SimpleNamespace(
        paths=paths,
        stations=stations,
        metros=list(metros),
        buttons=list(buttons),
        path_buttons=[],
        speed_buttons=[],
        path_redraw=None,
        path_edit_selection=selection,
        time_ms=0,
        deliveries=0,
        line_credits=0,
        is_game_over=False,
    )


def surface_bytes(surface: pygame.Surface) -> bytes:
    return pygame.image.tobytes(surface, "RGBA")


def pixel(surface: pygame.Surface, position) -> tuple[int, int, int, int]:
    x, y = position
    return tuple(surface.get_at((round(x), round(y))))


class TestGM05cHandleRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.size = (520, 320)
        self.stations = [
            StationStub("A", 100, 150),
            StationStub("B", 260, 150),
            StationStub("C", 420, 150),
        ]
        self.path = build_path(self.stations)
        self.state = make_state([self.path], self.stations)

    def test_invalid_feedback_uses_one_existing_red(self) -> None:
        self.assertEqual(config.path_handle_invalid_color, INVALID_PREVIEW_COLOR)
        self.assertEqual(config.path_handle_invalid_color, INVALID_OUTLINE_COLOR)

    def handles(self):
        return tuple(
            path_handles_module().build_path_handles_for_state(
                self.state,
                self.path,
                viewport_size=self.size,
            )
        )

    def test_game_renderer_places_leaders_below_entities_and_markers_below_controls(
        self,
    ) -> None:
        module = path_handles_module()
        log: list[str] = []
        stations = [
            StationStub("A", 100, 150, log),
            StationStub("B", 260, 150, log),
        ]
        path = build_path(stations)
        state = make_state(
            [path],
            stations,
            selection=module.PathEditSelection(path),
            metros=[RecordingEntity("metro", log)],
            buttons=[RecordingEntity("button", log)],
        )
        handles = RecordingHandleRenderer(log)
        renderer = GameRenderer(
            network_renderer=RecordingNetworkRenderer(log, path),
            path_handle_renderer=handles,
        )

        with patch.object(
            renderer, "_draw_hud", side_effect=lambda *_: log.append("hud")
        ):
            renderer.draw(pygame.Surface(self.size, pygame.SRCALPHA, 32), state)

        self.assertEqual(
            log,
            [
                "network",
                "leaders",
                "station",
                "station",
                "metro",
                "markers",
                "button",
                "hud",
            ],
        )
        self.assertTrue(handles.leaders)
        self.assertEqual(handles.leaders, handles.markers)

    def test_active_handle_empty_pointer_renders_from_primitive_position(self) -> None:
        module = path_handles_module()
        handle = next(value for value in self.handles() if value.kind == "end")
        edit = module.PathHandleEdit.begin(self.path, handle)
        self.assertIsNotNone(edit)
        assert edit is not None
        self.state.path_redraw = PathRedrawGesture(
            self.path,
            handle_edit=edit.move_to((475, 80)),
        )

        GameRenderer().draw(pygame.Surface(self.size, pygame.SRCALPHA, 32), self.state)

    def test_endpoint_insertion_envelope_selected_and_invalid_pixels(self) -> None:
        handles = self.handles()
        endpoint = next(handle for handle in handles if handle.kind == "start")
        insertion = next(handle for handle in handles if handle.kind == "insert")
        renderer = path_handle_renderer()

        endpoint_surface = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        insertion_surface = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        renderer.draw_markers(endpoint_surface, (endpoint,))
        renderer.draw_markers(insertion_surface, (insertion,))

        self.assertGreater(pixel(endpoint_surface, endpoint.center)[3], 0)
        self.assertEqual(pixel(insertion_surface, insertion.center)[3], 0)
        cx, cy = insertion.center
        radius = insertion.hit_radius
        for edge in (
            (cx + radius, cy),
            (cx - radius, cy),
            (cx, cy + radius),
            (cx, cy - radius),
        ):
            with self.subTest(edge=edge):
                self.assertGreater(pixel(insertion_surface, edge)[3], 0)
        self.assertEqual(pixel(insertion_surface, (cx + radius + 3, cy))[3], 0)

        normal = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        selected = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        invalid = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        renderer.draw_markers(normal, (endpoint,))
        renderer.draw_markers(selected, (endpoint,), selected=endpoint)
        renderer.draw_markers(invalid, (endpoint,), selected=endpoint, invalid=True)
        self.assertNotEqual(surface_bytes(normal), surface_bytes(selected))
        self.assertNotEqual(surface_bytes(selected), surface_bytes(invalid))
        invalid_rgb = pygame.surfarray.array3d(invalid)
        self.assertTrue(
            (
                (invalid_rgb[:, :, 0] > invalid_rgb[:, :, 1] + 60)
                & (invalid_rgb[:, :, 0] > invalid_rgb[:, :, 2] + 60)
            ).any()
        )

    def test_leader_pixels_connect_canonical_anchor_to_relocated_center(self) -> None:
        handle = next(item for item in self.handles() if item.anchor != item.center)
        surface = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        path_handle_renderer().draw_leaders(surface, (handle,))
        midpoint = (
            (handle.anchor[0] + handle.center[0]) / 2,
            (handle.anchor[1] + handle.center[1]) / 2,
        )
        self.assertGreater(pixel(surface, midpoint)[3], 0)

    def test_injected_network_style_cannot_redefine_canonical_handles(self) -> None:
        module = path_handles_module()
        other = build_path(self.stations, color=(220, 70, 40))
        self.state.paths[:] = [other, self.path]
        self.state.path_edit_selection = module.PathEditSelection(self.path)
        expected = self.handles()

        captured = []
        for spacing in (path_order_shift, 47):
            recorder = RecordingHandleRenderer()
            renderer = GameRenderer(
                network_renderer=NetworkRenderer(
                    NetworkStyle(
                        lane_spacing=spacing,
                        stroke_width=8,
                        halo_width=14,
                        supersample=2,
                    )
                ),
                path_handle_renderer=recorder,
            )
            with patch.object(renderer, "_draw_hud"):
                renderer.draw(
                    pygame.Surface(self.size, pygame.SRCALPHA, 32), self.state
                )
            captured.append(recorder.markers)

        self.assertEqual(captured, [expected, expected])

    def test_arbitrary_insertion_previews_match_committed_pixels(self) -> None:
        style = NetworkStyle(
            lane_spacing=10,
            stroke_width=8,
            halo_width=14,
            supersample=2,
        )
        cases = (
            ("start", 0, False, Point(55, 70)),
            ("end", 3, False, Point(470, 250)),
            ("interior", 1, False, Point(180, 65)),
            ("loop-closure", 3, True, Point(300, 265)),
        )
        for name, slot, loop, temp_point in cases:
            with self.subTest(case=name):
                pointer = StationStub("pointer", temp_point.left, temp_point.top)
                candidate_stations = list(self.stations)
                candidate_stations.insert(slot, pointer)
                candidate = build_path(candidate_stations, loop=loop)
                committed = pygame.Surface(self.size, pygame.SRCALPHA, 32)
                preview = pygame.Surface(self.size, pygame.SRCALPHA, 32)

                NetworkRenderer(style).draw(committed, [candidate], orders=[0.5])
                NetworkRenderer(style).draw_preview(
                    preview,
                    path_id=candidate.id,
                    color=candidate.color,
                    stations=self.stations,
                    order=0.5,
                    loop=loop,
                    temp_point=temp_point,
                    temp_insertion_index=slot,
                    invalid=False,
                )

                self.assertEqual(surface_bytes(preview), surface_bytes(committed))

    def test_shortening_overlay_is_explicit_and_never_erases_crossing(self) -> None:
        style = NetworkStyle(stroke_width=8, halo_width=14, supersample=2)
        horizontal = build_path(
            [StationStub("L", 50, 160), StationStub("R", 470, 160)],
            color=(210, 45, 45),
        )
        vertical = build_path(
            [StationStub("T", 260, 30), StationStub("D", 260, 290)],
            color=(40, 80, 220),
        )
        surface = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        surface.fill(screen_color)
        NetworkRenderer(style).draw(surface, [horizontal, vertical], orders=[0, 0])
        before = surface.copy()

        path_handle_renderer().draw_shortening_removal(
            surface,
            ((50.0, 160.0), (470.0, 160.0)),
            color=horizontal.color,
        )

        before_rgb = pygame.surfarray.array3d(before)
        after_rgb = pygame.surfarray.array3d(surface)
        changed = (before_rgb != after_rgb).any(axis=2)
        self.assertTrue(
            changed[80:220, 150:170].any(),
            "feedback must be away from the cursor",
        )
        self.assertTrue(
            changed[250:271, 150:171].any(),
            "crossing needs an explicit strike",
        )
        crossing = after_rgb[250:271, 150:171]
        crossing_changed = changed[250:271, 150:171]
        self.assertFalse(
            ((crossing == screen_color).all(axis=2) & crossing_changed).any()
        )

    def test_shortening_overlay_tracks_the_selected_shared_route_lane(self) -> None:
        stations = [StationStub("A", 100, 150), StationStub("B", 420, 150)]
        lower = build_path(stations, color=(210, 45, 45))
        upper = build_path(stations, color=(40, 80, 220))
        layouts = NetworkRenderer().draw(
            pygame.Surface(self.size, pygame.SRCALPHA, 32),
            [lower, upper],
        )
        raw = ((100.0, 150.0), (420.0, 150.0))

        removal = removal_on_layout(upper, layouts[1], raw)

        self.assertIsNotNone(removal)
        assert removal is not None
        selected_segment = next(
            segment for segment in layouts[1].segments if segment.kind == "path"
        )
        self.assertEqual(removal, (selected_segment.start, selected_segment.end))
        self.assertNotEqual(removal, raw)

    def test_caches_stay_bounded_handles_repeat_and_retain_no_gameplay_refs(
        self,
    ) -> None:
        handles = self.handles()
        before = (
            tuple(station.position.to_tuple() for station in self.stations),
            tuple(
                (segment.segment_start.to_tuple(), segment.segment_end.to_tuple())
                for segment in self.path.segments
            ),
        )
        network = NetworkRenderer()
        handle_renderer = path_handle_renderer()
        first = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        second = pygame.Surface(self.size, pygame.SRCALPHA, 32)

        network.draw(first, [self.path])
        network.draw(second, [self.path])
        self.assertEqual(
            (network.cache_entry_count, network.cache_rebuild_count), (1, 1)
        )
        self.assertEqual(network.preview_cache_entry_count, 0)

        preview_kwargs = dict(
            path_id=self.path.id,
            color=self.path.color,
            stations=self.stations,
            order=0,
            loop=False,
            temp_point=Point(180, 65),
            temp_insertion_index=1,
            invalid=False,
        )
        network.draw_preview(first, **preview_kwargs)
        network.draw_preview(second, **preview_kwargs)
        self.assertEqual(
            (network.preview_cache_entry_count, network.preview_cache_rebuild_count),
            (1, 1),
        )
        self.assertEqual(
            (network.cache_entry_count, network.cache_rebuild_count), (1, 1)
        )

        handle_frames = []
        for _ in range(2):
            frame = pygame.Surface(self.size, pygame.SRCALPHA, 32)
            handle_renderer.draw_leaders(frame, handles)
            handle_renderer.draw_markers(frame, handles)
            handle_frames.append(surface_bytes(frame))
        self.assertEqual(handle_frames[0], handle_frames[1])
        self.assertEqual(
            (network.cache_entry_count, network.preview_cache_entry_count), (1, 1)
        )
        self.assertEqual(
            before,
            (
                tuple(station.position.to_tuple() for station in self.stations),
                tuple(
                    (segment.segment_start.to_tuple(), segment.segment_end.to_tuple())
                    for segment in self.path.segments
                ),
            ),
        )

        path_ref = weakref.ref(self.path)
        station_ref = weakref.ref(self.stations[0])
        path = self.path
        stations = self.stations
        state = self.state
        del preview_kwargs, handles, path, stations, state
        self.path = None
        self.stations = []
        self.state = None
        gc.collect()
        self.assertIsNone(path_ref())
        self.assertIsNone(station_ref())


if __name__ == "__main__":
    unittest.main()
