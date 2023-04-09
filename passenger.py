import random


class Passenger:
    def __init__(self, origin, destination):
        self.origin = origin
        self.destination = destination
        self.generate_destination()

    def generate_destination(self):
        destination_candidates = [
            station for station in self.origin.city.stations if station != self.origin
        ]
        self.destination = random.choice(destination_candidates)
