# Smooth rendering review

## Outcome

Approved after two fix/review iterations. Three independent in-process reviewers converged with no remaining important findings. The required external Codex and Claude commands were attempted, but restricted network access and the account usage limit prevented either service from returning review content; the exact limitation is retained in `raw/codex.md` and `raw/opus.md`. Codex CLI 0.144.1 met the pinned model's minimum version, while the required global upgrade was also blocked by the usage limit.

## Findings and dispositions

| Severity | Finding | Disposition |
|---|---|---|
| High | Geometry revisions replaced logical segments without preserving active metro references/positions. | Fixed. Rebuilds now rebind every metro, preserve normalized progress for in-transit metros, and snap stopped metros to their moved station. Mid-segment and stopped regressions pass. |
| High | Compatibility rendering constructed a new renderer/cache/resource set on every call. | Fixed. `Mediator` retains one lazy compatibility renderer; the GUI and future pixel environments own their explicit persistent renderer. Twenty warm compatibility frames took 0.0146 seconds in reviewer verification. |
| Medium | A paused sub-step remainder could become the first resumed simulation update. | Fixed. Pause/terminal consumption resets the accumulator; the 16 ms paused plus 1 ms resumed reproduction no longer advances simulation. |
| Medium | Compatibility rendering retained default-size hitboxes on arbitrary surfaces. | Fixed. The compatibility entrypoint prepares layout only when the target size changes and retains the same renderer. |
| Medium | Legacy `Path.draw(..., path_order)` ignored its ordering argument. | Fixed. It derives an immutable ordered visual lane and draws it without rebuilding logical segments or allocating line entities. |
| Medium | Per-entity `inspect.signature()` consumed about 1.24 ms/frame in the review fixture. | Fixed. Supported keyword contracts use a bounded 128-entry cache; reviewer re-profile recorded four misses and 1,196 hits over 100 frames. |
| Medium | Fresh-process headless/no-display/no-UUID acceptance was missing. | Fixed. `test/test_headless_render.py` starts a dummy-SDL subprocess, proves state-only construction initializes no render resources, renders repeatable pixels without a display mode, and fails on any model/entity UUID allocation. |
| Medium | Initial before/after captures used visibly different route/control state. | Fixed. `after.png` was recaptured with the same documented three-station, two-route, two-metro, two-control comparison scene; `EVIDENCE.md` records the fixture. |
| Low | Architecture/design named planned rather than implemented modules/classes. | Fixed. The tree includes `layout.py` and `test_headless_render.py`; design text names `NetworkRenderer`, `GameRenderer`, and `MetroInterpolator`. |

## Validation

- Python unit suite: 233/233 passed after all review fixes.
- Fresh-process headless render: passed without `display.set_mode` or identity allocation.
- Repeated real-surface rendering: byte-identical RGBA, unchanged canonical checkpoint, unchanged explicit render-facing mutable state.
- Rendered-every-update versus never-rendered scripted trajectories: identical canonical checkpoint.
- Route cache: one entry, one build across repeated unchanged frames.
- Warm benchmark: 300 cached 1920x1080 frames in 0.4051 seconds (~1.35 ms/frame) before the later signature-cache optimization.
- Visual after evidence SHA-256: `af98f801230703e3c91aa2acffcf32952031773c064d4a5a40f64d7d3a3209c7`.
