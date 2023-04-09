import pygame

from game import Game


def main():
    game = Game(800, 600)
    game.running = True

    while game.running:
        game.handle_input()
        game.update()
        game.render()
        game.clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
