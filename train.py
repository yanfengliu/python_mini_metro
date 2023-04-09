import pygame

from line import Line
from station import Station


class Train:
    def __init__(self, line: Line):
        self.line = line
        self.current_station_index = 0
        self.current_station = self.line.stations[self.current_station_index]
        self.position = self.current_station.position

    def update(self) -> None:
        """Update the train's position and move it between stations."""
        pass  # Implement train movement logic here

    def render(self, screen: pygame.Surface) -> None:
        """Render the train on the screen.

        :param screen: The Pygame surface to draw on.
        """
        color = (255, 0, 0)
        pygame.draw.circle(screen, color, self.position, 5)
