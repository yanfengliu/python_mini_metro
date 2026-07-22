# Diff — CI action Node 20 deprecation bump (iteration 1)

Scope: `.github/workflows/test.yml` only. Bumps `actions/checkout` v4→v7, `actions/setup-python` v5→v7, `actions/setup-node` v4→v7 across both the `build` (ubuntu-latest) and `rl-smoke` (windows-latest) jobs. No application code.

```diff
diff --git a/.github/workflows/test.yml b/.github/workflows/test.yml
index 192da39..d2a321d 100644
--- a/.github/workflows/test.yml
+++ b/.github/workflows/test.yml
@@ -11,20 +11,20 @@ jobs:

     steps:
       - name: Checkout python_mini_metro
-        uses: actions/checkout@v4
+        uses: actions/checkout@v7
         with:
           path: python_mini_metro
           persist-credentials: false
           fetch-depth: 0

       - name: Set up Python 3.13
-        uses: actions/setup-python@v5
+        uses: actions/setup-python@v7
         with:
           python-version: "3.13"
           architecture: "x64"

       - name: Set up Node 22
-        uses: actions/setup-node@v4
+        uses: actions/setup-node@v7
         with:
           node-version: "22"
           cache: npm
@@ -58,19 +58,19 @@ jobs:

     steps:
       - name: Checkout python_mini_metro
-        uses: actions/checkout@v4
+        uses: actions/checkout@v7
         with:
           persist-credentials: false
           fetch-depth: 0

       - name: Set up Python 3.13
-        uses: actions/setup-python@v5
+        uses: actions/setup-python@v7
         with:
           python-version: "3.13"
           architecture: "x64"

       - name: Set up Node 22
-        uses: actions/setup-node@v4
+        uses: actions/setup-node@v7
         with:
           node-version: "22"
           cache: npm
```
