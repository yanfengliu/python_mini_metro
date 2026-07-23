"""GM-08c red contract: the pure ``tutorial`` step machine (D-031).

The coached-tutorial state machine observes the live mediator each frame (the
GM-08b snapshot-differ pattern) and advances seven lessons as the player performs
each real action. Every product surface is probed through ``require`` guards so a
missing symbol is a clean FAILURE, never an import/collection ERROR.
"""

from __future__ import annotations

import importlib
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

MODULE = "tutorial"


def _module(tc):
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        tc.fail(f"GM-08c product module missing: {MODULE} ({error})")


def _sym(tc, name):
    value = getattr(_module(tc), name, None)
    tc.assertIsNotNone(value, f"GM-08c product symbol missing: {MODULE}.{name}")
    return value


def _pax(wait_ms=0):
    return SimpleNamespace(wait_ms=wait_ms)


def _station(passengers=()):
    return SimpleNamespace(passengers=list(passengers))


def _path(pid, station_ids=(), looped=False, being_created=False):
    return SimpleNamespace(
        id=pid,
        stations=[SimpleNamespace(id=s) for s in station_ids],
        is_looped=looped,
        is_being_created=being_created,
    )


def _host(
    paths=(),
    metros=0,
    deliveries=0,
    paused=False,
    speed=1,
    stations=(),
):
    return SimpleNamespace(
        paths=list(paths),
        metros=[object() for _ in range(metros)],
        deliveries=deliveries,
        is_paused=paused,
        game_speed_multiplier=speed,
        stations=list(stations),
    )


class TestGM08cSnapshot(unittest.TestCase):
    def test_snapshot_captures_the_signals_tolerantly(self):
        snap = _sym(self, "tutorial_snapshot")
        host = _host(
            paths=[_path("A", ("s1", "s2"))],
            metros=1,
            deliveries=3,
            paused=True,
            speed=2,
            stations=[_station([_pax(1000), _pax(35000)]), _station()],
        )
        s = snap(host)
        self.assertEqual(s["committed_paths"], 1)
        self.assertEqual(s["metros"], 1)
        self.assertEqual(s["deliveries"], 3)
        self.assertIs(s["paused"], True)
        self.assertEqual(s["speed"], 2)
        self.assertEqual(s["max_wait_ms"], 35000)
        self.assertEqual(s["route_signatures"], {"A": (("s1", "s2"), False)})

    def test_snapshot_excludes_being_created_paths(self):
        snap = _sym(self, "tutorial_snapshot")
        host = _host(paths=[_path("A", ("s1", "s2"), being_created=True)])
        self.assertEqual(
            snap(host)["committed_paths"], 0, "a dragging line is not committed"
        )

    def test_snapshot_tolerates_a_bare_host(self):
        # A cosmetic overlay must never crash the loop on a partial host.
        snap = _sym(self, "tutorial_snapshot")
        s = snap(SimpleNamespace())
        self.assertEqual(s["committed_paths"], 0)
        self.assertEqual(s["max_wait_ms"], 0)
        self.assertEqual(s["route_signatures"], {})


