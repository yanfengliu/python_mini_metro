from math import ceil
from unittest.mock import MagicMock

from test import mediator_test_support as support

# isort: split

from config import (
    framerate,
    passenger_spawning_start_step,
    station_color,
    station_size,
)
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from geometry.triangle import Triangle
from geometry.type import ShapeType
from mediator import Mediator
from travel_plan import TravelPlan
from utils import get_random_position


class TestMediatorRouting(support.MediatorTestCase):
    def test_passengers_at_connected_stations_have_a_way_to_destination(self):
        self.mediator.stations = [
            Station(
                Rect(
                    color=station_color,
                    width=2 * station_size,
                    height=2 * station_size,
                ),
                Point(100, 100),
            ),
            Station(
                Circle(
                    color=station_color,
                    radius=station_size,
                ),
                Point(100, 200),
            ),
        ]
        # Need to draw stations if you want to override them
        for station in self.mediator.stations:
            station.draw(self.screen)

        # Run the game until first wave of passengers spawn
        for _ in range(passenger_spawning_start_step):
            self.mediator.increment_time(ceil(1000 / framerate))

        self.connect_stations([0, 1])
        self.mediator.increment_time(ceil(1000 / framerate))

        for passenger in self.mediator.passengers:
            self.assertIn(passenger, self.mediator.travel_plans)
            self.assertIsNotNone(self.mediator.travel_plans[passenger])
            self.assertIsNotNone(self.mediator.travel_plans[passenger].next_path)
            self.assertIsNotNone(self.mediator.travel_plans[passenger].next_station)

    def test_passengers_at_isolated_stations_have_no_way_to_destination(self):
        # Run the game until first wave of passengers spawn, then 1 more frame
        for _ in range(passenger_spawning_start_step + 1):
            self.mediator.increment_time(ceil(1000 / framerate))

        for passenger in self.mediator.passengers:
            self.assertIn(passenger, self.mediator.travel_plans)
            self.assertIsNotNone(self.mediator.travel_plans[passenger])
            self.assertIsNone(self.mediator.travel_plans[passenger].next_path)
            self.assertIsNone(self.mediator.travel_plans[passenger].next_station)

    def test_get_station_for_shape_type(self):
        self.mediator.stations = [
            Station(
                Rect(
                    color=station_color,
                    width=2 * station_size,
                    height=2 * station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Circle(
                    color=station_color,
                    radius=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Circle(
                    color=station_color,
                    radius=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Triangle(
                    color=station_color,
                    size=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Triangle(
                    color=station_color,
                    size=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
            Station(
                Triangle(
                    color=station_color,
                    size=station_size,
                ),
                get_random_position(self.width, self.height),
            ),
        ]
        rect_stations = self.mediator.get_stations_for_shape_type(ShapeType.RECT)
        circle_stations = self.mediator.get_stations_for_shape_type(ShapeType.CIRCLE)
        triangle_stations = self.mediator.get_stations_for_shape_type(
            ShapeType.TRIANGLE
        )

        self.assertCountEqual(rect_stations, self.mediator.stations[0:1])
        self.assertCountEqual(circle_stations, self.mediator.stations[1:3])
        self.assertCountEqual(triangle_stations, self.mediator.stations[3:])

    def test_skip_stations_on_same_path(self):
        station_a = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        station_b = Station(Circle(station_color, station_size), Point(100, 0))
        station_c = Station(Triangle(station_color, station_size), Point(200, 0))
        self.mediator.stations = [station_a, station_b, station_c]
        for station in self.mediator.stations:
            station.draw(self.screen)
        self.connect_stations([0, 1, 2])

        passenger_a = Passenger(station_c.shape)
        passenger_b = Passenger(station_a.shape)
        passenger_c = Passenger(station_b.shape)
        station_a.add_passenger(passenger_a)
        station_b.add_passenger(passenger_b)
        station_c.add_passenger(passenger_c)
        self.mediator.passengers = [passenger_a, passenger_b, passenger_c]

        self.mediator.find_travel_plan_for_passengers()
        for station in self.mediator.stations:
            for passenger in station.passengers:
                self.assertEqual(
                    len(self.mediator.travel_plans[passenger].node_path), 1
                )

    def test_find_shared_path_returns_none(self):
        mediator = Mediator()
        station_a = mediator.stations[0]
        station_b = mediator.stations[1]
        self.assertIsNone(mediator.find_shared_path(station_a, station_b))

    def test_find_travel_plan_handles_arrived_passenger(self):
        mediator = Mediator()
        station = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        mediator.stations = [station]
        passenger = Passenger(station.shape)
        station.add_passenger(passenger)
        mediator.passengers.append(passenger)
        mediator.travel_plans[passenger] = TravelPlan([])

        mediator.find_travel_plan_for_passengers()

        self.assertNotIn(passenger, station.passengers)
        self.assertNotIn(passenger, mediator.passengers)
        self.assertTrue(passenger.is_at_destination)
        self.assertNotIn(passenger, mediator.travel_plans)

    def test_passenger_boards_metro_using_shortest_destination_route(self):
        mediator = Mediator()
        start_station = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        intermediate_station = Station(
            Circle(station_color, station_size), Point(10, 0)
        )
        short_destination = Station(Triangle(station_color, station_size), Point(20, 0))
        long_destination = Station(Triangle(station_color, station_size), Point(30, 0))
        mediator.stations = [
            start_station,
            intermediate_station,
            short_destination,
            long_destination,
        ]

        short_path = Path((10, 20, 30))
        short_path.add_station(start_station)
        short_path.add_station(short_destination)

        long_path = Path((40, 50, 60))
        long_path.add_station(start_station)
        long_path.add_station(intermediate_station)
        long_path.add_station(long_destination)

        metro = Metro()
        short_path.add_metro(metro)
        metro.current_station = start_station
        mediator.paths = [short_path, long_path]
        mediator.metros = [metro]

        passenger = Passenger(short_destination.shape)
        start_station.add_passenger(passenger)
        mediator.passengers = [passenger]

        mediator.get_stations_for_shape_type = MagicMock(
            return_value=[long_destination, short_destination]
        )
        mediator.find_travel_plan_for_passengers()
        mediator.move_passengers(1000)

        self.assertIn(passenger, metro.passengers)
        self.assertNotIn(passenger, start_station.passengers)
        self.assertEqual(mediator.travel_plans[passenger].next_path, short_path)

    def test_passenger_boards_first_arriving_eligible_metro(self):
        mediator = Mediator()
        start_station = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        intermediate_station = Station(
            Circle(station_color, station_size), Point(10, 0)
        )
        short_destination = Station(Triangle(station_color, station_size), Point(20, 0))
        long_destination = Station(Triangle(station_color, station_size), Point(30, 0))
        mediator.stations = [
            start_station,
            intermediate_station,
            short_destination,
            long_destination,
        ]

        short_path = Path((10, 20, 30))
        short_path.add_station(start_station)
        short_path.add_station(short_destination)

        long_path = Path((40, 50, 60))
        long_path.add_station(start_station)
        long_path.add_station(intermediate_station)
        long_path.add_station(long_destination)

        metro = Metro()
        long_path.add_metro(metro)
        metro.current_station = start_station
        mediator.paths = [short_path, long_path]
        mediator.metros = [metro]

        passenger = Passenger(short_destination.shape)
        start_station.add_passenger(passenger)
        mediator.passengers = [passenger]

        mediator.find_travel_plan_for_passengers()
        self.assertEqual(mediator.travel_plans[passenger].next_path, short_path)

        mediator.move_passengers(1000)

        self.assertIn(passenger, metro.passengers)
        self.assertNotIn(passenger, start_station.passengers)
        self.assertEqual(mediator.travel_plans[passenger].next_path, long_path)
