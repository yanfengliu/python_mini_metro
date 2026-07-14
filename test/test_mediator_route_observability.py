from collections.abc import Iterator
from unittest.mock import MagicMock, patch

from test import mediator_test_support as support

# isort: split

import mediator as mediator_module
from config import station_color, station_size
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from graph.graph_algo import build_station_nodes_dict
from graph.node import Node
from mediator import Mediator
from travel_plan import TravelPlan


def _rect_station(x: int = 0) -> Station:
    return Station(Rect(station_color, 2 * station_size, 2 * station_size), Point(x, 0))


def _circle_station(x: int = 10) -> Station:
    return Station(Circle(station_color, station_size), Point(x, 0))


def _path_through(*stations: Station) -> Path:
    path = Path((10, 20, 30))
    for station in stations:
        path.add_station(station)
    return path


class _BoundedLenList(list[Node]):
    def __init__(self, values: list[Node], allowed_calls: int) -> None:
        super().__init__(values)
        self.allowed_calls = allowed_calls
        self.len_calls = 0

    def __len__(self) -> int:
        self.len_calls += 1
        if self.len_calls > self.allowed_calls:
            raise RuntimeError("route length re-read")
        return super().__len__()


class TestMediatorRouteObservability(support.MediatorTestCase):
    def test_arrival_does_not_remeasure_the_selected_node_path(self):
        mediator = Mediator()
        station = _rect_station()
        passenger = Passenger(station.shape)
        station.add_passenger(passenger)
        mediator.stations = [station]
        mediator.passengers = [passenger]
        mediator.travel_plans = {passenger: TravelPlan([])}
        station_node = Node(station)
        arrival = _BoundedLenList([station_node], allowed_calls=1)
        mediator.get_stations_for_shape_type = MagicMock(return_value=[station])

        with (
            patch.object(
                mediator_module,
                "build_station_nodes_dict",
                return_value={station: station_node},
            ),
            patch.object(mediator_module, "bfs", return_value=arrival),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertEqual(arrival.len_calls, 1)
        self.assertTrue(passenger.is_at_destination)
        self.assertNotIn(passenger, mediator.passengers)

    def test_reachable_route_does_not_remeasure_the_reduced_path(self):
        mediator = Mediator()
        start = _rect_station()
        destination = _circle_station()
        path = _path_through(start, destination)
        passenger = Passenger(destination.shape)
        start.add_passenger(passenger)
        mediator.stations = [start, destination]
        mediator.paths = [path]
        mediator.passengers = [passenger]
        nodes = build_station_nodes_dict(mediator.stations, mediator.paths)
        reduced = _BoundedLenList([nodes[start], nodes[destination]], allowed_calls=1)
        mediator.get_stations_for_shape_type = MagicMock(return_value=[destination])
        mediator.skip_stations_on_same_path = MagicMock(return_value=reduced)

        with (
            patch.object(
                mediator_module, "build_station_nodes_dict", return_value=nodes
            ),
            patch.object(
                mediator_module,
                "bfs",
                return_value=[nodes[start], nodes[destination]],
            ),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertEqual(reduced.len_calls, 1)
        self.assertIs(mediator.travel_plans[passenger].next_path, path)

    def test_one_node_reduced_route_is_not_reclassified_as_arrival(self):
        mediator = Mediator()
        start = _rect_station()
        destination = _circle_station()
        path = _path_through(start, destination)
        passenger = Passenger(destination.shape)
        start.add_passenger(passenger)
        mediator.stations = [start, destination]
        mediator.paths = [path]
        mediator.passengers = [passenger]
        nodes = build_station_nodes_dict(mediator.stations, mediator.paths)
        mediator.get_stations_for_shape_type = MagicMock(return_value=[destination])
        mediator.skip_stations_on_same_path = MagicMock(return_value=[nodes[start]])

        with (
            patch.object(
                mediator_module, "build_station_nodes_dict", return_value=nodes
            ),
            patch.object(
                mediator_module,
                "bfs",
                return_value=[nodes[start], nodes[destination]],
            ),
            self.assertRaises(AssertionError),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertFalse(passenger.is_at_destination)
        self.assertIn(passenger, start.passengers)
        self.assertEqual(mediator.travel_plans[passenger].node_path, [])

    def test_arrival_runs_fallback_guard_after_map_deletion_side_effect(self):
        mediator = Mediator()
        station = _rect_station()
        passenger = Passenger(station.shape)
        station.add_passenger(passenger)
        mediator.stations = [station]
        mediator.passengers = [passenger]
        station_node = Node(station)

        class ResettingPlans(dict[Passenger, TravelPlan]):
            def __delitem__(self, item: Passenger) -> None:
                super().__delitem__(item)
                item.is_at_destination = False

        mediator.travel_plans = ResettingPlans({passenger: TravelPlan([])})
        mediator.get_stations_for_shape_type = MagicMock(return_value=[station])
        with (
            patch.object(
                mediator_module,
                "build_station_nodes_dict",
                return_value={station: station_node},
            ),
            patch.object(mediator_module, "bfs", return_value=[station_node]),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertFalse(passenger.is_at_destination)
        self.assertNotIn(passenger, mediator.passengers)
        self.assertEqual(mediator.travel_plans[passenger].node_path, [])

    def test_arrival_effects_precede_destination_iterator_finalization(self):
        mediator = Mediator()
        station = _rect_station()
        passenger = Passenger(station.shape)
        station.add_passenger(passenger)
        mediator.stations = [station]
        mediator.passengers = [passenger]
        mediator.travel_plans = {passenger: TravelPlan([])}
        station_node = Node(station)

        class RebindingDestinations:
            def __iter__(self) -> Iterator[Station]:
                try:
                    yield station
                finally:
                    mediator.travel_plans = {}

        mediator.get_stations_for_shape_type = MagicMock(
            return_value=RebindingDestinations()
        )
        with (
            patch.object(
                mediator_module,
                "build_station_nodes_dict",
                return_value={station: station_node},
            ),
            patch.object(mediator_module, "bfs", return_value=[station_node]),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertTrue(passenger.is_at_destination)
        self.assertEqual(mediator.travel_plans, {})

    def test_arrival_retains_destination_local_through_fallback_guard(self):
        mediator = Mediator()
        station = _rect_station()
        passenger = Passenger(station.shape)
        station.add_passenger(passenger)
        mediator.stations = [station]
        mediator.passengers = [passenger]
        mediator.travel_plans = {passenger: TravelPlan([])}
        station_node = Node(station)
        events: list[str] = []

        class Destination:
            def __del__(self):
                events.append("released")
                passenger.is_at_destination = False

        class NodeMap:
            def __getitem__(self, _key):
                return station_node

        def destinations():
            yield Destination()

        mediator.get_stations_for_shape_type = MagicMock(return_value=destinations())
        with (
            patch.object(
                mediator_module, "build_station_nodes_dict", return_value=NodeMap()
            ),
            patch.object(mediator_module, "bfs", return_value=[station_node]),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertEqual(events, ["released"])
        self.assertFalse(passenger.is_at_destination)
        self.assertNotIn(passenger, mediator.travel_plans)

    def test_arrival_retains_prior_reduced_route_through_fallback_guard(self):
        mediator = Mediator()
        start = _rect_station()
        destination = _circle_station()
        passenger = Passenger(start.shape)
        start.add_passenger(passenger)
        mediator.stations = [start, destination]
        mediator.passengers = [passenger]
        mediator.travel_plans = {passenger: TravelPlan([])}
        nodes = build_station_nodes_dict(mediator.stations, [])
        events: list[str] = []

        class ReducedRoute(list[Node]):
            def __del__(self):
                events.append("released")
                passenger.is_at_destination = False

        def find_path(_start: Node, end: Node) -> list[Node]:
            if end is nodes[start]:
                return [nodes[start]]
            return [nodes[start], nodes[destination]]

        mediator.get_stations_for_shape_type = MagicMock(
            return_value=[destination, start]
        )
        mediator.skip_stations_on_same_path = MagicMock(
            side_effect=lambda _nodes: ReducedRoute([nodes[start], nodes[destination]])
        )
        with (
            patch.object(
                mediator_module, "build_station_nodes_dict", return_value=nodes
            ),
            patch.object(mediator_module, "bfs", side_effect=find_path),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertEqual(events, ["released"])
        self.assertFalse(passenger.is_at_destination)
        self.assertNotIn(passenger, mediator.travel_plans)

    def test_reducer_callable_is_released_before_bulk_plan_installation(self):
        events: list[str] = []

        class ObservingMediator(Mediator):
            @property
            def skip_stations_on_same_path(self):
                owner = self

                class Reducer:
                    def __call__(self, nodes):
                        events.append("call")
                        return nodes

                    def __del__(self):
                        events.append("released")
                        owner.travel_plans.clear()

                return Reducer()

            def find_next_path_for_passenger_at_station(self, passenger, station):
                events.append("wire")
                return super().find_next_path_for_passenger_at_station(
                    passenger, station
                )

        mediator = ObservingMediator()
        start = _rect_station()
        destination = _circle_station()
        path = _path_through(start, destination)
        passenger = Passenger(destination.shape)
        start.add_passenger(passenger)
        mediator.stations = [start, destination]
        mediator.paths = [path]
        mediator.passengers = [passenger]
        nodes = build_station_nodes_dict(mediator.stations, mediator.paths)
        mediator.get_stations_for_shape_type = MagicMock(return_value=[destination])
        with (
            patch.object(
                mediator_module, "build_station_nodes_dict", return_value=nodes
            ),
            patch.object(
                mediator_module,
                "bfs",
                return_value=[nodes[start], nodes[destination]],
            ),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertEqual(events, ["call", "released", "wire"])
        self.assertIn(passenger, mediator.travel_plans)
