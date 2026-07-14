from unittest.mock import MagicMock

from test import mediator_test_support as support

# isort: split

from config import station_color, station_size
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from geometry.circle import Circle
from geometry.point import Point
from geometry.rect import Rect
from graph.node import Node
from mediator import Mediator
from travel_plan import TravelPlan


class TestMediatorPassengerFlow(support.MediatorTestCase):
    def test_move_passengers_covers_all_transfers(self):
        mediator, station_a, station_b, path, metro = self._build_two_station_mediator()
        mediator.update_unlocked_num_paths = MagicMock()
        mediator.update_unlocked_num_stations = MagicMock()

        passenger_at_destination = Passenger(station_a.shape)
        passenger_to_station = Passenger(station_b.shape)
        passenger_to_metro = Passenger(station_b.shape)

        metro.add_passenger(passenger_at_destination)
        metro.add_passenger(passenger_to_station)
        station_a.add_passenger(passenger_to_metro)
        mediator.passengers.extend(
            [passenger_at_destination, passenger_to_station, passenger_to_metro]
        )

        mediator.travel_plans[passenger_at_destination] = TravelPlan([Node(station_a)])
        mediator.travel_plans[passenger_to_station] = TravelPlan(
            [Node(station_a), Node(station_b)]
        )
        mediator.travel_plans[passenger_to_metro] = TravelPlan([Node(station_b)])
        mediator.travel_plans[passenger_to_metro].next_path = path

        self.assertEqual(mediator.total_travels_handled, 0)
        mediator.move_passengers(1000)

        self.assertNotIn(passenger_at_destination, mediator.passengers)
        self.assertTrue(passenger_at_destination.is_at_destination)
        self.assertNotIn(passenger_at_destination, mediator.travel_plans)
        self.assertEqual(mediator.score, 1)
        self.assertEqual(mediator.total_travels_handled, 1)

        self.assertIn(passenger_to_station, station_a.passengers)
        self.assertNotIn(passenger_to_station, metro.passengers)
        self.assertEqual(mediator.travel_plans[passenger_to_station].next_path, path)

        mediator.move_passengers(500)
        self.assertIn(passenger_to_metro, metro.passengers)
        self.assertNotIn(passenger_to_metro, station_a.passengers)

    def test_move_passengers_increments_total_travels_per_delivery(self):
        mediator, station_a, _, _, metro = self._build_two_station_mediator()

        passenger_one = Passenger(station_a.shape)
        passenger_two = Passenger(station_a.shape)
        metro.add_passenger(passenger_one)
        metro.add_passenger(passenger_two)
        mediator.passengers.extend([passenger_one, passenger_two])
        mediator.travel_plans[passenger_one] = TravelPlan([Node(station_a)])
        mediator.travel_plans[passenger_two] = TravelPlan([Node(station_a)])

        self.assertEqual(mediator.deliveries, 0)
        self.assertEqual(mediator.line_credits, 0)
        mediator.move_passengers(1000)

        self.assertEqual(mediator.deliveries, 2)
        self.assertEqual(mediator.line_credits, 2)
        self.assertEqual(mediator.total_travels_handled, 2)
        self.assertEqual(mediator.score, 2)

    def test_delivery_calls_public_progression_hooks_in_order_after_award(self):
        mediator, station_a, _, _, metro = self._build_two_station_mediator()
        passenger = Passenger(station_a.shape)
        metro.add_passenger(passenger)
        mediator.passengers.append(passenger)
        mediator.travel_plans[passenger] = TravelPlan([Node(station_a)])
        calls = []

        def record_path_update():
            calls.append(("paths", mediator.deliveries, mediator.line_credits))

        def record_station_update():
            calls.append(("stations", mediator.deliveries, mediator.line_credits))

        mediator.update_unlocked_num_paths = record_path_update
        mediator.update_unlocked_num_stations = record_station_update

        mediator.move_passengers(500)

        self.assertEqual(calls, [("paths", 1, 1), ("stations", 1, 1)])

    def test_metro_stops_to_board_then_accelerates(self):
        mediator = Mediator()
        mediator.is_passenger_spawn_time = MagicMock(return_value=False)
        station_a = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        station_b = Station(Circle(station_color, station_size), Point(1000, 0))
        mediator.stations = [station_a, station_b]
        path = Path((10, 20, 30))
        path.add_station(station_a)
        path.add_station(station_b)
        metro = Metro()
        path.add_metro(metro)
        metro.current_station = station_a
        mediator.paths = [path]
        mediator.metros = [metro]

        passenger = Passenger(station_b.shape)
        station_a.add_passenger(passenger)
        mediator.passengers = [passenger]
        mediator.find_travel_plan_for_passengers()

        mediator.increment_time(250)
        self.assertIn(passenger, station_a.passengers)
        self.assertEqual(metro.speed, 0)
        self.assertEqual(metro.stop_time_remaining_ms, 250)

        mediator.increment_time(250)
        self.assertIn(passenger, metro.passengers)
        self.assertNotIn(passenger, station_a.passengers)
        self.assertEqual(metro.stop_time_remaining_ms, 0)

        mediator.increment_time(500)
        self.assertGreater(metro.speed, 0)
        self.assertLess(metro.speed, metro.max_speed)

        mediator.increment_time(500)
        self.assertAlmostEqual(metro.speed, metro.max_speed, places=6)

    def test_metro_skips_stop_when_no_one_can_board(self):
        mediator = Mediator()
        mediator.is_passenger_spawn_time = MagicMock(return_value=False)
        station_a = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        station_b = Station(Circle(station_color, station_size), Point(1000, 0))
        mediator.stations = [station_a, station_b]
        path = Path((10, 20, 30))
        path.add_station(station_a)
        path.add_station(station_b)
        metro = Metro()
        path.add_metro(metro)
        metro.current_station = station_a
        mediator.paths = [path]
        mediator.metros = [metro]
        mediator.passengers = []

        mediator.increment_time(100)

        self.assertIsNone(metro.current_station)
        self.assertEqual(metro.stop_time_remaining_ms, 0)

    def test_increment_time_handles_padding_segment_without_crashing(self):
        mediator = Mediator()
        mediator.is_passenger_spawn_time = MagicMock(return_value=False)
        station_a = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        station_b = Station(Circle(station_color, station_size), Point(200, 0))
        station_c = Station(Circle(station_color, station_size), Point(400, 0))
        mediator.stations = [station_a, station_b, station_c]

        path = Path((10, 20, 30))
        path.add_station(station_a)
        path.add_station(station_b)
        path.add_station(station_c)
        metro = Metro()
        path.add_metro(metro)
        metro.current_segment_idx = 1  # padding segment
        metro.current_segment = path.segments[1]
        metro.position = metro.current_segment.segment_start
        metro.current_station = None

        mediator.paths = [path]
        mediator.metros = [metro]
        mediator.passengers = []

        mediator.increment_time(100)

        self.assertIsNotNone(metro.current_segment)

    def test_full_metro_does_not_dwell_when_no_one_can_alight(self):
        mediator = Mediator()
        mediator.is_passenger_spawn_time = MagicMock(return_value=False)
        station_a = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        station_b = Station(Circle(station_color, station_size), Point(1000, 0))
        mediator.stations = [station_a, station_b]

        path = Path((10, 20, 30))
        path.add_station(station_a)
        path.add_station(station_b)
        metro = Metro()
        path.add_metro(metro)
        metro.current_station = station_a
        mediator.paths = [path]
        mediator.metros = [metro]

        waiting_passenger = Passenger(station_b.shape)
        station_a.add_passenger(waiting_passenger)
        mediator.passengers = [waiting_passenger]
        mediator.find_travel_plan_for_passengers()

        for _ in range(metro.capacity):
            onboard_passenger = Passenger(station_b.shape)
            metro.add_passenger(onboard_passenger)
            mediator.passengers.append(onboard_passenger)
            mediator.travel_plans[onboard_passenger] = TravelPlan([Node(station_b)])

        mediator.increment_time(100)

        self.assertIsNone(metro.current_station)
        self.assertEqual(metro.stop_time_remaining_ms, 0)

    def test_passengers_unload_one_by_one_every_half_second(self):
        mediator, station_a, _, _, metro = self._build_two_station_mediator()
        mediator.update_unlocked_num_paths = MagicMock()
        mediator.update_unlocked_num_stations = MagicMock()
        passenger_one = Passenger(station_a.shape)
        passenger_two = Passenger(station_a.shape)
        metro.add_passenger(passenger_one)
        metro.add_passenger(passenger_two)
        mediator.passengers.extend([passenger_one, passenger_two])
        mediator.travel_plans[passenger_one] = TravelPlan([Node(station_a)])
        mediator.travel_plans[passenger_two] = TravelPlan([Node(station_a)])

        mediator.move_passengers(500)
        self.assertEqual(len(metro.passengers), 1)
        self.assertEqual(mediator.score, 1)

        mediator.move_passengers(500)
        self.assertEqual(len(metro.passengers), 0)
        self.assertEqual(mediator.score, 2)

    def test_passengers_board_one_by_one_every_half_second(self):
        mediator, station_a, station_b, path, metro = self._build_two_station_mediator()
        passenger_one = Passenger(station_b.shape)
        passenger_two = Passenger(station_b.shape)
        station_a.add_passenger(passenger_one)
        station_a.add_passenger(passenger_two)
        mediator.passengers.extend([passenger_one, passenger_two])
        mediator.travel_plans[passenger_one] = TravelPlan([Node(station_b)])
        mediator.travel_plans[passenger_one].next_path = path
        mediator.travel_plans[passenger_two] = TravelPlan([Node(station_b)])
        mediator.travel_plans[passenger_two].next_path = path

        mediator.move_passengers(500)
        self.assertEqual(len(metro.passengers), 1)
        self.assertEqual(len(station_a.passengers), 1)

        mediator.move_passengers(500)
        self.assertEqual(len(metro.passengers), 2)
        self.assertEqual(len(station_a.passengers), 0)
