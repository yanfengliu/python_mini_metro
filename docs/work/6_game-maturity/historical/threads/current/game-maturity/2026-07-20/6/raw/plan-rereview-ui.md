# GM-06b controls and PlayerPixel plan re-review

Status: `CLEAN`

The reviewer reread the revised iteration-6 plan/review, first-pass UI review, parent GM-06 scope/state/evidence, and live input, handle, button, renderer, PlayerPixel/protocol, privileged-oracle, demonstrator, and regression-test code. Red tests can be written without guessing.

- Release ownership is exact for direct, bare-up, cross-control, zero-station redraw, captured-handle, and nonempty-redraw cases; fleet release has `finally` cleanup, false/raise behavior, exception propagation, and no path deletion/redraw.
- Multi-queue styling is deterministic: one shared eligibility query owns mutation/presentation, the badge is orthogonal, enabled/disabled/hover priority is selected, and immediate detachment recomputes synchronously.
- Every real control must satisfy the exact canonical-to-profile-to-canonical inside-self/outside-sibling-parent-station invariant for fast and fidelity, plus discriminating non-cursor scaled CHW pixels.
- Fleet controls retain only PathButton association, resolve the rebound path at release, join `buttons` for station-first precedence and handle obstacles, and make locked/empty slots fail closed.
- The demonstrator has one authoritative UUID-free path-indexed coordinate source from currently rebound real controls behind `PrivilegedSnapshot`, active-profile quantization, and ordinary DOWN/UP only; PlayerPixel info/action protocol stay untouched.
- `fleet_input.py` is a sufficient narrow extraction. The plan pins sub-500 counts for InputCoordinator, GameRenderer, and every other changed handwritten production file, with only the existing Mediator below the 1,000 hard ceiling.

No substantive controls, rendering, Pixel, demonstrator, cache, purity, or file-boundary finding remains.
