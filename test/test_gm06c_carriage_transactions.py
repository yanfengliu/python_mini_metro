from __future__ import annotations

import importlib
import os
import sys
import unittest
from copy import deepcopy
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.passenger import Passenger
from geometry.line import Line
from geometry.point import Point
from mediator import Mediator

_MISSING = object()


def _carriage_type():
    return importlib.import_module("entity.carriage").Carriage


def _management():
    return importlib.import_module("carriage_management").CarriageManagement()


def _identity_union(*groups):
    result = []
    for group in groups:
        for item in group:
            if all(item is not prior for prior in result):
                result.append(item)
    return tuple(result)


def _assert_identities(test, actual, expected) -> None:
    test.assertEqual(len(actual), len(expected))
    for item, prior in zip(actual, expected):
        test.assertIs(item, prior)


def _unlock_all_paths(mediator: Mediator) -> None:
    mediator.unlocked_num_paths = mediator.num_paths
    mediator.update_path_button_lock_states()


def _different_shape_indices(mediator: Mediator) -> tuple[int, int]:
    for first, source in enumerate(mediator.stations):
        for second, destination in enumerate(mediator.stations):
            if source.shape.type != destination.shape.type:
                return first, second
    raise AssertionError("test setup requires two station shape types")


def _full_graph(seed: int):
    mediator = Mediator(seed=seed)
    _unlock_all_paths(mediator)
    mediator.num_metros = 2
    first, second = _different_shape_indices(mediator)
    third = next(
        index for index in range(len(mediator.stations)) if index not in (first, second)
    )
    paths = []
    for route in ([first, second, third], [second, first, third]):
        path = mediator.create_path_from_station_indices(route)
        if path is None or not mediator.assign_locomotive(path):
            raise AssertionError("test setup could not create the full graph")
        paths.append(path)
    plans = []
    for path in paths:
        passenger = Passenger(path.stations[1].shape)
        path.stations[0].add_passenger(passenger)
        mediator.passengers.append(passenger)
        mediator.find_travel_plan_for_passengers()
        plans.append(mediator.travel_plans[passenger])
    metros = tuple(path.metros[0] for path in paths)
    Carriage = _carriage_type()
    for metro in metros:
        metro.carriages.extend((Carriage(), Carriage()))
    mediator.num_carriages = 6
    return mediator, tuple(paths), metros, tuple(plans)


def _collection_state(collection):
    return collection, tuple(collection)


def _point_state(point):
    return point, point.to_tuple()


def _snapshot(host: Mediator) -> dict[str, object]:
    paths = tuple(host.paths)
    metros = _identity_union(host.metros, *(path.metros for path in paths))
    segments = _identity_union(
        *(
            collection
            for path in paths
            for collection in (path.segments, path.path_segments, path.padding_segments)
        )
    )
    plans = _identity_union(host.travel_plans.values())
    return {
        "total": host.num_carriages,
        "terminal": host.is_game_over,
        "time": host.time_ms,
        "python_rng": host.context.python_random.getstate(),
        "numpy_rng": deepcopy(host.context.numpy_random.bit_generator.state),
        "paths": _collection_state(host.paths),
        "stations": _collection_state(host.stations),
        "metros": _collection_state(host.metros),
        "plans": (host.travel_plans, tuple(host.travel_plans.items())),
        "creating": host.is_creating_path,
        "creating_path": host.path_being_created,
        "path_state": tuple(
            (
                path,
                path.id,
                path.color,
                path.path_order,
                path.is_looped,
                path.is_being_created,
                path.temp_point,
                *(
                    _collection_state(collection)
                    for collection in (
                        path.stations,
                        path.segments,
                        path.path_segments,
                        path.padding_segments,
                        path.metros,
                    )
                ),
            )
            for path in paths
        ),
        "station_state": tuple(
            (station, *_point_state(station.position)) for station in host.stations
        ),
        "segment_state": tuple(
            (
                segment,
                getattr(segment, "start_station", _MISSING),
                getattr(segment, "end_station", _MISSING),
                getattr(segment, "path_order", _MISSING),
                segment.color,
                *_point_state(segment.segment_start),
                *_point_state(segment.segment_end),
                segment.line,
                segment.line.color,
                *_point_state(segment.line.start),
                *_point_state(segment.line.end),
                segment.line.width,
            )
            for segment in segments
        ),
        "metro_state": tuple(
            (
                metro,
                *_collection_state(metro.carriages),
                *_collection_state(metro.passengers),
                metro._base_capacity,
                metro.is_unassignment_queued,
                metro.path_id,
                metro.current_segment,
                metro.current_segment_idx,
                metro.current_station,
                *_point_state(metro.position),
                metro.is_forward,
                metro.stop_time_remaining_ms,
                metro.boarding_progress_ms,
                metro.speed,
                getattr(metro, "_station_service_action", _MISSING),
            )
            for metro in metros
        ),
        "carriage_state": tuple(
            (carriage, carriage.id, carriage.capacity, carriage.shape)
            for carriage in _identity_union(*(metro.carriages for metro in metros))
        ),
        "plan_state": tuple(
            (
                plan,
                plan.next_path,
                plan.next_station,
                plan.next_station_idx,
                *_collection_state(plan.node_path),
            )
            for plan in plans
        ),
    }


