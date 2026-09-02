# Lessons

A queue, not a record. Every entry here is prose that has not become a gate yet, and every entry costs each session in this repo the time to read it — so an entry names the gate it is waiting for, and is deleted in the commit that lands that gate.

An entry is anchored to a measurement, a commit, or a test id, and states the gate that will retire it: a test, a lint rule, a schema check, a fixed command. An entry that can name no gate is not a lesson. Fleet-wide knowledge with no mechanical trigger is staged in [canon-candidates.md](canon-candidates.md) for the constitution, repo-only knowledge goes to [../policies/local-rules.md](../policies/local-rules.md), and the rest is folklore and is dropped.

A new lesson is one line here plus an entry in [lessons-evidence.md](lessons-evidence.md) holding the war story and the anchor. There is no `lessons:check` script here yet, so the two files are kept in step by hand: a rule always has an entry, and an entry always has a rule.

Gates that have already retired a lesson, and the mutation each was made to fail under, are in [gate-proofs.md](gate-proofs.md). That file stays.

## Rules

### Editing this repo

- Anchor programmatic text edits to the file's real bytes: these files are mixed CRLF and LF, and a formatter may already have rewritten the line you are matching. **Waiting on:** repo-wide line-ending normalisation (`* text=auto eol=lf` in `.gitattributes`, one normalising pass, and a test asserting every tracked `.py` uses one line ending), which would remove the class rather than describe it. That pass rewrites every file and rotates the training-source fingerprint, so it is its own change. ([evidence](lessons-evidence.md#anchor-text-edits-to-the-files-real-bytes))

The other 22 entries this file held on 2026-09-02 were retired: 13 into gates (see [gate-proofs.md](gate-proofs.md)) and 9 staged in [canon-candidates.md](canon-candidates.md), one of those as an amendment to a rule already in the constitution.
