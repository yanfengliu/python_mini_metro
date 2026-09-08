# GM-10b plan v2 — dedicated-RNG weekly offer generator (D-042)

## Scope (minimal coherent unit)
The SEEDED OFFER GENERATOR behind the GM-10a week boundary: at each held week boundary,
generate a deterministic, CONTINUE-EXACT set of upgrade OFFERS (data only), stored on the
mediator and rendered read-only in the OFFER modal.

**In scope:** a dedicated PER-WEEK offer RNG (derived read-only from persisted state — see the
pivot below); the offer data model + pure generator (`src/offers.py`); mediator generation/
storage at the boundary; read-only modal render; config constants.

**Explicitly OUT of scope (roadmap-split):**
- APPLYING a chosen offer / interactive choice controls → **GM-10c**.
- Per-kind EFFECTS (line/locomotive/carriage/tunnel grants) → **GM-10d–g**.
- Persisting an APPLIED offer's effects + mid-offer save + replay reconciliation → **GM-10h**.
- RL observation of offers → not needed (weeks gated OFF for RL).

## Plan-review pivot (v1 → v2): Codex BLOCKER → stateless derivation
Dual plan review (harness REVISE, Codex BLOCK). Codex's BLOCKER (VERIFIED against
`README.md:66` "Continue … resumes **exactly** where you left off"): plan v1 used a dedicated
`offer_random` stream (a 3rd `SeedSequence.spawn(3)`) that was NOT persisted (deferred to
GM-10h) — but that stream RESETS on Continue, so the next week's offers would DIVERGE from
uninterrupted play, violating the exact-Continue contract. The harness lane had rated the same
deferral "clean" — the two-lane disagreement is the review-coverage lesson again.

