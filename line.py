class Line:
    def __init__(self, name):
        self.name = name
        self.stations = []

    def add_station(self, station):
        if station not in self.stations:
            self.stations.append(station)
            return True
        return False

    def next_station(self, current_station, reverse=False):
        if current_station in self.stations:
            index = self.stations.index(current_station)
            if reverse:
                return self.stations[index - 1] if index > 0 else None
            else:
                return (
                    self.stations[index + 1] if index < len(self.stations) - 1 else None
                )
        return None
