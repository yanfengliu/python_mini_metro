- CONFIRMED — MAJOR: the mixer-free test/headless gate is false. [main.py](C:/Users/38909/Documents/github/python_mini_metro/src/main.py:183) calls `pygame.init()` before selecting `NullAudio` at line 241; a live dummy-driver probe changed `mixer.get_init()` from `None` to `(44100, -16, 2)`. Additionally, legacy tests patch only `main.pygame` and call unbounded `run_game()`—for example [test_gm07a_app_controller.py](C:/Users/38909/Documents/github/python_mini_metro/test/test_gm07a_app_controller.py:195)—so [audio.py](C:/Users/38909/Documents/github/python_mini_metro/src/audio.py:117) still initializes its real pygame mixer. Instrumenting that existing test recorded one real `mixer.init` call. The GM-07e eventless-game-over test can consequently emit the 320 ms tone and leave the successful mixer initialized.

- CONFIRMED — MINOR: same-batch input after Continue loses legitimate SFX. [main.py](C:/Users/38909/Documents/github/python_mini_metro/src/main.py:267) drains the entire event batch before `_audio_step`; Continue swaps sessions immediately in [app_controller.py](C:/Users/38909/Documents/github/python_mini_metro/src/app_controller.py:173). The reset at [main.py](C:/Users/38909/Documents/github/python_mini_metro/src/main.py:84) therefore snapshots any later new-session mutations in that batch. Live reproduction: Continue a loaded run with 90 credits, then queue a locked-line `MOUSE_UP` in the same batch. The purchase completed (`credits=0`, `unlocked_num_paths=2`) but `played=[]`.

- CONFIRMED — MINOR: tones are generated for 44.1 kHz even when the live mixer is not. [audio.py](C:/Users/38909/Documents/github/python_mini_metro/src/audio.py:30) hardcodes the sample rate, while `ProceduralAudio` reads only `get_init()[2]`—the channel count—at line 88. With an already initialized 48 kHz mixer, `create_audio()` remained real but the nominal 880 Hz/90 ms delivery tone became approximately 957.8 Hz/82.69 ms.

Refuted:

- The ordinary Continue burst is fixed: render-loop and audio session references are independent, and reset precedes diffing. `reconcile_game_over()` does not swap sessions.
- Stereo shaping is correct; every tone is expanded to the reported channel count before `make_sound`.
- Current env/agent/recursive/RL/rendering imports remain audio-free. Both isolation scans name `audio`; their focused tests pass.
- Tone generation is fixed-input deterministic and bounded to `[-16383, 16383]` int16.
- Normal game over fires once on the post-reconcile false→true edge.
- Delivery/path/station counters are monotonic at the sampling boundary; failed removal restores them synchronously. Snap expiry cannot double-fire, though its documented best-effort differ may miss an expiry-balanced snap.
- Default settings, `all_stations=None`, and `Sound.set_volume`/`play` failures do not produce a live crash path.

Focused validation: 18 GM-08b tests and 2 isolation tests passed; the three probes above reproduce gaps those tests do not cover.

NOT CLEAN

Severity: 1 MAJOR mixer-isolation defect; 2 MINOR missed/incorrect-cue defects.
