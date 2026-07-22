# GM-06d red evidence — occupied return and cancellation lane

Command: `python -m unittest test.test_gm06d_occupied_return -v` and `python -m unittest test.test_gm06d_cancel_unassignment -v` in `py313` at the GM-06c-finalized baseline (`a21a3c0`), before any production change.

- `test_gm06d_occupied_return.py` (377 physical lines): 9 tests — 6 FAIL / 0 ERROR / 3 ok. All six reds are `AssertionError` for the intended reasons: occupied-only paths reject queueing today (widened fewest-passenger/latest-order selection missing, four tests) and riders remain aboard a queued metro after the tick (one-batch drain seam missing, two tests). The three greens are explicitly marked `# regression guard: green at baseline`: empty-preference selection, empty fast-path clear+detach, and timed non-instant destination unload on a queued occupied metro.
- `test_gm06d_cancel_unassignment.py` (433 physical lines): 12 tests — 11 red / 1 guard green (unittest tally with subTests: failures=14, errors=6). Six `AttributeError` reds: `Mediator.can_cancel_unassignment`/`cancel_unassignment` do not exist (facades plus four zero-effect rejection tests). Five `AssertionError` reds: crafted recursive v1-v4 documents and v5 selector variants validate today (unknown-type fall-through, "ValueError not raised"), crafted agent v1-v5 records replay past reset, and live structured `cancel_unassignment` returns `action_ok=False`. The single green is the vacuously-green malformed-selector guard, commented as such.
- Combined: 21 tests, 17 genuinely red, 4 guard greens. Ruff check and format pass both files; both under the 500-line ceiling.

Baseline discoveries recorded into the plan:

- Third contract flip: `test_rider_injected_after_queue_blocks_destructive_settlement` (`test/test_gm06b_fleet_queue.py:432`) asserts a planless rider aboard a queued metro stays aboard at a real-station tick; the Case 1 drain rule consciously inverts that scenario. Added to the plan's contract-flip list.
- At baseline, `queue()`'s real-station service-state clear is only reachable through empty candidates, so the occupied-preservation red comes from the selection gate rather than observed clearing — consistent with the plan.
- "Travel plans cleared" is encoded as stale-plan-identity-gone rather than strict mapping absence, because the ordinary re-plan sweep may legitimately install a fresh plan within the same `increment_time`.
- Supporting baselines confirmed: destination unloads on queued metros are un-gated and timed at the 500 ms interval; `Mediator.increment_time(0)` runs the full flow including settle for deterministic same-tick assertions; the baseline queue selects the later of two fresh metros first, making cancel-earliest ordering observable.
