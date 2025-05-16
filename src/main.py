import pygame

from config import framerate, gamespeed, screen_color, screen_height, screen_width
from event.convert import convert_pygame_event
from mediator import Mediator, MeditatorState
from visuals.background import draw_waves

# init
pygame.init()

# settings
flags = pygame.SCALED

# game constants initialization
screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
clock = pygame.time.Clock()

mediator = Mediator(gen_stations_first=False)

game_over = False
p = False
while not game_over:
    dt_ms = clock.tick(framerate)
    game_over = mediator.increment_time(dt_ms) == MeditatorState.ENDED
    screen.fill(screen_color)
    draw_waves(screen, mediator.time_ms)
    mediator.render(screen)

    # react to user interaction
    for pygame_event in pygame.event.get():
        if pygame_event.type == pygame.QUIT:
            raise SystemExit
        else:
            event = convert_pygame_event(pygame_event)
            mediator.react(event)

    pygame.display.flip()

print('Game Over, Score = ', mediator.score)