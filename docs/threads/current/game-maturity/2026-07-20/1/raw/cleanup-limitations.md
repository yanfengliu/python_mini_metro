# GM-04c cleanup limitations

Four old ignored output pre-commit cache roots remain retained because ACL-blocked descendants prevent a safe complete-removal proof: `output/gm04a-precommit-cache`, `output/gm04b-a3-precommit-cache`, `output/gm04b-final-precommit-cache`, and `output/gm04b-precommit-cache-final2`.

These roots are unrelated ignored cache/evidence surfaces, are not proof inputs, and are excluded from the tracked GM-04c transaction. No broad output cleanup is authorized or attempted.

The exact task cache `C:\tmp\python-mini-metro-gm04b-precommit-cache` remains intentionally retained only through the GM-04c changed-path pre-commit hooks. It is excluded from commit content and may be reconsidered only through exact scoped inspection and cleanup after those hooks finish.
