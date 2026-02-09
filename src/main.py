import os

import pygame
from config import framerate, screen_color, screen_height, screen_width
from event.convert import convert_pygame_event
from geometry.point import Point
from mediator import Mediator


def run_game(max_frames: int | None = None) -> None:
    pygame.init()
    flags = pygame.SCALED
    screen = pygame.display.set_mode((screen_width, screen_height), flags, vsync=1)
    clock = pygame.time.Clock()
    mediator = Mediator()
    frames = 0

    while True:
        dt_ms = clock.tick(framerate)
        is_game_over = mediator.is_game_over is True
        if not is_game_over:
            mediator.increment_time(dt_ms)
        screen.fill(screen_color)
        mediator.render(screen)

        # react to user interaction
        restart_requested = False
        for pygame_event in pygame.event.get():
            if pygame_event.type == pygame.QUIT:
                raise SystemExit
            else:
                if is_game_over:
                    if pygame_event.type == pygame.KEYUP:
                        if pygame_event.key == pygame.K_r:
                            restart_requested = True
                            break
                        if pygame_event.key == pygame.K_ESCAPE:
                            raise SystemExit
                    if pygame_event.type == pygame.MOUSEBUTTONUP:
                        position = getattr(pygame_event, "pos", pygame.mouse.get_pos())
                        action = mediator.handle_game_over_click(
                            Point(position[0], position[1])
                        )
                        if action == "restart":
                            restart_requested = True
                            break
                        if action == "exit":
                            raise SystemExit
                    continue
                event = convert_pygame_event(pygame_event)
                mediator.react(event)

        pygame.display.flip()
        if restart_requested:
            mediator = Mediator()
            continue

        if max_frames is not None:
            frames += 1
            if frames >= max_frames:
                break


if __name__ == "__main__":
    max_frames_env = os.getenv("PYTHON_MINI_METRO_MAX_FRAMES")
    max_frames = int(max_frames_env) if max_frames_env and max_frames_env.isdigit() else None
    run_game(max_frames=max_frames)
