# GM-04 cross-platform and supply-chain audit

Conditional approval requires a checked-in pin descriptor, package and regenerated lock agreement, and an ignored repo-owned checkout outside `node_modules`. The live audit reproduced 25/44 with 19 failures caused by the sibling mismatch; GM-04c must retain all 44 baseline test names and report the larger exact post-change total.

Npm local-file layout is configuration-sensitive. Commit `install-links=false`, build the isolated pin before root `npm ci`, and require `realpath(node_modules/civ-engine)` to equal the configured pin root. A dependency-light verifier should run before tests and public playtest commands so a stale sibling junction produces one attributable failure before engine code executes.

Use a Node setup entry point with argv arrays, `shell: false`, and `npm.cmd` on Windows. Clone only a fixed public HTTPS origin at the exact commit; accept no credentials or caller-selected origin. Existing dirty or mismatched pin directories fail safely unless a future explicit exact-path refresh contract is reviewed. CI must use the same repo-relative location, least-privilege permissions, and no persisted credentials.

Reject clones below `node_modules`, manual untracked junction fixes, environment-only overrides, global caches, arbitrary temporary paths, Git npm dependencies without built retained Git identity, and the rolling engine release. GM-04c must prove descriptor/manifest/lock agreement, ignore/untracked state, exact root/version/commit/digest, complete tests, a clean recursive pass, fail-fast sibling mismatch, repeat setup stability, and no credential material.
