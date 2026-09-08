# GM-02c temporal and recurrent finder/refuter

## Finding

MEDIUM — `test_recurrent_episode_start_masks_reset_only_at_episode_boundaries` used a recording fake policy through the custom evaluator, so it did not exercise RecurrentPPO and duplicated existing fake evaluation coverage. A real probe against the live named-history runtime produced `[[True], [False], [True]]`; make that the regression.

## Final refutation

CLEAN — the corrected real `RecurrentPPO.learn` mask test passed and captured `[[True], [False], [True]]`. The complete runtime scan passed 29/29 exact-RL tests covering wrapper order, Dummy/spawned Subproc, reset/terminal/TimeLimit semantics, timeout bootstrap, save/load/predict, pre-rollout space mismatch, cleanup paths, and exact VecFrameStack equivalence for stacks 1/4/8/13. No edits were made by the reviewer.
