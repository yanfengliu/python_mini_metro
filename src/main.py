import pygame  # type: ignore

from config import framerate, screen_color, screen_height, screen_width
from event import KeyboardEvent, KeyboardEventType, MouseEvent, MouseEventType
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
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise SystemExit
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_position = tuple_to_point(pygame.mouse.get_pos())
            mediator.react(MouseEvent(MouseEventType.MOUSE_DOWN, mouse_position))
        elif event.type == pygame.MOUSEBUTTONUP:
            mouse_position = tuple_to_point(pygame.mouse.get_pos())
            mediator.react(MouseEvent(MouseEventType.MOUSE_UP, mouse_position))
        elif event.type == pygame.MOUSEMOTION:
            mouse_position = tuple_to_point(pygame.mouse.get_pos())
            mediator.react(MouseEvent(MouseEventType.MOUSE_MOTION, mouse_position))
        elif event.type == pygame.KEYUP:
            mediator.react(KeyboardEvent(KeyboardEventType.KEY_UP, event.key))

    pygame.display.flip()
