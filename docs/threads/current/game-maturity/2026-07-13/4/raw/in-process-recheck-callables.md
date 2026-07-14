[P2] Resolved callables are retained longer than HEAD.

`route_planner.py` assigned resolved reducers/shared-path functions/factories to locals. HEAD invokes each resolved callable directly, releasing it after that call.

Verified against the actual HEAD class:

- HEAD: `call → reducer released → wire`; rider plan remains installed.
- Current: `call → wire → reducer released`; its finalizer clears the map after installation, so the plan disappears.

Use direct call composition such as `get_reduce_node_path()(list(node_path))`; Python resolves the callable before evaluating arguments without retaining it afterward. Apply the same form to shared-path and plan-factory calls.

The previous selection-local issue is fixed: the exact HEAD differential now matches. All 51 targeted tests pass. No other drift found.
