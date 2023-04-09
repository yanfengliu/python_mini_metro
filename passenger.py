import random


class Passenger:
    def __init__(self, destination_types):
        self.destination_type = random.choice(destination_types)
        self.current_station = None
        self.on_train = False

    def board_train(self):
        if not self.on_train:
            self.on_train = True
            return True
        return False

    def leave_train(self, station):
        if self.on_train and station.station_type == self.destination_type:
            self.on_train = False
            self.current_station = station
            return True
        return False