def _assert_snapshot(test: unittest.TestCase, host: Mediator, before) -> None:
    test.assertEqual(host.num_carriages, before["total"])
    test.assertIs(host.is_game_over, before["terminal"])
    test.assertEqual(host.time_ms, before["time"])
    test.assertEqual(host.context.python_random.getstate(), before["python_rng"])
    test.assertEqual(host.context.numpy_random.bit_generator.state, before["numpy_rng"])
    for key, current in (
        ("paths", host.paths),
        ("stations", host.stations),
        ("metros", host.metros),
    ):
        collection, contents = before[key]
        test.assertIs(current, collection)
        _assert_identities(test, current, contents)
    mapping, items = before["plans"]
    test.assertIs(host.travel_plans, mapping)
    test.assertEqual(len(host.travel_plans), len(items))
    for actual, expected in zip(host.travel_plans.items(), items):
        test.assertIs(actual[0], expected[0])
        test.assertIs(actual[1], expected[1])
    test.assertIs(host.is_creating_path, before["creating"])
    test.assertIs(host.path_being_created, before["creating_path"])
    for state in before["path_state"]:
        path, path_id, color, order, looped, creating, temp, *collections = state
        test.assertEqual(
            (path.id, path.color, path.path_order), (path_id, color, order)
        )
        test.assertIs(path.is_looped, looped)
        test.assertIs(path.is_being_created, creating)
        test.assertIs(path.temp_point, temp)
        for current, (collection, contents) in zip(
            (
                path.stations,
                path.segments,
                path.path_segments,
                path.padding_segments,
                path.metros,
            ),
            collections,
        ):
            test.assertIs(current, collection)
            _assert_identities(test, current, contents)
    for station, position, coordinates in before["station_state"]:
        test.assertIs(station.position, position)
        test.assertEqual(station.position.to_tuple(), coordinates)
    for state in before["segment_state"]:
        (
            segment,
            start_station,
            end_station,
            order,
            color,
            start,
            start_xy,
            end,
            end_xy,
            line,
            line_color,
            line_start,
            line_start_xy,
            line_end,
            line_end_xy,
            width,
        ) = state
        test.assertIs(getattr(segment, "start_station", _MISSING), start_station)
        test.assertIs(getattr(segment, "end_station", _MISSING), end_station)
        test.assertEqual(getattr(segment, "path_order", _MISSING), order)
        test.assertEqual(segment.color, color)
        for current, identity, coordinates in (
            (segment.segment_start, start, start_xy),
            (segment.segment_end, end, end_xy),
            (segment.line.start, line_start, line_start_xy),
            (segment.line.end, line_end, line_end_xy),
        ):
            test.assertIs(current, identity)
            test.assertEqual(current.to_tuple(), coordinates)
        test.assertIs(segment.line, line)
        test.assertEqual((segment.line.color, segment.line.width), (line_color, width))
    for state in before["metro_state"]:
        (
            metro,
            carriage_list,
            carriages,
            passenger_list,
            passengers,
            base,
            queued,
            path_id,
            segment,
            index,
            station,
            position,
            position_xy,
            forward,
            stop,
            progress,
            speed,
            service,
        ) = state
        test.assertIs(metro.carriages, carriage_list)
        _assert_identities(test, metro.carriages, carriages)
        test.assertIs(metro.passengers, passenger_list)
        _assert_identities(test, metro.passengers, passengers)
        test.assertEqual(
            (metro._base_capacity, metro.path_id, metro.current_segment_idx),
            (base, path_id, index),
        )
        test.assertIs(metro.is_unassignment_queued, queued)
        test.assertIs(metro.current_segment, segment)
        test.assertIs(metro.current_station, station)
        test.assertIs(metro.position, position)
        test.assertEqual(metro.position.to_tuple(), position_xy)
        test.assertIs(metro.is_forward, forward)
        test.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms, metro.speed),
            (stop, progress, speed),
        )
        test.assertIs(getattr(metro, "_station_service_action", _MISSING), service)
    for carriage, carriage_id, capacity, shape in before["carriage_state"]:
        test.assertEqual((carriage.id, carriage.capacity), (carriage_id, capacity))
        test.assertIs(carriage.shape, shape)
    for plan, next_path, station, index, nodes, node_items in before["plan_state"]:
        test.assertIs(plan.next_path, next_path)
        test.assertIs(plan.next_station, station)
        test.assertEqual(plan.next_station_idx, index)
        test.assertIs(plan.node_path, nodes)
        _assert_identities(test, plan.node_path, node_items)


