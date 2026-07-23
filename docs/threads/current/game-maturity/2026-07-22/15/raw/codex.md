Two major correctness issues found. No files were modified.

### Findings

- **MAJOR** — [src/settings.py:74](/C:/Users/38909/Documents/github/python_mini_metro/src/settings.py:74), [save_schema_records.py:115](/C:/Users/38909/Documents/github/python_mini_metro/src/save_schema_records.py:115) — `validate_settings` can leak `TypeError`. An otherwise-valid dict with unknown keys `1` and `None` reaches `_exact_keys`, whose `sorted()` cannot compare them. Fix: reject non-string keys with `ValueError` before `_exact_keys`; add a mixed-key regression.

- **MAJOR** — [game_renderer.py:297](/C:/Users/38909/Documents/github/python_mini_metro/src/rendering/game_renderer.py:297), [carriage.py:48](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/carriage.py:48), [carriage.py:115](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/carriage.py:115) — Reduced motion misses passengers rendered in carriages. The dispatcher correctly filters `reduced_motion` from `Carriage.draw`, which then calls `Passenger.draw` without another carrier. A schema-valid loaded save can contain seven onboard riders, one carriage, and warning-age `waitMs`; riders 1–6 stay visible while rider 7 still blinks. Fix while preserving the no-carriage-kwarg contract: under reduced motion, pass `passenger_max_wait_time_ms=None` to non-Metro consist bodies. Add a valid-load seven-rider regression.

- **MINOR** — [src/settings.py:159](/C:/Users/38909/Documents/github/python_mini_metro/src/settings.py:159) — The known `mkstemp` fd-ownership gap is copied here. If `os.fdopen` raises, the raw descriptor is never closed; Windows can then reject the cleanup unlink, leak the `.tmp`, and mask the original exception. Fix with an explicit descriptor-ownership guard.

- **MINOR** — [menu_screens.py:241](/C:/Users/38909/Documents/github/python_mini_metro/src/ui/menu_screens.py:241), [PLAN.md:22](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-22/13/PLAN.md:22) — Volume rows look functional but are not labeled stored-only. Setting Master Volume to 0% does not mute anything. Add an “audio coming soon”/“stored only” note as required by the plan.

- **MINOR** — [test_gm08a_settings_render.py:57](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm08a_settings_render.py:57), [test_gm07b_save_determinism.py:29](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07b_save_determinism.py:29) — Required guards are incomplete: no PathButton case, no full-renderer/carriage propagation, no off-phase implicit-default comparison, suppression is tested only by inequality, and no GM-08a test pins `"settings"` membership in the isolation set. These gaps allowed the carriage defect through. Add exact pixel/reference and explicit isolation-membership tests.

- **MINOR** — [DECISIONS.md:185](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md:185), [PLAN.md:39](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-22/13/PLAN.md:39) — Binding text says the snap blip is held steady, while the revised design and implementation suppress it. Harmonize this to “warning/unlock blinks held visible; snap blips suppressed.”

- **MINOR** — [ARCHITECTURE.md:72](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:72), [ARCHITECTURE.md:374](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:374), [ARCHITECTURE.md:420](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:420) — The tree omits both new modules, the primary state-machine description omits `SETTINGS` and still describes three-button menus, and the line-count note still says `GameRenderer` is 494 lines rather than 478. Update these surfaces. Also qualify “imports no gameplay” as “no direct gameplay imports”; the shared save validators load gameplay/checkpoint dependencies transitively.

### Sound

- Bool/int/range/version checks otherwise work; duplicate JSON keys, BOM/non-ASCII, malformed/deep JSON, and unreadable files fall back to the exact `DEFAULT_SETTINGS`.
- Save validation occurs before filesystem writes; canonical output is sorted ASCII with one LF, and ordinary `os.replace` failure preserves the prior file.
- Default-`False` built-in render predicates preserve historical pixel behavior. Warning/unlock indicators are held visible and snap rings are suppressed.
- `flexible_draw` preserves the extracted dispatch/cache behavior and has no live import cycle; unsupported kwargs are filtered from built-in carriage and speed/control draws.
- Fullscreen startup, change gating, `FULLSCREEN | SCALED`, surface reassignment, first-frame application, viewport recomputation, and letterboxing are correct.
- SETTINGS origin, pause hold, exactly-once seam save, seam-less edits, and `advance(0)` freezing are correct.
- Named headless/RL surfaces import no settings module; no forbidden simulation/schema/frozen files changed. All touched renderer/entity files remain below 500 lines.

VERDICT: NOT CLEAN
