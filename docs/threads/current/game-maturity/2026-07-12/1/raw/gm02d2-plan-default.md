One medium finding remains:

`evaluate_promotion()` must suppress metrics whenever the campaign is incomplete, has an invalid repeat, or has workload-setting drift—not only when a repeat is invalid. Otherwise missing/duplicate rows or batch/epoch drift still produce partial or non-matched medians.

Use:

```python
metrics_usable = complete and all_valid and settings_match
```

When false, all four medians and three resource-gate outcomes should be unavailable, ideally `None`, so reasons cannot misleadingly claim that memory or throughput failed. Extend the existing missing/duplicate/invalid/batch-drift/epoch-drift tests to assert suppression.

The corrected history-default split is approved:

- fresh recurrent and omitted `build_vector_env` history → exact promoted 10-multiscale history;
- fresh explicit PPO without history → contiguous eight;
- `DEFAULT_FRAME_STACK` remains `8` for compatibility;
- resume/evaluation always consume persisted history.
