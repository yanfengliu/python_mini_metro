BLOCKED for Commit A as written.

Main gaps:

- Original acceptance requires expected/actual path, version, commit, and digest. Current docs omit the paths and `matches.path=false`.
- Credential evidence covers the documentation payload, not the required tracked/staged dependency material. Current scan across 14 payload paths and 10 dependency surfaces found zero high-confidence matches; rerun after staging.
- `raw/isolated-mismatch-review.md:7` incorrectly says only required tracked surfaces were copied. The harness copied the complete physical `scripts/` tree: 49 files, including 9 ignored `.pyc` files. Preserve verbatim raw output if applicable, but adjudicate this in `REVIEW.md`.
- Three raw reviews cite the now-removed harness. Record its ephemeral boundary and reviewed SHA-256, or retain the exact reviewed source.
- Tighten “exact diagnostic/no engine-body output” to the evidence actually asserted: diagnostic present, no canonical body sentinel, with pre-body ordering established statically.

CLEAN:

- GM-04b → GM-04c cursor and A/B transaction state.
- Recursive artifact coherence and bounded `no-fix-candidate` scope.
- Root/pin/sibling identity and cleanup limitations.
- Ephemeral-versus-retained evidence boundary, except for the omitted harness-source boundary.

Final staging scope is 14 exact paths; `.agents/`, ignored output, pin, `node_modules`, setup artifacts, and temporary caches must remain excluded. No files were edited or staged.
