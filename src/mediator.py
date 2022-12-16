from config import num_metros, num_path, num_stations, passenger_gen_rate
from event import Event, EventType, MouseEvent
from geometry.point import Point
from singleton import Singleton
from station import Station
from get_entity import get_metros, get_random_stations


class Mediator(Singleton):
    def __init__(self) -> None:
        self.stations = get_random_stations(num_stations)
        self.metros = get_metros(num_metros)
        self.passenger_rate = passenger_gen_rate
        self.num_path = num_path

    def react(self, event: Event):
        if isinstance(event, MouseEvent):
            if event.event_type == EventType.MOUSE_DOWN:
                entity = self.check_clicked_on(event.position)
                if entity and isinstance(entity, Station):
                    # create path
                    pass

    def check_clicked_on(self, position: Point):
        for station in self.stations:
            if station.contains(position):
                return station

        for metro in self.metros:
            if metro.contains(position):
                return metro
