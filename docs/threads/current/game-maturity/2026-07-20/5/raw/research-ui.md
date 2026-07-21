# GM-06a HUD and Pixel research

Recommendation: render `Locomotives Available: <count>` as a third HUD line using the existing lazy HUD font and per-render text surfaces. The observed Courier 50 text is wider than the old two-line route-handle HUD exclusion, so the config-owned rectangle must expand conservatively for all three lines.

Expose `structured["fleet"]` with total, assigned, and available locomotive scalars. Do not add GM-06b controls/actions, GM-06c carriages/capacity, GM-06d rider-removal behavior, or privileged PlayerPixel info.

Evidence must use actual fast/fidelity CHW `step_result[0]` frames, mask cursor effects, distinguish fresh/consumed/refunded count pixels, prove seeded determinism and render/checkpoint purity, and keep relocated route handles outside the expanded HUD blocker while reachable after each registered-profile action round trip.

No files were changed by this research lane.
