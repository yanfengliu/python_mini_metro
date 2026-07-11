import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from event.keyboard import KeyboardEvent
from event.type import KeyboardEventType
from game_clock import FixedStepClock
from game_session import GameSession


class RecordingMediator:
    def __init__(self) -> None:
        self.is_paused = False
        self.is_game_over = False
        self.calls: list[tuple[object, ...]] = []

    def prepare_layout(self, width: int, height: int) -> None:
        self.calls.append(("layout", width, height))

    def react(self, event) -> None:
        self.calls.append(("event", event))

    def increment_time(self, dt_ms: int) -> None:
        self.calls.append(("time", dt_ms))


class StubSurface:
    def __init__(self, size: tuple[int, int]) -> None:
        self._size = size

    def get_size(self) -> tuple[int, int]:
        return self._size


class RecordingObserver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def before_step(self, mediator: object) -> None:
        self.calls.append(("before", mediator))

    def after_step(self, mediator: object) -> None:
        self.calls.append(("after", mediator))

    def clear_interpolation(self) -> None:
        self.calls.append(("clear", self))


class TestFixedStepClock(unittest.TestCase):
    def test_sixty_updates_cover_exactly_one_second(self):
        clock = FixedStepClock()
        dts: list[int] = []

        for elapsed_ms in (17, 17, 16) * 20:
            dts.extend(clock.advance(elapsed_ms).dts)

        self.assertEqual(len(dts), 60)
        self.assertEqual(sum(dts), 1000)
        self.assertEqual(tuple(dts[:6]), (17, 17, 16, 17, 17, 16))

    def test_irregular_wall_time_partitions_preserve_global_cadence(self):
        single = FixedStepClock().advance(109)
        partitioned_clock = FixedStepClock()
        partitioned_dts: list[int] = []
        for elapsed_ms in (7, 22, 3, 41, 36):
            partitioned_dts.extend(partitioned_clock.advance(elapsed_ms).dts)
        partitioned = partitioned_clock.advance(0)

        self.assertEqual(tuple(partitioned_dts), single.dts)
        self.assertEqual(partitioned.alpha, single.alpha)
        self.assertEqual(partitioned.dropped_ms, single.dropped_ms)

    def test_catchup_cap_drops_complete_steps_and_keeps_substep_remainder(self):
        clock = FixedStepClock(max_elapsed_ms=1000, max_catchup_updates=2)

        result = clock.advance(109)

        self.assertEqual(result.dts, (17, 17))
        self.assertEqual(result.dropped_ms, 66)
        self.assertAlmostEqual(result.alpha, 9 / 17)
        self.assertEqual(clock.advance(8).dts, (17,))

    def test_negative_elapsed_is_zero_and_huge_elapsed_is_clamped(self):
        clock = FixedStepClock(max_elapsed_ms=100, max_catchup_updates=10)

        negative = clock.advance(-50)
        huge = clock.advance(1000)

        self.assertEqual(negative.dts, ())
        self.assertEqual(negative.dropped_ms, 0)
        self.assertEqual(negative.alpha, 0.0)
        self.assertEqual(huge.dts, (17, 17, 16, 17, 17, 16))
        self.assertEqual(huge.dropped_ms, 900)
        self.assertEqual(huge.alpha, 0.0)

    def test_reset_clears_remainder_and_restarts_pattern(self):
        clock = FixedStepClock()
        self.assertEqual(clock.advance(34).dts, (17, 17))

        clock.reset()

        reset_result = clock.advance(16)
        self.assertEqual(reset_result.dts, ())
        self.assertAlmostEqual(reset_result.alpha, 16 / 17)

    def test_exact_steps_share_cadence_without_catchup_limits(self):
        clock = FixedStepClock(max_catchup_updates=2)

        first = clock.take_exact_steps(6)
        second = clock.take_exact_steps(6)

        self.assertEqual(first, (17, 17, 16, 17, 17, 16))
        self.assertEqual(second, first)
        self.assertEqual(sum(first + second), 200)

    def test_exact_steps_reject_mixing_with_wall_time_remainder(self):
        clock = FixedStepClock()
        clock.advance(5)

        with self.assertRaisesRegex(RuntimeError, "wall-time remainder"):
            clock.take_exact_steps(1)


class TestGameSession(unittest.TestCase):
    def test_paused_and_game_over_time_is_consumed_without_update_calls(self):
        mediator = RecordingMediator()
        session = GameSession(mediator)
        mediator.is_paused = True

        paused_result = session.advance(100)
        mediator.is_paused = False
        resumed_result = session.advance(17)
        mediator.is_game_over = True
        game_over_result = session.advance(50)

        self.assertEqual(sum(paused_result.dts), 100)
        self.assertEqual(resumed_result.dts, (17,))
        self.assertEqual(sum(game_over_result.dts), 50)
        self.assertEqual(mediator.calls, [("time", 17)])

    def test_layout_events_and_updates_are_forwarded_in_call_order(self):
        mediator = RecordingMediator()
        session = GameSession(mediator)
        surface = StubSurface((800, 600))
        first = KeyboardEvent(KeyboardEventType.KEY_UP, "first")
        second = KeyboardEvent(KeyboardEventType.KEY_UP, "second")

        session.prepare_layout(surface)
        session.dispatch(first)
        session.dispatch(second)
        result = session.advance(34)

        self.assertEqual(result.dts, (17, 17))
        self.assertEqual(
            mediator.calls,
            [
                ("layout", 800, 600),
                ("event", first),
                ("event", second),
                ("time", 17),
                ("time", 17),
            ],
        )

    def test_step_observer_brackets_each_simulation_update(self):
        mediator = RecordingMediator()
        observer = RecordingObserver()
        session = GameSession(mediator, step_observer=observer)

        advance = session.advance(34)

        self.assertEqual(advance.dts, (17, 17))
        self.assertEqual(
            observer.calls,
            [
                ("before", mediator),
                ("after", mediator),
                ("before", mediator),
                ("after", mediator),
            ],
        )

    def test_paused_session_consumes_time_and_clears_interpolation(self):
        mediator = RecordingMediator()
        mediator.is_paused = True
        observer = RecordingObserver()
        session = GameSession(mediator, step_observer=observer)

        advance = session.advance(50)

        self.assertEqual(sum(advance.dts), 50)
        self.assertEqual(mediator.calls, [])
        self.assertEqual(observer.calls, [("clear", observer)])

    def test_paused_substep_remainder_is_discarded_before_resume(self):
        mediator = RecordingMediator()
        session = GameSession(mediator)
        mediator.is_paused = True

        self.assertEqual(session.advance(16).dts, ())
        mediator.is_paused = False

        self.assertEqual(session.advance(1).dts, ())
        self.assertEqual(session.advance(16).dts, (17,))
        self.assertEqual(mediator.calls, [("time", 17)])

    def test_exact_advance_applies_requested_fixed_ticks(self):
        mediator = RecordingMediator()
        observer = RecordingObserver()
        session = GameSession(mediator, step_observer=observer)

        applied = session.advance_exact(6)

        self.assertEqual(applied, (17, 17, 16, 17, 17, 16))
        self.assertEqual(
            mediator.calls,
            [("time", dt_ms) for dt_ms in applied],
        )
        self.assertEqual(len(observer.calls), 12)

    def test_exact_advance_paused_applies_no_ticks_or_backlog(self):
        mediator = RecordingMediator()
        mediator.is_paused = True
        session = GameSession(mediator)

        self.assertEqual(session.advance_exact(6), ())
        mediator.is_paused = False
        self.assertEqual(session.advance_exact(1), (17,))


if __name__ == "__main__":
    unittest.main()
