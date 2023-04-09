from typing import Optional

import pygame

from city import City
from line import Line
from train import Train


class Game:
    def __init__(self, screen_width: int, screen_height: int):
        pygame.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Mini Metro")
        self.clock = pygame.time.Clock()
        self.running = True
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.city = City()
        self.lines = []
        self.trains = []
        self.current_line = None
        self.paused = False
        self.score = 0
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)

    def run(self) -> None:
        """Run the game loop."""
        while self.running:
            dt = self.clock.tick(60)  # Delta time since last frame in milliseconds
            self.handle_events()
            if not self.paused:
                self.update(dt)
            self.render()

        pygame.quit()

    def handle_events(self) -> None:
        """Handle user input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_p:
                    self.paused = not self.paused
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    pos = pygame.mouse.get_pos()
                    clicked_station = self.city.station_at_position(pos)
                    if clicked_station:
                        if not self.current_line:
                            self.current_line = Line("Line " + str(len(self.lines) + 1))
                            self.current_line.add_station(clicked_station)
                            self.lines.append(self.current_line)
                        else:
                            if clicked_station in self.current_line.stations:
                                self.current_line = None
                            else:
                                self.current_line.add_station(clicked_station)
            elif event.type == pygame.MOUSEMOTION:
                if self.current_line:
                    pos = pygame.mouse.get_pos()
                    clicked_station = self.city.station_at_position(pos)
                    if (
                        clicked_station
                        and clicked_station not in self.current_line.stations
                    ):
                        self.current_line.add_station(clicked_station)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left mouse button
                    if self.current_line:
                        new_train = Train(self.current_line)
                        self.trains.append(new_train)
                    self.current_line = None

    def update(self, dt: int) -> None:
        """Update the game state.

        :param dt: Time passed since the last frame in milliseconds.
        """
        self.city.update(dt)
        for train in self.trains:
            train.update()

    def render(self) -> None:
        """Render the game on the screen."""
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
