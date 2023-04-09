import pygame


class Station:
    TYPES = ["circle", "triangle", "square"]

    def __init__(self, position, station_type):
        self.position = position
        self.station_type = station_type
        self.passengers = []

    def render(self, screen):
        color = (0, 0, 0)
        if self.station_type == "circle":
            pygame.draw.circle(screen, color, self.position, 15)
        elif self.station_type == "triangle":
            pygame.draw.polygon(
                screen,
                color,
                [
                    (self.position[0] - 15, self.position[1] + 15),
                    (self.position[0] + 15, self.position[1] + 15),
                    (self.position[0], self.position[1] - 15),
                ],
            )
        elif self.station_type == "square":
            pygame.draw.rect(
                screen, color, (self.position[0] - 15, self.position[1] - 15, 30, 30)
            )
