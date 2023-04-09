import math

import pygame

from line import Line
from station import Station


class Train:
    def __init__(self, line: Line):
        self.line = line
        self.current_station = line.stations[0]
        self.position = self.current_station.position
        self.current_station_index = 0
        self.direction = 1  # 1 for forward, -1 for backward
        self.speed = 1

    def update(self) -> None:
        if len(self.line.stations) > 1:
            next_station_index = self.current_station_index + self.direction
            if 0 <= next_station_index < len(self.line.stations):
                next_station = self.line.stations[next_station_index]
                dx = next_station.position[0] - self.position[0]
                dy = next_station.position[1] - self.position[1]
                distance = math.sqrt(dx * dx + dy * dy)

                if distance <= self.speed:
                    self.position = next_station.position
                    self.current_station_index = next_station_index
                    self.current_station = next_station
                    if (
                        self.current_station_index == 0
                        or self.current_station_index == len(self.line.stations) - 1
                    ):
                        self.direction *= -1
                else:
                    self.position = (
                        self.position[0] + dx / distance * self.speed,
                        self.position[1] + dy / distance * self.speed,
                    )

    def render(self, screen: pygame.Surface) -> None:
        color = self.line.color
        rect_width = self.current_station.radius // 2
        rect_height = self.current_station.radius
        rect = pygame.Rect(0, 0, rect_width, rect_height)
        rect.center = self.position

        if len(self.line.stations) > 1:
            next_station_index = self.current_station_index + self.direction
            if 0 <= next_station_index < len(self.line.stations):
                next_station = self.line.stations[next_station_index]
                dx = next_station.position[0] - self.position[0]
                dy = next_station.position[1] - self.position[1]
                angle = math.atan2(dy, dx) * 180 / math.pi
                rotated_rect = pygame.Surface(
                    (rect_width, rect_height), pygame.SRCALPHA
                )
                pygame.draw.rect(rotated_rect, color, rect)
                rotated_rect = pygame.transform.rotate(rotated_rect, -angle)
                screen.blit(
                    rotated_rect,
                    (
                        self.position[0] - rect_width // 2,
                        self.position[1] - rect_height // 2,
                    ),
                )
            else:
                pygame.draw.rect(screen, color, rect)
        else:
            pygame.draw.rect(screen, color, rect)
