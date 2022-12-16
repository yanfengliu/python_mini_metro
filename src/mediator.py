from config import num_metros, num_path, num_stations, passenger_gen_rate
from singleton import Singleton
from utils import get_metros, get_random_stations


class Mediator(Singleton):
    def __init__(self) -> None:
        self.stations = get_random_stations(num_stations)
        self.metros = get_metros(num_metros)
        self.passenger_rate = passenger_gen_rate
        self.num_path = num_path
