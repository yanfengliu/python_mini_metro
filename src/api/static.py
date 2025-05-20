from time import sleep
from typing import List, Tuple
import pygame

from config import framerate, screen_color
from mediator import Mediator, MeditatorState
from visuals.background import draw_waves

from .base import GameAPI


class StaticStationGame(GameAPI):
    """
       A game simulator. When instantiating the simulator all stations are generated randomly.<br/>
       Call StationDeterminedGame::run() to start the game with same stations and given paths.
    """
    def __init__(self, gamespeed: int = 1, visuals: bool = False):
        """
            Initialize the game simulator.<br/>
            If visuals is true, it will display full game simulation on the screen with some speed costs.
        """
        super().__init__(is_static=True, gamespeed=gamespeed, visuals=visuals)

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
            dt_ms = 1000 // framerate
            new_game_state = self.mediator.increment_time(dt_ms)
            game_over = (new_game_state == MeditatorState.ENDED)

            if self.visuals:
                self.screen.fill(screen_color)
                draw_waves(self.screen, self.mediator.time_ms)
                self.mediator.render(self.screen)
                pygame.display.flip()
                
                for pygame_event in pygame.event.get():
                    if pygame_event.type == pygame.QUIT:
                        raise SystemExit
                
                sleep(1 / framerate)
        
        return self.mediator.score
