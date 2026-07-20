from copy import deepcopy

from test import mediator_test_support as support

# isort: split

from config import path_order_shift
from entity.metro import Metro
from entity.padding_segment import PaddingSegment
from entity.path import Path
from entity.path_segment import PathSegment
from geometry.point import Point
from mediator import Mediator
from rendering.layout import build_visual_path

_POSITIONS = (
    (100, 100),
    (300, 100),
    (300, 300),
    (500, 200),
)


def _build_network(route=(0, 1, 2), *, loop=False, path_order=0, metro_count=1):
    mediator = Mediator(seed=501)
    stations = list(mediator.all_stations[:4])
    for station, (left, top) in zip(stations, _POSITIONS):
        station.position = Point(left, top)
        station.shape.position = station.position
    mediator.stations = stations
    mediator.unlocked_num_stations = len(stations)

    color = next(iter(mediator.path_colors))
    path = Path(color)
    path.path_order = path_order
    for index in route:
        path.add_station(stations[index])
    if loop:
        path.set_loop()

    metros = [Metro() for _ in range(metro_count)]
    for metro in metros:
        path.add_metro(metro)
    mediator.paths = [path]
    mediator.metros = list(metros)
    mediator.path_colors[color] = True
    mediator.path_to_color[path] = color
    button = mediator.path_buttons[0]
    button.assign_path(path)
    mediator.path_to_button[path] = button
    return mediator, stations, path, metros


def _move_partway(path, metro):
    path.move_metro(metro, 400)
    assert metro.current_station is None


def _move_into_first_padding(path, metro):
    path.move_metro(metro, 2_000, should_stop_at_next_station=True)
    assert metro.current_station is path.stations[1]
    assert isinstance(metro.current_segment, PaddingSegment)
    path.move_metro(metro, 100)
    assert metro.current_station is None
    assert isinstance(metro.current_segment, PaddingSegment)


def _arrive_at_first_interior(path, metro):
    path.move_metro(metro, 2_000, should_stop_at_next_station=True)
    assert metro.current_station is path.stations[1]
    assert metro.just_arrived_and_stopped


def _arrive_forward_through_loop_closure(path, metro):
    _arrive_at_first_interior(path, metro)
    path.move_metro(metro, 1_000)
    path.move_metro(metro, 2_000, should_stop_at_next_station=True)
    assert metro.current_station is path.stations[2]
    path.move_metro(metro, 1_000)
    path.move_metro(metro, 2_000, should_stop_at_next_station=True)
    assert metro.current_station is path.stations[0]
    assert isinstance(metro.current_segment, PaddingSegment)


def _point(point):
    return (point.left, point.top)


def _logical_geometry(path):
    return tuple(
        (
            type(segment),
            id(segment.start_station) if segment.start_station is not None else None,
            id(segment.end_station) if segment.end_station is not None else None,
            _point(segment.segment_start),
            _point(segment.segment_end),
            segment.line.color,
            segment.line.width,
        )
        for segment in path.segments
    )


def _candidate(path, stations, loop):
    candidate = Path(path.color)
    candidate.path_order = path.path_order
    candidate.stations.extend(stations)
    candidate.is_looped = loop
    candidate.update_segments()
    return candidate


def _pose(metro):
    return {
        "position": metro.position,
        "coordinates": _point(metro.position),
        "speed": metro.speed,
        "heading": metro.shape.degrees,
        "current_station": metro.current_station,
        "stop_time": metro.stop_time_remaining_ms,
        "boarding_progress": metro.boarding_progress_ms,
        "just_arrived": metro.just_arrived_and_stopped,
        "passenger_list": metro.passengers,
        "passengers": tuple(metro.passengers),
    }


