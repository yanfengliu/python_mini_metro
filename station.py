from typing import Tuple

import pygame


class Station:
    TYPES = ["circle", "triangle", "square"]

    def __init__(self, position: Tuple[int, int], station_type: str):
        self.position = position
        self.station_type = station_type
        self.radius = 15
        self.passengers = []

    def render(self, screen: pygame.Surface) -> None:
        """Render the station on the screen.

        :param screen: The Pygame surface to draw on.
        """
        color = (0, 0, 0)
        if self.station_type == "circle":
            pygame.draw.circle(screen, color, self.position, self.radius, 2)
        elif self.station_type == "triangle":
            pygame.draw.polygon(screen, color, self._triangle_points(), 2)
        elif self.station_type == "square":
            pygame.draw.rect(screen, color, self._square_rect(), 2)

    def _triangle_points(
        self,
    ) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        """Return the coordinates of the triangle's vertices."""
        return (
            (self.position[0], self.position[1] - self.radius),
            (self.position[0] - self.radius, self.position[1] + self.radius),
            (self.position[0] + self.radius, self.position[1] + self.radius),
        )

    def _square_rect(self) -> Tuple[int, int, int, int]:
        """Return the coordinates and dimensions of the square."""
        return (
            self.position[0] - self.radius,
            self.position[1] - self.radius,
            self.radius * 2,
            self.radius * 2,
        )
