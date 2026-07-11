from __future__ import annotations

from typing import Protocol

from event.event import Event
from game_clock import ClockAdvance, FixedStepClock


class LayoutSurface(Protocol):
    def get_size(self) -> tuple[int, int]: ...


class SessionMediator(Protocol):
    is_paused: bool
    is_game_over: bool

    def prepare_layout(self, width: int, height: int) -> None: ...

    def react(self, event: Event | None) -> None: ...

    def increment_time(self, dt_ms: int) -> None: ...


class StepObserver(Protocol):
    def before_step(self, mediator: SessionMediator) -> None: ...

    def after_step(self, mediator: SessionMediator) -> None: ...

    def clear_interpolation(self) -> None: ...


class GameSession:
    """Shared input and fixed-update driver for a player-facing game session."""

    def __init__(
        self,
        mediator: SessionMediator,
        clock: FixedStepClock | None = None,
        step_observer: StepObserver | None = None,
    ) -> None:
        self.mediator = mediator
        self.clock = clock if clock is not None else FixedStepClock()
        self.step_observer = step_observer

    def prepare_layout(self, surface: LayoutSurface) -> None:
        width, height = surface.get_size()
        self.mediator.prepare_layout(int(width), int(height))

    def dispatch(self, event: Event | None) -> None:
        self.mediator.react(event)

    def advance(self, elapsed_ms: int) -> ClockAdvance:
        advance = self.clock.advance(elapsed_ms)
        if self.mediator.is_paused or self.mediator.is_game_over:
            self.clock.reset()
            if self.step_observer is not None:
                self.step_observer.clear_interpolation()
            return advance
        self._apply_steps(advance.dts)
        return advance

    def advance_exact(self, step_count: int) -> tuple[int, ...]:
        """Apply exact fixed ticks for deterministic non-wall-clock sessions."""

        dts = self.clock.take_exact_steps(step_count)
        if self.mediator.is_paused or self.mediator.is_game_over:
            self.clock.reset()
            if self.step_observer is not None:
                self.step_observer.clear_interpolation()
            return ()
        return self._apply_steps(dts)

    def _apply_steps(self, dts: tuple[int, ...]) -> tuple[int, ...]:
        applied: list[int] = []
        for dt_ms in dts:
            if self.mediator.is_paused or self.mediator.is_game_over:
                self.clock.reset()
                if self.step_observer is not None:
                    self.step_observer.clear_interpolation()
                break
            if self.step_observer is not None:
                self.step_observer.before_step(self.mediator)
            self.mediator.increment_time(dt_ms)
            applied.append(dt_ms)
            if self.step_observer is not None:
                self.step_observer.after_step(self.mediator)
            if self.mediator.is_paused or self.mediator.is_game_over:
                self.clock.reset()
                if self.step_observer is not None:
                    self.step_observer.clear_interpolation()
                break
        return tuple(applied)

    def reset_clock(self) -> None:
        self.clock.reset()
