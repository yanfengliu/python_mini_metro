import math

import pygame

from city import City
from line import Line
from train import Train


class Game:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self.city = City(screen_width, screen_height, station_radius=20)
        self.lines = []
        self.trains = []
        self.current_line = None
        self._station_timer = 0
        self.station_generation_interval = 5000  # milliseconds
        self.min_station_distance = 100  # minimum distance between stations

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    pos = pygame.mouse.get_pos()
                    clicked_station = self.city.station_at_position(pos)
                    if clicked_station:
                        if not self.current_line:
                            self.current_line = Line("Line " + str(len(self.lines)))
                            self.lines.append(self.current_line)
                        self.current_line.add_station(clicked_station)

                        if not self.trains:
                            new_train = Train(self.current_line)
                            self.trains.append(new_train)

    def update(self) -> None:
        self.clock.tick(60)
        self._station_timer += self.clock.get_time()

        if self._station_timer >= self.station_generation_interval:
            self.city.generate_station()
            self._station_timer = 0

        for train in self.trains:
            train.update()

    def render(self) -> None:
        self.screen.fill((255, 255, 255))

        # Render lines
        for line in self.lines:
            line_color = line.color
            for i in range(len(line.stations) - 1):
                start = line.stations[i].position
                end = line.stations[i + 1].position
                pygame.draw.line(self.screen, line_color, start, end, 4)

        self.city.render(self.screen)

        for train in self.trains:
            train.render(self.screen)

        pygame.display.flip()
