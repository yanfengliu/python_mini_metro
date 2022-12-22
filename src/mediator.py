from __future__ import annotations

import pprint
import random
from typing import Dict, List

import pygame  # type: ignore

from config import (
    num_metros,
    num_path,
    num_stations,
    passenger_color,
    passenger_size,
    passenger_spawning_interval_step,
    passenger_spawning_start_step,
    station_color,
    station_size,
)
from entity.get_entity import get_random_stations
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from event.event import Event
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from geometry.point import Point
from geometry.type import ShapeType
from graph.graph_algo import bfs, build_station_nodes_dict
from graph.node import Node
from travel_plan import TravelPlan
from utils import get_random_color, get_shape_from_type

TravelPlans = Dict[Passenger, TravelPlan]
pp = pprint.PrettyPrinter(indent=4)


class Mediator:
    def __init__(self) -> None:
        # configs
        self.passenger_spawning_step = passenger_spawning_start_step
        self.passenger_spawning_interval_step = passenger_spawning_interval_step
        self.num_path = num_path
        self.num_metro = num_metros
        self.num_stations = num_stations

        # entities
        self.stations = get_random_stations(self.num_stations)
        self.metros: List[Metro] = []
        self.paths: List[Path] = []
        self.passengers: List[Passenger] = []

        # status
        self.time_ms = 0
        self.steps = 0
        self.steps_since_last_spawn = self.passenger_spawning_interval_step + 1
        self.is_mouse_down = False
        self.is_creating_path = False
        self.path_being_created: Path | None = None
        self.travel_plans: TravelPlans = {}
        self.is_paused = False

    def render(self, screen: pygame.surface.Surface) -> None:
        for path in self.paths:
            path.draw(screen)
        for station in self.stations:
            station.draw(screen)
        for metro in self.metros:
            metro.draw(screen)

    def react(self, event: Event):
        if isinstance(event, MouseEvent):
            entity = self.get_containing_entity(event.position)
            if event.event_type == MouseEventType.MOUSE_DOWN:
                self.is_mouse_down = True
                if entity and isinstance(entity, Station):
                    self.start_path_on_station(entity)

            elif event.event_type == MouseEventType.MOUSE_UP:
                self.is_mouse_down = False
                if self.is_creating_path:
                    assert self.path_being_created is not None
                    if entity and isinstance(entity, Station):
                        self.end_path_on_station(entity)
                    else:
                        self.abort_path_creation()

            elif event.event_type == MouseEventType.MOUSE_MOTION:
                if (
                    self.is_mouse_down
                    and self.is_creating_path
                    and self.path_being_created
                ):
                    if entity and isinstance(entity, Station):
                        self.add_station_to_path(entity)
                    else:
                        self.path_being_created.set_temporary_point(event.position)
        elif isinstance(event, KeyboardEvent):
            if event.event_type == KeyboardEventType.KEY_UP:
                if event.key == pygame.K_SPACE:
                    self.is_paused = not self.is_paused

    def get_containing_entity(self, position: Point):
        for station in self.stations:
            if station.contains(position):
                return station

    def start_path_on_station(self, station: Station) -> None:
        if len(self.paths) < self.num_path:
            self.is_creating_path = True
            path = Path()
            path.add_station(station)
            path.is_being_created = True
            self.path_being_created = path
            self.paths.append(path)

    def add_station_to_path(self, station: Station) -> None:
        assert self.path_being_created is not None
        if self.path_being_created.stations[-1] == station:
            return
        # loop
        if (
            len(self.path_being_created.stations) > 1
            and self.path_being_created.stations[0] == station
        ):
            self.path_being_created.set_loop()
        # non-loop
        elif self.path_being_created.stations[0] != station:
            if self.path_being_created.is_looped:
                self.path_being_created.remove_loop()
            self.path_being_created.add_station(station)

    def abort_path_creation(self) -> None:
        assert self.path_being_created is not None
        self.is_creating_path = False
        self.paths.remove(self.path_being_created)
        self.path_being_created = None

    def finish_path_creation(self) -> None:
        assert self.path_being_created is not None
        self.is_creating_path = False
        self.path_being_created.is_being_created = False
        self.path_being_created.remove_temporary_point()
        if len(self.metros) < self.num_metro:
            metro = Metro()
            self.path_being_created.add_metro(metro)
            self.metros.append(metro)
        self.path_being_created = None

    def end_path_on_station(self, station: Station) -> None:
        assert self.path_being_created is not None
        if self.path_being_created.stations[-1] == station:
            self.finish_path_creation()
        # loop
        elif (
            len(self.path_being_created.stations) > 1
            and self.path_being_created.stations[0] == station
        ):
            self.path_being_created.set_loop()
            self.finish_path_creation()
        # non-loop
        elif self.path_being_created.stations[0] != station:
            self.path_being_created.add_station(station)
            self.finish_path_creation()
        else:
            self.abort_path_creation()

    def get_station_shape_types(self):
        station_shape_types: List[ShapeType] = []
        for station in self.stations:
            if station.shape.type not in station_shape_types:
                station_shape_types.append(station.shape.type)
        return station_shape_types

    def is_passenger_spawn_time(self) -> bool:
        return (
            self.steps == self.passenger_spawning_step
            or self.steps_since_last_spawn == self.passenger_spawning_interval_step
        )

    def spawn_passengers(self):
        for station in self.stations:
            station_types = self.get_station_shape_types()
            other_station_shape_types = [
                x for x in station_types if x != station.shape.type
            ]
            destination_shape_type = random.choice(other_station_shape_types)
            destination_shape = get_shape_from_type(
                destination_shape_type, get_random_color(), passenger_size
            )
            passenger = Passenger(destination_shape)
            if station.has_room():
                station.add_passenger(passenger)
                self.passengers.append(passenger)

    def increment_time(self, dt_ms: int) -> None:
        if self.is_paused:
            return

        # record time
        self.time_ms += dt_ms
        self.steps += 1
        self.steps_since_last_spawn += 1

        # move metros
        for path in self.paths:
            for metro in path.metros:
                path.move_metro(metro, dt_ms)

        # spawn passengers
        if self.is_passenger_spawn_time():
            self.spawn_passengers()
            self.steps_since_last_spawn = 0

        self.find_travel_plan_for_passengers()
        self.move_passengers()

    def move_passengers(self) -> None:
        for metro in self.metros:
            if metro.current_station:
                passengers_to_remove = []
                passengers_from_metro_to_station = []
                passengers_from_station_to_metro = []

                # queue
                for passenger in metro.passengers:
                    if (
                        metro.current_station.shape.type
                        == passenger.destination_shape.type
                    ):
                        passengers_to_remove.append(passenger)
                    elif (
                        self.travel_plans[passenger].next_station
                        == metro.current_station
                    ):
                        passengers_from_metro_to_station.append(passenger)
                for passenger in metro.current_station.passengers:
                    if (
                        self.travel_plans[passenger].next_path
                        and self.travel_plans[passenger].next_path.id == metro.path_id  # type: ignore
                    ):
                        passengers_from_station_to_metro.append(passenger)

                # process
                for passenger in passengers_to_remove:
                    passenger.is_at_destination = True
                    metro.remove_passenger(passenger)
                    self.passengers.remove(passenger)
                    del self.travel_plans[passenger]

                for passenger in passengers_from_metro_to_station:
                    if metro.current_station.has_room():
                        metro.move_passenger(passenger, metro.current_station)
                        self.find_next_path_for_passenger_at_station(
                            passenger, metro.current_station
                        )

                for passenger in passengers_from_station_to_metro:
                    if metro.has_room():
                        metro.current_station.move_passenger(passenger, metro)

    def get_stations_for_shape_type(self, shape_type: ShapeType):
        stations: List[Station] = []
        for station in self.stations:
            if station.shape.type == shape_type:
                stations.append(station)

        return stations

    def find_shared_path(self, station_a: Station, station_b: Station) -> Path | None:
        for path in self.paths:
            stations = path.stations
            if (station_a in stations) and (station_b in stations):
                return path
        return None

    def passenger_has_travel_plan(self, passenger: Passenger) -> bool:
        return (
            passenger in self.travel_plans
            and self.travel_plans[passenger].next_path is not None
        )

    def find_next_path_for_passenger_at_station(
        self, passenger: Passenger, station: Station
    ):
        next_station = self.travel_plans[passenger].get_next_station()
        assert next_station is not None
        next_path = self.find_shared_path(station, next_station)
        assert next_path is not None
        self.travel_plans[passenger].next_path = next_path

    def skip_stations_on_same_path(self, node_path: List[Node]):
        assert len(node_path) >= 2
        if len(node_path) == 2:
            return node_path
        else:
            nodes_to_remove = []
            i = 0
            j = 1
            path_set_list = [x.paths for x in node_path]
            path_set_list.append(set())
            while j <= len(path_set_list) - 1:
                set_a = path_set_list[i]
                set_b = path_set_list[j]
                if set_a & set_b:
                    j += 1
                else:
                    for k in range(i + 1, j - 1):
                        nodes_to_remove.append(node_path[k])
                    i = j - 1
                    j += 1
            for node in nodes_to_remove:
                node_path.remove(node)
        return node_path

    def find_travel_plan_for_passengers(self) -> None:
        station_nodes_dict = build_station_nodes_dict(self.stations, self.paths)
        for station in self.stations:
            for passenger in station.passengers:
                if not self.passenger_has_travel_plan(passenger):
                    possible_dst_stations = self.get_stations_for_shape_type(
                        passenger.destination_shape.type
                    )
                    should_set_null_path = True
                    for possible_dst_station in possible_dst_stations:
                        start = station_nodes_dict[station]
                        end = station_nodes_dict[possible_dst_station]
                        node_path = bfs(start, end)
                        if len(node_path) == 1:
                            # passenger arrived at destination
                            station.remove_passenger(passenger)
                            self.passengers.remove(passenger)
                            passenger.is_at_destination = True
                            del self.travel_plans[passenger]
                            should_set_null_path = False
                            break
                        elif len(node_path) > 1:
                            node_path = self.skip_stations_on_same_path(node_path)
                            self.travel_plans[passenger] = TravelPlan(node_path[1:])
                            self.find_next_path_for_passenger_at_station(
                                passenger, station
                            )
                            should_set_null_path = False
                            break
                    if should_set_null_path:
                        self.travel_plans[passenger] = TravelPlan([])
