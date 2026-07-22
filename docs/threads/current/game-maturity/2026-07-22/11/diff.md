# GM-07c atomic autosave, Continue, and menu integration diff ledger

Status: implementation review-clean; local gates green; Commit A staging active

## Implemented production surface

- `src/app_controller.py`: two optional inert seams — `build_from(mediator)` (wraps a loaded Mediator like `build_game`) and an `autosave` object (`save`/`delete`/`peek`/`load`) — a public `notice` attribute cleared on state change, autosave on menu entry (after the menu hold) and on `exit_to_title` before the menu release, autosave delete at the game-over promotion and its exit sites, and Continue via `peek` → `load` (catching `(ValueError, OSError)`, notice on failure) → `release_pause_reason("menu")` → `build_from` → PLAYING; a seam-less controller is behaviorally identical to pre-GM-07c.
- `src/main.py`: module-level `AUTOSAVE_PATH` and patchable `write_autosave`/`delete_autosave`/`peek_autosave`/`load_autosave`, a `build_from` closure, the autosave seam, the state-gated `pygame.QUIT` branch (delete when `is_game_over`, save from `PAUSE_MENU` or un-over `PLAYING`, else neither), and the live title Continue button plus notice draw.
- `src/ui/menu_screens.py`: a three-button `title_layout` (`continue` between new_game and exit), `draw_title_screen(surface, continue_available=False)`, a public byte-stable `draw_notice`, and a font-cache staleness fix.
- No schema, observation, action, checkpoint, protocol, or frozen-artifact change; the GM-07b save API and its isolation guard are untouched.

## Implemented evidence surface

- Reconcile GM-07b Commit A run `29941339839` and Commit B run `29941743007`, and the two owner/session out-of-scope fixes now on `origin/main` (`9a33aaf` GM-07b:C checkpoint stale-cache acceptance, `5522da2` GM-03f verifier retirement); record D-027 (single-slot autosave at quiescent boundaries, delete on game over, Continue reconciliation) in the parent decision log.
- Research lane; combined adversarial plan review (one blocker + six findings) folded; a self-verified narrow recheck (independent lane interrupted by a model limit); a 25-record red baseline with zero collateral; and one combined implementation-review lane (CLEAN) with real probes and a windowed run — all preserved under `raw/`.
- Update `README.md` (Continue/autosave, save location), `GAME_RULES.md` (autosave/Continue/game-over-deletes line), `ARCHITECTURE.md` (autosave seam + Continue note), and `PROGRESS.md`.

Local gates: four GM-07c modules 25/25; full py313 suite 1173/0 with 12 expected skips; guarded `npm test` 249/0; Ruff and per-file pre-commit clean; budgets held. Commit A rebases onto `origin/main`, re-verifies, then pushes; evidence-only Commit B follows the exact remote workflow.