**Resolution (Codex's suggested alternative, empirically proven):** generate offers STATELESSLY
from ALREADY-PERSISTED inputs. The per-week offer RNG is derived READ-ONLY from
`self.context.python_random.getstate()` + `week_index`. This is:
- **Continue-exact** (proven, seeds 0/1/7): `python_random.getstate()` at a week boundary is
  byte-IDENTICAL after a mid-game save→load round-trip (the existing RNG-persistence contract
  already makes every future step's state exact) → same derived seed → same offers. No new
  persisted state needed; the GM-10h persistence deferral is HONORED and correct.
- **Gameplay-inert** (proven): `getstate()` is READ-ONLY — it consumes ZERO `python_random`
  draws, so the station-spawn/gameplay stream is byte-untouched (directly assertable:
  `getstate()` identical immediately before and after generation).
- **Simpler & lower-risk than v1**: NO `SimulationContext` change (no `spawn(3)`), NO save/
  checkpoint/schema change, and it DISSOLVES Codex MAJOR-2 (no offer-stream state for the
  gesture-rollback snapshots to capture). "Dedicated RNG" is satisfied by a dedicated per-week
  `random.Random` for offers, seeded deterministically, that shares no draws with gameplay.

## Empirically proven premises (headless probes, this session)
1. **Cadence**: seeded games last ~4–6 weeks before game-over → ~4–6 offers/game. `line_credits
   == deliveries`, ~4–5/week.
2. **Read-only inertness**: `getstate()` consumes no draws; a separate `random.Random` at every
   boundary leaves the gameplay trajectory BYTE-IDENTICAL (seeds 0/1/7/42).
3. **Continue-exact**: `python_random.getstate()` at the week-3 boundary is byte-identical after
   a mid-game `serialize_game`→`deserialize_game` round-trip (seeds 0/1/7) → the derived offers
   reproduce exactly on Continue.
4. **Zero new save/checkpoint bytes**: GM-10b touches NO serialization (no offer stream, no
   `current_offers` persisted — a save is blocked mid-offer by `_require_quiescent`, and offers
   exist only during a held boundary). Every frozen fixture (`save-v1.json`, `save-v2-classic.json`,
   GM-09a fingerprints, checkpoint schemas) stays frozen, UNTOUCHED.

## Design (per file)

### `src/offers.py` (NEW — dependency-light, import-safe; stdlib-only)
- Imports only `enum`, `dataclasses`, `random` — NO pygame/mediator/entity → import-safe on every
  headless/RL path (stricter than `crossings.py`/`maps.py`, which import `geometry`/`config`).
- `class OfferKind(Enum)`: `NEW_LINE`, `LOCOMOTIVE`, `CARRIAGE`, `TUNNEL`.
- `@dataclass(frozen=True) class Offer`: `kind: OfferKind`, `label: str`.
- `_KIND_LABELS: dict[OfferKind, str]` ("New Line" / "+1 Locomotive" / "+1 Carriage" / "+1 Tunnel");
  `describe(kind) -> Offer`.
- `_CLASSIC_POOL` / `_BOUNDED_POOL`: EXPLICITLY-ORDERED tuples of kinds (order fixed so
  `rng.sample` is deterministic; `_BOUNDED_POOL` includes `TUNNEL`, `_CLASSIC_POOL` excludes it).
- `generate_offers(rng: random.Random, *, count: int, tunnels_bounded: bool) -> tuple[Offer, ...]`:
  pool = `_BOUNDED_POOL if tunnels_bounded else _CLASSIC_POOL`; draws `count` DISTINCT kinds via
  `rng.sample(pool, min(count, len(pool)))`. The `min` clamp gets a one-line comment: it is a
  SILENT cap (review NIT-10) — harmless at `OFFERS_PER_WEEK=2` over the 3-kind CLASSIC pool, but a
  future `count > pool` yields fewer offers on CLASSIC. `ValueError` (named) if `count < 1`.

### `src/mediator.py`
- `__init__`: `self.current_offers: tuple[Offer, ...] = ()` (after the week fields, so every
  construction path — incl. duck-typed hosts and fakes — has it; avoids `AttributeError`).
- New `_offer_rng_for_current_week(self) -> random.Random`: derive a fresh per-week RNG READ-ONLY:
  `seed = int.from_bytes(hashlib.sha256(repr((self.week_index, self.context.python_random.getstate())).encode()).digest()[:8], "big")`;
  return `random.Random(seed)`. (Deterministic + cross-process stable — `repr` of the int-tuple
  state + sha256, never PYTHONHASHSEED-salted `hash()`. READ-ONLY: does not advance python_random.)
- `_maybe_hold_week_boundary(old_steps)`: when the hold fires (calendar on, boundary crossed, not
  game over), BEFORE holding the pause set
  `self.current_offers = generate_offers(self._offer_rng_for_current_week(), count=OFFERS_PER_WEEK, tunnels_bounded=self.num_tunnels is not None)`.
  Gated identically to the hold → RL/headless/tutorial never generate; `current_offers` stays `()`.
- `resolve_week_boundary()`: `self.current_offers = ()` then release the pause. (GM-10c will APPLY
  the chosen offer here BEFORE clearing; correct the stale `:703` comment to name GM-10c.)

### `src/ui/menu_screens.py`
- `draw_offer_screen(surface, week_index, offers)` gains `offers`: under "Week N complete", render
  each offer's `label` as read-only stacked text. `offer_menu_layout` unchanged (single "Continue").

### `src/main.py`
- Pass `controller.mediator.current_offers` into `draw_offer_screen(...)` at the OFFER render.

### `test/test_gm10a_calendar.py` (MUST update — plan-review MAJOR, both lanes)
- `_LoopMediator.__init__` (~:383) gains `self.current_offers = ()` — else `main.py`'s
  `controller.mediator.current_offers` raises `AttributeError` out of `run_game`.
- the `patch("main.draw_offer_screen", side_effect=lambda surface, week_index: ...)` (~:440)
  becomes arity-3 (`lambda surface, week_index, offers: ...`) — else `TypeError`.

### `src/config.py`
- `OFFERS_PER_WEEK = 2` (near `WEEK_LENGTH_STEPS`, GM-11-tunable comment).

### Docs (review MAJOR-5 — reconcile the canon)
- `README.md` / `GAME_RULES.md`: the week modal now previews the week's upgrade OFFERS (read-only;
  choosing is GM-10c). `ARCHITECTURE.md`: `src/offers.py` module + the stateless-derivation boundary;
  reconcile the GM-10a note that deferred "offer" to GM-10b. `PROGRESS.md`: GM-10b bullet. `DECISIONS.md`
  (nested thread): D-042 (records the option-B pivot + the GM-10c-not-before-GM-10h ordering constraint).
- NO `SimulationContext` docstring change (no spawn change in v2).

### No changes to
`simulation_context.py`, `env.py`, `save_*.py`, `recursive_checkpoint*.py`, gesture snapshots.

## TDD tests (`test/test_gm10b_offers.py`)
1. **Determinism**: two `Mediator(seed=s)` played identically → identical `current_offers`
   week-by-week; pin the exact seed-0 sequence against a FROZEN literal (review MINOR-9: a frozen
   constant, never a live `git show HEAD:` checkout — nested-worktree CRLF trap).
2. **Continue-exact (regression lock of the BLOCKER fix)**: play → mid-game `serialize_game` →
   `deserialize_game` → resume → the offers at the next boundary are IDENTICAL to uninterrupted
   play. (The property Codex flagged as false-green; now directly asserted.)
3. **Read-only gameplay inertness (review MAJOR-3, direct)**: `python_random.getstate()` AND
   `numpy_random.bit_generator.state` are IDENTICAL immediately before vs after
   `_maybe_hold_week_boundary` generates offers (zero draws consumed) — a direct state-equality
   assertion, not a clock-reset-confounded trajectory compare. Plus the GM-09a determinism locks
   stay green (import + run them).
4. **Gated OFF for RL/headless**: `MiniMetroEnv`/`PlayerPixelEnv`/frame-limited `run_game` step
   past a boundary with `current_offers == ()` always.
5. **Offer shape**: `OFFERS_PER_WEEK` DISTINCT kinds; TUNNEL EXCLUDED on CLASSIC
   (`num_tunnels is None`), INCLUDED on a bounded map (RIVER, budget 3).
6. **Regenerate per week**: offers generated fresh each boundary (week 2 derives from the week-2
   state, distinct derivation from week 1) — pin the seed-0 week-1 vs week-2 sets.
7. **resolve clears**: `resolve_week_boundary()` empties `current_offers`.
8. **Modal render (review MAJOR-4, strong)**: `draw_offer_screen` with offers paints EACH label's
   region (compare against a no-offer baseline surface; assert the offer-bearing surface differs in
   the label rows and is byte-stable across repeated draws) — NOT a generic non-blank check.
9. **run_game OFFER integration (harness update)**: the GM-10a `_drive_run_game` harness renders
   the exact ordered offer tuple, stable across repeated OFFER frames (via `current_offers` on the
   real mediator through `main.run_game`).
10. **Import-safety**: `import offers` in a subprocess with no pygame initialised.
11. **`generate_offers` misuse**: `count < 1` → named `ValueError`; `count > pool` clamps (documented).

## Risks / review foci
- **Continue-exactness is the load-bearing claim** — proven (premise 3) + regression-locked (test 2).
- **Read-only derivation** must consume no gameplay draws — proven + directly asserted (test 3).
- **Scope**: application/effects/persistence OUT. **Ordering constraint (review MINOR-8, in D-042):**
  GM-10c (apply a choice) must NOT ship ahead of GM-10h (applied-offer/replay reconciliation).
- **`_require_running_config` pin** (Explore): not hit by GM-10b; FLAG for GM-10c/e.
- New module + game-mechanic + config + a determinism-sensitive derivation → HIGH-RISK → dual impl
  review (this plan pivot was itself dual-reviewed).
