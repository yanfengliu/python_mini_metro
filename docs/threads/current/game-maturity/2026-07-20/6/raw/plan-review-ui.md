# GM-06b controls and PlayerPixel plan review - first pass

Status: `NOT CLEAN`

1. `HIGH` - FleetButton release ownership is not specified across the current gesture branches. Pin direct click, bare mouse-up, down on one control/up on another, assigned PathButton down followed by zero-station fleet-control up, and handle/full-redraw release over a fleet control. Also define cleanup when the facade rejects or raises.

2. `HIGH` - Minus state is ambiguous when one metro is queued and another remains eligible. Define enabled/disabled/hover/queued priority after multiple queues, immediate detach, and a queued-only state, and derive mutation and display from one eligibility predicate.

3. `MEDIUM` - Registered-profile reachability needs the real canonical quantization round trip. For every plus/minus control and both profiles, require the canonical center to map through action coordinates back inside that control and outside siblings/path/stations, plus discriminating pixels after scaling.

4. `MEDIUM` - The plan needs an InputCoordinator extraction boundary and exact physical-line gates rather than compact opaque branches.

5. `MEDIUM` - Demonstrator coordinate ownership is unresolved. Resolve the currently rebound real plus control through the existing explicit privileged-oracle boundary, quantize for the active profile, click it through down/up, and update the action-sequence assertions without duplicating layout arithmetic or exposing PlayerPixel info.

Evidence inspected: `src/input_coordinator.py:161-331,409-475`, `test/test_gm05c_handle_input.py:279-340`, `src/rl/player_env.py:226-275`, `src/rl/protocol.py:191-217`, `src/rl/demonstrator.py:68-76,132-166`, `src/rl/privileged_oracle.py:17-70`, and the candidate iteration-6 plan.
