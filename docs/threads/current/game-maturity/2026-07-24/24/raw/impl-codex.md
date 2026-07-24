BLOCKER — No findings.

- MAJOR — [src/save_game.py:46](/C:/Users/38909/Documents/github/python_mini_metro/src/save_game.py:46) — A `MapDefinition` subclass implementing `__bool__ -> False` is replaced by `CLASSIC` through `getattr(...) or CLASSIC`. A forged River definition therefore serialized as `classic@1`; reload silently lost its rivers and tunnel budget. Fix: default to Classic only when `map_definition is None`, then resolve and structurally compare the actual value. Add a falsey-map regression.

- MINOR — [src/save_schema.py:116](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema.py:116) — A v2 document with `mapId="ríver"` passes `validate_save`, contrary to PLAN v2’s non-empty ASCII contract. Whitespace-bearing IDs also pass despite the claimed RL-validator parity. Loading still fails closed through `resolve_map`. Fix: enforce ASCII—and whitespace exclusion if parity is intended—and add negative cases.

- MINOR — [README.md:215](/C:/Users/38909/Documents/github/python_mini_metro/README.md:215), [README.md:221](/C:/Users/38909/Documents/github/python_mini_metro/README.md:221), [ARCHITECTURE.md:35](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:35), [DECISIONS.md:241](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md:241) — Current docs still describe serialization/current schema as v1, omit `save-v2-classic.json`, and end D-038 by saying the already-landed fields remain deferred. Fix those stale statements.

NIT — No findings.

Verified clean:

- Focused suite: 34/34 passed.
- Full suite: 1,442 passed, 12 skipped.
- Ruff and format checks passed for all ten changed Python files; `git diff --check` passed.
- Frozen v1 remains 15,442 bytes with SHA-256 `d34736a6…acd1e`.
- Frozen v2 is the exact 15,485-byte v1→v2 upgrade with SHA-256 `60f2bc16…bd84`; cross-process determinism passed.
- Missing/bool/float/list/string/null/0/3 schema versions raise `ValueError`; version/key mismatches fail closed.
- Unknown map IDs and unsupported versions raise named resolver errors.
- Inactive pool stations are checked; inclusive land boundaries pass; exact-budget River state round-trips; forged over-budget load is rejected.
- Existing forged-Classic rejection still passes, and registered River/Delta/Lake round-trips are substantive rather than tautological.
- Recursive checkpoints, agent replay, and RL manifests remain separate; no non-test consumer assumes save schema 1.

The explicit test corpus still lacks direct regressions for list-valued `schemaVersion`, exact/over-budget loading, inclusive boundaries, and forged Delta/Lake definitions; current behavior passed probes, but those cases should be codified with the fixes.

FIX-FIRST
