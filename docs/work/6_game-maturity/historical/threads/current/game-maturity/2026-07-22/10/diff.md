# GM-07b versioned save-snapshot diff ledger

Status: delivered as Commit A `5906370` (rebased over the owner-launched oracle fix `d99d9e8` with one additive PROGRESS merge and a byte-exact fixture re-materialization), exact [run 29941339839](https://github.com/yanfengliu/python_mini_metro/actions/runs/29941339839) green; evidence-only Commit B active

## Implemented production surface

- Add `src/save_schema.py` and `src/save_schema_records.py`: the strict v1 save-document validator family — exact keys and exact types per section, forward-version rejection, pinned `stateContract`/`rulesVersion` literals, per-class ID grammar with global uniqueness, exact pause vocabulary, int speed domain, exactly-one-per-pool-station spawn coverage, range-pinned RNG domains, active-prefix reference validation, per-metro nullable `serviceAction` records with at-station/zero-speed/timer-invariant enforcement, ordered-array encodings, duplicate/dangling rejection, and document-wide checkpoint-safe coercion — plus `canonical_save_bytes` (ASCII recipe, trailing LF).
- Add `src/save_game.py` and `src/save_load.py`: pure verbatim serialization (service caches included, mid-gesture saves rejected, non-prefix station lists rejected) through a save-local mkstemp→fsync→`os.replace` atomic writer with no `rl.` import; and the repo's first JSON-to-Mediator loader — RNG deep-tuple restoration after construction, post-construction ID assignment, geometry rebuild while `path.metros` is empty, manual metro binding with shape-color re-derivation, direct-append over-capacity station queues, verbatim service-cache restoration (never re-derived), node rehydration from ref-filtered path-ID sets, synchronous button restoration with validate-equal locks, verbatim pause-reason holds, and fail-closed `ValueError` rejection with no partial Mediator escaping.
- Freeze `scripts/fixtures/save-v1.json` (15,442 bytes, SHA-256 pinned in-test, LF, no `.gitattributes` entry) at a boundary carrying a live bound board action; add `config.save_dir_name` and the anchored `/saves/` ignore line.
- No recursive/agent contract, observation, protocol, or gameplay change; headless surfaces gain no save imports (AST-scan enforced including the checkpoint verifier); `recursive_checkpoint.py` remains a one-way verifier and the state-equality oracle.

## Implemented evidence surface

- Reconcile GM-07a Commit A run `29907589648` and Commit B run `29907985159`; record D-026 (save directory, ASCII canonical bytes, `rulesVersion` plus the config-change⇒schema-bump policy, map identity deferred).
- Two research lanes, two plan-review lanes plus recheck (23 findings), 49-record red baseline, the constitution's high-risk battery — Codex CLI external lane (verbatim `raw/codex.md`) plus an independent harness probe lane — one converging blocker fixed by the verbatim service-action schema amendment with red-first reproductions at exact boundaries, and a CLEAN final re-review with an independent 402-boundary sweep; all preserved under `raw/` and `red-evidence.md`.
- Update `README.md` (save/load API, ID-selector honesty), `ARCHITECTURE.md` (new modules, boundary notes), `PROGRESS.md`; file two pre-existing-defect background tasks (checkpoint crash on stale service caches; the dead GM-03f differential verifier).

Local gates: six GM-07b modules 66/66; full py313 suite 1147/0 with 12 expected skips; guarded `npm test` 249/0; Ruff and per-file pre-commit clean; all line budgets held. Commit A staging, push, and remote results remain.
