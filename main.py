import sys
import pygame
from station import Station
from shapes.rect import Rect

pygame.init()

# settings
size = width, height = 640, 480
framerate = 60
flags = pygame.SCALED

# game constants initialization
screen = pygame.display.set_mode(size, flags, vsync=1)
clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    clock.tick(framerate)

    screen.fill(255, 255, 255)
    stations = [
        Station(
            position={"left": 50, "top": 100},
            shape=Rect(color=(0, 0, 0), width=20, height=20),
        )
    ]
    for station in stations:
        station.draw(screen)

    # for path in paths:
    #     # draw path

    # for passenger in passengers:
    #     # draw passenger

    # for metro in metros:
    #     # draw metro

    pygame.display.flip()
