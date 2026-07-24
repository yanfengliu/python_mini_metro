# GM-09c PLAN — external Codex ultra lane (findings captured from run summary)

NOTE ON CAPTURE: Codex completed the review (traced the live route/creation flows + independent adversarial checks) but its `-o` file write failed (empty file) — the second consecutive flaky Codex output this session (GM-09b impl hung; this `-o` empty). The detailed file:line evidence was lost with the `-o` write; the substantive findings below are captured verbatim from Codex's delivered run summary. Flagged per the standing rule; the harness lane's independent full trace (`raw/plan-harness.md`) covers the same surface with file:line evidence.

## Codex verdict: NOT CLEAN

"The core 'derived counter needs no replacement/removal snapshot field' claim is SOUND for completed routes, but the plan is not clean:
1. drafts are counted as live,
2. two-station loops are double-charged,
3. rejected structured creation leaks snap-blip state,
4. and the observation addition breaks checkpoint v4 immediately."

## Dispositions (folded into Plan v2)
- (1) DRAFTS COUNTED AS LIVE — matches harness M2. `consumed_tunnels` sums over `self.paths`, which includes an `is_being_created` draft (`path_lifecycle.py:287`). Fold: EXCLUDE `is_being_created` paths from `consumed_tunnels`; the finish gate adds the finishing path's own crossings.
- (2) TWO-STATION LOOPS DOUBLE-CHARGED (new) — a 2-station looped path has segments A→B AND the loop-closure B→A, which RETRACE the same physical line, so a single river crossing is counted twice. Fold: only add the loop-closure segment when `len(stations) >= 3` (a 2-station loop's closure is a retrace); test a 2-station cross-river loop counts 1.
- (3) REJECTED STRUCTURED CREATION LEAKS SNAP-BLIP STATE (new) — rejecting an over-budget creation must FULLY abort (the clean `abort_path_creation` discarding the draft) and must not leave snap-blip visual state that a later `canonical_checkpoint` would reject. Fold: route the creation-gate rejection through the clean abort; test `canonical_checkpoint` is valid after a rejected creation.
- (4) OBSERVATION BREAKS CHECKPOINT v4 — matches harness MAJOR. Fold: emit the tunnels triplet as a SIBLING `structured["tunnels"]` block, NOT inside the `fleet` dict (the checkpoint's fixed whitelist ignores unknown top-level keys), so `canonical_checkpoint` for CLASSIC and every checkpoint test stays valid.
