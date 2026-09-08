===BEGIN-REVIEW===
VERDICT: FIX-FIRST

1. [MAJOR] The visible-offer path is mutation-weak at two layers. Replacing the live `current_offers` argument with `()` at src/main.py:434-437 passes because the run-loop spy discards its `offers` argument and its mediator supplies an empty tuple at test/test_gm10a_calendar.py:389,441-444. Separately, removing the label blit at src/ui/menu_screens.py:243-245 still passes test/test_gm10b_offers.py:258-265 because offer count changes panel geometry and heading position even when no label glyph is painted. The modal can therefore display no offer text while all focused tests remain green.

2. [MAJOR] Continue-exactness is tested only with seed 0, the same seed used by deserialization’s temporary constructor. Both trajectories use `_played(0)` at test/test_gm10b_offers.py:191-200, while loading constructs `Mediator(seed=0)` before restoring RNG at src/save_load.py:346-350. A derivation conditionally salted by an unpersisted, nonzero constructor seed passes every current test—seed-0 Continue remains exact and seed-3 fresh games still match each other—yet diverges after loading a seed-3 game. The live implementation at src/mediator.py:717-727 is correct; the blocker-resolution invariant is under-pinned.

3. [MAJOR] The claimed gameplay byte-identity test does not cover the complete gameplay RNG/state. test/test_gm10b_offers.py:157-185 compares only `python_random`, steps, and deliveries. A single `numpy_random` draw during offer derivation survives all GM-10a/b tests while shifting later station positions/colors, which consume that stream at src/utils.py:22-37. Both RNG streams are persistence state at src/save_game.py:289-292, so the test’s “gameplay byte-identical” claim is materially stronger than its assertions.

4. [MINOR] `test_offers_module_imports_without_pygame` does not verify its stated contract. Its subprocess merely imports `offers` and prints an enum value at test/test_gm10b_offers.py:280-290; adding `import pygame` would still pass. The live module is presently stdlib-only at src/offers.py:15-19.

5. [MINOR] The `count < 1` error contract is only tested at zero. test/test_gm10b_offers.py:122-124 does not cover a negative count, so changing src/offers.py:80 from `< 1` to `== 0` survives while negative input falls through to `random.sample`’s non-domain-specific error.

6. [MINOR] Interactive-only gating does not prevent RL artifact compatibility drift. `compute_content_fingerprint` hashes every non-RL file under `src/**` at src/rl/training.py:296-323, so the new module and modified runtime files rotate the content fingerprint and cause older manifests to fail strict resume/evaluation. ARCHITECTURE.md:382 and PROGRESS.md:184 document unchanged save/checkpoint/observation bytes but omit this operational boundary.

Mutation audit:
- Frozen generator/pool sequence: test/test_gm10b_offers.py:134-135 turns red.
- Ignoring `week_index`: test/test_gm10b_offers.py:134-135 turns red; the weaker “weeks differ” check at :142-145 does not.
- Consuming a Python gameplay draw: :157-185 turns red. NumPy consumption survives, as finding 3 explains.
- Removing the calendar gate: :234-248 turns red.
- Leaking TUNNEL into CLASSIC: :86-114 turns red.
- Failing to clear on resolve: :151-155 turns red.
- Dropping one offer entry inside the renderer: :258-265 turns red. Dropping the transport argument or all glyph blits survives, as finding 1 explains.
- Ordinary seed-0 save/load divergence: :187-211 turns red. Constructor-dependent nonzero-seed divergence survives, as finding 2 explains.

Confirmed:
- The stateless pivot resolves the original blocker: `getstate()` is read-only, SHA-256 is unsalted, and the isolated `Random` does not advance gameplay RNG at src/mediator.py:717-727. Save/load persists and restores the exact Python state at src/save_game.py:289-292 and src/save_load.py:57-65.
- No offer/save/checkpoint bytes were added; save exact-key validation remains unchanged at src/save_schema.py:60-84,230-250. Frozen v1/v2 pins and GM-09a construction/trajectory fingerprints remain green.
- RL, pixel RL, tutorial, and frame-limited runs remain gated off through src/mediator.py:168-177,788-809 and src/main.py:223-256.
- Settlement and game-over complete before offer generation at src/mediator.py:771-809; game-over promotion precedes offer promotion at src/main.py:376-386.
- The live offer pools, distinct sampling, clamp, map rule, current main wiring, and repeat-stable modal rendering are correct. No application effects or offer persistence leaked into GM-10b.
- The focused GM-10a/b suite passed 43/43 tests.
===END-REVIEW===
