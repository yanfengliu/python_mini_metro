# GM-03f semantic plan review messages

The following reviewer payloads are preserved verbatim in emission order.

One remaining substantive plan gap: PLAN line 19's resolver inventory omits six late-read mediator globals used by the frozen bodies: game_over_button_width/height/spacing, game_over_font_size (mediator.py 249-256), and screen_width/screen_height (379-380). Lines 38/49 generically promise module-global rebinding, but as written line 19 can be satisfied while importing/capturing these numeric config values in input_coordinator, breaking mediator-module monkeypatch behavior. Please explicitly add getter thunks/original-expression resolution for layout and surface-fallback config globals, and cover rebinding in facade/direct differential tests.

Also tighten PLAN invariants 8-9: live mouse dispatch uses `isinstance` for Station, PathButton, SpeedButton, and Button (mediator.py 429,436,441,446,452,457), so the phrase “exact type tests” is ambiguous and could permit `type(...) is ...`, breaking subclasses/multiple-inheritance precedence. State `isinstance` explicitly and include subclass/dual-class precedence characterization, parallel to corrected dict-subclass wording.

A second collaborator-lifetime site should be frozen alongside the newly added unlock-query case: in can_purchase_path_button_idx, Python binds `self._progression.can_purchase_resolved_path_button_idx` before evaluating the nested public `get_purchase_price_for_path_button_idx(...)` argument (mediator.py 341-345). If that public price hook rebinds `_progression`, baseline still calls the old aggregate. Add this old-progression/price-hook case to line 49 and differential; purchase ordering alone does not prove it.

One last wording/test edge before CLEAN: apply_action uses `isinstance(action_type, str)` at mediator.py 561, so `str` subclasses are accepted just like dict subclasses. PLAN line 37 currently says only “require a string type”; make the operator/subclass behavior explicit and include it in structured-action characterization to prevent an exact-type rewrite.

Related exact-type edge: get_surface_size uses `isinstance(maybe_width, (int, float))` / same for height (mediator.py 383-386), accepting int/float subclasses as well as bool. PLAN line 29 should name `isinstance`/numeric-subclass acceptance, not “only int or float,” and test independent subclass conversion/fallback.

Final adversarial re-review: CLEAN. The corrected live plan now closes the substantive risks I found: complete late numeric/global resolver inventory; dict/string/numeric/entity/event subclass semantics; mouse dual-class precedence; both old-progression bound-method capture sites; explicit pre-production facade characterization; and portable/cardinality-guarded differential replay. The exact 19-method boundary remains semantically defensible as stateless interaction/UI/programmatic-drive coordination while canonical state and adjacent algorithms remain on Mediator/existing components.

CLEAN
