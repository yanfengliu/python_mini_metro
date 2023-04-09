class Line:
    def __init__(self, name):
        self.name = name
        self.stations = []

    def add_station(self, station):
        if station not in self.stations:
            self.stations.append(station)
            return True
        return False

    def remove_station(self, station):
        if station in self.stations:
            self.stations.remove(station)
            return True
        return False

    def next_station(self, current_station):
        if current_station in self.stations:
            index = self.stations.index(current_station)
            if index < len(self.stations) - 1:
                return self.stations[index + 1]
        return None