def _mutate_full_graph(host, paths, metros, plans) -> None:
    stations = tuple(host.stations)
    segments = _identity_union(
        *(
            collection
            for path in paths
            for collection in (path.segments, path.path_segments, path.padding_segments)
        )
    )
    carriages = _identity_union(*(metro.carriages for metro in metros))
    host.num_carriages = 99
    host.is_game_over = True
    host.time_ms += 123
    host.context.python_random.random()
    host.context.numpy_random.random()
    host.paths = list(reversed(host.paths))
    host.stations = list(reversed(host.stations))
    host.metros = list(reversed(host.metros))
    host.travel_plans = dict(reversed(tuple(host.travel_plans.items())))
    host.is_creating_path = True
    host.path_being_created = paths[-1]
    for offset, path in enumerate(paths, 1):
        path.id += "-mutated"
        path.color = (offset, 2, 3)
        path.path_order += offset
        path.is_looped = not path.is_looped
        path.is_being_created = True
        path.temp_point = Point(offset, offset)
        path.stations = list(reversed(path.stations))
        path.segments = list(reversed(path.segments))
        path.path_segments = list(reversed(path.path_segments))
        path.padding_segments = list(reversed(path.padding_segments))
        path.metros = list(reversed(path.metros))
    for offset, station in enumerate(stations, 1):
        station.position = Point(900 + offset, 950 + offset)
    for offset, segment in enumerate(segments, 1):
        segment.color = (4, 5, offset)
        segment.segment_start = Point(-10 - offset, -20 - offset)
        segment.segment_end = Point(30 + offset, 40 + offset)
        if hasattr(segment, "path_order"):
            segment.path_order += 3
            segment.start_station = paths[0].stations[-1]
            segment.end_station = paths[0].stations[0]
        segment.line = Line(
            color=(7, 8, offset),
            start=Point(-offset, -offset),
            end=Point(offset, offset),
            width=50 + offset,
        )
    for offset, carriage in enumerate(carriages, 1):
        carriage.id = f"{carriage.id}-mutated-{offset}"
    for offset, metro in enumerate(metros, 1):
        metro.carriages = [*metro.carriages, _carriage_type()()]
        metro.passengers = list(reversed(metro.passengers))
        metro._base_capacity += offset
        metro.is_unassignment_queued = True
        metro.path_id += "-mutated"
        metro.current_segment = None
        metro.current_segment_idx = 90 + offset
        metro.current_station = paths[0].stations[0]
        metro.position = Point(40 + offset, 50 + offset)
        metro.is_forward = not metro.is_forward
        metro.stop_time_remaining_ms = 100 + offset
        metro.boarding_progress_ms = 200 + offset
        metro.speed = 300 + offset
        metro._station_service_action = ("boarding", next(iter(host.passengers)))
    for plan in plans:
        plan.next_path = None
        plan.next_station = None
        plan.next_station_idx += 7
        plan.node_path = []


