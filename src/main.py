import sys
from typing import List

import pygame

from config import framerate, screen_height, screen_width
from station import Station
from utils import get_random_position, get_random_station_shape

pygame.init()

# settings
flags = pygame.SCALED

# game constants initialization
screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
clock = pygame.time.Clock()

stations: List[Station] = []
for i in range(10):
    stations.append(
        Station(
            shape=get_random_station_shape(),
            position=get_random_position(screen_width, screen_height),
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
