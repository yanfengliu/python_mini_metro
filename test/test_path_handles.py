from __future__ import annotations

import gc
import math
import os
import sys
import unittest
import weakref
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from path_handles import (  # noqa: E402
    PathEditSelection,
    PathHandleEdit,
    build_path_handles_for_state,
    hit_test_path_handles,
)
from rl.protocol import (  # noqa: E402
    FAST_RENDER_PROFILE,
    FIDELITY_RENDER_PROFILE,
    canonical_to_action_coordinate,
    map_action_coordinate,
)


class PointStub:
    def __init__(self, left: float, top: float) -> None:
        self.left = left
        self.top = top

    def to_tuple(self) -> tuple[float, float]:
        return (self.left, self.top)


class StationStub:
    def __init__(self, name: str, left: float, top: float) -> None:
        self.id = name
        self.position = PointStub(left, top)
        self.size = 30

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StationStub) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class PathStub:
    def __init__(
        self, name: str, stations: list[StationStub], *, loop: bool = False
    ) -> None:
        self.id = name
        self.color = (30, 110, 210)
        self.stations = stations
        self.is_looped = loop


class ButtonStub:
    def __init__(self, left: float, top: float, radius: float = 30) -> None:
        self.position = PointStub(left, top)
        self.shape = SimpleNamespace(radius=radius)


def station(name: str, left: float, top: float) -> StationStub:
    return StationStub(name, left, top)


def route(
    *values: tuple[str, float, float], name: str = "path", loop: bool = False
) -> PathStub:
    return PathStub(name, [station(*value) for value in values], loop=loop)


def state_for(
    path: PathStub,
    *,
    paths: list[PathStub] | None = None,
    foreign_stations: tuple[StationStub, ...] = (),
    buttons: tuple[ButtonStub, ...] = (),
):
    path_values = [path] if paths is None else paths
    return SimpleNamespace(
        paths=path_values,
        stations=[*path.stations, *foreign_stations],
        path_buttons=list(buttons),
        speed_buttons=[],
        buttons=list(buttons),
    )


def handles(path: PathStub, *, state=None, viewport=(1000, 700)):
    state = state or state_for(path)
    return build_path_handles_for_state(state, path, viewport_size=viewport)


def by_kind(values, kind: str):
    return tuple(handle for handle in values if handle.kind == kind)


def distance(left, right) -> float:
    return math.hypot(left[0] - right[0], left[1] - right[1])


class TestPathEditSelection(unittest.TestCase):
    def test_selection_is_weak_and_resolves_one_exact_live_identity(self) -> None:
        path = route(("A", 250, 300), ("B", 450, 300))
        equal_alias = PathStub(path.id, list(path.stations))
        selection = PathEditSelection(path)

        self.assertIsInstance(selection.path_ref, weakref.ReferenceType)
        self.assertIs(selection.path_ref(), path)
        self.assertIs(selection.resolve([path]), path)
        self.assertIsNone(selection.resolve([equal_alias]))
        self.assertIsNone(selection.resolve([path, path]))

        retained = weakref.ref(path)
        del path
        gc.collect()
        self.assertIsNone(retained())
        self.assertIsNone(selection.path_ref())
        self.assertIsNone(selection.resolve([]))