class TestGM06cTransactionRollback(unittest.TestCase):
    def _invoke(self, callback, error) -> None:
        if isinstance(error, BaseException) and not isinstance(error, Exception):
            try:
                callback()
            except BaseException as raised:
                self.assertIs(raised, error)
            else:
                self.fail(f"{type(error).__name__} was not raised")
        else:
            self.assertFalse(callback())

    def test_factory_mutation_return_raise_and_base_restore_entire_active_graph(
        self,
    ) -> None:
        for mode in ("return", "ordinary", "base"):
            with self.subTest(mode=mode):
                host, paths, metros, plans = _full_graph(61000 + len(mode))
                before = _snapshot(host)
                calls = MagicMock()
                base_error = KeyboardInterrupt("factory base fault")

                def factory():
                    calls()
                    _mutate_full_graph(host, paths, metros, plans)
                    if mode == "ordinary":
                        raise RuntimeError("factory fault")
                    if mode == "base":
                        raise base_error
                    return _carriage_type()()

                getter = MagicMock(return_value=factory)
                self._invoke(
                    lambda: _management().attach(
                        host,
                        paths[0],
                        get_carriage_factory=getter,
                        reconcile_station_service=MagicMock(),
                    ),
                    base_error if mode == "base" else None,
                )
                getter.assert_called_once_with()
                calls.assert_called_once_with()
                _assert_snapshot(self, host, before)

    def test_real_station_reconciliation_failures_restore_attach_and_detach(
        self,
    ) -> None:
        for operation in ("attach", "detach"):
            for error in (None, RuntimeError("reconcile"), KeyboardInterrupt()):
                with self.subTest(
                    operation=operation,
                    error=None if error is None else type(error).__name__,
                ):
                    host, paths, metros, plans = _full_graph(61100 + len(operation))
                    metro = metros[0]
                    metro.current_station = paths[0].stations[0]
                    metro.position = metro.current_station.position
                    known = _carriage_type()()
                    if operation == "detach":
                        metro.carriages.append(known)
                    before = _snapshot(host)
                    reconcile = MagicMock()

                    def fail(selected):
                        reconcile(selected)
                        if operation == "attach":
                            self.assertIs(selected.carriages[-1], known)
                        else:
                            self.assertTrue(
                                all(item is not known for item in selected.carriages)
                            )
                        _mutate_full_graph(host, paths, metros, plans)
                        if error is not None:
                            raise error

                    if operation == "attach":
                        factory = MagicMock(return_value=known)
                        getter = MagicMock(return_value=factory)

                    def invoke():
                        if operation == "attach":
                            return _management().attach(
                                host,
                                paths[0],
                                get_carriage_factory=getter,
                                reconcile_station_service=fail,
                            )
                        return _management().detach(
                            host, paths[0], reconcile_station_service=fail
                        )

                    self._invoke(invoke, error)
                    reconcile.assert_called_once_with(metro)
                    _assert_snapshot(self, host, before)


if __name__ == "__main__":
    unittest.main()
