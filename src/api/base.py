from typing import List
import pygame

from config import screen_height, screen_width, screen_color
from mediator import Mediator

from entity.station import Station
from entity.path import Path
from visuals.background import draw_waves

"""
Useful properties of game objects

- Station (seq# same as array index)
    public:
        - position
        - shape
        - passengers
        - capacity
        - timeout_ratio

    forbidden:
        - next_passenger_spawn_time

- Path
    public:
        - color / path_order
        - stations: List[Station]
        - metros: List[Metro]
        - is_looped
"""
class GameAPI:
    def __init__(self, is_static: bool, gamespeed: int = 1, visuals: bool = False):
        self.mediator = Mediator(gamespeed, gen_stations_first=is_static)
        # self.gamespeed = gamespeed // unused?
        self.clock = pygame.time.Clock()
        self.visuals = visuals

        pygame.init()
        pygame.display.quit()
        if visuals:
            self.open_window()

    # def set_game_speed(self, gamespeed: float):
    #     self.gamespeed = gamespeed

    @property
    def stations(self) -> List[Station]:
        return self.mediator.stations
    
    @property
    def paths(self) -> List[Path]:
        return self.mediator.paths
    
    @property
    def current_score(self) -> int:
        return self.mediator.score
    
    def open_window(self):
        self.visuals = True
        flags = pygame.SCALED
        self.screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
        self.mediator.assign_paths_to_buttons()
    
    def close_window(self):
        self.visuals = False
        pygame.display.quit()
    
    def screenshot(self, file_path: str, *initial_paths):
        if self.visuals:
            self.mediator.reset_progress()
            self.mediator.initialize_paths(*initial_paths)
            self.mediator.increment_time(0)

            self.screen.fill(screen_color)
            draw_waves(self.screen, self.mediator.time_ms)
            self.mediator.render(self.screen)
            pygame.display.flip()
            pygame.image.save(self.screen, file_path)
        else:
            raise RuntimeError("Visuals are not enabled. Cannot take a screenshot.")
