# GM-09a2 versioned task-descriptor identity plan

Status: implemented and locally green. GM-09a2 is the second half of the roadmap's GM-09a, split out at the dual plan review (`../18/PLAN.md` "Plan v2" + `../18/GM-09a2-foundation.md`). The load-bearing descriptor-version switch was verified byte-exact (both review lanes' predicted hashes reproduced) before the manifest/CLI layers were built. Reconciles GM-09a's Commit B `0f733a8`.

Transaction marker: `[GM-09a2:A]`

## Scope

Versioned RL task identity with strict legacy-byte-compat (D-033): the descriptor-version switch (map-absent = byte-identical legacy hash), training manifest v3, `task_spec_from_manifest` inheritance, the thunk map threading, `PlayerPixelEnv`/`Mediator` map wiring, the CLI `--map` with resume-inherit, and the committed legacy fixture. No save-schema/high-score change (GM-09f), no gameplay change (Classic == default map).

## Folded from the thread-18 dual plan review

- MAJOR-1 (resume-inherit): `scripts/train_rl.py` parses the resume manifest BEFORE the spec and `_resolve_map_identity` inherits the map from the manifest; `--map` defaults to None so a legacy resume still validates.
- Codex-2 (git-ignored fixture): the real pre-map manifest is committed sanitized to `scripts/fixtures/legacy-training-manifest-v1.json`; a test reconstructs it to `c2ef342f…`.
- Codex-5 (v3 invariants): explicit V1/V2/V3 constants; history emitted for v2+v3; map keys only v3; `__post_init__` schema/map lockstep; the factory selects v3 from map presence.
- MINOR (env default None): `PlayerPixelEnv()` stays map-absent so `PlayerPixelEnv().task_spec == TaskSpec()` holds; NIT (append fields last) honored.

## Delivery

TDD-first (`test_gm09a2_task_identity`, `test_gm09a2_manifest`): the legacy byte-lock + real-fixture reconstruction, the map-bound descriptor, TaskSpec/manifest invariants, v3 round-trip, and the CLI resume-inherit. Full py313 suite 1357/0 (12 skips), ruff/format/pre-commit clean, `EXPECTED_LF_TRAINING` re-pinned. Combined adversarial implementation review (harness + external Codex lane, since this is NEW versioning behavior on the RL protocol) with an empirical legacy-hash proof. Then rebase, `[GM-09a2:A]`, exact CI, evidence `[GM-09a2:B]`; GM-09b (terrain/regions + first river map) opens next.