def _identity_snapshot(mediator, path, metros):
    button = mediator.path_to_button[path]
    return {
        "path": path,
        "path_id": path.id,
        "color": path.color,
        "path_order": path.path_order,
        "paths_list": mediator.paths,
        "paths": tuple(mediator.paths),
        "global_metros_list": mediator.metros,
        "global_metros": tuple(mediator.metros),
        "station_list": path.stations,
        "segment_list": path.segments,
        "path_segment_list": path.path_segments,
        "padding_segment_list": path.padding_segments,
        "fleet_list": path.metros,
        "fleet": tuple(path.metros),
        "button_map": mediator.path_to_button,
        "button_items": tuple(mediator.path_to_button.items()),
        "color_map": mediator.path_to_color,
        "color_items": tuple(mediator.path_to_color.items()),
        "button": button,
        "button_path": button.path,
        "button_cross": button.cross,
        "poses": tuple(_pose(metro) for metro in metros),
    }


def _transaction_snapshot(mediator, path, metros):
    snapshot = _identity_snapshot(mediator, path, metros)
    snapshot.update(
        {
            "stations": tuple(path.stations),
            "segments": tuple(path.segments),
            "path_segments": tuple(path.path_segments),
            "padding_segments": tuple(path.padding_segments),
            "is_looped": path.is_looped,
            "bindings": tuple(
                (metro.current_segment, metro.current_segment_idx, metro.is_forward)
                for metro in metros
            ),
            "python_rng": mediator.context.python_random.getstate(),
            "numpy_rng": deepcopy(mediator.context.numpy_random.bit_generator.state),
        }
    )
    return snapshot


