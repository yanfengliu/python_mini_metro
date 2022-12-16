import sys

import pygame

from config import framerate, screen_height, screen_width
from mediator import Mediator

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
            print("Mouse button down")
        elif event.type == pygame.MOUSEBUTTONUP:
            print("Mouse button up")

    clock.tick(framerate)
    screen.fill((255, 255, 255))

    # rendering
    for station in mediator.stations:
        station.draw(screen)

    pygame.display.flip()
