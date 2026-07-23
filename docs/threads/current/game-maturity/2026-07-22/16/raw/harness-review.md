# GM-08b implementation review — harness general-purpose lane (verbatim)

Verdict: **NOT CLEAN** — one MAJOR isolation leak, empirically confirmed on this machine.

## MAJOR-A — Real mixer leaks into the unit suite via the pre-existing GM-07 loop tests (attack #3, confirmed)

**Files:** `src/main.py:241-242` + `src/audio.py:26,117-119`; triggered by `test/test_gm07c_run_game_loop.py:135`, `test/test_gm07d_run_game_loop.py:128`, `test/test_gm07e_game_over_reconcile.py:377-378` (caller `:429`).

**What GM-08b claims** (`src/main.py:68-73`): "a headless/max_frames run (and the whole suite) gets an inert NullAudio and opens no mixer." **This is false for part of the existing suite.**

**Reachable scenario (proven):** `run_game`'s audio gate is `create_audio() if max_frames is None else NullAudio()`. Several pre-existing loop tests drive the *real* `main.run_game` and terminate via a `pygame.QUIT` → `SystemExit`, so they legitimately pass **`max_frames=None`** and mock **only** `main.pygame`:

- `test_gm07c_run_game_loop.py`: `_drive_window_close` → `main.run_game(start_state=start_state)` (5 test methods).
- `test_gm07d_run_game_loop.py`: `main.run_game(start_state=start_state)`.
- `test_gm07e_game_over_reconcile.py`: the `max_frames is None` branch (`main.run_game(start_state=AppScreen.PLAYING)`), reached by `_drive(self, [[], [quit_event]], ...)` at `:429`.

None of them inject `audio_backend` nor patch `main.create_audio`. So `run_game` hits `_default_audio_backend(None)` → `create_audio()`, and because `audio.py` imports its **own** `pygame` (`src/audio.py:26`), `patch("main.pygame")` does **not** stop `audio.pygame.mixer.init(...)` (`src/audio.py:118`). This is exactly the trap flagged in the brief.

**Empirical proof** (py313, replicating `_drive_window_close`'s patch set exactly, `SDL_AUDIODRIVER` unset):
```
mixer.get_init() BEFORE run_game: None
audio.pygame is main.pygame (unpatched)? True
audio.pygame is main.pygame now (main.pygame mocked)? False
run_game exited via SystemExit (expected)
mixer.get_init() AFTER run_game: (44100, -16, 2)   <-- REAL stereo device left OPEN
```
Before GM-08b `run_game` made no `create_audio` call (and `pygame.init()` at `main.py:183` is the mocked `main.pygame`), so the suite opened nothing. GM-08b introduced this. There is **no** project `conftest.py` and no global `SDL_AUDIODRIVER=dummy`, so nothing mitigates it.

**Impact / why MAJOR (not a hard failure):** The tests still *pass* — `create_audio` fail-safes to `NullAudio` on a device-less runner, and the QUIT exits before the audio step. But on any audio-capable host — including the user's primary Windows 11 dev box and the AGENTS.md-mandated Windows CI `python -m unittest -v` gate — it opens a real audio device that stays initialized for the rest of the process (global pygame state leak, wasted `mixer.init` cost, environment-dependent test behavior). This directly violates the stated hermeticity invariant and is precisely the "real-mixer leakage" defect class the review targets. The `max_frames` gate is the wrong enforcement mechanism here because real-`run_game` tests legitimately use `max_frames=None`; the actual enforcement seam is `audio_backend` injection, which GM-08b added (`main.py:181,238-240`) but did not wire into the pre-existing loop drivers.

**Fix:** Inject the inert backend into those three loop drivers, e.g. `main.run_game(start_state=..., audio_backend=NullAudio())` (or add `patch("main.create_audio", return_value=NullAudio())` to each driver's `ExitStack`). One line per driver; uses the seam the design already provides.

## Claims tried and could NOT refute (the change is correct here)

- **MAJOR-1 session-change reset (Continue/New Game/Restart):** `diff_and_play` never runs before the reset — the reset lives entirely in `main._audio_step` (`main.py:84-86`) and executes *before* the gameplay-screen `diff_and_play` block (`:87-94`). The consumer owns `previous_audio_session`, independent of the render loop's `previous_session` (advanced at `main.py:309`, before the hook). On a session swap it re-baselines to the *live* (loaded) mediator, so the subsequent diff sees `current == baseline` → zero tones. `_continue_game`/`_start_new_game` reassign `mediator` and `session` together (`app_controller.py:169,186`). Not refutable.
- **MAJOR-2 stereo `make_sound`:** `ProceduralAudio.__init__` reads the real negotiated channel count (`get_init()[2]`) and `_shape_for_mixer` builds a C-contiguous `(n, channels)` int16 array. My repro opened a real `(44100, -16, 2)` mixer and `create_audio` returned a live `ProceduralAudio`, proving all five stereo `make_sound` calls succeed — no swallow-into-permanent-silence.
- **Isolation of `src/` (attack #4):** `audio` is imported by exactly one module — `main.py:8` (grep across all of `src/`). `rendering/game_renderer.py` does not import it, so `rl/player_env.py → rendering` never reaches audio. Both isolation scans name `"audio"`.
- **Determinism / int16 safety (attack #5):** `samples = wave·envelope·(0.5·32767)` bounds |sample| ≤ 16383.5 ≪ 32767, so `astype(np.int16)` never overflows/clips; deterministic within a build.
- **game_over one-shot edge (attack #6):** Fires only on `cur_over and not prev_over`; the snapshot advances each frame so it cannot refire; reconcile-then-audio ordering lets the promotion-frame tone through. Game-over state is never persisted, so a Continue-loaded mediator is never already-over.
- **Raise-into-loop (attack #7):** `snapshot_of` reads every counter via `getattr(..., default)`; `_snap_sum` guards `all_stations` with `or ()` and real `Station.snap_blips` is always a list. `ProceduralAudio.play` wraps `set_volume`+`play` in try/except. `controller.current_settings` is always a `Settings` dataclass.

## NITs (non-blocking)

- **NIT-1 (documentation accuracy):** The `main.py:68-73` comment ("the whole suite … opens no mixer") is factually wrong given MAJOR-A. Fix it in the same change.
- **NIT-2 (UX consistency):** `reduced_motion` suppresses the *visual* snap blip (`entity/station.py:111`) but the differ still counts `snap_blips` and plays the snap tone. Defensible (reduced-motion ≠ mute; users have `sfx_volume`), but the accessibility setting and the cosmetic click now diverge.
- **NIT-3 (redundant init):** In interactive runs `pygame.init()` (`main.py:183`) already initializes the mixer subsystem, so `create_audio`'s `pygame.mixer.init` is a second, no-op init. Harmless, but the mixer channel count (and rate) are really chosen by `pygame.init`'s defaults, not by `create_audio`.

**Verdict: NOT CLEAN** — MAJOR-A is a genuine, empirically-verified isolation defect. gm07a and the gm08a/gm08b/`test_main` loop tests are unaffected (they pass `max_frames`, yielding `NullAudio`).
