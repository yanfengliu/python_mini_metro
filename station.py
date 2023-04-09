from typing import Tuple

import pygame


class Station:
    def __init__(self, position: Tuple[int, int], radius: int):
        self.position = position
        self.radius = radius

    def contains(self, pos: Tuple[int, int]) -> bool:
        dx = pos[0] - self.position[0]
        dy = pos[1] - self.position[1]
        return dx * dx + dy * dy <= self.radius * self.radius

    def render(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(screen, (0, 0, 0), self.position, self.radius, 2)
        pygame.draw.circle(screen, (255, 255, 255), self.position, self.radius - 2)