class TestPathHandleGeometry(unittest.TestCase):
    def test_linear_endpoints_point_outward_and_edges_use_insertion_slots(self) -> None:
        path = route(("A", 250, 300), ("B", 450, 300), ("C", 650, 300))
        values = handles(path)
        endpoints = {
            handle.kind: handle for handle in values if handle.kind != "insert"
        }
        inserts = by_kind(values, "insert")

        self.assertEqual(set(endpoints), {"start", "end"})
        self.assertEqual(endpoints["start"].slot, 0)
        self.assertEqual(endpoints["end"].slot, 3)
        self.assertLess(endpoints["start"].center[0], endpoints["start"].anchor[0])
        self.assertGreater(endpoints["end"].center[0], endpoints["end"].anchor[0])
        self.assertEqual([handle.slot for handle in inserts], [1, 2])
        self.assertEqual(
            [handle.anchor for handle in inserts], [(350.0, 300.0), (550.0, 300.0)]
        )

        sample = values[0]
        self.assertIsInstance(sample.path_id, str)
        self.assertGreater(sample.hit_radius, 0)
        self.assertFalse(hasattr(sample, "path"))
        with self.assertRaises(FrozenInstanceError):
            sample.slot = 99

    def test_loops_have_all_physical_edges_but_no_endpoints(self) -> None:
        loop = route(
            ("A", 300, 220),
            ("B", 560, 260),
            ("C", 430, 500),
            loop=True,
        )
        values = handles(loop)
        self.assertEqual([item.kind for item in values], ["insert"] * 3)
        self.assertEqual([item.slot for item in values], [1, 2, 3])

        two = route(("A", 300, 300), ("B", 600, 300), loop=True)
        reverse = PathStub("reverse", list(reversed(two.stations)), loop=True)
        first = handles(two)
        second = handles(reverse)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].slot, 1)
        self.assertEqual(first[0].center, second[0].center)

    def test_relocation_clears_short_edges_foreign_stations_buttons_and_crossings(
        self,
    ) -> None:
        short = route(("A", 350, 300), ("B", 365, 300))
        short_values = handles(short)
        self.assertEqual(len(short_values), 3)
        for index, left in enumerate(short_values):
            for right in short_values[index + 1 :]:
                self.assertGreaterEqual(
                    distance(left.center, right.center),
                    left.hit_radius + right.hit_radius,
                )

        path = route(("A", 250, 300), ("B", 650, 300))
        blocker = station("foreign", 450, 300)
        button = ButtonStub(450, 300)
        insert = by_kind(
            handles(
                path,
                state=state_for(path, foreign_stations=(blocker,), buttons=(button,)),
            ),
            "insert",
        )[0]
        self.assertGreater(
            distance(insert.center, blocker.position.to_tuple()),
            blocker.size + insert.hit_radius,
        )
        self.assertGreater(
            distance(insert.center, button.position.to_tuple()),
            button.shape.radius + insert.hit_radius,
        )

        crossing = route(
            ("A", 250, 200),
            ("B", 650, 500),
            ("C", 250, 500),
            ("D", 650, 200),
        )
        crossing_inserts = by_kind(handles(crossing), "insert")
        self.assertEqual(crossing_inserts[0].anchor, crossing_inserts[2].anchor)
        self.assertNotEqual(crossing_inserts[0].center, crossing_inserts[2].center)

    def test_hud_viewport_and_registered_profile_round_trips_stay_clear(self) -> None:
        hud_route = route(("A", 80, 70), ("B", 300, 70))
        hud_insert = by_kind(handles(hud_route, viewport=(1920, 1080)), "insert")[0]
        self.assertFalse(
            0 <= hud_insert.center[0] <= 700 and 0 <= hud_insert.center[1] <= 140
        )

        path = route(("A", 500, 300), ("B", 950, 500), ("C", 1450, 300))
        for handle in handles(path, viewport=(1920, 1080)):
            x, y = handle.center
            self.assertLessEqual(handle.hit_radius, x)
            self.assertLessEqual(x, 1920 - handle.hit_radius)
            self.assertLessEqual(handle.hit_radius, y)
            self.assertLessEqual(y, 1080 - handle.hit_radius)
            for profile in (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE):
                grid = canonical_to_action_coordinate(round(x), round(y), profile)
                mapped = map_action_coordinate(*grid, profile)
                self.assertLessEqual(distance(mapped, handle.center), handle.hit_radius)

    def test_reversal_repeated_builds_and_degenerate_omission_are_stable(self) -> None:
        path = route(("A", 250, 260), ("B", 470, 410), ("C", 720, 250))
        repeated = handles(path)
        self.assertEqual(repeated, handles(path))
        reversed_path = PathStub("reverse", list(reversed(path.stations)))
        self.assertEqual(
            {item.center for item in repeated},
            {item.center for item in handles(reversed_path)},
        )

        collapsed = route(("A", 400, 300), ("B", 400, 300))
        self.assertEqual(handles(collapsed), ())
        collapsed.stations[1].position.left = math.nan
        self.assertEqual(handles(collapsed), ())

    def test_hit_testing_returns_unique_nearest_or_explicit_ambiguity(self) -> None:
        base = handles(route(("A", 250, 300), ("B", 650, 300)))
        first = replace(base[0], center=(90.0, 100.0), hit_radius=30.0)
        second = replace(base[1], center=(110.0, 100.0), hit_radius=30.0)

        unique = hit_test_path_handles((first, second), (92.0, 100.0))
        self.assertIs(unique.handle, first)
        self.assertFalse(unique.ambiguous)
        tied = hit_test_path_handles((first, second), (100.0, 100.0))
        self.assertIsNone(tied.handle)
        self.assertTrue(tied.ambiguous)
        miss = hit_test_path_handles((first, second), (300.0, 300.0))
        self.assertIsNone(miss.handle)
        self.assertFalse(miss.ambiguous)


