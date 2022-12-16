import sys

import pygame

from config import framerate, screen_height, screen_width
from event import EventType, MouseEvent
from mediator import Mediator
from utils import tuple_to_point

pygame.init()

# settings
flags = pygame.SCALED

# game constants initialization
screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
clock = pygame.time.Clock()

mediator = Mediator()

while True:
    # react to user interaction
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise SystemExit
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_position = tuple_to_point(pygame.mouse.get_pos())
            mediator.react(MouseEvent(EventType.MOUSE_DOWN, mouse_position))
        elif event.type == pygame.MOUSEBUTTONUP:
            mouse_position = tuple_to_point(pygame.mouse.get_pos())
            mediator.react(MouseEvent(EventType.MOUSE_UP, mouse_position))
        elif event.type == pygame.MOUSEMOTION:
            mouse_position = tuple_to_point(pygame.mouse.get_pos())
            mediator.react(MouseEvent(EventType.MOUSE_MOTION, mouse_position))

    clock.tick(framerate)
    screen.fill((255, 255, 255))

    # rendering
    for station in mediator.stations:
        station.draw(screen)
    for path in mediator.paths:
        path.draw(screen)
    for metro in mediator.metros:
        metro.draw(screen)
    for passenger in mediator.passengers:
        passenger.draw(screen)

    pygame.display.flip()
