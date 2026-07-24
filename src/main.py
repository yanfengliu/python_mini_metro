import os
from pathlib import Path
from types import SimpleNamespace

import pygame

from app_controller import AppController, AppScreen
from audio import NullAudio, create_audio, diff_and_play, snapshot_of
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
    RecordResult,
    load_highscores,
    record_score,
    save_highscores,
)
from mediator import Mediator
from rendering.game_renderer import GameRenderer
from save_game import load_game, save_game
from save_schema import SAVE_RULES_VERSION
from settings import load_settings, save_settings
from ui.menu_screens import (
    draw_best_indicator,
    draw_notice,
    draw_pause_menu,
    draw_settings_menu,
    draw_title_screen,
    draw_tutorial_overlay,
    title_layout,
)
from ui.viewport import get_viewport_transform

# Single canonical autosave slot (D-027); patchable so tests never touch it.
AUTOSAVE_PATH = Path(save_dir_name) / "autosave.json"
# Persistent high-score leaderboard (D-028); patchable so tests never touch it.
HIGHSCORES_PATH = Path(save_dir_name) / "highscores.json"
# Persistent presentation-only settings (D-029); patchable so tests never touch it.
SETTINGS_PATH = Path(save_dir_name) / "settings.json"


def read_settings():
    # load_settings already fails safe to DEFAULT_SETTINGS and never raises; the
    # module-level path is resolved at call time so tests can redirect it.
    return load_settings(SETTINGS_PATH)


def write_settings(settings) -> None:
    # Best-effort persist that never blocks the settings screen; save_settings
    # raises on failure and the swallow lives here, as for autosave/highscores.
    try:
        save_settings(settings, SETTINGS_PATH)
    except Exception:
        pass


TUTORIAL_SEED = 42  # the probed seed whose 3 initial stations are all distinct
_TUTORIAL_NO_GAME_OVER = 10**9


def _tutorial_mediator():
    # A seeded coached-tutorial game whose game-over is suppressed on THIS instance
    # so the sim never freezes mid-lesson (GM-08c, D-031): a per-instance write,
    # not a Mediator class or config change — the tutorial is a forgiving sandbox.
    mediator = Mediator(seed=TUTORIAL_SEED)
    mediator.overdue_passenger_threshold = _TUTORIAL_NO_GAME_OVER
    return mediator


def _default_audio_backend(max_frames: int | None):
    # The real-audio opt-in used ONLY by the __main__ entry point: a human run
    # (max_frames is None) builds procedural audio; an env-driven headless run
    # (PYTHON_MINI_METRO_MAX_FRAMES set) stays silent. run_game itself NEVER
    # calls this — it defaults to NullAudio — so no programmatic caller or test
    # opens a mixer even when it drives real run_game UNBOUNDED and patches only
    # main.pygame (audio.py imports its own pygame; GM-08b review MAJOR).
    return create_audio() if max_frames is None else NullAudio()


def _audio_step(controller, state, previous_audio_session, snapshot, backend):
    # One per-frame audio consumer step, run AFTER reconcile_game_over so it reads
    # the post-promotion state and mediator counters. It owns its OWN session ref
    # (never the loop's previous_session, already advanced before the hook): the
    # moment controller.session changes it re-baselines the snapshot to the live
    # mediator, so New Game / Restart / Continue never replay a stored delta as a
    # spurious tone burst (GM-08b, review MAJOR-1). Re-baselining to the CURRENT
    # (post-batch) state is what avoids that burst; the accepted price is that a
    # gameplay mutation in the SAME event batch as a session swap (e.g. a line
    # purchase clicked in the same ~16 ms frame as Continue) is absorbed into the
    # baseline and its tone missed — a best-effort limit, like snap, unreachable
    # in human play (review MINOR). Then, only on a gameplay screen, it plays one
    # tone per newly-occurred delta at the live SFX volumes.
    if controller.session is not previous_audio_session:
        previous_audio_session = controller.session
        snapshot = snapshot_of(controller.mediator)
    if state in (AppScreen.PLAYING, AppScreen.PAUSE_MENU, AppScreen.GAME_OVER):
        snapshot = diff_and_play(
            controller.mediator,
            snapshot,
            backend,
            controller.current_settings.master_volume,
            controller.current_settings.sfx_volume,
        )
    return previous_audio_session, snapshot


