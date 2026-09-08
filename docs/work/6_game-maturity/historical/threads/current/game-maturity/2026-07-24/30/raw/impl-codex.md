===BEGIN-REVIEW===
Verdict: FIX-FIRST

1. [MAJOR] Offer application is not actually confined to a pending human offer. src/mediator.py:710-718 applies any non-None Offer without checking is_week_boundary_pending or membership in current_offers; src/mediator.py:725-743 then grants NEW_LINE. Although the normal UI safely passes current_offers[index] at src/app_controller.py:331-352, the public mediator exposed at src/env.py:21 accepts a fabricated NEW_LINE in a headless game with no calendar or offers, and also accepts NEW_LINE when a genuine boundary offered different kinds. That bypasses the weekly economy and refutes the stronger “RL/headless never grant” claim. test/test_gm10d_line.py:98-106 even calls resolve_week_boundary with no pending boundary, so no test rejects this path. A non-None choice must require a pending boundary and a currently offered value.

2. [MAJOR] MUTATION-WEAK: the important “at or above cap” guard is not pinned. The implementation at src/progression.py:103-106 correctly uses >=, but test/test_gm10d_line.py:50-58 only reaches exactly num_paths. Replacing >= with == leaves every GM-10d test green. This is material because src/save_schema.py:159-162 accepts purchasedNumPaths above numPaths when unlockedNumPaths is clamped, and src/save_load.py:113-114 restores that state; the mutant would grant again from such a valid loaded state. Also, deleting the cap entirely makes the while loop at test/test_gm10d_line.py:53 hang, although test_new_line_grant_at_the_cap_is_a_state_inert_noop fails at lines 98-106. Add a bounded above-cap regression.

3. [MINOR] MUTATION-WEAK: the claimed exact purchase-flow refresh does not pin the unlock blink. src/input_coordinator.py:63-73 starts the blink only when the recomputed unlock count exceeds the previous cached count. A mutant that eagerly updates NetworkProgression.unlocked_num_paths inside grant_free_path passes all GM-10d tests, leaves the count correct and button unlocked, but suppresses the blink. test/test_gm10d_line.py:69-81 checks only counts and is_locked; the generic blink test at test/test_mediator_progression.py:91-105 does not exercise a free-line grant.

4. [NIT] src/mediator.py:721-724 still states that every dispatch arm is a no-op and changes no game state, directly contradicting the NEW_LINE arm below it. The executable GM-10c inertness assertion is otherwise correctly narrowed at test/test_gm10c_choice.py:218-236; no other stale executable all-kinds-inert assertion remains.

Confirmed:
- Current cap and derived clamping are correct: src/progression.py:52-53, 96-106.
- Grant and purchase currently use the same refresh path, including cache, blink, and button locks: src/mediator.py:737-743 and src/input_coordinator.py:63-77, 91-105.
- Grants spend no credits: src/progression.py:90-106. Credit-spend mutants turn test_grant_unlocks_the_next_line_without_spending_credits red at test/test_gm10d_line.py:41-48 and the end-to-end choice test red at lines 69-76.
- Omitting cache refresh turns test_choosing_new_line_unlocks_a_line_and_refreshes_caches red at test/test_gm10d_line.py:69-81; omitting only lock refresh fails lines 80-81.
- Making the NEW_LINE arm inert fails that same end-to-end test. Making any stub grant fails test_the_other_offer_kinds_still_grant_nothing at test/test_gm10d_line.py:110-117 and the broader inertness test at test/test_gm10c_choice.py:218-236.
- Continue storage is sound: src/save_game.py:260-264 already writes credits, purchased, unlocked, and total paths; src/save_load.py:44-54 and 104-115 pins only total numPaths and restores purchased/unlocked. Existing checkpoints already contain these values at src/recursive_checkpoint.py:376 and 385-390. No save/checkpoint schema was changed.
- LOCOMOTIVE/CARRIAGE/TUNNEL remain no-ops at src/mediator.py:728-733. The at-cap wasted pick is explicitly documented at GAME_RULES.md:161 and ARCHITECTURE.md:384.
===END-REVIEW===
