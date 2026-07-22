import os
from pathlib import Path
from types import SimpleNamespace

import pygame

from app_controller import AppController, AppScreen
from config import (
    framerate,
    game_over_button_border_color,
    game_over_button_border_width,
    game_over_button_color,
    game_over_hint_font_size,
    game_over_text_color,
    save_dir_name,
    screen_color,
    screen_height,
    screen_width,
)
from event.convert import convert_pygame_event
from game_session import GameSession
from highscores import (
    HIGHSCORES_MAP_CLASSIC,
    RecordResult,
    load_highscores,
    record_score,
    save_highscores,
)
from mediator import Mediator
from rendering.game_renderer import GameRenderer
from save_game import load_game, save_game
from save_schema import SAVE_RULES_VERSION
from ui.menu_screens import (
    draw_best_indicator,
    draw_notice,
    draw_pause_menu,
    draw_title_screen,
    title_layout,
)
from ui.viewport import get_viewport_transform

# Single canonical autosave slot (D-027); patchable so tests never touch it.
AUTOSAVE_PATH = Path(save_dir_name) / "autosave.json"
# Persistent high-score leaderboard (D-028); patchable so tests never touch it.
HIGHSCORES_PATH = Path(save_dir_name) / "highscores.json"


def record_highscore(mediator: object) -> RecordResult | None:
    # The single best-effort recorder BOTH game-over surfaces funnel through --
    # the controller promotion seam and the window-close race -- so patching this
    # one symbol (or HIGHSCORES_PATH) intercepts all recording (codex MINOR-4).
    # It reads the objective off the mediator and must never crash or block the
    # game loop: any failure (a corrupt board, an unwritable directory, or even a
    # RecursionError from a pathologically nested file -- MAJOR-2) is swallowed to
    # None, exactly as the proven autosave writer does.
    try:
        document = load_highscores(HIGHSCORES_PATH)
        result = record_score(
            document,
            deliveries=mediator.deliveries,
            map=HIGHSCORES_MAP_CLASSIC,
            rules_version=SAVE_RULES_VERSION,
        )
        save_highscores(result.document, HIGHSCORES_PATH)
        return result
    except Exception:
        return None


def write_autosave(mediator: object) -> None:
    # Best-effort atomic save that must never crash or block the game loop: the
    # real app raises only ValueError (a mid-gesture boundary) or OSError, and
    # the atomic writer leaves the previous valid autosave intact on failure.
    try:
        save_game(mediator, AUTOSAVE_PATH)
    except Exception:
        pass


def delete_autosave() -> None:
    try:
        AUTOSAVE_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def peek_autosave() -> bool:
    return AUTOSAVE_PATH.exists()


def load_autosave() -> Mediator:
    return load_game(AUTOSAVE_PATH)


def _draw_title_continue_button(surface: pygame.Surface) -> None:
    # Painted through main's own pygame -- not menu_screens' -- so the GM-07a
    # run-loop harness (which mocks main.pygame and stubs main.draw_title_screen
    # with a single-argument callable) stays inert; the base title chrome is
    # still drawn by draw_title_screen and this button reuses its style.
    width, height = surface.get_size()
    rect = title_layout(width, height)["continue"]
    pygame.draw.rect(surface, game_over_button_color, rect, border_radius=8)
    pygame.draw.rect(
        surface,
        game_over_button_border_color,
        rect,
        game_over_button_border_width,
        border_radius=8,
    )
    text = pygame.font.Font(None, game_over_hint_font_size).render(
        "Continue", True, game_over_text_color
    )
    surface.blit(text, text.get_rect(center=rect.center))


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


def run_game(
    max_frames: int | None = None,
    start_state: AppScreen | None = None,
) -> None:
    pygame.init()
    flags = pygame.RESIZABLE
    window_surface = pygame.display.set_mode((screen_width, screen_height), flags)
    game_surface = pygame.Surface((screen_width, screen_height))
    clock = pygame.time.Clock()

    def build_game():
        mediator = Mediator()
        renderer = GameRenderer()
        session = GameSession(mediator, step_observer=renderer)
        session.prepare_layout(game_surface)
        return mediator, renderer, session

    def build_from(mediator):
        # Wrap a loaded Mediator into the live triple exactly as build_game does
        # (prepare_layout included), returning the SAME loaded mediator.
        renderer = GameRenderer()
        session = GameSession(mediator, step_observer=renderer)
        session.prepare_layout(game_surface)
        return mediator, renderer, session

    autosave = SimpleNamespace(
        save=write_autosave,
        delete=delete_autosave,
        peek=peek_autosave,
        load=load_autosave,
    )

    # The controller records the high score at the PLAYING->GAME_OVER promotion
    # and hands back the result for the best indicator (D-028). The promotion
    # passes the deliveries scalar; route it through the one patchable
    # record_highscore (looked up at call time) so both game-over surfaces share
    # a single recorder and a single test seam (codex MINOR-4).
    def _record_promotion(deliveries: int) -> RecordResult | None:
        return record_highscore(SimpleNamespace(deliveries=deliveries))

    highscores = SimpleNamespace(record=_record_promotion)

    if start_state is None:
        start_state = AppScreen.PLAYING if max_frames is not None else AppScreen.TITLE
    controller = AppController(
        build_game,
        start_state=start_state,
        build_from=build_from,
        autosave=autosave,
        highscores=highscores,
    )
    presentation_surface: pygame.Surface | None = None
    previous_session = controller.session
    frames = 0

    while True:
        elapsed_ms = clock.tick(framerate)
        window_width, window_height = get_window_size(window_surface)
        viewport = get_viewport_transform(
            window_width, window_height, screen_width, screen_height
        )
        for pygame_event in pygame.event.get():
            if pygame_event.type == pygame.QUIT:
                # State-gated window-close autosave (D-027/F1): persist a mid-run
                # boundary, drop a finished run's save, and touch nothing on the
                # title screen (nor for a non-game controller).
                if controller.state in (AppScreen.PLAYING, AppScreen.PAUSE_MENU):
                    if controller.mediator.is_game_over:
                        delete_autosave()
                        # Record the finished run at the window-close race,
                        # mutually exclusive with the controller promotion which
                        # never fires for a QUIT event (D-028).
                        record_highscore(controller.mediator)
                    else:
                        write_autosave(controller.mediator)
                raise SystemExit
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
                    if pygame_event.type == pygame.MOUSEBUTTONUP:
                        game_position = (-1, -1)
                    else:
                        continue
            event = convert_pygame_event(pygame_event, mouse_position=game_position)
            controller.handle_event(event)

        state = controller.state
        session = controller.session
        if state == AppScreen.TITLE or session is not previous_session:
            advance = session.advance(0)
        else:
            advance = session.advance(elapsed_ms)
        previous_session = session

        game_surface.fill(screen_color)
        if state == AppScreen.TITLE:
            draw_title_screen(game_surface)
            if peek_autosave():
                _draw_title_continue_button(game_surface)
            if controller.notice:
                draw_notice(game_surface, controller.notice)
        else:
            controller.renderer.draw(
                game_surface, controller.mediator, alpha=advance.alpha
            )
            if state == AppScreen.PAUSE_MENU:
                draw_pause_menu(game_surface)
            elif state == AppScreen.GAME_OVER:
                # Painted after the renderer's game-over frame so the near-ceiling
                # game_renderer stays untouched; the primitive no-ops unless the
                # result is a new best (D-028).
                draw_best_indicator(game_surface, controller.last_highscore_result)
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
