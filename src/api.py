from typing import Generator, List, Tuple
import pygame

from config import framerate, screen_color, screen_height, screen_width, num_stations_max
from mediator import Mediator, MeditatorState
from visuals.background import draw_waves

class StaticStationGame:
    """
       A game simulator. When instantiating the simulator all stations are generated randomly.<br/>
       Call StationDeterminedGame::run() to start the game with same stations and given paths.
    """
    def __init__(self, gamespeed: int = 250, visuals: bool = False):
        """
            Initialize the game simulator.<br/>
            If visuals is true, it will display full game simulation on the screen with some speed costs.
        """
        if visuals:
            pygame.init()
        self.mediator = Mediator(gamespeed, gen_stations_first=True)
        self.gamespeed = gamespeed
        self.clock = pygame.time.Clock()
        self.visuals = visuals

        if visuals:
            flags = pygame.SCALED
            self.screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
            self.mediator.assign_paths_to_buttons()
    
    def set_game_speed(self, gamespeed: float):
        self.gamespeed = gamespeed

    def run(self, *paths: Tuple[List[int], bool]) -> int:
        """
            Runs the game with the given initial paths.<br/>
            Each path has the format ([0, 1, ...], is_looped) as path: station1 -> station2 -> ... -> back to start if looped.<br/>
            Returns the final score.<br/><br/>
            Example:<br/>
            >>> game = StationDeterminedGame()
            >>> game.run(([0, 1, 2, 3, 4], True))
        """
        self.mediator.reset_progress()
        self.mediator.initialize_paths(*paths)
        game_over = False
        while not game_over:
            dt_ms = self.clock.tick(framerate)
            game_over = self.mediator.increment_time(dt_ms) == MeditatorState.ENDED
            if self.visuals:
                self.screen.fill(screen_color)
                draw_waves(self.screen, self.mediator.time_ms)
                self.mediator.render(self.screen)
                pygame.display.flip()
                
            for pygame_event in pygame.event.get():
                if pygame_event.type == pygame.QUIT:
                    raise SystemExit
        return self.mediator.score

class ProgressiveStationGame:
    """
       A game simulator. When instantiating the simulator there's only one station.<br/>
       Call StationDeterminedGame::run() to start the game with same stations and given paths,
       however it yields when new station spawns.
    """
    def __init__(self, gamespeed: int = 250, yield_interval_ms: int = 100, yield_when_station_spawned: bool = True, visuals: bool = False):
        """
            Initialize the game simulator.<br/>
            If visuals is true, it will display full game simulation on the screen with some speed costs.
        """
        self.mediator = Mediator(gamespeed, gen_stations_first=False)
        self.clock = pygame.time.Clock()
        
        self.gamespeed = gamespeed
        self.yield_interval_ms = yield_interval_ms
        self.yield_when_station_spawned = yield_when_station_spawned
        self.visuals = visuals

        self.time_acc_ms = 0

        if visuals:
            pygame.init()
            flags = pygame.SCALED
            self.screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
            self.mediator.assign_paths_to_buttons()
    
    def set_game_speed(self, gamespeed: float):
        self.gamespeed = gamespeed

    def run(self) -> Generator[None, List[Tuple[List[int], bool]], int]:
        """
            Runs the game with no path at start. However, if new station is spawned it will yield and wait for new paths sent by the user.<br/>
            If the game ends, it will return the final score.<br/><br/>
            Example:<br/>
            >>> game = ProgressiveStationGame()
            >>> simulation = game.run()
            >>> next(simulation)
            >>> while True:
            ...     simulation.send([([0, 1, 2, 3, 4], True), ...])
        """
        self.mediator.reset_progress()
        game_over = False
        while not game_over:
            dt_ms = self.clock.tick(framerate)
            state = self.mediator.increment_time(dt_ms)

            self.time_acc_ms += dt_ms
            if self.yield_when_station_spawned and state == MeditatorState.NEW_STATION or self.time_acc_ms >= self.yield_interval_ms:
                paths = yield
                self.mediator.initialize_paths(*paths)
                self.time_acc_ms = 0
            
            if state == MeditatorState.ENDED:
                game_over = True
            if self.visuals:
                self.screen.fill(screen_color)
                draw_waves(self.screen, self.mediator.time_ms)
                self.mediator.render(self.screen)
                pygame.display.flip()

            for pygame_event in pygame.event.get():
                if pygame_event.type == pygame.QUIT:
                    raise SystemExit
        return self.mediator.score