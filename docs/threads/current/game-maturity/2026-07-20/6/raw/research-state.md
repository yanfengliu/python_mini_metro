# GM-06b state, checkpoint, and replay research

Result: queue intent is future-affecting state and must be checkpoint-visible; existing recursive and agent action payloads are generic JSON, while the PlayerPixel pointer protocol need not change.

- Keep queued locomotives in path/global assigned collections until safe completion. Force stops and block boarding through existing Mediator passenger-flow seams, then settle after passenger movement.
- Expose pending state per structured Metro and keep total/assigned/available meanings unchanged. Avoid a redundant array unless an equality oracle justifies it.
- Preserve exact identity on direct safe movement between collections and roll back list objects/contents, route fields, and request state on failure. Reject or keep pending on malformed ownership instead of losing a rider/resource.
- Existing canonical v1/v2 checkpoint generation, recursive v1-v3, and agent-play v1-v3 require a declared compatibility boundary. Index selectors are appropriate for fresh-process replay because public entity IDs are session-unique.
- Update the positive-delivery demonstrator to use the real visible assignment control; otherwise route creation becomes unserved and RL smoke loses its delivery proof.
- Required regression matrix includes queued/no-queued checkpoint distinction, input immutability, legacy/current versions, index-selected fresh-process replay, reused mutable action copies, malformed/repeated/terminal zero effects, replacement/removal/over-cap identity, and real fast/fidelity manual assignment/removal.

This lane proposed conditionally adding queue intent to existing checkpoint versions because inactive old bytes could be preserved. The parent plan's stricter invariant says adding a persisted field is not backward compatible by accident; the candidate plan therefore escalates to explicit new versions and retains this proposal as reviewed dissent.

No files were edited by this research lane.
