from unittest.mock import MagicMock, patch

import mediator as mediator_module
from entity.metro import Metro
from entity.path import Path
from geometry.point import Point


def path_through(*stations, color=(10, 20, 30)):
    path = Path(color)
    for station in stations:
        path.add_station(station)
    return path


class LoggingList(list):
    def __init__(self, values, label, names, events, on_remove=None):
        super().__init__(values)
        self.label = label
        self.names = names
        self.events = events
        self.on_remove = on_remove

    def remove(self, value):
        self.events.append(f"{self.label}:{self.names[id(value)]}")
        if self.on_remove is not None:
            self.on_remove(value)
        super().remove(value)


class LoggingPlans(dict):
    def __init__(self, values, names, events):
        super().__init__(values)
        self.names = names
        self.events = events

    def pop(self, key, default=None):
        self.events.append(f"plan:{self.names[id(key)]}")
        return super().pop(key, default)


class ExplodingNodes(list):
    def __iter__(self):
        raise AssertionError("surviving onboard plans must not inspect node_path")


class IntSubclass(int):
    pass


def assert_late_path_factory(test_case, mediator):
    color = next(iter(mediator.path_colors))
    snapshots = {}
    created = []

    def late_factory(assigned_color):
        snapshots["factory"] = (
            mediator.is_creating_path,
            mediator.path_colors[assigned_color],
            len(mediator.path_to_color),
            len(mediator.paths),
            mediator.path_being_created,
        )
        path = Path(assigned_color)
        created.append(path)
        original_add = path.add_station

        def add_station(station):
            snapshots["add"] = (
                mediator.path_to_color.get(path) is assigned_color,
                path in mediator.paths,
                mediator.path_being_created,
                path.is_being_created,
            )
            original_add(station)

        path.add_station = add_station
        return path

    class RebindingPalette(dict):
        def __setitem__(self, key, value):
            super().__setitem__(key, value)
            if value is True:
                mediator_module.Path = late_factory

    palette = RebindingPalette({color: False})
    mediator.path_colors = palette
    with patch.object(
        mediator_module,
        "Path",
        MagicMock(side_effect=AssertionError("factory resolved too early")),
    ):
        mediator.start_path_on_station(mediator.stations[0])

    path = created[0]
    test_case.assertEqual(snapshots["factory"], (True, True, 0, 0, None))
    test_case.assertEqual(snapshots["add"], (True, False, None, False))
    test_case.assertIs(mediator.path_being_created, path)
    test_case.assertIs(mediator.paths[0], path)
    test_case.assertIs(mediator.path_to_color[path], path.color)
    test_case.assertTrue(path.is_being_created)
    test_case.assertIs(mediator.path_colors, palette)


def assert_late_metro_factory(test_case, mediator):
    mediator.start_path_on_station(mediator.stations[0])
    mediator.add_station_to_path(mediator.stations[1])
    path = mediator.path_being_created
    assert path is not None
    path.set_temporary_point(Point(123, 456))
    snapshots = {}
    created = []
    original_remove_temporary_point = path.remove_temporary_point
    original_add_metro = path.add_metro

    def late_factory():
        snapshots["factory"] = (
            mediator.is_creating_path,
            path.is_being_created,
            path.temp_point,
            mediator.path_being_created is path,
            tuple(mediator.metros),
        )
        metro = Metro()
        created.append(metro)
        return metro

    def remove_temporary_point():
        snapshots["remove-temp"] = (
            mediator.is_creating_path,
            path.is_being_created,
            path.temp_point is not None,
        )
        original_remove_temporary_point()
        mediator_module.Metro = late_factory

    def add_metro(metro):
        snapshots["add"] = (
            mediator.path_being_created is path,
            tuple(path.metros),
            tuple(mediator.metros),
        )
        original_add_metro(metro)

    path.remove_temporary_point = remove_temporary_point
    path.add_metro = add_metro
    mediator.assign_paths_to_buttons = MagicMock(
        side_effect=lambda: snapshots.__setitem__(
            "assign",
            (
                mediator.path_being_created,
                tuple(path.metros),
                tuple(mediator.metros),
            ),
        )
    )
    with patch.object(
        mediator_module,
        "Metro",
        MagicMock(side_effect=AssertionError("factory resolved too early")),
    ):
        mediator.finish_path_creation()

    metro = created[0]
    test_case.assertEqual(snapshots["remove-temp"], (False, False, True))
    test_case.assertEqual(snapshots["factory"], (False, False, None, True, ()))
    test_case.assertEqual(snapshots["add"], (True, (), ()))
    test_case.assertEqual(snapshots["assign"], (None, (metro,), (metro,)))
    test_case.assertIs(path.metros[0], metro)
    test_case.assertIs(mediator.metros[0], metro)
