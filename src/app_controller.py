"""Screen-state machine for the human application shell (D-010).

The controller consumes already-converted virtual-coordinate events, decides
which of them reach the live ``GameSession``, and owns the one shared
game-reconstruction path (title New Game, pause-menu Restart, game-over
restart). It never touches the display; ``main.run_game`` keeps window,
surface, clock, viewport, and pump ownership and supplies the construction
callable, so headless and programmatic entries never meet this module.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from enum import Enum, auto

import pygame

from config import screen_height, screen_width
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from geometry.point import Point
from settings import DEFAULT_SETTINGS
from ui.menu_screens import pause_menu_layout, settings_menu_layout, title_layout

GameTriple = tuple[object, object, object]
_MENU_REASON = "menu"
_LOAD_FAILURE_NOTICE = "Could not load the saved game."
_VOLUME_STEP = 25
_VOLUME_MAX = 100


class AppScreen(Enum):
    """Top-level screens owned by the human entry path."""

    TITLE = auto()
    PLAYING = auto()
    PAUSE_MENU = auto()
    GAME_OVER = auto()
    SETTINGS = auto()


def _cycle_volume(value: int) -> int:
    # Step to the next grid multiple of 25, wrapping past 100 back to 0.
    nxt = (value // _VOLUME_STEP + 1) * _VOLUME_STEP
    return 0 if nxt > _VOLUME_MAX else nxt


def _is_key_up(event: object, key: int) -> bool:
    return (
        isinstance(event, KeyboardEvent)
        and event.event_type == KeyboardEventType.KEY_UP
        and event.key == key
    )


def _mouse_up_position(event: object) -> Point | None:
    if isinstance(event, MouseEvent) and event.event_type == MouseEventType.MOUSE_UP:
        return event.position
    return None


def _mouse_down_position(event: object) -> Point | None:
    if isinstance(event, MouseEvent) and event.event_type == MouseEventType.MOUSE_DOWN:
        return event.position
    return None


def _clicked(layout: dict[str, pygame.Rect], key: str, position: Point) -> bool:
    return bool(layout[key].collidepoint((position.left, position.top)))


class AppController:
    """Route converted events per screen and expose the live game triple."""

    def __init__(
        self,
        build_game: Callable[[], GameTriple],
        start_state: AppScreen = AppScreen.TITLE,
        *,
        build_from: Callable[[object], GameTriple] | None = None,
        autosave: object | None = None,
        highscores: object | None = None,
        settings: object | None = None,
    ) -> None:
        self._build_game = build_game
        # Every seam is optional with an inert default (D-027/D-028/D-029): a
        # controller built without them never autosaves, never records a high
        # score, never persists settings, keeps Continue unavailable, and
        # behaves exactly as the GM-07a baseline did.
        self._build_from = build_from
        self._autosave = autosave
        self._highscores = highscores
        self._settings = settings
        self.state = start_state
        self._armed_menu_control: str | None = None
        self._settings_origin = AppScreen.TITLE
        self.notice: str | None = None
        # The most recent game-over record result, or None when the last
        # promotion had no seam or minted no record (D-028/MINOR-7).
        self.last_highscore_result: object | None = None
        # The presentation-only settings value edited by the SETTINGS screen
        # (D-029); a seam-less controller keeps the typed defaults in memory.
        self.current_settings = (
            settings.load() if settings is not None else DEFAULT_SETTINGS
        )
        self.mediator, self.renderer, self.session = build_game()

    def _autosave_save(self) -> None:
        # Persistence is best-effort: the seam swallows its own failures, so a
        # save that cannot run still lets play or exit proceed (D-027/F3).
        if self._autosave is not None:
            self._autosave.save(self.mediator)

    def _autosave_delete(self) -> None:
        if self._autosave is not None:
            self._autosave.delete()

    def _record_highscore(self) -> None:
        # Record the finished run's lifetime deliveries exactly once at the
        # promotion (D-028). deliveries is read ONLY when the seam is present,
        # so a seam-less controller never touches a mediator that lacks it
        # (MAJOR-3). Every promotion (re)assigns the result -- to None when the
        # seam is absent or minted nothing -- so a restart shows no stale best.
        if self._highscores is not None:
            self.last_highscore_result = self._highscores.record(
                self.mediator.deliveries
            )
        else:
            self.last_highscore_result = None

    def reconcile_game_over(self) -> None:
        """Promote a finished run to ``GAME_OVER`` exactly once (D-027/D-028).

        Idempotent and a no-op unless the controller is still ``PLAYING`` and the
        mediator has flipped game over. It drops the autosave so a finished run
        can never be Continued (D-027) and records the run's high score exactly
        once (D-028), storing the result for the best indicator. ``handle_event``
        calls it at the top -- the historical inline promotion -- and
        ``main.run_game`` calls it once per frame after ``session.advance``, so a
        tick-driven game over with no promoting event still promotes, records,
        and shows the indicator the frame it ends, deterministically and
        independent of any incidental event. The window-close QUIT record in
        ``main`` stays mutually exclusive: once this promotes, that gate sees
        ``GAME_OVER`` and never re-records.
        """
        if self.state is AppScreen.PLAYING and self.mediator.is_game_over is True:
            self.state = AppScreen.GAME_OVER
            self._autosave_delete()
            self._record_highscore()

    def handle_event(self, event: object) -> None:
        """Route one converted event according to the current screen."""

        self.reconcile_game_over()
        if self.state is AppScreen.PLAYING:
            self._handle_playing(event)
        elif self.state is AppScreen.PAUSE_MENU:
            self._handle_pause_menu(event)
        elif self.state is AppScreen.TITLE:
            self._handle_title(event)
        elif self.state is AppScreen.GAME_OVER:
            self._handle_game_over(event)
        elif self.state is AppScreen.SETTINGS:
            self._handle_settings(event)

    def _start_new_game(self) -> None:
        self.mediator, self.renderer, self.session = self._build_game()
        self.notice = None
        self.state = AppScreen.PLAYING

    def _continue_game(self) -> None:
        # Continue is inert without a proven-loadable autosave: peek gates the
        # attempt (F4), a failed load surfaces a notice and stays on TITLE, and
        # success releases only the menu reason before swapping in the triple.
        autosave = self._autosave
        if autosave is None or not autosave.peek():
            return
        try:
            loaded = autosave.load()
        except (ValueError, OSError):
            self.notice = _LOAD_FAILURE_NOTICE
            return
        loaded.release_pause_reason(_MENU_REASON)
        self.mediator, self.renderer, self.session = self._build_from(loaded)
        self.notice = None
        self.state = AppScreen.PLAYING

    def _handle_playing(self, event: object) -> None:
        if _is_key_up(event, pygame.K_ESCAPE):
            # Abandon any armed gesture through the pinned letterbox-cancel
            # semantics strictly before freezing gameplay under the menu hold.
            self.session.dispatch(MouseEvent(MouseEventType.MOUSE_UP, Point(-1, -1)))
            self.mediator.hold_pause_reason(_MENU_REASON)
            # Save AFTER holding the menu reason so the document records it; the
            # letterbox cancel already cleared every armed gesture, so the
            # saver's quiescence preflight passes (D-027/F1).
            self._autosave_save()
            self.state = AppScreen.PAUSE_MENU
            return
        self.session.dispatch(event)

    def _close_pause_menu(self, next_state: AppScreen) -> None:
        # Leaving the menu state always disarms, so a stale press can never
        # fire a control on a later menu visit.
        self._armed_menu_control = None
        self.mediator.release_pause_reason(_MENU_REASON)
        self.state = next_state

    def _handle_pause_menu(self, event: object) -> None:
        # Gameplay input is never dispatched here, so the Space toggle cannot
        # reach the user pause reason and the menu hold stays controller-owned.
        if _is_key_up(event, pygame.K_ESCAPE):
            self._close_pause_menu(AppScreen.PLAYING)
            return
        layout = pause_menu_layout(screen_width, screen_height)
        pressed = _mouse_down_position(event)
        if pressed is not None:
            self._armed_menu_control = next(
                (key for key in layout if _clicked(layout, key, pressed)), None
            )
            return
        position = _mouse_up_position(event)
        if position is None:
            return
        # A release fires only the control its own in-menu press armed (review
        # F2): a bare release -- e.g. a gameplay drag that outlived the Escape
        # -- is a no-op, and every release disarms.
        armed = self._armed_menu_control
        self._armed_menu_control = None
        if armed is None or not _clicked(layout, armed, position):
            return
        if armed == "resume":
            self._close_pause_menu(AppScreen.PLAYING)
        elif armed == "restart":
            self._close_pause_menu(AppScreen.PLAYING)
            self._start_new_game()
        elif armed == "exit_to_title":
            # Rewrite the byte-identical boundary save BEFORE the menu reason is
            # released, so a later Continue reloads the menu-entry document.
            self._autosave_save()
            self._close_pause_menu(AppScreen.TITLE)
        elif armed == "settings":
            # Open settings WITHOUT releasing the menu hold, so Back returns to a
            # still-paused pause menu (D-029); the armed control is already
            # cleared above.
            self._open_settings(AppScreen.PAUSE_MENU)

    def _handle_title(self, event: object) -> None:
        if _is_key_up(event, pygame.K_RETURN):
            self._start_new_game()
            return
        position = _mouse_up_position(event)
        if position is None:
            return
        layout = title_layout(screen_width, screen_height)
        if _clicked(layout, "new_game", position):
            self._start_new_game()
        elif _clicked(layout, "continue", position):
            self._continue_game()
        elif _clicked(layout, "exit", position):
            raise SystemExit
        elif _clicked(layout, "settings", position):
            self._open_settings(AppScreen.TITLE)

    def _handle_game_over(self, event: object) -> None:
        # Mirrors the historical loop-inline branch: R restarts, Escape exits,
        # and clicks resolve through the prepared game-over rects.
        if isinstance(event, KeyboardEvent):
            if _is_key_up(event, pygame.K_r):
                self._start_new_game()
            elif _is_key_up(event, pygame.K_ESCAPE):
                self._autosave_delete()
                raise SystemExit
            return
        position = _mouse_up_position(event)
        if position is None:
            return
        action = self.mediator.handle_game_over_click(position)
        if action == "restart":
            self._start_new_game()
        elif action == "exit":
            self._autosave_delete()
            raise SystemExit

    def _open_settings(self, origin: AppScreen) -> None:
        # Record where Back returns to; entering from the pause menu keeps the
        # menu hold, so this never touches the pause reason (D-029).
        self._settings_origin = origin
        self.state = AppScreen.SETTINGS

    def _handle_settings(self, event: object) -> None:
        position = _mouse_up_position(event)
        if position is None:
            return
        layout = settings_menu_layout(screen_width, screen_height)
        if _clicked(layout, "back", position):
            self.state = self._settings_origin
            return
        updated = self._edited_settings(layout, position)
        if updated is None:
            return
        # Update in memory so the live consumers work even seam-less; persist
        # once through the seam when one is present (D-029).
        self.current_settings = updated
        if self._settings is not None:
            self._settings.save(updated)

    def _edited_settings(self, layout: dict[str, pygame.Rect], position: Point):
        current = self.current_settings
        if _clicked(layout, "fullscreen", position):
            return replace(current, fullscreen=not current.fullscreen)
        if _clicked(layout, "reduced_motion", position):
            return replace(current, reduced_motion=not current.reduced_motion)
        if _clicked(layout, "master_volume", position):
            return replace(current, master_volume=_cycle_volume(current.master_volume))
        if _clicked(layout, "music_volume", position):
            return replace(current, music_volume=_cycle_volume(current.music_volume))
        if _clicked(layout, "sfx_volume", position):
            return replace(current, sfx_volume=_cycle_volume(current.sfx_volume))
        return None
