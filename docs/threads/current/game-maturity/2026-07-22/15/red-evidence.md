# GM-08a red evidence

Captured against the pre-GM-08a baseline (`60f59c0`). Red tests first, per the plan:

- `test/test_gm08a_settings.py`: strict schema validation (exact keys/types, forward-version and duplicate-key rejection, strict-bool via `_bool`, volume range/non-int via `_percent_int`), `Settings`<->document roundtrip and defaults, `load_settings` FAIL-SAFE-TO-DEFAULTS on missing/corrupt/forward-version/deep-nested and strict-accept on valid, `save_settings` validate-before-write plus atomic interrupted-write preservation.
- `test/test_gm08a_settings_controller.py`: SETTINGS navigation (title/pause->settings->back, pause `menu` hold preserved across the round trip), each control edits `current_settings` and persists exactly once, and the seam-less regression guard (updates memory, never persists, never crashes).
- `test/test_gm08a_settings_render.py`: reduced-motion gating (passenger-warning and station/path-button unlock blinks held visible, snap blip suppressed, default-`False` byte-identical incl. the off-phase skip branch), `draw_settings_menu` byte-stable and value-reflecting, and the GM-08a-owned isolation membership.
- `test/test_gm08a_settings_main.py`: fullscreen `set_mode`-only-on-change with window-surface reassignment and reduced_motion threading into `renderer.draw`.

Required existing-test edits (product-driven contract updates): `test_main.py` (set_mode-once insulated by patching `main.read_settings` to `DEFAULT_SETTINGS`, plus `reduced_motion=False` in the renderer draw assertion), `test_station.py` (`reduced_motion=False` pinned in the three passenger-draw assertions), `test_gm07a_run_game_loop.py` (the recording-renderer double accepts `reduced_motion`), and `test_gm07b_save_determinism.py` (`SAVE_MODULE_NAMES += "settings"`).

Fold red tests (from the external Codex persistence lane): a non-string-key `ValueError` (not `TypeError`) test, a carriage-rider-held-visible test through the `_call_flexibly` dispatch, and an `os.fdopen`-failure fd-guard fault-injection test.

Every failure at the baseline was a clean assertion via the `require_attribute` idiom or a missing product symbol; zero collateral beyond the intended GM-07a/07b/07c/main contract edits.
