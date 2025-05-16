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
            dt_ms = self.clock.tick(framerate) * self.gamespeed
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
    def __init__(self, gamespeed: int = 250, visuals: bool = False):
        """
            Initialize the game simulator.<br/>
            If visuals is true, it will display full game simulation on the screen with some speed costs.
        """
        self.mediator = Mediator(gamespeed, gen_stations_first=False)
        self.gamespeed = gamespeed
        self.clock = pygame.time.Clock()
        self.visuals = visuals

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
            dt_ms = self.clock.tick(framerate) * self.gamespeed
            state = self.mediator.increment_time(dt_ms)
            if state == MeditatorState.NEW_STATION:
                paths = yield
                self.mediator.initialize_paths(*paths)
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

game = ProgressiveStationGame(gamespeed=50, visuals=True)
simulation = game.run()
next(simulation)
while True:
    try:
        paths = []
        while input('Add path? (y/n): ') == 'y':
            path = [int(a) for a in input('Path: ').split()]
            looped = input('Looped? (y/n): ') == 'y'
            paths.append((path, looped))
        simulation.send(paths)
    except StopIteration as result:
        print('Final score:', result.value)
        break