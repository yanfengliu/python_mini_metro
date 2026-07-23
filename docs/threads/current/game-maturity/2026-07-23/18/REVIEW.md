# GM-09a plan — dual adversarial review synthesis

The maps-milestone opening is the highest-risk unit in the roadmap (RL task fingerprint + training manifest + save schema, all with strict legacy-byte-compatibility). It was reviewed pre-code by two independent lanes, plus empirical anchor verification.

- **Empirical anchors** (`raw/legacy-anchors.md`): the reference `TaskSpec(fast,6,deliveries,4)` reproduces the real fixture fingerprint `c2ef342f…` exactly; `Mediator(seed=N)` station spawns pinned for seeds 0/42/123.
- **Harness lane** (`raw/plan-harness.md`, NOT CLEAN): empirically PROTOTYPED the byte-compat switch (map-absent bytes byte-identical) and reproduced both anchors; found 2 MAJOR (resume-inherit; manifest-v3 history conditionals) + MINORs; judged the unit "large but coherent, no split".
- **External Codex ultra lane** (`raw/plan-codex.md`, NOT CLEAN): independently reproduced the anchors (map-bound descriptor = 710 bytes, hash `efec72da…`); found **8 MAJOR + 2 MINOR** and recommended SPLITTING the unit.

Both lanes agree the central byte-compat mechanism is SOUND. The reviews' load-bearing findings drove a re-scope (see `PLAN.md` "Plan v2").

## Decisive outcome: split into two risk-isolated units

Codex's split recommendation is adopted (risk isolation over the harness's "coherent" view — for byte-exact work, coupling the RNG-parity change with the RL-versioning change into one review is unsafe):

- **GM-09a** — the `Classic` map abstraction, behavior-preserving (data-only `MapDefinition`, one-way consumption, full determinism parity, save fail-closed guard). No RL/manifest/CLI/high-score change.
- **GM-09a2** — the versioned task-descriptor identity (TaskSpec map fields, descriptor-version switch, manifest v3, CLI resume-inherit, thunk version enforcement, committed legacy fixture).
- **GM-09f** — high-score `mapDefinitionVersion` + save-schema map field (deferred; inert with one map).

## Findings and dispositions (all folded into PLAN.md v2)

- **MAJOR (both) — `--map classic` default breaks legacy resume.** Fix: resume/evaluate INHERIT map identity from the manifest (omission = `None`); only fresh training defaults to Classic. (GM-09a2)
- **MAJOR (Codex) — legacy fixture is git-ignored (`/output/`).** The highest-risk regression can't run in CI. Fix: commit frozen legacy manifest bytes under `scripts/fixtures/`, assert canonical bytes + the full `c2ef342f…` hash. (GM-09a2)
- **MAJOR (Codex+harness) — "station bytes" can't prove determinism.** Station IDs are unseeded UUIDs, and station+color draws share one RNG stream. Fix: pin an ID-free station projection + both RNG states + `path_colors` + spawn intervals + a canonical trajectory (the checkpoint already captures these) vs a clean pre-change worktree, seeds 0+1, distinct `PYTHONHASHSEED`s; snapshot config shape-lists into ordered tuples. (GM-09a)
- **MAJOR (Codex) — `maps.py` ownership contradicts import-isolation.** `get_entity` pulls pygame. Fix: `maps.py` is data-only; `get_entity`/`mediator` consume a `MapDefinition` one-way; `rl/protocol.py` never imports the registry. (GM-09a)
- **MAJOR (Codex) — high-score promotion seam would silently break.** Reading `mediator.map_definition` in the `SimpleNamespace` promotion raises-and-is-swallowed. Fix: leave the hardcoded `"classic"` untouched this unit; defer high-score map-sourcing + version to GM-09f. (deferred)
- **MAJOR (Codex) — ID-only lookup ignores `map_definition_version`.** Fix: resolve/validate the exact pair; legacy `(None,None)`→Classic operationally. (GM-09a)
- **MAJOR (Codex) — manifest v3 invariants.** Keep explicit V1/V2/V3; history for v2/v3, map only v3; `__post_init__` v1/v2-mapless / v3-map-bound; factory derives all from one `TaskSpec`. (GM-09a2)
- **MAJOR (Codex) — save deferral needs a fail-closed guard.** A non-Classic def must be unconstructible/unserializable through a save-capable Mediator until the schema migration lands (≤ first alternate map). (GM-09a)
- **MINORs** — env must default `map_id=None` (bare-env test); `env.py` builds no TaskSpec (phantom surface — only a `Mediator(map_definition=)` param); count fields not map-owned yet; append TaskSpec fields last; profiler/README/observation deferred to GM-09f. (folded)

## Result
NOT CLEAN → re-scoped into two risk-isolated units with all findings folded; the byte-compat core is empirically verified and anchored. GM-09a (the Classic map abstraction) is the next implementation target — behavior-preserving, self-contained, with rigorous determinism-parity tests against a clean pre-change worktree. This is a dually-reviewed, de-risked, implementation-ready plan for the maps foundation.

## Implementation review (GM-09a Classic map abstraction)

- **Harness lane** (`raw/impl-harness.md`): **CLEAN.** Independently reconstructed the pre-change HEAD code and reproduced the pinned fingerprints (proving the regression lock is non-circular), ran a 20,000-seed `choice(list)`-vs-`choice(tuple)` stress (0 mismatches), confirmed seed 1 exercises the retry loop and both seeds hit the unique-shape path, and verified the fail-closed save guard (adds no bytes, `save-v1.json` frozen), import-safety/no-cycle, deep immutability, `resolve_map` errors, and behavior preservation across every caller. Three NITs; two folded (tuple `__post_init__` coercion; a durable unique-path coverage assertion), one no-action.
- **External Codex lane** (`raw/impl-codex-declined.md`): DECLINED this run (a safety egress refusal to transmit repo code; not worked around). Substituted by the harness lane's independent pre-change reconstruction + a driver-run 60-seed byte-identity check — appropriate for a behavior-preserving refactor whose only delta is list↔tuple in `choice()`/iteration.
- **Empirical** (driver): 60 seeds, 0 mismatches between the default (list) and explicit-Classic (tuple) station draws including both RNG states; 59/60 exercise the unique-shape path.

## Result
CLEAN → the map abstraction is byte-identical to pre-change behavior (construction + trajectory), independently proven; the save guard is fail-closed with no byte change; import-safety and immutability hold. Local gates green (full suite 1336/0 + 12 skips, GM-09a 12/0, ruff/pre-commit clean, budgets held). Ready for CI-gated `[GM-09a:A]` delivery.