class TestPathHandleEdit(unittest.TestCase):
    def setUp(self) -> None:
        self.path = route(("A", 250, 300), ("B", 450, 300), ("C", 650, 300))
        self.extra = station("D", 500, 500)
        self.active = [*self.path.stations, self.extra]
        values = handles(self.path)
        self.start = next(item for item in values if item.kind == "start")
        self.end = next(item for item in values if item.kind == "end")
        self.insert = next(
            item for item in values if item.kind == "insert" and item.slot == 1
        )

    def result(self, handle, target):
        edit = PathHandleEdit.begin(self.path, handle)
        self.assertIsNotNone(edit)
        assert edit is not None
        return edit.result([self.path], self.active, target)

    def test_endpoints_extend_and_shorten_exactly_one_station(self) -> None:
        self.assertEqual(
            self.result(self.start, self.extra), (self.path, [3, 0, 1, 2], False)
        )
        self.assertEqual(
            self.result(self.end, self.extra), (self.path, [0, 1, 2, 3], False)
        )
        self.assertEqual(
            self.result(self.start, self.path.stations[1]), (self.path, [1, 2], False)
        )
        self.assertEqual(
            self.result(self.end, self.path.stations[1]), (self.path, [0, 1], False)
        )
        self.assertIsNone(self.result(self.start, self.path.stations[0]))
        self.assertIsNone(self.result(self.start, self.path.stations[2]))

        two = route(("A", 250, 300), ("B", 650, 300))
        start = next(item for item in handles(two) if item.kind == "start")
        edit = PathHandleEdit.begin(two, start)
        self.assertIsNotNone(edit)
        assert edit is not None
        self.assertIsNone(edit.result([two], two.stations, two.stations[1]))

    def test_insertion_covers_linear_and_loop_closing_slots(self) -> None:
        self.assertEqual(
            self.result(self.insert, self.extra), (self.path, [0, 3, 1, 2], False)
        )
        self.assertIsNone(self.result(self.insert, self.path.stations[2]))

        loop = PathStub("loop", list(self.path.stations), loop=True)
        extra = station("E", 800, 500)
        closing = next(
            item for item in handles(loop) if item.slot == len(loop.stations)
        )
        edit = PathHandleEdit.begin(loop, closing)
        self.assertIsNotNone(edit)
        assert edit is not None
        self.assertEqual(
            edit.result([loop], [*loop.stations, extra], extra),
            (loop, [0, 1, 2, 3], True),
        )

    def test_stale_aliasing_and_malformed_sources_reject_by_identity(self) -> None:
        edit = PathHandleEdit.begin(self.path, self.insert)
        self.assertIsNotNone(edit)
        assert edit is not None
        self.assertIsNone(edit.result([], self.active, self.extra))
        self.assertIsNone(edit.result([self.path, self.path], self.active, self.extra))

        original = self.path.stations
        self.path.stations = list(original)
        self.path.stations[0] = station(original[0].id, 250, 300)
        self.assertIsNone(
            edit.result([self.path], [*self.path.stations, self.extra], self.extra)
        )
        self.path.stations = original
        self.path.is_looped = True
        self.assertIsNone(edit.result([self.path], self.active, self.extra))

        wrong_path = replace(self.insert, path_id="other")
        self.assertIsNone(PathHandleEdit.begin(self.path, wrong_path))
        wrong_slot = replace(self.insert, slot=99)
        self.assertIsNone(PathHandleEdit.begin(self.path, wrong_slot))

    def test_preview_specs_cover_arbitrary_slots_invalidity_and_shortening(
        self,
    ) -> None:
        start = PathHandleEdit.begin(self.path, self.start)
        insert = PathHandleEdit.begin(self.path, self.insert)
        self.assertIsNotNone(start)
        self.assertIsNotNone(insert)
        assert start is not None and insert is not None

        moving = start.move_to((120.0, 260.0))
        self.assertEqual(moving.preview_spec.stations, tuple(self.path.stations))
        self.assertFalse(moving.preview_spec.loop)
        self.assertEqual(moving.preview_spec.temp_point, (120.0, 260.0))
        self.assertEqual(moving.preview_spec.temp_insertion_index, 0)
        self.assertFalse(moving.preview_spec.invalid)

        insertion = insert.move_to(self.extra.position.to_tuple(), self.extra)
        self.assertEqual(
            insertion.preview_spec.stations,
            (self.path.stations[0], self.extra, *self.path.stations[1:]),
        )
        self.assertIsNone(insertion.preview_spec.temp_point)
        self.assertEqual(insertion.preview_spec.temp_insertion_index, 1)

        invalid = insert.move_to(
            self.path.stations[2].position.to_tuple(), self.path.stations[2]
        )
        self.assertTrue(invalid.preview_spec.invalid)
        shortened = start.move_to(
            self.path.stations[1].position.to_tuple(), self.path.stations[1]
        )
        self.assertEqual(shortened.preview_spec.stations, tuple(self.path.stations[1:]))
        self.assertIsNone(shortened.preview_spec.temp_point)
        self.assertEqual(
            set(shortened.preview_spec.removal_segment),
            {item.position.to_tuple() for item in self.path.stations[:2]},
        )
        end = PathHandleEdit.begin(self.path, self.end)
        self.assertIsNotNone(end)
        assert end is not None
        end_shortened = end.move_to(
            self.path.stations[-2].position.to_tuple(), self.path.stations[-2]
        )
        self.assertEqual(
            end_shortened.preview_spec.removal_segment[0],
            self.path.stations[-1].position.to_tuple(),
        )

    def test_descriptors_are_weak_but_active_edits_release_strong_sources(self) -> None:
        path = route(("A", 300, 300), ("B", 600, 300))
        state = state_for(path)
        descriptor = handles(path, state=state)[0]
        path_ref = weakref.ref(path)
        station_ref = weakref.ref(path.stations[0])
        del state
        edit = PathHandleEdit.begin(path, descriptor)
        self.assertIsNotNone(edit)
        del path
        gc.collect()
        self.assertIsNotNone(path_ref())
        self.assertIsNotNone(station_ref())
        del edit
        gc.collect()
        self.assertIsNone(path_ref())
        self.assertIsNone(station_ref())
        self.assertEqual(descriptor.path_id, "path")


if __name__ == "__main__":
    unittest.main()
