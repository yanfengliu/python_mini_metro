Verdict: approve the stateful component design, conditionally on preserving the existing Mediator call graph and stale-cache semantics. I recommend it over a stateless controller mutating a host Protocol.

A stateful component—preferably named `NetworkProgression` to avoid colliding conceptually with GM-10’s weekly progression—gives one canonical store, a narrow domain boundary, no host reference cycle, simpler direct unit tests, and a natural future GM-07 serialization unit. A stateless `ProgressionController[MediatorProtocol]` keeps compatibility cheaply, but it does not truly extract ownership: it remains coupled to a large mutable host interface, requires fake Mediators to test, and either holds a `Mediator -> controller -> Mediator` cycle or takes the host on every call.

## Contract verdict

The explicit property facade preserves all requested contracts if implemented as follows:

- Direct writes: preserved. Data-descriptor getters/setters make `mediator.deliveries = 7`, `+=`, `score`, `total_travels_handled`, and direct purchased/cache writes hit the single component state.
- Cached unlocks: preserved only if `unlocked_num_paths`, `unlocked_num_stations`, and `path_purchase_prices` remain stored mutable caches. Do not compute them eagerly or auto-reconcile them in setters.
- Checkpoint surface: preserved. `recursive_checkpoint.py:390-405` and `:421-440` use ordinary attribute access, not `Mediator.__dict__`. Properties are sufficient.
- Monkeypatching: preserved only if delivery and purchase orchestration continue calling the public Mediator wrappers. Existing tests replace `mediator.update_unlocked_num_paths` and `update_unlocked_num_stations` at `test/test_mediator_passenger_flow.py:23-24` and `:208-209`.
- Constructor RNG order: preserved if the component performs only list sorting/copying and arithmetic, is installed in the current config-initialization position, and consumes no RNG. Station generation and color generation must remain in their current order at `src/mediator.py:89-94`.
- Future GM-07 saves: stateful is superior. GM-07 can explicitly serialize/restore the aggregate without introspecting Mediator internals, then independently restore station/button/topology state. This aligns with strict JSON roundtrips at `PLAN.md:170-185`.

## Concrete defects to prevent

1. Do not make `record_delivery()` update cached unlock counts atomically.

   Current delivery behavior is counter mutation followed by two public calls in order at `src/mediator.py:909-912`. The component should award one delivery and one credit only; `move_passengers()` must then call:

   ```python
   self.update_unlocked_num_paths()
   self.update_unlocked_num_stations()
   ```

   Otherwise monkeypatch interception and unlock-blink transitions change.

2. Do not make a component-level purchase atomically update the unlocked cache.

   Preserve the sequence at `src/mediator.py:258-273`: button lock/member checks, public affordability/price calls, debit/increment, then public `update_unlocked_num_paths()`. The component can own the raw debit and `purchased_num_paths += 1`, but Mediator must orchestrate UI synchronization.

3. Preserve the current public-to-public dynamic dispatch where practical.

   Specifically:

   - `update_unlocked_num_stations()` currently calls `self.get_unlocked_num_stations()`.
   - `update_unlocked_num_paths()` calls `self.get_unlocked_num_paths()` and `self.update_path_button_lock_states()`.
   - `can_purchase_path_button_idx()` calls the two public query methods.
   - `try_purchase_path_button()` calls public eligibility, price, and update methods.

   Moving those calls wholly inside the component silently defeats instance monkeypatches and subclass overrides.

4. Every moved normal attribute should remain writable through the facade.

   This includes the five counters/caches and, for strict compatibility, `num_paths`, `num_stations`, `initial_num_stations`, both milestone lists, and `path_purchase_prices`. Setters must not add validation or synchronization that does not exist today.

5. Return live component-owned lists, not defensive copies.

   The current milestone and price fields are mutable lists and checkpoint code reads them directly. Sorting should still create private copies of the config lists, matching `src/mediator.py:71` and `:76`.

6. Preserve stale derived-state behavior.

   - Writing deliveries does not unlock stations until the explicit update.
   - Writing purchased count does not unlock lines until the explicit update.
   - Lowering deliveries and updating can lower the cached count without shrinking `mediator.stations`.
   - Reassigning milestones does not automatically recalculate cached prices.
   - `get_path_purchase_prices()` recalculates from the current limit/milestones; it must not merely return the cached list.

7. Keep button/UI validation outside the component.

   `try_purchase_path_button()` must still reject an unlocked button and a foreign button before domain mutation. `try_purchase_path_button_by_index()` bounds against `len(path_buttons)` before forwarding. Do not introduce stricter index typing in these lower-level methods; `apply_action()` already owns its exact `type(...) is int` validation.

8. Do not expose `_progression` as the preferred gameplay mutation surface.

   Keep it private. Internal and future code should use Mediator’s facade or a deliberate future snapshot API so station/button side effects cannot be bypassed accidentally.

9. Do not use automatic dataclass serialization as the GM-07 schema.

   The stateful aggregate is a good source for an explicit versioned snapshot, but rules/configuration must be validated separately from mutable save state. `recursive_checkpoint.py` remains a one-way verifier per `PLAN.md:180`.

10. One low-risk compatibility change remains unless explicitly preserved: constructor virtual dispatch.

   Today `Mediator.__init__` calls `self.get_path_purchase_prices()` at `src/mediator.py:72`. Deriving prices entirely inside the component means a hypothetical Mediator subclass override no longer controls initial cached prices. No subclasses exist in the repository, but strict neutrality can preserve this by installing the component first and initializing its cached prices through the facade method.

With those constraints, I find no architectural blocker. The stateful single-store design is the stronger long-term boundary; the stateless host-Protocol controller is safer only as a very short-lived mechanical extraction and would create migration debt before GM-07/GM-10.
