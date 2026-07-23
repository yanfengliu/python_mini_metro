1. **CONFIRMED-RESOLVED** — [src/settings.py:74](/C:/Users/38909/Documents/github/python_mini_metro/src/settings.py:74). Non-string keys are rejected before `_exact_keys`. A valid JSON round-trip validated normally; adding both `1` and `None` keys raised `ValueError: settings document has a non-string key`.

2. **CONFIRMED-RESOLVED** — [src/entity/carriage.py:48](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/carriage.py:48), [src/rendering/game_renderer.py:297](/C:/Users/38909/Documents/github/python_mini_metro/src/rendering/game_renderer.py:297), [src/entity/metro.py:149](/C:/Users/38909/Documents/github/python_mini_metro/src/entity/metro.py:149). The locomotive and carriage use the same consist dispatch and both forward `reduced_motion`. At a blink-off phase, a seven-rider consist hid both locomotive and carriage riders under implicit/default and explicit `False`, with byte-identical output; `True` held both visible. Real speed and carriage-button probes confirmed unsupported kwargs remain filtered.

3. **CONFIRMED-RESOLVED** — [src/settings.py:168](/C:/Users/38909/Documents/github/python_mini_metro/src/settings.py:168). Injecting an `os.fdopen` failure propagated the identical exception object, left the fd closed (`EBADF`), preserved the previous destination bytes, and left only `settings.json`—no `.tmp` litter.

4. **CONFIRMED-RESOLVED** — [src/ui/menu_screens.py:241](/C:/Users/38909/Documents/github/python_mini_metro/src/ui/menu_screens.py:241). All three rows now display `% (stored)`.

5. **STILL-BROKEN — MINOR, incomplete regression guards.** The new tests are individually meaningful:

   - The carriage test at [test_gm08a_settings_render.py:165](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm08a_settings_render.py:165) catches filtering or dropping the carriage flag.
   - The isolation test at [test_gm08a_settings_render.py:202](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm08a_settings_render.py:202) directly forbids runtime `settings` imports.
   - The mixed-key test at [test_gm08a_settings.py:145](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm08a_settings.py:145) fails on the former `TypeError`.

   However, the carriage test bypasses `GameRenderer`; deleting the propagation at [game_renderer.py:310](/C:/Users/38909/Documents/github/python_mini_metro/src/rendering/game_renderer.py:310) would leave it green. There is still no reduced-motion `PathButton` test for [path_button.py:101](/C:/Users/38909/Documents/github/python_mini_metro/src/ui/path_button.py:101), the default comparison remains an on-phase passenger case, and snap suppression still asserts only inequality.

6. **CONFIRMED-RESOLVED** — [DECISIONS.md:185](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md:185) and [PLAN.md:39](/C:/Users/38909/Documents/github/python_mini_metro/docs/threads/current/game-maturity/2026-07-22/13/PLAN.md:39) consistently say blinks are held steady and snap-blip rings are suppressed.

7. **CONFIRMED-RESOLVED** — `ARCHITECTURE.md` now includes [settings.py:113](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:113), [flexible_draw.py:155](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:155), the SETTINGS/appended-menu description at [line 376](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:376), “no gameplay directly” at [line 389](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:389), and the 478-line count at [line 422](/C:/Users/38909/Documents/github/python_mini_metro/ARCHITECTURE.md:422).

New regressions:

- **MINOR** — [test_gm08a_settings_render.py:217](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm08a_settings_render.py:217) uses `open(...).read()` without closing. The focused run emitted 25 `ResourceWarning: unclosed file` warnings.
- **MINOR** — [test_gm08a_settings.py:252](/C:/Users/38909/Documents/github/python_mini_metro/test/test_gm08a_settings.py:252) tests `os.replace` failure but has no permanent `os.fdopen`-failure regression; removing the new fd guard would leave the suite green.

Requested regression checks otherwise passed: valid JSON is unaffected; button filtering is intact; default carriage pixels are unchanged; line counts are 187/123/252/478; and the settings-menu tests remain property-based. Full suite: **1,258 passed, 12 skipped**. Focused Ruff check/format passed. No files were modified.

VERDICT: NOT CLEAN
