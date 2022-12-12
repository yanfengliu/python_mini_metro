import sys
import pygame
pygame.init()

size = width, height = 640, 480
framerate = 60
speed = [2, 2]
black = 0, 0, 0
flags = pygame.SCALED

screen = pygame.display.set_mode(size, flags, vsync=1)

ball = pygame.image.load("intro_ball.gif")
ball_rect = ball.get_rect()

clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    clock.tick(framerate)
    ball_rect = ball_rect.move(speed)
    if ball_rect.left < 0 or ball_rect.right > width:
        speed[0] = -speed[0]
    if ball_rect.top < 0 or ball_rect.bottom > height:
        speed[1] = -speed[1]

    screen.fill(black)
    screen.blit(ball, ball_rect)
    pygame.display.flip()
