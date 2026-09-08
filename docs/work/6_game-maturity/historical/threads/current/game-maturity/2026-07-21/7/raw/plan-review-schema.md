NOT CLEAN.

1. P1 — Checkpoint v4’s canonical carriage wire shape is undefined. Raw observations contain process-local IDs, while checkpoints must remain UUID-free and index-based. Define exact normalized carriage fields, owner/reference index domains, structured/full-union prefix correspondence, and assert no Metro or Carriage ID appears in checkpoint bytes.

2. P1 — Legacy normalization could silently erase forward carriage state. Current v3 validation accepts unknown carriage fields; I confirmed a v3 checkpoint containing `carriages` and `limits.num_carriages` normalizes successfully. V1–v3 must explicitly reject every v4-only carriage field before zero-carriage synthesis.

3. P1 — No historical recursive-v4 or agent-v4 output oracle exists. The plan freezes v4 input bytes only; current exact outcome fixtures cover v1–v3. Freeze exact pre-change v4 transcript/checkpoint and agent-v4 outcome digests before production edits.

4. P2 — Specify that agent v5 requires both `fleet_action_contract` and `carriage_action_contract`, rejects the carriage contract in v1–v4, and preflights malformed v5 actions before reset.

5. P2 — V4 validation must reject zero carriage capacity and empty IDs, not merely negative capacities and duplicate IDs.
