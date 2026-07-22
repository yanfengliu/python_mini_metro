# Diff — iteration 2 (SHA-pin hardening)

Follow-up to iteration 1 (v4/v5 -> v7 tag bump, reviewed clean, CI green at commit 7beb43f). This iteration replaces the floating `@v7` major tags with immutable full commit SHAs plus `# vX.Y.Z` version comments, across both jobs. No version change: each pinned SHA is the commit the already-reviewed v7 tag resolves to (and each is that action's latest release).

```diff
       - name: Checkout python_mini_metro
-        uses: actions/checkout@v7
+        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
       - name: Set up Python 3.13
-        uses: actions/setup-python@v7
+        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
       - name: Set up Node 22
-        uses: actions/setup-node@v7
+        uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
```

Applied identically in the `build` (ubuntu-latest, lines 14/21/27) and `rl-smoke` (windows-latest, lines 61/67/73) jobs — six `uses:` lines total, zero floating tags remaining.

Resolved SHAs (authoritative, `gh api repos/actions/<name>/commits/<tag>`):

| Action | Tag (= latest release) | Commit SHA |
|---|---|---|
| actions/checkout | v7.0.1 | 3d3c42e5aac5ba805825da76410c181273ba90b1 |
| actions/setup-python | v7.0.0 | 5fda3b95a4ea91299a34e894583c3862153e4b97 |
| actions/setup-node | v7.0.0 | 820762786026740c76f36085b0efc47a31fe5020 |
