class Train:
    def __init__(self, game, line, capacity=6):
        self.game = game
        self.line = line
        self.capacity = capacity
        self.passengers = []
        self.current_station = None
        self.reverse = False

    def move(self):
        next_station = self.line.next_station(
            self.current_station, reverse=self.reverse
        )
        if next_station is not None:
            self.current_station = next_station
            self.drop_off_passengers()
            self.pick_up_passengers()

    def pick_up_passengers(self):
        available_space = self.capacity - len(self.passengers)
        if available_space > 0:
            for passenger in self.current_station.passengers[:]:
                if passenger.destination_type != self.current_station.station_type:
                    if passenger.board_train():
                        self.passengers.append(passenger)
                        self.current_station.remove_passenger(passenger)
                        available_space -= 1
                        if available_space == 0:
                            break

    def drop_off_passengers(self):
        for passenger in self.passengers[:]:
            if passenger.destination_type == self.current_station.station_type:
                if passenger.leave_train(self.current_station):
                    self.passengers.remove(passenger)
