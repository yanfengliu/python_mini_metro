class Station:
    def __init__(self, station_type, position, capacity=10):
        self.station_type = station_type
        self.position = position
        self.capacity = capacity
        self.passengers = []

    def is_full(self):
        return len(self.passengers) >= self.capacity

    def add_passenger(self, passenger):
        if not self.is_full():
            self.passengers.append(passenger)
            return True
        return False

    def remove_passenger(self, passenger):
        if passenger in self.passengers:
            self.passengers.remove(passenger)
            return True
        return False

    def count_passengers_for_destination(self, destination_type):
        return sum(
            1
            for passenger in self.passengers
            if passenger.destination_type == destination_type
        )
