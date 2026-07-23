# GM-08b procedural-tone audio — implementation review synthesis

Two independent adversarial lanes reviewed the GM-08b implementation against the live code, plus a real headless-mixer smoke:

- **Plan review** (`raw/plan-review.md`): NOT CLEAN pre-code (2 majors + minors), all folded into `PLAN.md` before implementation.
- **Harness general-purpose lane** (`raw/harness-review.md`): NOT CLEAN — 1 MAJOR (mixer leak), empirically proven; everything else refuted; 3 NITs.
- **External Codex persistence/isolation lane** (`raw/codex.md`, `gpt-5.6-sol` ultra): NOT CLEAN — the SAME 1 MAJOR (independently confirmed) + 2 MINOR; the rest refuted.
- **End-to-end smoke** (`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`): real `ProceduralAudio` (all five sounds) threaded through the real loop for 4000 frames, no crash, `game_over` tone fires on the real promotion frame.

Both independent lanes converged on the same MAJOR — strong signal. All findings resolved below.

## Findings and dispositions

### MAJOR — real-mixer leak in unbounded run_game loop tests (both lanes, empirically proven) — FIXED
The `max_frames` gate (`_default_audio_backend`) was the wrong enforcement seam: the pre-existing gm07c/gm07d/gm07e loop drivers run REAL `run_game` **unbounded** (`max_frames=None`, terminating via QUIT→SystemExit) and patch only `main.pygame`. Because `audio.py` imports its OWN `pygame`, `create_audio()` opened a real `audio.pygame.mixer` — the harness proved `mixer.get_init()` went `None → (44100,-16,2)` and stayed open for the process. This violates suite hermeticity on any audio-capable host (the user's Windows dev box + Windows CI).

**Fix (structural, stronger than the reviewers' per-driver patch):** `run_game` now defaults `audio_backend` to `NullAudio()` **always**; the real backend is opted into ONLY at the `__main__` entry point via `_default_audio_backend(max_frames)`. No programmatic caller — test or embedder, bounded or unbounded — can open a mixer, by construction. Verified: a new `test_unbounded_run_game_never_constructs_a_mixer` (exits the loop right after setup and asserts `create_audio` never ran) plus an out-of-band empirical check that `audio.pygame.mixer.get_init()` stays `None` after a real unbounded `run_game`. The `main.py` comments (harness NIT-1) were corrected in the same change.

### MINOR — tones generated at the hardcoded 44.1 kHz even when the live mixer negotiated another rate (Codex; relates to harness NIT-3) — FIXED
`ProceduralAudio` read `get_init()[2]` (channels) but not `[0]` (rate); since `pygame.init()` may pre-open the mixer, `create_audio`'s requested frequency can be a no-op and a 48 kHz mixer would detune the 880 Hz tone to ~957 Hz. **Fix:** `_generate_tone` takes `sample_rate` and `ProceduralAudio` reads the real `get_init()[0]`. Pinned by `test_generate_tone_length_tracks_sample_rate` and a real-rate assertion in the dummy-driver test (the delivery sound's sample count equals `int(get_init()[0] * 90ms/1000)`).

### MINOR — a purchase in the SAME event batch as Continue misses its tone (Codex) — DOCUMENTED as inherent best-effort
`_audio_step` re-baselines the snapshot to the CURRENT (post-batch) mediator on a session swap — which is exactly what prevents the MAJOR-1 spurious burst. The accepted price is that a gameplay mutation in the same ~16 ms event batch as the session swap is absorbed into the baseline and its tone missed. This is unreachable in human play (a line purchase clicked in the same frame as Continue) and analogous to the already-accepted best-effort snap semantics. Documented at the `_audio_step` source and in Acceptance; no code change (resetting to zero instead would reintroduce the burst).

### NIT-2 — reduced_motion suppresses the visual snap blip but the snap tone still plays — KEPT, documented
`reduced_motion` is a visual-motion accessibility setting; audio is governed by `sfx_volume`/`master_volume`. Coupling the two would bind audio to a visual flag; a user wanting silence sets the SFX volume to 0. Left independent by design.

## Refuted (survived both lanes)
Session-reset burst avoidance (Continue/New Game/Restart), stereo `make_sound` shaping, `src/` isolation (audio imported only by `main`, unreachable from `rendering`/RL, named in both scans), tone determinism + int16 safety, the `game_over` one-shot post-reconcile edge, counter monotonicity, and every raise-into-loop path (`getattr`-tolerant `snapshot_of`, guarded `_snap_sum`, best-effort `play`, always-present `Settings`).

## Result
NOT CLEAN → all findings fixed or dispositioned; full py313 suite green (12 skips), both isolation scans green, guarded `npm test` pending, budgets held (audio.py 196, main.py 393). Ready for CI-gated delivery.
