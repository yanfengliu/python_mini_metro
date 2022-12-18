from __future__ import annotations

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
)
from entity.get_entity import get_random_stations
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from event import KeyboardEvent, KeyboardEventType, MouseEvent, MouseEventType
from geometry.point import Point
from geometry.type import ShapeType
from singleton import Singleton
from travel_plan import TravelPlan
from utils import get_shape_from_type

TravelPlans = Dict[Passenger, TravelPlan]


class Mediator(Singleton):
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

    def react(self, event: pygame.event.Event):
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

    def spawn_passengers(self):
        for station in self.stations:
            station_types = self.get_station_shape_types()
            other_station_shape_types = [
                x for x in station_types if x != station.shape.type
            ]
            destination_shape_type = random.choice(other_station_shape_types)
            destination_shape = get_shape_from_type(
                destination_shape_type, passenger_color, passenger_size
            )
            passenger = Passenger(destination_shape)
            if station.has_room():
                station.add_passenger(passenger)

    def increment_time(self, dt_ms: int) -> None:
        if self.is_paused:
            return

        self.time_ms += dt_ms
        self.steps += 1
        self.steps_since_last_spawn += 1

        for path in self.paths:
            for metro in path.metros:
                path.move_metro(metro, dt_ms)

        if (
            self.steps == self.passenger_spawning_step
            or self.steps_since_last_spawn == self.passenger_spawning_interval_step
        ):
            self.spawn_passengers()
            self.steps_since_last_spawn = 0
