from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClockAdvance:
    """One immutable conversion from wall time to simulation updates."""

    dts: tuple[int, ...]
    alpha: float
    dropped_ms: int


class FixedStepClock:
    """Convert integer wall milliseconds to a deterministic 60 Hz cadence."""

    STEP_PATTERN_MS = (17, 17, 16)
    DEFAULT_MAX_ELAPSED_MS = 250
    DEFAULT_MAX_CATCHUP_UPDATES = 8

    def __init__(
        self,
        *,
        max_elapsed_ms: int = DEFAULT_MAX_ELAPSED_MS,
        max_catchup_updates: int = DEFAULT_MAX_CATCHUP_UPDATES,
    ) -> None:
        if isinstance(max_elapsed_ms, bool) or not isinstance(max_elapsed_ms, int):
            raise TypeError("max_elapsed_ms must be an integer")
        if max_elapsed_ms <= 0:
            raise ValueError("max_elapsed_ms must be positive")
        if isinstance(max_catchup_updates, bool) or not isinstance(
            max_catchup_updates, int
        ):
            raise TypeError("max_catchup_updates must be an integer")
        if max_catchup_updates <= 0:
            raise ValueError("max_catchup_updates must be positive")

        self.max_elapsed_ms = max_elapsed_ms
        self.max_catchup_updates = max_catchup_updates
        self.reset()

    def reset(self) -> None:
        """Clear accumulated wall time and restart the global cadence."""

        self._accumulator_ms = 0
        self._pattern_index = 0

    def advance(self, elapsed_ms: int) -> ClockAdvance:
        """Consume wall time and return bounded simulation updates.

        Negative elapsed time is treated as zero. Time beyond ``max_elapsed_ms``
        and complete updates beyond the catch-up cap are reported as dropped.
        The cadence phase still advances across dropped updates, while a final
        sub-step remainder is retained for the next call.
        """

        if isinstance(elapsed_ms, bool) or not isinstance(elapsed_ms, int):
            raise TypeError("elapsed_ms must be an integer")

        non_negative_elapsed_ms = max(0, elapsed_ms)
        accepted_elapsed_ms = min(non_negative_elapsed_ms, self.max_elapsed_ms)
        dropped_ms = non_negative_elapsed_ms - accepted_elapsed_ms
        self._accumulator_ms += accepted_elapsed_ms

        dts: list[int] = []
        while (
            len(dts) < self.max_catchup_updates
            and self._accumulator_ms >= self._next_dt_ms
        ):
            dt_ms = self._consume_next_step()
            dts.append(dt_ms)

        while self._accumulator_ms >= self._next_dt_ms:
            dropped_ms += self._consume_next_step()

        alpha = self._accumulator_ms / self._next_dt_ms
        return ClockAdvance(tuple(dts), alpha, dropped_ms)

    def take_exact_steps(self, count: int) -> tuple[int, ...]:
        """Advance the shared cadence by an exact number of simulation ticks."""

        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("count must be an integer")
        if count < 0:
            raise ValueError("count cannot be negative")
        if self._accumulator_ms:
            raise RuntimeError("cannot take exact steps with a wall-time remainder")
        return tuple(self._take_next_step() for _ in range(count))

    @property
    def _next_dt_ms(self) -> int:
        return self.STEP_PATTERN_MS[self._pattern_index]

    def _consume_next_step(self) -> int:
        dt_ms = self._take_next_step()
        self._accumulator_ms -= dt_ms
        return dt_ms

    def _take_next_step(self) -> int:
        dt_ms = self._next_dt_ms
        self._pattern_index = (self._pattern_index + 1) % len(self.STEP_PATTERN_MS)
        return dt_ms
