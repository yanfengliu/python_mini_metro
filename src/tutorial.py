"""GM-08c coached-tutorial step machine (D-031).

A pure, duck-typed state machine that turns a real seeded game into a guided
first experience: it observes the live mediator each frame (the GM-08b snapshot
pattern) and advances seven lessons as the player performs each real action. It
imports no gameplay/rendering/save module - it reads mediator attributes only —
so only ``app_controller``/``main`` import it and no headless/RL path constructs
it.

Two step kinds:

* ``state`` - advances when the step's predicate over the live snapshot is
  satisfied (draw a line, add a train, deliver, reroute, pause, speed).
* ``dwell`` - advances after a few seconds of UNPAUSED play (overload pressure
  is a consequence to observe, not an action; a good player never overloads, so
  a pure crowd/wait gate would soft-lock), or sooner if a passenger actually
  enters the warning window.

The tutorial's seeded mediator has its game-over suppressed by the caller, so the
sim never freezes and no step can soft-lock.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

OVERLOAD_DWELL_MS = 4500  # unpaused play before the overload lesson auto-advances
WARNING_START_MS = 30000  # a passenger this deep into its wait is in the warning ring


@dataclass(frozen=True)
class Step:
    key: str
    prompt: str
    kind: str  # "state" or "dwell"
    predicate: Callable[[dict, dict], bool] = field(compare=False)


def _committed_paths(cur: dict, base: dict) -> bool:
    return cur["committed_paths"] > base["committed_paths"]


def _has_a_train(cur: dict, base: dict) -> bool:
    # Current state, not an edge (review MAJOR-2): the metro inventory is capped
    # (num_metros), so if the player assigned trains during an earlier lesson an
    # edge `current > baseline` could baseline at the cap and never fire again.
    # "Has at least one train" is always reachable and never soft-locks.
    return cur["metros"] >= 1


def _more_deliveries(cur: dict, base: dict) -> bool:
    return cur["deliveries"] > base["deliveries"]


def _route_changed(cur: dict, base: dict) -> bool:
    # Any change to the route topology since the lesson began -- an existing
    # line's stations changed, or a line added/removed. Loosened from "an existing
    # id changed" (review MAJOR-1): a first-timer who deletes-and-redraws a line
    # gets a FRESH path id, which a strict same-id check would never match ->
    # soft-lock. Route signatures change only through player action (no
    # engine-driven path mutation exists), so a plain inequality never false-fires.
    return cur["route_signatures"] != base["route_signatures"]


def _passenger_in_warning(cur: dict, base: dict) -> bool:
    return cur["max_wait_ms"] >= WARNING_START_MS


def _is_paused(cur: dict, base: dict) -> bool:
    # Current state, not an edge: if the player already paused during a wait the
    # lesson is satisfied rather than soft-locked.
    return bool(cur["paused"])


def _sped_up(cur: dict, base: dict) -> bool:
    return cur["speed"] != 1


# Reroute precedes the train: path-lifecycle keeps the strict GM-07b default, so
# a metro mid-service persistently blocks replace_path (empirically confirmed) —
# a train-less line reroutes reliably. So: draw, reroute, then add a train and
# watch it deliver.
TUTORIAL_STEPS: tuple[Step, ...] = (
    Step(
        "draw",
        "Drag between two stations to draw your first line.",
        "state",
        _committed_paths,
    ),
    Step(
        "reroute",
        "Drag your line's round endpoint to a station to extend or reroute it.",
        "state",
        _route_changed,
    ),
    Step(
        "train",
        "Click a line's train slot to add a train - trains carry more passengers.",
        "state",
        _has_a_train,
    ),
    Step(
        "deliver",
        "Watch your train deliver a passenger to its matching shape to earn credits.",
        "state",
        _more_deliveries,
    ),
    Step(
        "overload",
        "Passengers waiting too long overload a station - watch the warning rings and keep lines flowing.",
        "dwell",
        _passenger_in_warning,
    ),
    Step("pause", "Press Space to pause and plan your network.", "state", _is_paused),
    Step("speed", "Press 2 or 3 to speed up time.", "state", _sped_up),
)

STEP_TOTAL = len(TUTORIAL_STEPS)
_COMPLETE_PROMPT = "Tutorial complete - press Esc to return to the menu."


def tutorial_snapshot(mediator) -> dict:
    """Capture the tutorial-relevant signals off a duck-typed mediator.

    Tolerant (every field via ``getattr``, absent → inert) so a partial or mocked
    host never crashes the loop. Route tuples are copied out of the live lists
    because a reroute mutates ``path.stations[:]`` in place.
    """
    paths = getattr(mediator, "paths", ()) or ()
    routes: dict = {}
    for index, path in enumerate(paths):
        key = getattr(path, "id", None)
        if key is None:
            key = index
        stations = tuple(
            getattr(s, "id", None) for s in getattr(path, "stations", ()) or ()
        )
        routes[key] = (stations, bool(getattr(path, "is_looped", False)))
    committed = sum(
        1 for path in paths if not bool(getattr(path, "is_being_created", False))
    )
    stations = getattr(mediator, "stations", ()) or ()
    max_wait = max(
        (
            int(getattr(pax, "wait_ms", 0))
            for st in stations
            for pax in (getattr(st, "passengers", ()) or ())
        ),
        default=0,
    )
    return {
        "committed_paths": committed,
        "route_signatures": routes,
        "metros": len(getattr(mediator, "metros", ()) or ()),
        "deliveries": int(getattr(mediator, "deliveries", 0)),
        "paused": bool(getattr(mediator, "is_paused", False)),
        "speed": int(getattr(mediator, "game_speed_multiplier", 1)),
        "max_wait_ms": max_wait,
    }


@dataclass(frozen=True)
class TutorialProgress:
    index: int
    baseline: dict
    dwell_ms: int = 0
    done: bool = False


def start_progress(mediator) -> TutorialProgress:
    """Begin at the first lesson, baselined to the current mediator state."""
    return TutorialProgress(index=0, baseline=tutorial_snapshot(mediator))


def advance(
    progress: TutorialProgress, mediator, elapsed_ms: int, paused: bool
) -> TutorialProgress:
    """Advance the current lesson if satisfied; return the (re-baselined) progress.

    Pure and idempotent: a completed tutorial returns unchanged. A ``state`` step
    completes on its predicate; a ``dwell`` step accumulates unpaused ``elapsed_ms``
    and completes at ``OVERLOAD_DWELL_MS`` (or its predicate). On completion the
    index advances, the baseline resets to the moment the next lesson activated,
    and the dwell timer clears.
    """
    if progress.done:
        return progress
    step = TUTORIAL_STEPS[progress.index]
    current = tutorial_snapshot(mediator)
    completed = step.predicate(current, progress.baseline)
    dwell_ms = progress.dwell_ms
    if step.kind == "dwell":
        if not paused:
            dwell_ms += int(elapsed_ms)
        if dwell_ms >= OVERLOAD_DWELL_MS:
            completed = True
    if not completed:
        if dwell_ms != progress.dwell_ms:
            return replace(progress, dwell_ms=dwell_ms)
        return progress
    next_index = progress.index + 1
    if next_index >= STEP_TOTAL:
        return replace(progress, done=True, dwell_ms=0)
    return TutorialProgress(index=next_index, baseline=current, dwell_ms=0)


def is_complete(progress: TutorialProgress) -> bool:
    return progress.done


def current_prompt(progress: TutorialProgress) -> str:
    if progress.done:
        return _COMPLETE_PROMPT
    return TUTORIAL_STEPS[progress.index].prompt


def step_ordinal(progress: TutorialProgress) -> int:
    """1-based lesson number, capped at ``STEP_TOTAL`` on completion."""
    if progress.done:
        return STEP_TOTAL
    return progress.index + 1
