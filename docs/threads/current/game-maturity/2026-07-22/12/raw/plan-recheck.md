# GM-07d plan narrow recheck — disposition

Self-verified by the implementing session (the run of independent-lane subagents is being paced against model-quota limits already hit this session; the substantive combined plan review at `raw/plan-review-combined.md` was independent and is the primary gate). All nine folded findings verified internally consistent against the plan text and live-code anchors:

- MAJOR-1 (existing gm07c window-close test edit) is now a named REQUIRED contract edit in step 2, with the patch targets (`main.record_highscore`, `main.HIGHSCORES_PATH`) specified.
- MAJOR-2 (broad `Exception` catch at both the load and the game-over record surfaces, matching the proven `write_autosave`) is folded in the load and main bullets; the "like the autosave writer" wording is corrected.
- MAJOR-3 (read `mediator.deliveries` only inside the `self._highscores is not None` guard) is pinned in the controller bullet.
- MAJOR-4 (inline the mkstemp->fsync->os.replace writer in `highscores.py`; do not claim to import a non-existent shared writer, do not touch the reviewed `save_game`) is pinned.
- MINOR-6 (rename `game_over_result` -> `last_highscore_result`) and MINOR-7 (unconditional reassign at the promotion) are folded consistently across the controller and main bullets.
- MINOR-5/MINOR-8 tension resolved: the two cannot both be literal because insertion order is itself history; the coherent pin is a canonical sort by (map asc, rules_version asc, deliveries desc) with exact ties broken by stable-over-append order, giving a document fully deterministic given the record sequence (which tests control) and a tie-with-best that ranks 2.
- MINOR-9 (forward-version overwrite) surfaced as an accepted cosmetic-stance consequence.

Cross-checks: the main bullet draws from `controller.last_highscore_result` gated on `state == GAME_OVER` and `is_best`, consistent with the controller's unconditional reassign; `game_renderer` remains untouched; the isolation scan gains `"highscores"`. No fresh contradiction. Ready for red tests.
