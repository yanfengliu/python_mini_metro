# GM-08b procedural-tone gameplay audio diff ledger

Status: delivered as Commit A `884c9dd` (clean fast-forward onto `origin/main` at `5917ef8`), exact [run 29979620418](https://github.com/yanfengliu/python_mini_metro/actions/runs/29979620418) green (`build` `89118544138`, `rl-smoke` `89118544167`); evidence-only Commit B `[GM-08b:B]` active. Both adversarial lanes' MAJOR (mixer leak) and Codex's two MINORs resolved.

## Implemented production surface

- `src/audio.py` (new, 196): the main-only procedural-tone SFX backend (D-030), importing only `pygame`/`numpy` (holds all its own constants; never `config`).
  - `_generate_tone(frequency_hz, duration_ms, sample_rate=_SAMPLE_RATE)`: a deterministic MONO int16 sine with a short linear attack/decay envelope; byte-stable and bounded to `[-16383, 16383]`. The rate is a PARAMETER (review MINOR) so the pitch/duration stay correct against the mixer's real rate.
  - `_shape_for_mixer(mono, channels)`: duplicates the mono column to the mixer's channel count (a stereo mixer needs `(n, channels)` for `make_sound`; review MAJOR-2).
  - `ProceduralAudio`: reads the ACTUAL negotiated `(rate, channels)` from `pygame.mixer.get_init()` (review MINOR/NIT-3 — `pygame.init()` may pre-open the mixer), builds one `Sound` per event, and `play(event, master, sfx)` sets volume `(master/100)*(sfx/100)` and plays best-effort (guards a `None` channel, swallows any play error).
  - `NullAudio`: inert no-op backend.
  - `create_audio()`: `mixer.init` + ALL sound builds in one `try/except` → `NullAudio` on any failure (mixer.quit on failure); never raises.
  - `snapshot_of(host)` / `diff_and_play(host, snapshot, backend, master, sfx)`: a PURE, duck-typed, TOLERANT counter differ (a host missing counters reads 0/False, so a cosmetic side-effect never crashes the loop). Plays one tone per newly-occurred `deliveries`/`unlocked_num_paths`/`unlocked_num_stations`/`is_game_over` (False→True edge)/snap-sum delta.
- `src/main.py`: `_default_audio_backend(max_frames)` (the sole real-audio opt-in, used ONLY by `__main__`); `_audio_step(controller, state, previous_audio_session, snapshot, backend)` (owns its OWN session ref, re-baselines on session change to kill the Continue burst, plays only on PLAYING/PAUSE_MENU/GAME_OVER at the live SFX volumes); an `audio_backend=None` seam on `run_game` that DEFAULTS TO `NullAudio()` (review MAJOR — the mixer-free guarantee is structural, not a max_frames gate); backend + `previous_audio_session` + `audio_snapshot` init; and the per-frame `_audio_step` call right after `reconcile_game_over()` reading the post-reconcile `state`. `__main__` opts into real audio via `_default_audio_backend(max_frames)`.
- No `Mediator`/`GameSession`/`rendering`/`config` change; no schema/observation/checkpoint/frozen-artifact change; numpy is already a core dependency (no lockfile/audit change).

## Implemented test/evidence surface

- `test/test_gm08b_audio.py` (new): tone determinism + int16 shape, rate-tracking length, `_shape_for_mixer` channel duplication, `create_audio` fail-safe → `NullAudio`, `NullAudio` no-op, the pure differ (flat/each-event/game-over-edge/advancing-snapshot), snapshot tolerance of a counterless host, and a REAL `SDL_AUDIODRIVER=dummy` `ProceduralAudio` building all five sounds + playing + generating against `get_init()[0]`.
- `test/test_gm08b_audio_main.py` (new): `_default_audio_backend` (real create_audio only for `max_frames is None`), `_audio_step` (session-change reset with no burst, same-session delta at live volumes, silent off-gameplay, audible on pause/game-over), and run_game wiring — bounded AND unbounded runs construct no mixer (the exact review-MAJOR scenario), plus per-frame consumer invocation with the injected backend.
- `test/test_gm07b_save_determinism.py` + `test/test_gm08a_settings_render.py`: both isolation scans now forbid `audio` (SAVE_MODULE_NAMES gains `"audio"`; the GM-08a mirror generalized to `{"settings","audio"}`); drifted comments corrected (review MINOR-5).
- `DECISIONS.md` D-030 recorded and reconciled with the review outcomes; thread artifacts (`PLAN.md`, `REVIEW.md`, `raw/plan-review.md`, `raw/harness-review.md`, `raw/codex.md`) preserved.
- Docs: `README.md`, `GAME_RULES.md`, `ARCHITECTURE.md`, `PROGRESS.md`.

Local gates: the GM-08b modules + affected gm07c/d/e loop tests green; full py313 suite green with 12 expected skips; both isolation scans green; end-to-end dummy-driver smoke green; empirical mixer-leak check green (`get_init()` stays `None`); Ruff + per-file pre-commit clean; audio.py 196 / main.py 393 (< 500). Commit A rebases onto `origin/main`, re-verifies, guarded `npm test`, then pushes; evidence-only Commit B follows the exact remote workflow.
