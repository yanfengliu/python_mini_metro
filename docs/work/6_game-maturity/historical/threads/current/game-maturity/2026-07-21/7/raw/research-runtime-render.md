# GM-06c runtime and rendering research

Read-only live-code audit; no files were edited by the research lane.

- The accepted GM-06c scope is carriage entities, capacity, attachment, rendering, stop timing, observations, and checkpoints. GM-06d retains occupied-locomotive return, cancellation/recovery, and destructive line-removal rider hardening.
- There is no Carriage entity. `Metro` is one `Holder` with fixed capacity six, one passenger list, and no composition field. `Holder.has_room()` and passenger transfer use that scalar.
- Both passenger-flow stop setup seams charge dwell for every boarding candidate, while actual boarding stops at `metro.has_room()`. A full six-seat train facing twelve candidates can therefore schedule phantom dwell.
- Increasing `Metro.capacity` alone is visually invalid: `Metro.draw()` packs all riders into one fixed 60x30 body. `GameRenderer` projects and draws one pose per Metro, and interpolation snapshots contain only the head pose/direction/stop state.
- Structured observations expose Metro ownership/passengers/queue and locomotive-only fleet totals. Arrays have positions/path indices but no capacity/composition. Checkpoint v3 has aggregate `metroMotion[].capacity` but no carriage identity or attachment order.
- Existing plus/minus controls are path-slot-bound and low-level-pixel reachable. Structured fleet dispatch is isolated in `fleet_input.py`, so carriage actions need not grow the near-limit InputCoordinator.
- Recommended canonical model is attached-only `Carriage` identities in `Metro.carriages`, no mutable global pool, total `Mediator.num_carriages`, and derived assigned/available counts. Metro remains the sole passenger holder and capacity is derived from base plus attachments.
- Recommended path-level targeting is balanced attach and deterministic reverse-order capacity-safe detach. Empty locomotive return should carry and refund the whole consist by canonical owner removal. Queued locomotives should reject composition changes.
- Carriage state changes future capacity, pixels, dwell, and action results, so it requires checkpoint v4 and recursive/agent v5 while preserving older versions explicitly.
- Before production edits, freeze checkpoint-v3 output at 16,262 canonical bytes and SHA-256 `9ca2f5bce174a8c59c608cb08bc3e5903151ab0ad04df6553c21f166bed63c02`, plus the current recursive-v4 default at 1,608 bytes and SHA-256 `807429bf99283a79341c1e78d4984880ec53deaccab1d5bc36ec2b4cf9610cee`, under explicit LF attributes.
- File-size risks are PassengerFlow 494, GameRenderer 495, InputCoordinator 492, path_replacement.py 495, and recursive_checkpoint.py 462 physical lines. New focused modules are required.
