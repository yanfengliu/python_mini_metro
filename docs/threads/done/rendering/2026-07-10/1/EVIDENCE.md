# Rendering evidence

`before.png` and `after.png` use the same deterministic 1920x1080 comparison scene: square station `(470, 266)`, circle station `(640, 425)`, square station `(768, 930)`, green and magenta lines over the ordered three-station route, one metro on each line at `(720, 829)` and `(557, 350)`, one passenger icon at each station, score zero, and two unlocked/assigned line controls. The before frame uses the former direct entity renderer; the after frame uses `GameRenderer` with the immutable visual-lane layout and refreshed style.

The after frame is also covered mechanically: repeated software-surface frames must have identical RGBA bytes and unchanged explicit/canonical state, and a fresh dummy-SDL subprocess must render twice without a display mode or any model/entity UUID allocation.
