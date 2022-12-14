import sys

import pygame

from shapes.rect import Rect
from station import Station
from utils import get_random_position, get_random_station_shape

pygame.init()

# settings
size = width, height = 640, 480
framerate = 60
flags = pygame.SCALED

# game constants initialization
screen = pygame.display.set_mode(size, flags, vsync=1)
clock = pygame.time.Clock()

stations = []
for i in range(10):
    stations.append(
        Station(
            position=get_random_position(width, height),
            shape=get_random_station_shape(),
        )
    )

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    clock.tick(framerate)

    screen.fill((255, 255, 255))
    for station in stations:
        station.draw(screen)

    # for path in paths:
    #     # draw path

    # for passenger in passengers:
    #     # draw passenger

    # for metro in metros:
    #     # draw metro

    pygame.display.flip()
