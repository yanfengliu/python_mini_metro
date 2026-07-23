# GM-07e diff — deterministic per-frame game-over reconciliation (commit a720cf7)

```diff
diff --git a/src/app_controller.py b/src/app_controller.py
index beaa1fe..5ee8fd4 100644
--- a/src/app_controller.py
+++ b/src/app_controller.py
@@ -111,17 +111,30 @@ class AppController:
         else:
             self.last_highscore_result = None

-    def handle_event(self, event: object) -> None:
-        """Route one converted event according to the current screen."""
-
+    def reconcile_game_over(self) -> None:
+        """Promote a finished run to ``GAME_OVER`` exactly once (D-027/D-028).
+
+        Idempotent and a no-op unless the controller is still ``PLAYING`` and the
+        mediator has flipped game over. It drops the autosave so a finished run
+        can never be Continued (D-027) and records the run's high score exactly
+        once (D-028), storing the result for the best indicator. ``handle_event``
+        calls it at the top -- the historical inline promotion -- and
+        ``main.run_game`` calls it once per frame after ``session.advance``, so a
+        tick-driven game over with no promoting event still promotes, records,
+        and shows the indicator the frame it ends, deterministically and
+        independent of any incidental event. The window-close QUIT record in
+        ``main`` stays mutually exclusive: once this promotes, that gate sees
+        ``GAME_OVER`` and never re-records.
+        """
         if self.state is AppScreen.PLAYING and self.mediator.is_game_over is True:
             self.state = AppScreen.GAME_OVER
-            # A finished run must never be resumable: drop the autosave at the
-            # promotion, the same handle_event call as any game-over exit below.
             self._autosave_delete()
-            # Record the run's high score at the same promotion (D-028); the
-            # window-close race in main covers the un-promoted game-over exit.
             self._record_highscore()
+
+    def handle_event(self, event: object) -> None:
+        """Route one converted event according to the current screen."""
+
+        self.reconcile_game_over()
         if self.state is AppScreen.PLAYING:
             self._handle_playing(event)
         elif self.state is AppScreen.PAUSE_MENU:
diff --git a/src/main.py b/src/main.py
index 775dd95..3ba8b4c 100644
--- a/src/main.py
+++ b/src/main.py
@@ -227,6 +227,15 @@ def run_game(
             advance = session.advance(elapsed_ms)
         previous_session = session

+        # Deterministic game-over reconciliation (D-027/D-028 follow-up): a tick
+        # that flips is_game_over with no promoting event this frame must still
+        # promote, drop the autosave, and record the score THIS frame, so the best
+        # indicator shows and the record no longer waits on an incidental event.
+        # Idempotent and mutually exclusive with the window-close QUIT gate above,
+        # which fires only while the state is still PLAYING/PAUSE_MENU.
+        controller.reconcile_game_over()
+        state = controller.state
+
         game_surface.fill(screen_color)
         if state == AppScreen.TITLE:
             draw_title_screen(game_surface)
```

The new red-first test suite `test/test_gm07e_game_over_reconcile.py` (491-line file) is committed in full at a720cf7; see the commit for its contents.
