# Full-Codebase Review: Iteration 2

## Reviewer Coverage

- Claude Opus was attempted again and was still quota-limited; `raw/opus.md` preserves the CLI response.
- Three independent Codex fallback reviewers completed. Raw outputs are in `raw/codex-1.md`, `raw/codex-2.md`, and `raw/codex-3.md`.
- The reviewed diff is in `diff.md`.

## Findings

### Medium: rejected actions still advanced simulation time

- Reported by: Codex 1.
- Evidence: `MiniMetroEnv.step()` advanced `dt_ms` after `action_ok=False`, so malformed actions could still mutate time, spawning, train motion, waits, or game-over state.
- Disposition: accepted and fixed. `step()` now advances time only when the action is accepted; `None` and explicit `noop` remain accepted.

### Medium: malformed action schemas still reported success

- Reported by: Codex 1, Codex 2, Codex 3.
- Evidence: missing or `None` action types were treated as noop; non-bool `loop` values were coerced with `bool(...)`; boolean station/path indices passed `isinstance(..., int)`.
- Disposition: accepted and fixed. `Mediator.apply_action()` now requires a string action type, explicit `noop`, real bool `loop` values, and exact `int` indices.

### Medium: programmatic loop creation dropped the final requested station

- Reported by: Codex 3.
- Evidence: looped `create_path` with `[0, 1, 2]` added only station `1` before closing to station `0`.
- Disposition: accepted and fixed. Programmatic loop creation now adds every requested station after the first, then closes to the first station. Repeated-first inputs still avoid adding the first station twice.

### Medium: removed-line invalidation stranded onboard transfer passengers

- Reported by: Codex 3.
- Evidence: `remove_path()` deleted any plan whose node path referenced the removed line, including passengers already riding a surviving metro whose next transfer station was still reachable on their current line.
- Disposition: accepted and fixed. Removed-line invalidation preserves onboard plans unless their immediate `next_path` is the removed path, allowing them to transfer at the next station and then recompute against the new network.

### Low: `pygame.draw` mock leaked from mediator tests

- Reported by: Codex 3.
- Evidence: `test/test_mediator.py` assigned `pygame.draw = MagicMock()` globally without restoring it.
- Disposition: accepted and fixed. `test/test_mediator.py` and the similar `test/test_gameplay.py` setup now register cleanup to restore `pygame.draw`; path-button font/draw tests also use scoped `patch(...)` contexts.

## Validation After Fix

- `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`: passed, 174 tests.
- `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff check <changed Python files>`: passed.
- `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff format --check <changed Python files>`: passed.
- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files <changed files>`: passed.
