from typing import List
import pygame

from config import screen_height, screen_width
from mediator import Mediator

from entity.station import Station
from entity.path import Path

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

        if visuals:
            pygame.init()
            flags = pygame.SCALED
            self.screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
            self.mediator.assign_paths_to_buttons()

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