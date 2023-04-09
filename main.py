import pygame

from game import Game


def main():
    pygame.init()

    screen_width = 800
    screen_height = 600
    game = Game(screen_width, screen_height)

    while game.running:
        game.handle_events()
        game.update()
        game.render()

    pygame.quit()


if __name__ == "__main__":
    main()
