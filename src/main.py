import pygame  # type: ignore

from config import framerate, screen_color, screen_height, screen_width
from event.convert import convert_pygame_event
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from mediator import Mediator
from utils import tuple_to_point

pygame.init()

# settings
flags = pygame.SCALED

# game constants initialization
screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
clock = pygame.time.Clock()
pygame.transform.rotate(screen, 30)

mediator = Mediator()

while True:
    dt_ms = clock.tick(framerate)
    mediator.increment_time(dt_ms)
    screen.fill(screen_color)
    mediator.render(screen)

    # react to user interaction
    for pygame_event in pygame.event.get():
        if pygame_event.type == pygame.QUIT:
            raise SystemExit
        else:
            event = convert_pygame_event(pygame_event)
            mediator.react(event)

    pygame.display.flip()
