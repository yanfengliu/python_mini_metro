CLEAN.

Compared all 16 extracted methods and Mediator wrappers against `2c4cd4f`. No semantic drift found in evaluation order, late rebinding, exception partial state, callable lifetime, graph freshness, generator finalization, or live-list mutation.

Evidence:

- Public signatures remain exact.
- Globals/router/progression collaborators resolve at baseline timing.
- Three graph phases remain independent and ordered.
- `PassengerFlow` is stateless and dependency-light.
- Protocol/training inputs are unchanged; content fingerprint includes the new runtime file.
- Focused direct/facade/effect/simulation/route-lifetime tests: 59/59 passed.
- Sizes: `passenger_flow.py` 448 lines; `mediator.py` 735 lines.
- Review was read-only.
