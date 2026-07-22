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
from geometry.triangle import Triangle
from graph.graph_algo import build_station_nodes_dict
from graph.node import Node
from mediator import Mediator
from travel_plan import TravelPlan


class TestMediatorPaths(support.MediatorTestCase):
    def test_remove_path_conserves_onboard_riders(self):
        mediator, station_a, station_b, path, metro = self._build_two_station_mediator()
        passenger = Passenger(station_b.shape)
        metro.add_passenger(passenger)
        mediator.passengers.append(passenger)
        plan = TravelPlan([Node(station_b)])
        mediator.travel_plans[passenger] = plan
        mediator.path_buttons[0].assign_path(path)
        mediator.path_to_button[path] = mediator.path_buttons[0]
        mediator.path_to_color[path] = path.color
        passenger.wait_ms = 4321
        mediator.remove_path(path)
        self.assertIn(passenger, mediator.passengers)
        self.assertIn(passenger, station_a.passengers)
        self.assertNotIn(passenger, metro.passengers)
        self.assertIsNot(mediator.travel_plans.get(passenger), plan)
        self.assertEqual(passenger.wait_ms, 0)
        self.assertFalse(passenger.is_at_destination)
        self.assertNotIn(path, mediator.paths)

    def test_remove_path_recomputes_waiting_passenger_plan(self):
        mediator, station_a, station_b, path, _ = self._build_two_station_mediator()
        passenger = Passenger(station_b.shape)
        station_a.add_passenger(passenger)
        mediator.passengers.append(passenger)
        mediator.travel_plans[passenger] = TravelPlan([Node(station_b)])
        mediator.travel_plans[passenger].next_path = path
        mediator.path_buttons[0].assign_path(path)
        mediator.path_to_button[path] = mediator.path_buttons[0]
        mediator.path_to_color[path] = path.color

        mediator.remove_path(path)

        self.assertIn(passenger, mediator.passengers)
        self.assertIn(passenger, mediator.travel_plans)
        self.assertIsNone(mediator.travel_plans[passenger].next_path)
        self.assertIsNone(mediator.travel_plans[passenger].next_station)

    def test_remove_path_keeps_onboard_plan_until_transfer_station(self):
        mediator = Mediator()
        station_a = Station(
            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
        )
        station_b = Station(Circle(station_color, station_size), Point(100, 0))
        station_c = Station(Triangle(station_color, station_size), Point(200, 0))
        mediator.stations = [station_a, station_b, station_c]

        surviving_path = Path((10, 20, 30))
        surviving_path.add_station(station_a)
        surviving_path.add_station(station_b)
        removed_path = Path((40, 50, 60))
        removed_path.add_station(station_b)
        removed_path.add_station(station_c)
        metro = Metro()
        surviving_path.add_metro(metro)
        metro.current_station = station_b
        metro.position = station_b.position
        mediator.paths = [surviving_path, removed_path]
        mediator.metros = [metro]
        for idx, path in enumerate(mediator.paths):
            mediator.path_buttons[idx].assign_path(path)
            mediator.path_to_button[path] = mediator.path_buttons[idx]
            mediator.path_to_color[path] = path.color

        passenger = Passenger(station_c.shape)
        metro.add_passenger(passenger)
        mediator.passengers = [passenger]
        station_nodes = build_station_nodes_dict(mediator.stations, mediator.paths)
        travel_plan = TravelPlan([station_nodes[station_b], station_nodes[station_c]])
        travel_plan.next_path = surviving_path
        mediator.travel_plans[passenger] = travel_plan

        mediator.remove_path(removed_path)
        mediator.move_passengers(1000)

        self.assertIn(passenger, station_b.passengers)
        self.assertIn(passenger, mediator.travel_plans)
        self.assertIsNone(mediator.travel_plans[passenger].next_path)
        self.assertIsNone(mediator.travel_plans[passenger].next_station)

    def test_add_station_to_path_returns_on_duplicate(self):
        mediator = Mediator()
        station = mediator.stations[0]
        path = Path((0, 0, 0))
        path.add_station(station)
        mediator.path_being_created = path
        mediator.is_creating_path = True
        mediator.add_station_to_path(station)
        self.assertEqual(len(path.stations), 1)

    def test_add_station_to_path_removes_loop(self):
        mediator = Mediator()
        station_a = mediator.stations[0]
        station_b = mediator.stations[1]
        station_c = mediator.stations[2]
        path = Path((0, 0, 0))
        path.add_station(station_a)
        path.add_station(station_b)
        path.set_loop()
        mediator.path_being_created = path
        mediator.is_creating_path = True
        mediator.add_station_to_path(station_c)
        self.assertFalse(path.is_looped)

    def test_add_station_to_path_starts_station_snap_blip(self):
        mediator = Mediator()
        station_a = mediator.stations[0]
        station_b = mediator.stations[1]
        path = Path((12, 34, 56))
        path.add_station(station_a)
        station_b.start_snap_blip = MagicMock()
        mediator.path_being_created = path
        mediator.is_creating_path = True

        mediator.add_station_to_path(station_b)

        station_b.start_snap_blip.assert_called_once_with(mediator.time_ms, path.color)

    def test_end_path_on_station_aborts(self):
        mediator = Mediator()
        station = mediator.stations[0]
        mediator.start_path_on_station(station)
        mediator.end_path_on_station(station)
        self.assertFalse(mediator.is_creating_path)
        self.assertIsNone(mediator.path_being_created)
        self.assertEqual(len(mediator.paths), 0)

    def test_end_path_on_station_starts_station_snap_blip_when_added(self):
        mediator = Mediator()
        station_a = mediator.stations[0]
        station_b = mediator.stations[1]
        mediator.start_path_on_station(station_a)
        assert mediator.path_being_created is not None
        path_color = mediator.path_being_created.color
        station_b.start_snap_blip = MagicMock()

        mediator.end_path_on_station(station_b)

        station_b.start_snap_blip.assert_called_once_with(mediator.time_ms, path_color)
