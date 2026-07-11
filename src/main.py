import os

import pygame

from config import framerate, screen_color, screen_height, screen_width
from event.convert import convert_pygame_event
from game_session import GameSession
from geometry.point import Point
from mediator import Mediator
from rendering.game_renderer import GameRenderer
from ui.viewport import get_viewport_transform


def get_window_size(window_surface: pygame.surface.Surface) -> tuple[int, int]:
    size = window_surface.get_size()
    if (
        isinstance(size, tuple)
        and len(size) == 2
        and isinstance(size[0], (int, float))
        and isinstance(size[1], (int, float))
    ):
        return (int(size[0]), int(size[1]))
    return (screen_width, screen_height)


def run_game(max_frames: int | None = None) -> None:
    pygame.init()
    flags = pygame.RESIZABLE
    window_surface = pygame.display.set_mode((screen_width, screen_height), flags)
    game_surface = pygame.Surface((screen_width, screen_height))
    clock = pygame.time.Clock()
    mediator = Mediator()
    renderer = GameRenderer()
    session = GameSession(mediator, step_observer=renderer)
    session.prepare_layout(game_surface)
    presentation_surface: pygame.Surface | None = None
    frames = 0

    while True:
        elapsed_ms = clock.tick(framerate)
        window_width, window_height = get_window_size(window_surface)
        viewport = get_viewport_transform(
            window_width, window_height, screen_width, screen_height
        )
        restart_requested = False
        for pygame_event in pygame.event.get():
            if pygame_event.type == pygame.QUIT:
                raise SystemExit
            if mediator.is_game_over is True:
                if pygame_event.type == pygame.KEYUP:
                    if pygame_event.key == pygame.K_r:
                        restart_requested = True
                        break
                    if pygame_event.key == pygame.K_ESCAPE:
                        raise SystemExit
                if pygame_event.type == pygame.MOUSEBUTTONUP:
                    position = getattr(pygame_event, "pos", pygame.mouse.get_pos())
                    game_position = viewport.map_window_to_virtual(
                        position[0], position[1], screen_width, screen_height
                    )
                    if game_position is None:
                        continue
                    action = mediator.handle_game_over_click(Point(*game_position))
                    if action == "restart":
                        restart_requested = True
                        break
                    if action == "exit":
                        raise SystemExit
                continue

            game_position = None
            if pygame_event.type in (
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
            ):
                position = getattr(pygame_event, "pos", pygame.mouse.get_pos())
                game_position = viewport.map_window_to_virtual(
                    position[0], position[1], screen_width, screen_height
                )
                if game_position is None:
                    continue
            event = convert_pygame_event(pygame_event, mouse_position=game_position)
            session.dispatch(event)

        if restart_requested:
            mediator = Mediator()
            renderer = GameRenderer()
            session = GameSession(mediator, step_observer=renderer)
            session.prepare_layout(game_surface)
            advance = session.advance(0)
        else:
            advance = session.advance(elapsed_ms)

        game_surface.fill(screen_color)
        renderer.draw(game_surface, mediator, alpha=advance.alpha)
        window_surface.fill(screen_color)
        target_size = (viewport.width, viewport.height)
        if viewport.width > 0 and viewport.height > 0:
            if target_size == game_surface.get_size():
                scaled_surface = game_surface
            else:
                if (
                    presentation_surface is None
                    or presentation_surface.get_size() != target_size
                ):
                    presentation_surface = pygame.Surface(target_size)
                pygame.transform.smoothscale(
                    game_surface, target_size, presentation_surface
                )
                scaled_surface = presentation_surface
            window_surface.blit(scaled_surface, (viewport.offset_x, viewport.offset_y))

        pygame.display.flip()

        if max_frames is not None:
            frames += 1
            if frames >= max_frames:
                break


if __name__ == "__main__":
    max_frames_env = os.getenv("PYTHON_MINI_METRO_MAX_FRAMES")
    max_frames = (
        int(max_frames_env) if max_frames_env and max_frames_env.isdigit() else None
    )
    run_game(max_frames=max_frames)