def record_highscore(mediator: object) -> RecordResult | None:
    # The single best-effort recorder BOTH game-over surfaces funnel through --
    # the controller promotion seam and the window-close race -- so patching this
    # one symbol (or HIGHSCORES_PATH) intercepts all recording (codex MINOR-4).
    # It reads the objective AND the live map identity off the mediator (GM-09f2) so
    # a non-Classic run is keyed by its own map, and must never crash or block the
    # game loop: any failure (a corrupt board, an unwritable directory, an exotic
    # mediator lacking map_definition, or even a RecursionError from a pathologically
    # nested file -- MAJOR-2) is swallowed to None, exactly as the autosave writer
    # does. Reading the map directly (no `or classic` default) is fail-SAFE: a
    # missing map records nothing rather than mislabelling a score (GM-09f `or
    # DEFAULT` lesson). A real Mediator always has map_definition (default CLASSIC).
    try:
        deliveries = mediator.deliveries
        map_definition = mediator.map_definition
        document = load_highscores(HIGHSCORES_PATH)
        result = record_score(
            document,
            deliveries=deliveries,
            map=map_definition.map_id,
            map_definition_version=map_definition.map_definition_version,
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
    audio_backend=None,
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

    def build_tutorial():
        # The coached-tutorial triple over a seeded, game-over-suppressed mediator
        # (GM-08c, D-031); same shape as build_game.
        mediator = _tutorial_mediator()
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
    # and hands back the result for the best indicator (D-028). The controller hands
    # the seam the LIVE mediator (GM-09f2), so the promotion and the window-close
    # race both call the IDENTICAL record_highscore(mediator) -- which reads the
    # deliveries objective AND the map identity off it. record_highscore is looked
    # up at call time (not bound) so a test patching main.record_highscore intercepts
    # both surfaces through this one seam (codex MINOR-4).
    def _record_promotion(mediator: object) -> RecordResult | None:
        return record_highscore(mediator)

    highscores = SimpleNamespace(record=_record_promotion)

    # The controller loads presentation-only settings at construction and edits
    # them through this seam on the SETTINGS screen (D-029).
    settings = SimpleNamespace(load=read_settings, save=write_settings)

    if start_state is None:
        start_state = AppScreen.PLAYING if max_frames is not None else AppScreen.TITLE
    controller = AppController(
        build_game,
        start_state=start_state,
        build_from=build_from,
        autosave=autosave,
        highscores=highscores,
        settings=settings,
        build_tutorial=build_tutorial,
    )
    presentation_surface: pygame.Surface | None = None
    previous_session = controller.session
    # The audio consumer owns a SEPARATE session reference and counter snapshot,
    # never the render loop's previous_session (already advanced before the hook,
    # so it can never signal a reset). run_game defaults to an INERT backend: the
    # real mixer is opted into only at the __main__ entry point, so no test or
    # embedder — even one driving run_game unbounded and patching only
    # main.pygame — ever opens a mixer (GM-08b, review MAJOR-1 + MAJOR mixer leak).
    if audio_backend is None:
        audio_backend = NullAudio()
    previous_audio_session = controller.session
    audio_snapshot = snapshot_of(controller.mediator)
    frames = 0
    # The startup set_mode above stays windowed (RESIZABLE); fullscreen is a
    # separate later set_mode applied only when the setting changes (D-029), so
    # the initial call keeps its exact windowed contract.
    applied_fullscreen = False

    while True:
        elapsed_ms = clock.tick(framerate)
        if controller.current_settings.fullscreen != applied_fullscreen:
            applied_fullscreen = controller.current_settings.fullscreen
            window_flags = (
                pygame.FULLSCREEN | pygame.SCALED
                if applied_fullscreen
                else pygame.RESIZABLE
            )
            window_surface = pygame.display.set_mode(
                (screen_width, screen_height), window_flags
            )
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
        if (
            state in (AppScreen.TITLE, AppScreen.SETTINGS)
            or session is not previous_session
        ):
            advance = session.advance(0)
        else:
            advance = session.advance(elapsed_ms)
        previous_session = session

        # Deterministic game-over reconciliation (D-027/D-028 follow-up): a tick
        # that flips is_game_over with no promoting event this frame must still
        # promote, drop the autosave, and record the score THIS frame, so the best
        # indicator shows and the record no longer waits on an incidental event.
        # Idempotent and mutually exclusive with the window-close QUIT gate above,
        # which fires only while the state is still PLAYING/PAUSE_MENU.
        controller.reconcile_game_over()
        state = controller.state

        # Gameplay SFX (GM-08b): after reconcile so the promotion-frame game-over
        # tone is allowed and the snapshot reset sees the post-swap session.
        previous_audio_session, audio_snapshot = _audio_step(
            controller, state, previous_audio_session, audio_snapshot, audio_backend
        )

        # Coached tutorial (GM-08c): observe the post-tick mediator and advance the
        # lesson; a no-op off TUTORIAL.
        controller.advance_tutorial(elapsed_ms)

        game_surface.fill(screen_color)
        if state == AppScreen.TITLE:
            draw_title_screen(game_surface)
            if peek_autosave():
                _draw_title_continue_button(game_surface)
            if controller.notice:
                draw_notice(game_surface, controller.notice)
        elif state == AppScreen.SETTINGS:
            # A full-screen settings panel over the frozen game (D-029); its own
            # chrome, not the game frame.
            draw_settings_menu(game_surface, controller.current_settings)
        else:
            controller.renderer.draw(
                game_surface,
                controller.mediator,
                alpha=advance.alpha,
                reduced_motion=controller.current_settings.reduced_motion,
            )
            if state == AppScreen.PAUSE_MENU:
                draw_pause_menu(game_surface)
            elif state == AppScreen.GAME_OVER:
                # Painted after the renderer's game-over frame so the near-ceiling
                # game_renderer stays untouched; the primitive no-ops unless the
                # result is a new best (D-028).
                draw_best_indicator(game_surface, controller.last_highscore_result)
            elif state == AppScreen.TUTORIAL:
                # The coaching banner over the real game frame (GM-08c). The
                # controller supplies the display data so main never imports the
                # tutorial module itself.
                overlay = controller.tutorial_overlay()
                if overlay is not None:
                    draw_tutorial_overlay(game_surface, *overlay)
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
    # The sole real-audio opt-in: a human run builds procedural audio, an
    # env-driven headless run stays silent. Every programmatic run_game caller
    # (tests, embedders) uses the inert default instead (GM-08b MAJOR).
    run_game(max_frames=max_frames, audio_backend=_default_audio_backend(max_frames))
