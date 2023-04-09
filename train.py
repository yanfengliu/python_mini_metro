import pygame

from line import Line
from station import Station


class Train:
    def __init__(self, line: Line):
        self.line = line
        self.current_station_index = 0
        self.current_station = self.line.stations[self.current_station_index]
        self.position = self.current_station.position
        self.speed = 2
        self.direction = 1  # 1 for forward, -1 for backward

    def update(self) -> None:
        """Update the train's position and move it between stations."""
        if 0 <= self.current_station_index + self.direction < len(self.line.stations):
            next_station = self.line.stations[
                self.current_station_index + self.direction
            ]
            dx = next_station.position[0] - self.position[0]
            dy = next_station.position[1] - self.position[1]
            distance = (dx**2 + dy**2) ** 0.5

            if distance <= self.speed:
                self.current_station_index += self.direction
                self.position = next_station.position
            else:
                self.position = (
                    self.position[0] + self.speed * dx / distance,
                    self.position[1] + self.speed * dy / distance,
                )
        else:
            self.direction *= -1

    def render(self, screen: pygame.Surface) -> None:
        """Render the train on the screen.

        :param screen: The Pygame surface to draw on.
        """
        color = self.line.color
        pygame.draw.circle(
            screen, color, (round(self.position[0]), round(self.position[1])), 5
        )
