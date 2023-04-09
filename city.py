import random

from station import Station


class City:
    def __init__(self, game, station_types, max_stations):
        self.game = game
        self.station_types = station_types
        self.max_stations = max_stations
        self.stations = []

    def generate_station(self):
        if len(self.stations) < self.max_stations:
            station_type = random.choice(self.station_types)
            position = self.generate_station_position()

            # Check if the position is valid and not too close to other stations
            if self.is_valid_station_position(position):
                station = Station(station_type, position)
                self.stations.append(station)
                return station

        return None

    def generate_station_position(self):
        x = random.randint(0, self.game.screen_width)
        y = random.randint(0, self.game.screen_height)
        return x, y

    def is_valid_station_position(self, position):
        min_distance = 50  # Minimum distance between two stations

        for station in self.stations:
            distance = (
                (station.position[0] - position[0]) ** 2
                + (station.position[1] - position[1]) ** 2
            ) ** 0.5
            if distance < min_distance:
                return False

        return True
