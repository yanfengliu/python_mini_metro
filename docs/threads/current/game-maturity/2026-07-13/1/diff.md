# GM-02e research-plan delta

- Reclassified the promoted ten-frame RecurrentPPO model as the bounded official pixel-only baseline rather than a complete long-horizon solution.
- Added an explicit three-tier boundary: official player pixels, assisted render-semantic state, and broader structured oracle/training-only information.
- Selected a measured model ladder: semantic structured-only and direct hybrid LSTM, then a pixel-only actor with privileged training assistance, then relation attention or temporal Transformers only after diagnostic failure.
- Required distinct protocol/task/history/manifest identity, Box-to-Dict lifecycle work, genuine pixel v1/v2 compatibility, single-authority artifact authentication, and leakage/isolation tests before training.
- Updated GM-12a/GM-12b so the final post-balance player-visible state is inventoried first and observation versions freeze only after executable feasibility/resource proof.
- Preserved the conditional pointer head and total-passenger-delivery held-out evaluation as independent promotion dimensions.
