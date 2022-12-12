import sys
import pygame
pygame.init()

size = width, height = 640, 480
speed = [2, 2]
black = 0, 0, 0
flags = pygame.SCALED

screen = pygame.display.set_mode(size, flags, vsync=1)

ball = pygame.image.load("intro_ball.gif")
ballrect = ball.get_rect()

clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    ballrect = ballrect.move(speed)
    if ballrect.left < 0 or ballrect.right > width:
        speed[0] = -speed[0]
    if ballrect.top < 0 or ballrect.bottom > height:
        speed[1] = -speed[1]

    screen.fill(black)
    screen.blit(ball, ballrect)
    pygame.display.flip()