class TestGM08cStepAdvance(unittest.TestCase):
    def _start(self, host):
        return _sym(self, "start_progress")(host)

    def _advance(self, progress, host, elapsed_ms=16, paused=False):
        return _sym(self, "advance")(progress, host, elapsed_ms, paused)

    def _drive_to_step(self, key):
        """Advance a fresh progress until the current step has the given key."""
        steps = _sym(self, "TUTORIAL_STEPS")
        keys = [s.key for s in steps]
        target = keys.index(key)
        # A cumulative host satisfying each step in TUTORIAL_STEPS order:
        # draw -> reroute -> train -> deliver -> overload -> pause -> speed.
        r3 = dict(paths=[_path("A", ("s1", "s2", "s3"))])  # A's route changed from draw
        hosts = {
            "draw": _host(paths=[_path("A", ("s1", "s2"))]),
            "reroute": _host(**r3),
            "train": _host(**r3, metros=1),
            "deliver": _host(**r3, metros=1, deliveries=1),
            "overload": _host(**r3, metros=1, deliveries=1),  # dwell, driven by elapsed
            "pause": _host(**r3, metros=1, deliveries=1, paused=True),
            "speed": _host(**r3, metros=1, deliveries=1, speed=2),
        }
        progress = self._start(_host())
        for k in keys[:target]:
            host = hosts[k]
            progress = self._advance(
                progress, host, elapsed_ms=99999, paused=bool(host.is_paused)
            )
        self.assertEqual(steps[progress.index].key, key, f"reached {key}")
        return progress

    def test_first_step_is_draw_and_prompts(self):
        steps = _sym(self, "TUTORIAL_STEPS")
        self.assertEqual(steps[0].key, "draw")
        progress = self._start(_host())
        prompt = _sym(self, "current_prompt")(progress)
        self.assertIn("line", prompt.lower())
        self.assertEqual(_sym(self, "step_ordinal")(progress), 1)

    def test_draw_advances_only_on_a_committed_path(self):
        progress = self._start(_host())
        # A being-created path does not advance.
        p2 = self._advance(
            progress, _host(paths=[_path("A", ("s1",), being_created=True)])
        )
        self.assertEqual(p2.index, 0, "a dragging line does not complete draw")
        p3 = self._advance(progress, _host(paths=[_path("A", ("s1", "s2"))]))
        self.assertEqual(p3.index, 1, "a committed line advances to the train step")

    def test_reroute_advances_on_any_route_change(self):
        progress = self._drive_to_step("reroute")
        # The reroute baseline is line A = (s1, s2). An unchanged frame does NOT
        # advance (only player action changes routes).
        same = _host(paths=[_path("A", ("s1", "s2"))])
        self.assertEqual(self._advance(progress, same).index, progress.index)
        # Changing line A's own stations advances (the in-place reroute).
        rerouted = _host(paths=[_path("A", ("s1", "s2", "s3"))])
        self.assertEqual(self._advance(progress, rerouted).index, progress.index + 1)

    def test_reroute_advances_on_a_delete_and_redraw_with_a_fresh_id(self):
        # Review MAJOR-1 regression: deleting the line and drawing a new one mints
        # a FRESH path id; a strict same-id check would soft-lock. A topology
        # change (old id gone, new id present) must advance.
        progress = self._drive_to_step("reroute")
        redrawn = _host(paths=[_path("B", ("s1", "s2"))])  # new id, old A deleted
        self.assertEqual(self._advance(progress, redrawn).index, progress.index + 1)

    def test_train_step_is_satisfied_at_the_locomotive_cap(self):
        # Review MAJOR-2 regression: if trains were assigned during an earlier
        # lesson, the train baseline can sit at the metro cap, where an edge
        # `current > baseline` could never fire. A current-state "has a train"
        # check advances regardless of the baseline.
        steps = _sym(self, "TUTORIAL_STEPS")
        train_index = [s.key for s in steps].index("train")
        progress_cls = _sym(self, "TutorialProgress")
        snapshot = _sym(self, "tutorial_snapshot")
        capped = _host(paths=[_path("A", ("s1", "s2"))], metros=4)  # 4 == the cap
        progress = progress_cls(index=train_index, baseline=snapshot(capped))
        self.assertEqual(
            self._advance(progress, capped).index,
            train_index + 1,
            "has-a-train is satisfied at the cap; an edge check would soft-lock",
        )

    def test_overload_is_a_dwell_step_gated_on_unpaused_time(self):
        progress = self._drive_to_step("overload")
        steps = _sym(self, "TUTORIAL_STEPS")
        self.assertEqual(steps[progress.index].kind, "dwell")
        dwell_total = _sym(self, "OVERLOAD_DWELL_MS")
        host = _host(paths=[_path("A", ("s1", "s2"))], metros=1, deliveries=1)
        # Paused time does not accumulate.
        paused = self._advance(progress, host, elapsed_ms=dwell_total * 2, paused=True)
        self.assertEqual(
            paused.index, progress.index, "paused dwell does not advance overload"
        )
        # Unpaused time past the threshold advances.
        run = self._advance(progress, host, elapsed_ms=dwell_total + 1, paused=False)
        self.assertEqual(
            run.index, progress.index + 1, "unpaused dwell completes overload"
        )

    def test_overload_also_completes_on_the_warning_window(self):
        progress = self._drive_to_step("overload")
        warn = _sym(self, "WARNING_START_MS")
        crowded = _host(
            paths=[_path("A", ("s1", "s2"))],
            metros=1,
            deliveries=1,
            stations=[_station([_pax(warn + 1)])],
        )
        # A single short frame, but a passenger is in the warning window.
        self.assertEqual(
            self._advance(progress, crowded, elapsed_ms=16).index, progress.index + 1
        )

    def test_pause_completes_on_current_state_even_if_already_paused(self):
        progress = self._drive_to_step("pause")
        host = _host(
            paths=[_path("A", ("s1", "s2"))], metros=1, deliveries=1, paused=True
        )
        self.assertEqual(
            self._advance(progress, host).index,
            progress.index + 1,
            "already-paused satisfies pause",
        )

    def test_speed_completes_when_multiplier_leaves_one(self):
        progress = self._drive_to_step("speed")
        host = _host(paths=[_path("A", ("s1", "s2"))], metros=1, deliveries=1, speed=2)
        nxt = self._advance(progress, host)
        self.assertTrue(
            _sym(self, "is_complete")(nxt),
            "speed is the last lesson; leaving 1x completes the tutorial",
        )

    def test_completion_prompt_and_idempotence(self):
        progress = self._drive_to_step("speed")
        host = _host(paths=[_path("A", ("s1", "s2"))], metros=1, deliveries=1, speed=4)
        done = self._advance(progress, host)
        self.assertTrue(_sym(self, "is_complete")(done))
        prompt = _sym(self, "current_prompt")(done)
        self.assertIn("complete", prompt.lower())
        # Advancing a completed tutorial is a no-op.
        self.assertTrue(_sym(self, "is_complete")(self._advance(done, host)))

    def test_a_later_signal_does_not_retro_complete_an_earlier_step(self):
        # On the draw step, having deliveries/metros already high must not skip ahead.
        progress = self._start(_host())
        loaded = _host(paths=[], metros=3, deliveries=9, speed=4, paused=True)
        self.assertEqual(
            self._advance(progress, loaded).index,
            0,
            "draw still requires a committed line",
        )


if __name__ == "__main__":
    unittest.main()
