===BEGIN-REVIEW===
VERDICT: FIX-FIRST

1. [MAJOR] Release ordering is MUTATION-WEAK. Production correctly applies, clears, then releases at src/mediator.py:715-718. However, test/test_gm10c_choice.py:152-179 observes offers during apply and only checks the final pause state. A release-before-apply mutant passes all GM-10c tests, violating the promised apply → clear → release ordering and exposing future/throwing effects to an already-released boundary.

2. [MAJOR] The state-inertness test is not a per-offer or full-runtime-state lock. test/test_gm10c_choice.py:194-206 applies all four kinds to one mediator, then takes one final snapshot. Compensating mutations can cancel, while nonserialized mutations such as changing current_offers or week_calendar are omitted by both _INERT_ATTRS at test/test_gm10c_choice.py:35-47 and serialize_game at src/save_game.py:244-293. Mutation probes confirmed these state-changing implementations remain green.

3. [MAJOR] Render tests do not bind each displayed label to its corresponding offer and exercise only two offers. test/test_gm10c_choice.py:228-255 checks painted regions, aggregate glyph pixels, two-rect disjointness, and repeat stability. Swapping labels—or painting offer 0’s label on every button—passes while clicks still dispatch by index at src/app_controller.py:350-352, causing the displayed choice to differ from the selected effect. Dropping, overlapping, or moving offer_2/offer_3 also survives because counts 3 and 4 are never rendered in these tests.

4. [MAJOR] The arming test does not prove that a mismatched release disarms. Production clears the arm before checking the release target at src/app_controller.py:342-345. test/test_gm10c_choice.py:135-140 stops after the first mismatched release. Moving the clear after the match guard passes every selection test, yet down offer_0 → up offer_1 → later up offer_0 incorrectly chooses offer_0.

5. [MINOR] Current documentation remains contradictory. GAME_RULES.md:160 still instructs players to click Continue and says choice arrives later, while line 161 correctly describes selectable offers. src/main.py:332-334 still says “there is no choice yet.” README.md:69 says the pick is “recorded,” but the real mediator stores no applied choice and clears current_offers after the no-op dispatch; applied-offer persistence remains deferred.

Confirmed:

- Normal live routing is correct: offers remain frozen while the modal is active, matching down/up selects current_offers[index], and a bare gameplay release cannot choose.
- All offer_menu_layout, draw_offer_screen, and resolve_week_boundary call sites have compatible arity. The window-close path still performs the no-argument forced resolve, and the GM-10a run-loop harness works.
- _apply_offer covers all four current OfferKind values, all arms are genuine no-ops, and an unknown kind raises the named ValueError. No GM-10d–g effect or GM-10h persistence leaked into production.
- The live 0–4 layouts are on-screen, disjoint, and byte-stable at 1920×1080. Button tops are 540, 622, 704, and 786 with 64-pixel height; count 0 yields no buttons.
- Wrong-index routing turns test_arming_an_offer_button_chooses_that_offer red. Dropping the arm-match check turns test_arming_one_button_and_releasing_on_another_does_not_choose red. Unknown-kind no-raise turns test_apply_offer_rejects_an_unknown_kind red. Clear-before-apply turns test_apply_runs_before_clear red. Dropping either of the two currently tested buttons turns test_each_offer_renders_a_button_at_its_rect red; third/fourth-button loss survives as noted above.
- All 57 focused GM-10a/b/c tests pass on the refreshed live worktree.
===END-REVIEW===
