# GM-10b plan review — harness lane (adversarial, live-code verified)

## Verdict: REVISE

The plan's load-bearing claims (byte-compat of the 3rd spawn, zero save/checkpoint bytes, RL/headless gating, tick ordering, scope split) are all **verified correct against live code**. But the plan misses one existing-test surface that its own changes will break, and does not mention updating it. That must be folded in before implementation. No BLOCKERs.

### Findings

**1. [MAJOR] The plan breaks `test/test_gm10a_calendar.py`'s run_game harness and does not mention fixing it.**
The plan changes `main.py:433` to pass a 3rd arg (`controller.mediator.current_offers`) into `draw_offer_screen`, and changes `menu_screens.draw_offer_screen(surface, week_index)` to add `offers`. The live GM-10a integration harness will fail on two counts:
- `test/test_gm10a_calendar.py:383-392` — `_LoopMediator.__init__` has no `current_offers`. Post-change `main.py` evaluates `controller.mediator.current_offers` on this fake → `AttributeError` (propagates out of `run_game`; `_drive_run_game` only catches `SystemExit`).
- `test/test_gm10a_calendar.py:440-442` — `patch("main.draw_offer_screen", side_effect=lambda surface, week_index: ...)` takes 2 args; `main.py` calls it with 3 → `TypeError`.
Fix (must be in the plan): add `self.current_offers = ()` to `_LoopMediator.__init__`, and change the patch to arity-3. List `test/test_gm10a_calendar.py` as a touched surface.

**2. [VERIFIED — claim 1 holds] Adding `offer_random` as the 3rd spawn is byte-back-compatible.** Empirical check across seeds 0/1/7/42/12345/2^31: `spawn(3)` yields byte-identical child-0/child-1 states and draws vs `spawn(2)`. GM-09a determinism locks unchanged; `test_simulation_context.py` asserts no spawn count.

**3. [VERIFIED — claim 2 holds, and is ENFORCED] GM-10b adds ZERO save/checkpoint bytes.** `save_game.py:289-292` rng block is python/numpy by name; `save_schema._exact_keys` REJECTS any stray key; checkpoint + `_normalize_observation` read only hardcoded keys; fixtures unmoved.

**4. [VERIFIED — claim 3 holds] Gating is identical to the week hold.** `week_calendar=False` default; only `build_game`/`build_from` set it; RL/tutorial never do. Existing gating tests lock it.

**5. [VERIFIED — claim 4 holds] Generation ordering correct.** `_maybe_hold_week_boundary` runs last after both settlement passes; offers generated once per crossing; game-over still wins.

**6. [VERIFIED — claim 5 holds] Scope split clean.** Saves blocked while pending; window-close resolves before autosave; gesture snapshots capture RNG by name.

**7. [VERIFIED] Data model + `num_tunnels` semantics reasonable.** `rng.sample` gives distinct kinds; excluding TUNNEL when `num_tunnels is None` matches live semantics; stdlib-only import-safe.

**8. [MINOR] Sequence GM-10h (persistence) before/with GM-10c (application)** — once GM-10c applies a choice, an unpersisted offer stream could inconsistently resurrect/replace it on Continue. Add an explicit ordering note.

**9. [MINOR] Test 2 control capture** — prefer a FROZEN fingerprint constant over a live `git show HEAD:` checkout (collides with the repo's nested-worktree CRLF/checkout traps).

**10. [NIT] `rng.sample` clamp is a silent cap** — worth a one-line comment.

**11. [NIT — already in plan] `resolve_week_boundary` comment** correction is already noted.

**Bottom line:** design sound, risky RNG/persistence/gating claims empirically + structurally verified. Fold Finding 1 (the harness update) into the touched-surfaces and test list; ready to implement.
