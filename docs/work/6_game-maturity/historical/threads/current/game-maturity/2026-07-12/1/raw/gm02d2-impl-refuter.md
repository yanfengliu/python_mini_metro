CLEAN.

Verified final live diff and evidence:

- Fresh recurrent = exact ten-frame history; explicit PPO = contiguous eight.
- Resume/evaluation preserve authenticated saved history.
- Fail-closed decisions reproduce exactly from all 17 rows.
- All 51 raw digests and both campaign summaries match.
- Canonical artifact: 18,811 bytes, SHA-256 `e63f00365a62e0b95abf493ff93037511f304b72711b17cf3e0302b37ebcfcdd`.
- 39 focused RL tests passed; YAML/PowerShell parsing and `git diff --check` passed.
- Changed files remain below 500 lines.
