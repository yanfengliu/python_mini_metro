**Findings**

- Low: `pygame.draw` mocks still leak in some tests. The path-button test at [test/test_coverage_utils.py](C:/Users/38909/Documents/github/python_mini_metro/test/test_coverage_utils.py:120) assigns `pygame.draw.circle = MagicMock()` directly with no cleanup, and similar direct assignments remain in geometry/path/station tests. That means the artifact claim in [docs/reviews/full/2026-04-28/2/REVIEW.md](C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/full/2026-04-28/2/REVIEW.md:39) that path-button font/draw tests use scoped patches is not fully accurate.

- Low: [GAME_RULES.md](C:/Users/38909/Documents/github/python_mini_metro/GAME_RULES.md:62) says removing a line invalidates any travel plan that used it. The final code intentionally preserves onboard passenger plans when `next_path` is a surviving line, then replans after transfer, so the doc overstates the behavior.

The core iteration-2 behavior fixes otherwise look addressed: rejected malformed actions do not advance time, strict bool/int validation is in place, loop creation keeps `[0, 1, 2]`, and the onboard transfer-plan preservation logic is present. I did not modify files or rerun validation.
