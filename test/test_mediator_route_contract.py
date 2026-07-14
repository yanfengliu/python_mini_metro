from collections.abc import Iterator
from unittest.mock import MagicMock, patch

from test import mediator_test_support as support

# isort: split

import mediator as mediator_module
from config import station_color, station_size
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from geometry.triangle import Triangle
from graph.graph_algo import build_station_nodes_dict
from graph.node import Node
from mediator import Mediator
from travel_plan import TravelPlan


def _rect_station(x: int = 0) -> Station:
    return Station(Rect(station_color, 2 * station_size, 2 * station_size), Point(x, 0))


def _circle_station(x: int = 10) -> Station:
    return Station(Circle(station_color, station_size), Point(x, 0))


def _triangle_station(x: int) -> Station:
    return Station(Triangle(station_color, station_size), Point(x, 0))


def _path_through(*stations: Station) -> Path:
    path = Path((10, 20, 30))
    for station in stations:
        path.add_station(station)
    return path


class _LoggingNodeMap(dict[Station, Node]):
    def __init__(self, values: dict[Station, Node], accesses: list[Station]) -> None:
        super().__init__(values)
        self.accesses = accesses

    def __getitem__(self, station: Station) -> Node:
        self.accesses.append(station)
        return super().__getitem__(station)


class _ExplodingPassengerList(list[Passenger]):
    def __iter__(self) -> Iterator[Passenger]:
        raise AssertionError("passengers must not be inspected")


