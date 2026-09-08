# Numbered planning and review records

The documentation migration imported 10 work units and 623 tracked source files into consecutive docs/work IDs. The registry binds each historical file to its original repository, commit, path, and SHA-256 digest. Existing raw captures remain exact where they were already tracked; no ignored output was imported. The generated plan entries identify uncertain historical metadata instead of inventing approvals or completion.

Live guides, rules, and source comments now resolve to the imported records. Historical prose and quoted paths remain historical; actual Markdown destinations were rebased where needed. Superseded routing indexes and empty legacy directories were removed only after preserving their source bytes.

The fleet coordinator owns integrated acceptance and active-owner holds. The reviewed old-to-new mapping, exact original backups, and per-file before/after journal are retained under ignored fleet/tmp/work-docs-migration until handoff. See [the migration work plan](../../../../fleet/docs/work/3_numbered-work-docs/plan.md) for checks, independent review, and remaining repositories. No commit or push is part of this migration.
