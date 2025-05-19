from typing import Generator, List, Tuple
import pygame

from config import framerate, screen_color
from mediator import Mediator, MeditatorState
from visuals.background import draw_waves

from .base import GameAPI


class ProgressiveStationGame(GameAPI):
    """
       A game simulator. When instantiating the simulator there's only one station.<br/>
       Call StationDeterminedGame::run() to start the game with same stations and given paths,
       however it yields when new station spawns.
    """
    def __init__(self, gamespeed: int = None, yield_interval_ms: int = 100, yield_when_station_spawned: bool = True, visuals: bool = False):
        """
            Initialize the game simulator.<br/>
            If visuals is true, it will display full game simulation on the screen with some speed costs.
        """
        super().__init__(is_static=False, gamespeed=gamespeed, visuals=visuals)


        self.yield_interval_ms = yield_interval_ms
        self.yield_when_station_spawned = yield_when_station_spawned
        self.time_acc_ms = 0

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
            if (self.yield_when_station_spawned and state == MeditatorState.NEW_STATION) \
                or self.time_acc_ms >= self.yield_interval_ms:
                yield
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
    
    # dummy interfaces
    def initialize_paths(self, *args, **kwargs):
        self.mediator.initialize_paths(*args, **kwargs)

    def delete_path(self, path_index: int):
        self.mediator.cancel_path(self.mediator.paths[path_index])

    def create_path(self, path_config: Tuple[List[int], bool]):
        self.mediator.create_path(path_config)

    def recreate_path(self, *args, **kwargs):
        self.mediator.recreate_path(*args, **kwargs)