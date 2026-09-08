# GM-05c implementation review - rendering and final integration

## Initial final-pass output

Found a reproducible GM-05c blocker: active handle motion over empty space crashes rendering. `PathHandleEdit.move_to` normalizes the pointer to a numeric tuple (`src/path_handles.py:180`), but `build_preview_visual_path` sends that tuple to `rendering.layout._position`, which only accepts `.left/.top` objects (`src/rendering/layout.py:63-64, 207-215`). Real repro: select route -> begin end handle -> MOUSEMOTION to empty point -> `GameRenderer.draw`; raises `AttributeError: 'tuple' object has no attribute 'left'` through `GameRenderer._draw_redraw_preview`/`NetworkRenderer.draw_preview`. Invalid-station previews have the same tuple path. Existing rendering test passes a `Point` directly and pixel test motions only to a valid shortening station, so the integration gap is untested. Severity P1 (normal desktop drag / PlayerPixel empty MOTION crashes).

## Disposition

Accepted. A real `PathHandleEdit` -> empty primitive position -> real `GameRenderer.draw` regression failed with the exact traceback before production changed. The layout boundary now accepts its own immutable two-float `Position` representation. Focused rendering, input, pixel, Ruff, the 719-test full suite, and the frozen differential pass after the fix.

## Preserved final rereview output

Final live rereview: CLEAN after the tuple-boundary fix. I verified `rendering.layout._position` now accepts the exact primitive `(float, float)` emitted by `PathHandleEdit.move_to`; the new regression builds a real `PathHandleEdit`, moves it to an empty primitive position, and draws through real `GameRenderer`. The original real-mediator reproduction now prints `RENDER_OK`. I also adversarially rendered 63 fresh real-Mediator cases across every linear/loop handle kind/slot, with empty-space motion plus every active station target (valid, neutral, shortening, and invalid); all rendered without exception. Rechecked input cleanup/one-hook ordering, exact identity/staleness validation, endpoint/insert/loop slot rules, game-over and outside-release cleanup, painter/cache/reference boundaries, and unchanged checkpoint/action/protocol modules. No remaining actionable finding.

The external multi-CLI path remained unavailable at the established repository-export authorization boundary. This is compensating in-process evidence and does not claim external approval.
