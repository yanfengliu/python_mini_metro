# GM-09b plan — dual adversarial review synthesis

Both lanes (harness + external Codex ultra) went NOT CLEAN and AGREED on the core: the scope decision (defer save-v2/high-score-v2 to GM-09f, keep the fail-closed guard) is SOUND — both exhaustively verified that no save-capable path constructs a river Mediator in GM-09b (human shell is Classic-only until GM-09f; RL uses checkpoints, not `save_game`). The defects are determinism/guard/rendering specification gaps, all folded into `PLAN.md` "Plan v2".

- **Harness** (`raw/plan-harness.md`, NOT CLEAN): 2 MAJOR (falsy `()` sentinel; `GameRenderer.draw` hook for RL pixels) + minors; also flagged the broken `geometry.Polygon.contains`.
- **Codex ultra** (`raw/plan-codex.md`, NOT CLEAN): corroborated both MAJORs and added TWO new ones — the forged-`classic@1` guard bypass and the under-modeled rejection draw count — plus the station-glyph-overlap and the import-allowlist gap.

## Findings and dispositions (all folded into Plan v2)

- **MAJOR (both) — CLASSIC's empty regions are `()` not `None`.** A `is None` sentinel sends CLASSIC into region processing → hang or moved fingerprint. FOLDED: falsy sentinel (`if not spawn_regions`), test `()` explicitly against both RNG states.
- **MAJOR (Codex, NEW) — the save guard isn't structurally fail-closed.** A forged `MapDefinition("classic",1,rivers=…)` passes the id+version guard and mis-saves. FOLDED: harden `_require_classic_map` to structural equality with canonical `CLASSIC` (frozen-dataclass `__eq__`); add a forged-terrain regression.
- **MAJOR (both) — the spawn chain omits `get_random_station`.** FOLDED: thread `spawn_regions` through `get_random_stations → get_random_station → get_station_spawn_position`; leave `get_random_position` byte-identical (rejection in the caller).
- **MAJOR (both) + MINOR (Codex) — rejection underspecified/unbounded + glyph overlap.** FOLDED: per-candidate retry bound (64) + named error; positive-area construction assertion; erode banks by `station_size`; keep the 8-candidate structure + one `python_random.choices` per station; a NEW RIVER fingerprint pins the real draw count (~153 candidates for a 20-pool, ~459 at seed 1, ~8% rejection).
- **MAJOR (both) — terrain hook in `GameRenderer.draw`, not `main`.** FOLDED: draw at the top of `GameRenderer.draw` so RL/headless pixels include the river; `getattr(state,"map_definition",None)`; CLASSIC no-op keeps byte-identity; `game_renderer` "modified but < 500".
- **MAJOR (both) — no live `geometry.Polygon`** (shapely + uuid + broken `contains`). FOLDED: tuples on `MapDefinition`, `pygame.draw.polygon` to render, pure point-in-rect to test.
- **MINOR — immutability/validation, import allowlist, docs, stale save comment.** FOLDED: recursive tuple-coerce + validate the geometry fields; add `shapely`/`geometry.polygon` to the maps import-forbidden set; update README/ARCHITECTURE/GAME_RULES/PROGRESS + the `save_game` comment.

## Result
NOT CLEAN → all findings folded into a v2 plan; the scope decision (defer save-v2 to GM-09f, harden the guard) is dual-confirmed sound. The RIVER spawn feasibility (deterministic rejection, terminates, confines to banks) is empirically anchored (`raw/river-spawn-feasibility.md`), corrected for the 8-candidate draw structure. Ready for red tests.

## Implementation review (post-fold)

Dual lane attempted on the built unit:
- **Harness lane** (`raw/impl-harness.md` — see the transcript; CLEAN): GOLD-STANDARD — it built an INDEPENDENT old-code mirror (`git show HEAD:` of `get_entity.py`/`mediator.py`) and diffed CLASSIC byte-identity across seeds 0/1/2/7/42 (every station position + shape + the full post-construction `python_random` AND numpy RNG states + path colors → ZERO diff), plus an identical full-frame render hash old-vs-new. It empirically verified RIVER spawn across 40 seeds (zero off-bank, zero glyph-overlaps-water; 13.8% single-draw rejection, max 6 consecutive in 200k draws vs the 64-try bound, P(64 fail)≈1e-55), the structural guard (rejects forged `classic@1`-with-terrain, river, and divergent-palette; does NOT over-reject a reconstructed-identical classic or `map_definition=None`), the RL observation (differs classic-vs-river, reproducible; CLASSIC byte-identical), import-safety, and the validation. Full suite 1372/0; ruff/format/pre-commit clean. Only non-actionable NITs (a benign 1-pixel waterline share; pre-existing `mediator.py` 844 LOC). Verdict CLEAN.
- **External Codex ultra lane**: HUNG this run — it produced ~8700 lines of verification tool activity then stalled for 13+ minutes with no final verdict written (a reliability failure, not a safety decline). Not blocking: the harness lane already performed the compensation the constitution prescribes for an external-lane failure (independent old-code reconstruction + a broad-seed empirical byte-identity proof), the full DUAL PLAN review had already run both lanes and folded Codex's forged-guard MAJOR + the determinism/render/Polygon findings pre-code, and the harness impl lane verified every one of those fixes. Recorded honestly.

## Result
CLEAN after fold. CLASSIC byte-identity is independently proven (old-code mirror + the frozen fingerprints/fixture); RIVER spawn is correct and deterministic across 40 seeds; the structural guard closes the forged-classic bypass; the river renders through `GameRenderer.draw` so RL pixels include it. Ready for CI-gated `[GM-09b:A]`.
