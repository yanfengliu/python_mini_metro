NOT CLEAN. Legacy bytes are preserved, but one major manifest-integrity defect remains.

### Findings

1. **MAJOR — the manifest factory can mint contradictory task identity.**
   [src/rl/manifest.py:62](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest.py:62) accepts the task fingerprint, task fields, and map fields independently; [schema selection at line 101](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest.py:101) depends only on `map_id`. I reproduced a valid v3 manifest declaring `classic@1` while retaining the legacy mapless `c2ef342f…` fingerprint. It serializes successfully, then [task_spec_from_manifest rejects it](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/training.py:283). The inverse—map-free v2 with a map-bound fingerprint—is also possible.
   **Fix:** accept one `TaskSpec` and derive schema, task fields, map fields, protocol fingerprint, and task fingerprint from it; alternatively reconstruct and cross-check a `TaskSpec` before returning.

2. **MINOR — unsupported map versions are not rejected before artifact access.**
   [task_spec_from_manifest](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/training.py:270) verifies syntax and fingerprint but never calls `resolve_map`. A self-consistent `classic@2` manifest therefore passes reconstruction even though the registry currently has only `classic@1`. Evaluation authenticates model bytes at [evaluate_rl.py:235](/C:/Users/38909/Documents/github/python_mini_metro/scripts/evaluate_rl.py:235) before environment construction at [line 250](/C:/Users/38909/Documents/github/python_mini_metro/scripts/evaluate_rl.py:250); resume similarly reads the artifact at [train_rl.py:325](/C:/Users/38909/Documents/github/python_mini_metro/scripts/train_rl.py:325). It eventually fails inside `PlayerPixelEnv`, potentially in a subprocess.
   **Fix:** resolve the exact non-null map pair during manifest task reconstruction, while retaining the worker-side resolution.

3. **MINOR — new v3 rejection messages omit the offending input.**
   [manifest_schema.py:239](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest_schema.py:239) reports only the requirement. For example, `mapId=""` produces `manifest v3 mapId must be...`, and version `0` similarly omits `0`. This violates the repository’s error-surface rule.
   **Fix:** include `got {map_id!r}` or `got {version!r}`.

4. **MINOR — canonical documentation contradicts the implementation.**
   [README.md:256](/C:/Users/38909/Documents/github/python_mini_metro/README.md:256) says every fresh artifact is v2, although `--map` creates v3. [ARCHITECTURE.md:370](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:370) still says GM-09a2 is deferred.
   **Fix:** document map-free v2 versus map-bound v3, resume inheritance, and the completed boundary; add the required `PROGRESS.md` entry before delivery.

5. **NIT — version-constant exports are incomplete.**
   [manifest_schema.py:14](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest_schema.py:14) has explicit V1 and V3 constants but no explicit `TRAINING_MANIFEST_SCHEMA_V2`; [rl.manifest.__all__](/C:/Users/38909/Documents/github/python_mini_metro/src/rl/manifest.py:35) also omits V3.
   **Fix:** define V2, retain the unsuffixed name as its compatibility alias, and export V2/V3 consistently.

6. **NIT — the legacy-fixture test leaks its file handle.**
   [test_gm09a2_task_identity.py:76](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm09a2_task_identity.py:76) uses `json.load(open(...))`; the suite emits `ResourceWarning: unclosed file`.
   **Fix:** use a context manager or `Path.read_text()`.

### Verified clean

- Live and `HEAD` mapless canonical descriptors are byte-identical; both hash to `c2ef342f9cedfc3b7292ec2517ec7ccca7b2dcf9b49811c6dec529c25e73933e`.
- The committed v1 fixture reconstructs mapless to that exact fingerprint.
- v1/v2 exact-key and map-free behavior, v3 required map keys, and v2/v3 history emission work.
- Resume parses before building the spec and correctly inherits map absence or identity; evaluation rebuilds the manifest spec.
- Thunks preserve both map fields and are pickle-safe; default `PlayerPixelEnv().task_spec == TaskSpec()`.
- `maps.py` is excluded from `TRAINING_SOURCE_PATHS` but included in the content fingerprint. The normalized LF training pin is correctly `4f4b8f32…`.
- Focused regression run: **85 tests passed, 7 skipped**.

**NOT CLEAN — legacy compatibility is intact, but the factory can still persist internally contradictory task identity.**