class TestGM05aMetroContinuity(support.MediatorTestCase):
    def _assert_pose_unchanged(self, metro, before):
        self.assertIs(metro.position, before["position"])
        self.assertEqual(_point(metro.position), before["coordinates"])
        self.assertEqual(metro.speed, before["speed"])
        self.assertEqual(metro.shape.degrees, before["heading"])
        self.assertIs(metro.current_station, before["current_station"])
        self.assertEqual(metro.stop_time_remaining_ms, before["stop_time"])
        self.assertEqual(metro.boarding_progress_ms, before["boarding_progress"])
        self.assertEqual(metro.just_arrived_and_stopped, before["just_arrived"])
        self.assertIs(metro.passengers, before["passenger_list"])
        self.assertEqual(tuple(metro.passengers), before["passengers"])

    def _assert_identity_preserved(self, mediator, path, metros, before):
        self.assertIs(path, before["path"])
        self.assertEqual(path.id, before["path_id"])
        self.assertIs(path.color, before["color"])
        self.assertEqual(path.path_order, before["path_order"])
        self.assertIs(mediator.paths, before["paths_list"])
        self.assertEqual(tuple(mediator.paths), before["paths"])
        self.assertIs(mediator.metros, before["global_metros_list"])
        self.assertEqual(tuple(mediator.metros), before["global_metros"])
        self.assertIs(path.stations, before["station_list"])
        self.assertIs(path.segments, before["segment_list"])
        self.assertIs(path.path_segments, before["path_segment_list"])
        self.assertIs(path.padding_segments, before["padding_segment_list"])
        self.assertIs(path.metros, before["fleet_list"])
        self.assertEqual(tuple(path.metros), before["fleet"])
        self.assertIs(mediator.path_to_button, before["button_map"])
        self.assertEqual(tuple(mediator.path_to_button.items()), before["button_items"])
        self.assertIs(mediator.path_to_color, before["color_map"])
        self.assertEqual(tuple(mediator.path_to_color.items()), before["color_items"])
        self.assertIs(before["button"].path, before["button_path"])
        self.assertIs(before["button"].cross, before["button_cross"])
        for metro, pose in zip(metros, before["poses"]):
            self._assert_pose_unchanged(metro, pose)

    def _assert_candidate_geometry(self, path, stations, loop):
        expected = _candidate(path, stations, loop)
        self.assertEqual(_logical_geometry(path), _logical_geometry(expected))
        actual_visual = build_visual_path(path, -0.5, path_order_shift)
        expected_visual = build_visual_path(expected, -0.5, path_order_shift)
        self.assertEqual(actual_visual.segments, expected_visual.segments)
        self.assertEqual(actual_visual.color, expected_visual.color)
        self.assertEqual(actual_visual.order, expected_visual.order)
        self.assertEqual(actual_visual.is_looped, expected_visual.is_looped)

    def _assert_rejected_unchanged(
        self, mediator, path, metros, station_indices, *, loop
    ):
        before = _transaction_snapshot(mediator, path, metros)
        self.assertFalse(mediator.replace_path(path, station_indices, loop=loop))
        self._assert_identity_preserved(mediator, path, metros, before)
        self.assertEqual(tuple(path.stations), before["stations"])
        self.assertEqual(tuple(path.segments), before["segments"])
        self.assertEqual(tuple(path.path_segments), before["path_segments"])
        self.assertEqual(tuple(path.padding_segments), before["padding_segments"])
        self.assertEqual(path.is_looped, before["is_looped"])
        self.assertEqual(
            tuple(
                (metro.current_segment, metro.current_segment_idx, metro.is_forward)
                for metro in metros
            ),
            before["bindings"],
        )
        self.assertEqual(
            mediator.context.python_random.getstate(), before["python_rng"]
        )
        self.assertEqual(
            mediator.context.numpy_random.bit_generator.state, before["numpy_rng"]
        )

    def test_linear_success_preserves_identity_pose_and_candidate_geometry(self):
        mediator, stations, path, metros = _build_network()
        metro = metros[0]
        _move_partway(path, metro)
        before = _identity_snapshot(mediator, path, metros)

        self.assertTrue(mediator.replace_path(path, [0, 1, 3, 2]))

        self._assert_identity_preserved(mediator, path, metros, before)
        self.assertEqual(
            path.stations, [stations[0], stations[1], stations[3], stations[2]]
        )
        self.assertFalse(path.is_looped)
        self.assertIs(metro.current_segment, path.path_segments[0])
        self.assertTrue(metro.is_forward)
        self._assert_candidate_geometry(path, path.stations, False)

    def test_loop_success_preserves_identity_pose_and_candidate_geometry(self):
        mediator, stations, path, metros = _build_network(loop=True)
        metro = metros[0]
        _move_partway(path, metro)
        before = _identity_snapshot(mediator, path, metros)

        self.assertTrue(mediator.replace_path(path, [0, 1, 3, 2], loop=True))

        self._assert_identity_preserved(mediator, path, metros, before)
        self.assertTrue(path.is_looped)
        self.assertEqual(len(path.path_segments), 4)
        self.assertEqual(len(path.padding_segments), 4)
        self.assertIs(metro.current_segment, path.path_segments[0])
        self._assert_candidate_geometry(path, path.stations, True)

    def test_reversed_logical_edge_preserves_physical_motion(self):
        mediator, stations, path, metros = _build_network()
        metro = metros[0]
        _move_partway(path, metro)
        pose = _pose(metro)

        self.assertTrue(mediator.replace_path(path, [2, 1, 0]))

        self._assert_pose_unchanged(metro, pose)
        self.assertIsInstance(metro.current_segment, PathSegment)
        self.assertIs(metro.current_segment.start_station, stations[1])
        self.assertIs(metro.current_segment.end_station, stations[0])
        self.assertFalse(metro.is_forward)
        self.assertEqual(
            path.segments.index(metro.current_segment), metro.current_segment_idx
        )

    def test_retained_padding_transition_preserves_motion(self):
        mediator, stations, path, metros = _build_network(path_order=1)
        metro = metros[0]
        _move_into_first_padding(path, metro)
        pose = _pose(metro)

        self.assertTrue(mediator.replace_path(path, [0, 1, 2, 3]))

        self._assert_pose_unchanged(metro, pose)
        self.assertIsInstance(metro.current_segment, PaddingSegment)
        self.assertEqual(
            path.segments.index(metro.current_segment), metro.current_segment_idx
        )

    def test_changed_padding_transition_rejects_without_effects(self):
        mediator, _, path, metros = _build_network(path_order=1)
        _move_into_first_padding(path, metros[0])

        self._assert_rejected_unchanged(
            mediator, path, metros, [0, 1, 3, 2], loop=False
        )

    def test_stopped_interior_reroute_and_new_terminus_use_real_arrival_state(self):
        for target, expected_forward, expected_type in (
            ([0, 1, 3], True, PaddingSegment),
            ([0, 1], False, PathSegment),
        ):
            with self.subTest(target=target):
                mediator, stations, path, metros = _build_network()
                metro = metros[0]
                _arrive_at_first_interior(path, metro)
                pose = _pose(metro)

                self.assertTrue(mediator.replace_path(path, target))

                self._assert_pose_unchanged(metro, pose)
                self.assertIs(metro.current_station, stations[1])
                self.assertIsInstance(metro.current_segment, expected_type)
                self.assertEqual(metro.is_forward, expected_forward)
                self.assertEqual(
                    path.segments.index(metro.current_segment),
                    metro.current_segment_idx,
                )

    def test_stopped_loop_closure_rebinds_from_real_arrival_edge(self):
        mediator, stations, path, metros = _build_network(loop=True)
        metro = metros[0]
        _arrive_forward_through_loop_closure(path, metro)
        pose = _pose(metro)

        self.assertTrue(mediator.replace_path(path, [2, 0, 1], loop=True))

        self._assert_pose_unchanged(metro, pose)
        self.assertIs(metro.current_station, stations[0])
        self.assertIs(metro.current_segment, path.padding_segments[0])
        self.assertEqual(
            path.segments.index(metro.current_segment), metro.current_segment_idx
        )
        self.assertTrue(metro.is_forward)

    def test_two_station_loop_reorder_uses_direction_to_disambiguate(self):
        mediator, stations, path, metros = _build_network(route=(0, 1), loop=True)
        metro = metros[0]
        _move_partway(path, metro)
        pose = _pose(metro)

        self.assertTrue(mediator.replace_path(path, [1, 0], loop=True))

        self._assert_pose_unchanged(metro, pose)
        self.assertEqual(path.stations, [stations[1], stations[0]])
        self.assertTrue(metro.is_forward)
        self.assertIs(metro.current_segment, path.path_segments[1])

    def test_off_segment_tolerance_is_inclusive_and_fail_closed(self):
        cases = (
            (Point(200, 100 + 1e-6), True),
            (Point(200, 100 + 1.01e-6), False),
            (Point(300 + 1e-9, 100), False),
            (Point("100", 100), False),
            (Point(True, 100), False),
            (Point(10**10000, 100), False),
        )
        for position, accepted in cases:
            with self.subTest(position=_point(position), accepted=accepted):
                mediator, _, path, metros = _build_network()
                metro = metros[0]
                metro.position = position
                pose = _pose(metro)
                before = _transaction_snapshot(mediator, path, metros)

                result = mediator.replace_path(path, [0, 1, 3, 2])

                self.assertEqual(result, accepted)
                self._assert_pose_unchanged(metro, pose)
                if accepted:
                    self.assertIs(metro.current_segment, path.path_segments[0])
                else:
                    self.assertEqual(tuple(path.segments), before["segments"])
                    self.assertIs(metro.current_segment, before["bindings"][0][0])
                    self.assertEqual(
                        mediator.context.python_random.getstate(), before["python_rng"]
                    )

    def test_one_unsafe_metro_rejects_before_rebinding_safe_metro(self):
        mediator, _, path, metros = _build_network(metro_count=2)
        safe, unsafe = metros
        _move_partway(path, safe)
        unsafe.current_segment_idx = 2
        unsafe.current_segment = path.segments[2]
        unsafe.position = Point(300 + 1e-4, 200)
        unsafe.current_station = None

        self._assert_rejected_unchanged(
            mediator, path, metros, [0, 1, 3, 2], loop=False
        )
