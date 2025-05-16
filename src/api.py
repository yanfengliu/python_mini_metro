from ast import List, Tuple
import pygame

from config import framerate, gamespeed, num_stations_max, screen_color, screen_height, screen_width, num_stations_max
from mediator import Mediator

class StationDeterminedGame:
    """
       A game simulator. When instantiating the simulator all stations are generated randomly.
       Call StationDeterminedGame::run() to start the game with same stations and given paths.
    """
    def __init__(self, visuals: bool = False):
        """
            Initialize the game simulator.
            If visuals is true, it will display full game simulation on the screen with some speed costs.
        """
        self.mediator = Mediator(gen_stations_first=True)
        self.clock = pygame.time.Clock()
        self.visuals = visuals

        if visuals:
            pygame.init()
            flags = pygame.SCALED
            self.screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
            self.mediator.assign_paths_to_buttons()

    def run(self, *paths) -> int:
        """
            Runs the game with the given initial paths.
            Each path has the format ([station1, station2, ...], is_looped).
            Returns the final score.
        """
        self.mediator.initialize_paths(*paths)
        game_over = False
        while not game_over:
            dt_ms = self.clock.tick(framerate) * gamespeed
            game_over = self.mediator.increment_time(dt_ms)
            if self.visuals:
                self.screen.fill(screen_color)
                self.mediator.render(self.screen)
                pygame.display.flip()
        return self.mediator.score