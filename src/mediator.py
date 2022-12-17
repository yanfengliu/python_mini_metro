from typing import List

from config import num_metros, num_path, num_stations, passenger_gen_rate
from entity.get_entity import get_random_stations
from entity.metro import Metro
from entity.passenger import Passenger
from entity.path import Path
from entity.station import Station
from event import Event, EventType, MouseEvent
from geometry.point import Point
from singleton import Singleton


class Mediator(Singleton):
    def __init__(self) -> None:
        # entities
        self.stations = get_random_stations(num_stations)
        self.metros: List[Metro] = []
        self.paths: List[Path] = []
        self.passengers: List[Passenger] = []

        # status
        self.is_mouse_down = False
        self.is_creating_path = False
        self.path_being_created: Path | None = None

        # configs
        self.passenger_rate = passenger_gen_rate
        self.num_path = num_path
        self.num_metro = num_metros

    def react(self, event: Event):
        if isinstance(event, MouseEvent):
            if event.event_type == EventType.MOUSE_DOWN:
                self.is_mouse_down = True
                entity = self.get_containing_entity(event.position)
                if entity and isinstance(entity, Station):
                    self.start_path_on_station(entity)

            elif event.event_type == EventType.MOUSE_UP:
                self.is_mouse_down = False
                entity = self.get_containing_entity(event.position)
                if self.is_creating_path:
                    assert self.path_being_created is not None
                    if entity:
                        if isinstance(entity, Station):
                            self.end_path_on_station(entity)
                        else:
                            self.abort_path_creation()
                    else:
                        self.abort_path_creation()

            elif event.event_type == EventType.MOUSE_MOTION:
                if (
                    self.is_mouse_down
                    and self.is_creating_path
                    and self.path_being_created
                ):
                    self.path_being_created.add_temporary_point(event.position)

    def get_containing_entity(self, position: Point):
        for station in self.stations:
            if station.contains(position):
                return station

    def start_path_on_station(self, station: Station):
        if len(self.paths) < self.num_path:
            self.is_creating_path = True
            path = Path()
            path.add_station(station)
            path.is_being_created = True
            self.path_being_created = path
            self.paths.append(path)

    def abort_path_creation(self):
        assert self.path_being_created is not None
        self.is_creating_path = False
        self.paths.remove(self.path_being_created)
        self.path_being_created = None

    def finish_path_creation(self):
        assert self.path_being_created is not None
        self.is_creating_path = False
        self.path_being_created.is_being_created = False
        self.path_being_created.temp_point = None
        if len(self.metros) < self.num_metro:
            metro = Metro()
            self.path_being_created.add_metro(metro)
            self.metros.append(metro)
        self.path_being_created = None

    def end_path_on_station(self, station: Station):
        assert self.path_being_created is not None
        # loop
        if (
            len(self.path_being_created.stations) > 1
            and self.path_being_created.stations[0] != station
        ):
            self.path_being_created.is_looped = True
            self.finish_path_creation()
        # non-loop
        elif self.path_being_created.stations[0] != station:
            self.path_being_created.add_station(station)
            self.finish_path_creation()
        else:
            self.abort_path_creation()

    def increment_time(self, dt_ms: int):
        for path in self.paths:
            for metro in path.metros:
                path.move_metro(metro, dt_ms)