class TestMediatorRouteContract(support.MediatorTestCase):
    def test_bulk_re_resolves_bfs_and_compression_between_destinations(self):
        mediator = Mediator()
        start = _rect_station()
        first_destination = _triangle_station(10)
        second_destination = _triangle_station(20)
        first_path = _path_through(start, first_destination)
        second_path = _path_through(start, second_destination)
        mediator.stations = [start, first_destination, second_destination]
        mediator.paths = [first_path, second_path]

        passenger = Passenger(first_destination.shape)
        start.add_passenger(passenger)
        mediator.passengers = [passenger]
        nodes = {station: Node(station) for station in mediator.stations}
        mediator.get_stations_for_shape_type = MagicMock(
            return_value=[first_destination, second_destination]
        )
        calls: list[str] = []

        def second_bfs(start_node: Node, end_node: Node) -> list[Node]:
            calls.append("bfs-2")
            return [start_node, end_node]

        def first_bfs(start_node: Node, end_node: Node) -> list[Node]:
            calls.append("bfs-1")
            mediator_module.bfs = second_bfs
            return [start_node, end_node]

        def second_compression(node_path: list[Node]) -> list[Node]:
            calls.append("compress-2")
            return node_path

        def first_compression(node_path: list[Node]) -> list[Node]:
            calls.append("compress-1")
            mediator.skip_stations_on_same_path = second_compression
            return node_path

        mediator.skip_stations_on_same_path = first_compression
        with (
            patch.object(
                mediator_module, "build_station_nodes_dict", return_value=nodes
            ),
            patch.object(mediator_module, "bfs", first_bfs),
        ):
            mediator.find_travel_plan_for_passengers()

        self.assertEqual(calls, ["bfs-1", "compress-1", "bfs-2", "compress-2"])
        travel_plan = mediator.travel_plans[passenger]
        self.assertIs(travel_plan.node_path[0], nodes[first_destination])
        self.assertIs(travel_plan.next_station, first_destination)
        self.assertIs(travel_plan.next_path, first_path)

    def test_boarding_re_resolves_plan_callback_after_each_applied_proposal(self):
        mediator = Mediator()
        station = _rect_station()
        next_station = _circle_station()
        path = _path_through(station, next_station)
        mediator.stations = [station, next_station]
        mediator.paths = [path]
        metro = Metro()
        metro.path_id = path.id

        first_passenger = Passenger(next_station.shape)
        second_passenger = Passenger(next_station.shape)
        station.add_passenger(first_passenger)
        station.add_passenger(second_passenger)
        first_plan = TravelPlan([Node(next_station)])
        second_plan = TravelPlan([Node(next_station)])
        calls: list[Passenger] = []

        def second_callback(
            passenger: Passenger,
            _station: Station,
            required_path: Path,
            _nodes: dict[Station, Node],
        ) -> TravelPlan:
            calls.append(passenger)
            self.assertIs(required_path, path)
            self.assertIs(mediator.travel_plans[first_passenger], first_plan)
            return second_plan

        def first_callback(
            passenger: Passenger,
            _station: Station,
            required_path: Path,
            _nodes: dict[Station, Node],
        ) -> TravelPlan:
            calls.append(passenger)
            self.assertIs(required_path, path)
            mediator.get_travel_plan_starting_with_path = second_callback
            return first_plan

        mediator.get_travel_plan_starting_with_path = first_callback
        candidates = mediator.get_boarding_candidates_for_metro(
            metro, station, {}, mutate_travel_plans=True
        )

        self.assertEqual(calls, [first_passenger, second_passenger])
        self.assertEqual(candidates, [first_passenger, second_passenger])
        self.assertIs(mediator.travel_plans[first_passenger], first_plan)
        self.assertIs(mediator.travel_plans[second_passenger], second_plan)

    def test_boarding_re_reads_metro_path_id_after_each_plan_lookup(self):
        mediator = Mediator()
        station = _rect_station()
        destination = _circle_station()
        initial_path = _path_through(station, destination)
        rebound_path = _path_through(station, destination)
        mediator.paths = [initial_path, rebound_path]
        metro = Metro()
        metro.path_id = initial_path.id

        first_passenger = Passenger(destination.shape)
        second_passenger = Passenger(destination.shape)
        station.passengers = [first_passenger, second_passenger]
        first_plan = TravelPlan([])
        second_plan = TravelPlan([])
        first_plan.next_path = rebound_path
        second_plan.next_path = rebound_path

        class RebindingPlans(dict[Passenger, TravelPlan]):
            def get(self, passenger: Passenger, default=None):
                metro.path_id = rebound_path.id
                return super().get(passenger, default)

        mediator.travel_plans = RebindingPlans(
            {first_passenger: first_plan, second_passenger: second_plan}
        )
        mediator.get_travel_plan_starting_with_path = MagicMock(return_value=None)

        candidates = mediator.get_boarding_candidates_for_metro(
            metro, station, {}, mutate_travel_plans=False
        )

        self.assertEqual(candidates, [first_passenger, second_passenger])
        mediator.get_travel_plan_starting_with_path.assert_not_called()

    def test_constrained_lookup_occurs_once_after_empty_destination_callback(self):
        mediator = Mediator()
        station = _rect_station()
        passenger = Passenger(_triangle_station(10).shape)
        required_path = Path((10, 20, 30))
        accesses: list[Station] = []
        events: list[str] = []
        station_nodes = _LoggingNodeMap({station: Node(station)}, accesses)

        def no_destinations(_shape_type: object) -> list[Station]:
            events.append("destinations")
            return []

        mediator.get_stations_for_shape_type = no_destinations
        result = mediator.get_travel_plan_starting_with_path(
            passenger, station, required_path, station_nodes
        )

        self.assertIsNone(result)
        self.assertEqual(events, ["destinations"])
        self.assertEqual(accesses, [station])

    def test_constrained_route_re_reads_required_path_id_after_shared_lookup(self):
        mediator = Mediator()
        start = _rect_station()
        destination = _circle_station()
        required_path = _path_through(start, destination)
        required_path.id = "initial"
        passenger = Passenger(destination.shape)
        nodes = build_station_nodes_dict([start, destination], [required_path])
        mediator.stations = [start, destination]
        shared_calls: list[tuple[Station, Station]] = []

        def find_shared_path(station_a: Station, station_b: Station) -> Path:
            shared_calls.append((station_a, station_b))
            required_path.id = "rebound"
            return required_path

        mediator.find_shared_path = find_shared_path
        with patch.object(
            mediator_module,
            "bfs",
            return_value=[nodes[start], nodes[destination]],
        ):
            plan = mediator.get_travel_plan_starting_with_path(
                passenger, start, required_path, nodes
            )

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertIs(plan.next_path, required_path)
        self.assertEqual(shared_calls, [(start, destination), (start, destination)])

    def test_bulk_mapping_lookup_repeats_per_destination_and_skips_empty_list(self):
        mediator = Mediator()
        start = _rect_station()
        first_destination = _triangle_station(10)
        second_destination = _triangle_station(20)
        mediator.stations = [start, first_destination, second_destination]
        passenger = Passenger(first_destination.shape)
        start.add_passenger(passenger)
        mediator.passengers = [passenger]

        accesses: list[Station] = []
        station_nodes = _LoggingNodeMap(
            {station: Node(station) for station in mediator.stations}, accesses
        )
        mediator.get_stations_for_shape_type = MagicMock(
            side_effect=[[first_destination, second_destination], []]
        )
        with (
            patch.object(
                mediator_module,
                "build_station_nodes_dict",
                return_value=station_nodes,
            ),
            patch.object(mediator_module, "bfs", return_value=[]) as bfs,
        ):
            mediator.find_travel_plan_for_passengers()
            self.assertEqual(
                accesses,
                [start, first_destination, start, second_destination],
            )
            self.assertEqual(bfs.call_count, 2)

            accesses.clear()
            mediator.find_travel_plan_for_passengers()

        self.assertEqual(accesses, [])
        self.assertEqual(bfs.call_count, 2)

    def test_compression_mutates_and_returns_the_exact_node_list(self):
        path = Path((10, 20, 30))
        start_node = Node(_rect_station())
        middle_node = Node(_circle_station())
        end_node = Node(_triangle_station(20))
        for node in (start_node, middle_node, end_node):
            node.paths.add(path)
        node_path = [start_node, middle_node, end_node]

        result = self.mediator.skip_stations_on_same_path(node_path)

        self.assertIs(result, node_path)
        self.assertEqual(len(result), 2)
        self.assertIs(result[0], start_node)
        self.assertIs(result[1], end_node)
        self.assertIs(next(iter(result[0].paths)), path)

    def test_absent_metro_path_short_circuits_without_passengers_or_rng(self):
        mediator = Mediator(seed=123)
        station = _rect_station()
        station.passengers = _ExplodingPassengerList()
        metro = Metro()
        metro.path_id = "missing-path"
        mediator.paths = []
        mediator.get_travel_plan_starting_with_path = MagicMock(
            side_effect=AssertionError("planning must not run")
        )
        rng_state = mediator.context.python_random.getstate()

        result = mediator.get_boarding_candidates_for_metro(
            metro, station, {}, mutate_travel_plans=True
        )

        self.assertEqual(result, [])
        self.assertEqual(mediator.context.python_random.getstate(), rng_state)
        mediator.get_travel_plan_starting_with_path.assert_not_called()

    def test_unreachable_sentinel_identity_survives_rng_consuming_retries(self):
        mediator = Mediator(seed=456)
        start = _rect_station()
        first_destination = _triangle_station(10)
        second_destination = _triangle_station(20)
        mediator.stations = [start, first_destination, second_destination]
        mediator.paths = []
        passenger = Passenger(first_destination.shape)
        start.add_passenger(passenger)
        mediator.passengers = [passenger]
        sentinel = TravelPlan([])
        mediator.travel_plans[passenger] = sentinel

        initial_rng_state = mediator.context.python_random.getstate()
        mediator.find_travel_plan_for_passengers()
        first_retry_rng_state = mediator.context.python_random.getstate()
        self.assertNotEqual(first_retry_rng_state, initial_rng_state)
        self.assertIs(mediator.travel_plans[passenger], sentinel)

        mediator.find_travel_plan_for_passengers()
        self.assertNotEqual(
            mediator.context.python_random.getstate(), first_retry_rng_state
        )
        self.assertIs(mediator.travel_plans[passenger], sentinel)

    def test_cached_plan_query_re_reads_rebound_map_for_index_lookup(self):
        mediator = Mediator()
        passenger = Passenger(_triangle_station(10).shape)
        old_plan = TravelPlan([])
        active_plan = TravelPlan([])
        active_plan.next_path = Path((10, 20, 30))
        replacement = {passenger: active_plan}

        class RebindingPlans(dict[Passenger, TravelPlan]):
            def __contains__(self, item: object) -> bool:
                mediator.travel_plans = replacement
                return super().__contains__(item)

        mediator.travel_plans = RebindingPlans({passenger: old_plan})

        self.assertTrue(mediator.passenger_has_travel_plan(passenger))

    def test_adjacent_arrival_is_skipped_until_the_next_bulk_call(self):
        mediator = Mediator()
        station = _rect_station()
        mediator.stations = [station]
        first_passenger = Passenger(station.shape)
        second_passenger = Passenger(station.shape)
        station.add_passenger(first_passenger)
        station.add_passenger(second_passenger)
        mediator.passengers = [first_passenger, second_passenger]
        mediator.travel_plans = {
            first_passenger: TravelPlan([]),
            second_passenger: TravelPlan([]),
        }

        mediator.find_travel_plan_for_passengers()

        self.assertTrue(first_passenger.is_at_destination)
        self.assertFalse(second_passenger.is_at_destination)
        self.assertEqual(station.passengers, [second_passenger])
        self.assertEqual(mediator.passengers, [second_passenger])
        self.assertIn(second_passenger, mediator.travel_plans)

        mediator.find_travel_plan_for_passengers()
        self.assertTrue(second_passenger.is_at_destination)
        self.assertEqual(station.passengers, [])
        self.assertEqual(mediator.passengers, [])

    def test_plan_hook_sees_constrained_plan_unowned_and_bulk_plan_installed(self):
        mediator = Mediator()
        start = _rect_station()
        destination = _circle_station()
        path = _path_through(start, destination)
        mediator.stations = [start, destination]
        mediator.paths = [path]
        passenger = Passenger(destination.shape)
        supplied_nodes = build_station_nodes_dict(mediator.stations, mediator.paths)
        hook_visibility: list[bool] = []

        class ObservingTravelPlan(TravelPlan):
            def get_next_station(self) -> Station | None:
                hook_visibility.append(
                    any(self is plan for plan in mediator.travel_plans.values())
                )
                return super().get_next_station()

        def plan_factory(node_path: list[Node]) -> ObservingTravelPlan:
            return ObservingTravelPlan(node_path)

        with patch.object(mediator_module, "TravelPlan", new=plan_factory):
            constrained_plan = mediator.get_travel_plan_starting_with_path(
                passenger, start, path, supplied_nodes
            )
            self.assertIsNotNone(constrained_plan)
            assert constrained_plan is not None
            self.assertEqual(hook_visibility, [False])
            self.assertIs(constrained_plan.node_path[0], supplied_nodes[destination])
            self.assertIs(constrained_plan.next_station, destination)
            self.assertIs(constrained_plan.next_path, path)

            start.add_passenger(passenger)
            mediator.passengers = [passenger]
            mediator.find_travel_plan_for_passengers()

        self.assertEqual(hook_visibility, [False, True])
        self.assertIsInstance(mediator.travel_plans[passenger], ObservingTravelPlan)
        self.assertIs(mediator.travel_plans[passenger].next_path, path)
