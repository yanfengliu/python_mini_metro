import pygame


class Train:
    def __init__(self, game, line):
        self.game = game
        self.line = line
        self.current_station = line.stations[0]
        self.speed = 2

    def update(self):
        next_station = self.line.next_station(self.current_station)
        if next_station:
            direction = (
                next_station.position[0] - self.current_station.position[0],
                next_station.position[1] - self.current_station.position[1],
            )
            distance = (direction[0] ** 2 + direction[1] ** 2) ** 0.5
            unit_direction = (direction[0] / distance, direction[1] / distance)

            self.current_station.position = (
                self.current_station.position[0] + unit_direction[0] * self.speed,
                self.current_station.position[1] + unit_direction[1] * self.speed,
            )

            if self.game.city.station_at_position(next_station.position, radius=15):
                self.current_station = next_station

    def render(self, screen):
        pygame.draw.circle(screen, (0, 255, 0), self.current_station.position, 7)
