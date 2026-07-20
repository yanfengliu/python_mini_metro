from __future__ import annotations

from typing import Any

import input_coordinator_differential_support as support


def run_progression_case() -> dict[str, Any]:
    import mediator as mediator_module

    host = support.bare_mediator()
    events: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    old = support.TraceProgression("old", events, previous=1, price=17)
    new = support.TraceProgression("new", events, previous=99, price=3)
    host._progression = old
    host.path_buttons = [support.TraceButton(str(index), events) for index in range(4)]
    host.time_ms = 73
    host.unlocked_num_paths = 1

    def unlocked_query() -> int:
        support.emit(events, "unlock.query")
        host._progression = new
        return 3

    host.get_unlocked_num_paths = unlocked_query
    host.update_path_button_lock_states = lambda: support.emit(events, "unlock.locks")
    mediator_module.Mediator.update_unlocked_num_paths(host)
    unlock_state = {
        "activeProgression": host._progression.name,
        "unlocked": host.unlocked_num_paths,
    }
    unlock_events = [
        event
        for event in events
        if event["event"] in {"progression.set", "button.blink"}
    ]
    if unlock_state != {"activeProgression": "new", "unlocked": 3}:
        raise AssertionError("unlock rebound state changed")
    if unlock_events != [
        {"event": "progression.set", "name": "old", "value": 3},
        {"button": "1", "event": "button.blink", "time": 73},
        {"button": "2", "event": "button.blink", "time": 73},
    ]:
        raise AssertionError("old progression capture or blink ordering changed")
    records.append(support.record("unlock-old-progression", events, state=unlock_state))

    host._progression = old
    host.get_next_path_button_idx_to_purchase = lambda: 2

    def price(button_idx: int) -> int:
        support.emit(events, "purchase.price", button=button_idx)
        host._progression = new
        return 17

    host.get_purchase_price_for_path_button_idx = price
    can_purchase = mediator_module.Mediator.can_purchase_path_button_idx(host, 2)
    can_events = [
        event
        for event in events
        if event["event"] in {"purchase.price", "progression.can"}
    ]
    if not can_purchase or can_events != [
        {"button": 2, "event": "purchase.price"},
        {
            "button": 2,
            "event": "progression.can",
            "name": "old",
            "next": 2,
            "price": 17,
        },
    ]:
        raise AssertionError("purchase price rebound capture changed")
    records.append(
        support.record(
            "purchase-old-progression", events, outcome=can_purchase, state=can_events
        )
    )

    host._progression = old
    host.unlocked_num_paths = 2
    buttons = [
        support.TraceButton("p0", events),
        support.TraceButton("p1", events),
        support.TraceButton("p2", events, locked=True),
    ]
    host.path_buttons = buttons
    mediator_module.Mediator.update_path_button_lock_states(host)
    host.can_purchase_path_button_idx = lambda index: (
        support.emit(events, "purchase.can-hook", button=index) or index == 2
    )
    host.get_purchase_price_for_path_button_idx = lambda index: (
        support.emit(events, "purchase.price-hook", button=index) or 17
    )
    host.update_unlocked_num_paths = lambda: support.emit(
        events, "purchase.unlock-hook"
    )
    purchase_result = mediator_module.Mediator.try_purchase_path_button(
        host, buttons[2]
    )
    host.try_purchase_path_button = lambda value: (
        support.emit(events, "purchase.button-hook", button=value.name) or True
    )
    bool_index_result = mediator_module.Mediator.try_purchase_path_button_by_index(
        host, True
    )
    purchase_state = {
        "boolIndexResult": bool_index_result,
        "locks": [button.is_locked for button in buttons],
        "purchaseResult": purchase_result,
    }
    if purchase_state != {
        "boolIndexResult": True,
        "locks": [False, False, True],
        "purchaseResult": True,
    }:
        raise AssertionError("lock, purchase, or Python bool index semantics changed")
    records.append(support.record("purchase-effects", events, state=purchase_state))

    class FailingProgression(support.TraceProgression):
        def record_path_purchase(self, value: int) -> None:
            super().record_path_purchase(value)
            raise RuntimeError("debit failed")

    failing = FailingProgression("failing", events, previous=2, price=17)
    host._progression = failing
    host.path_buttons = [support.TraceButton("failure", events, locked=True)]
    host.can_purchase_path_button_idx = lambda index: (
        support.emit(events, "failure.can", button=index) or True
    )
    host.get_purchase_price_for_path_button_idx = lambda index: (
        support.emit(events, "failure.price", button=index) or 17
    )
    host.update_unlocked_num_paths = lambda: support.emit(events, "failure.unlock")
    failure = support.capture(
        lambda: mediator_module.Mediator.try_purchase_path_button(
            host, host.path_buttons[0]
        )
    )
    if any(event["event"] == "failure.unlock" for event in events):
        raise AssertionError("failed debit unexpectedly advanced unlock state")
    records.append(
        support.record(
            "purchase-partial-failure",
            events,
            outcome=failure,
            state={"buttonStillLocked": host.path_buttons[0].is_locked},
        )
    )
    return {"events": events, "name": "progression-purchase", "records": records}


def run_action_case() -> dict[str, Any]:
    import mediator as mediator_module

    host = support.bare_mediator()
    events: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    host.is_paused = False
    host.game_speed_multiplier = 1
    host.increment_time = lambda value: support.emit(
        events, "time.increment", value=value
    )
    mediator_module.Mediator.step_time(host, 17)

    def late_speed(value: int) -> None:
        support.emit(events, "speed.late-set", value=value)
        host.game_speed_multiplier = value

    def pause_hook(value: bool) -> None:
        support.emit(events, "speed.pause-set", value=value)
        host.is_paused = value
        host.set_game_speed = late_speed

    host.set_paused = pause_hook
    host.set_game_speed = lambda value: support.emit(
        events, "speed.early-set", value=value
    )
    mediator_module.Mediator.apply_speed_action(host, "pause")
    mediator_module.Mediator.apply_speed_action(host, "speed_4")
    mediator_module.Mediator.apply_speed_action(host, "unknown")
    active = {
        action: mediator_module.Mediator.is_speed_button_active(host, action)
        for action in ("pause", "speed_1", "speed_2", "speed_4", "unknown")
    }
    speed_state = {
        "active": active,
        "multiplier": host.game_speed_multiplier,
        "paused": host.is_paused,
    }
    if speed_state != {
        "active": {
            "pause": False,
            "speed_1": False,
            "speed_2": False,
            "speed_4": True,
            "unknown": False,
        },
        "multiplier": 4,
        "paused": False,
    }:
        raise AssertionError("time, speed action, or active-button behavior changed")
    records.append(support.record("time-and-speed", events, state=speed_state))

    class Action(dict):
        pass

    class ActionType(str):
        pass

    host.is_game_over = False
    host.create_path_from_station_indices = lambda stations, loop=False: (
        support.emit(events, "action.create", loop=loop, stations=list(stations))
        or object()
    )
    host.try_purchase_path_button_by_index = lambda index=None: (
        support.emit(events, "action.buy", index=index) or True
    )
    host.remove_path_by_id = lambda path_id: (
        support.emit(events, "action.remove-id", pathId=path_id) or True
    )
    host.remove_path_by_index = lambda index: (
        support.emit(events, "action.remove-index", index=index) or True
    )
    host.set_paused = lambda value: (
        support.emit(events, "action.pause", value=value)
        or setattr(host, "is_paused", value)
    )
    actions: list[tuple[str, Any]] = [
        (
            "create",
            Action(type=ActionType("create_path"), stations=[0, 1], loop=True),
        ),
        ("bad-loop", Action(type=ActionType("create_path"), loop=1)),
        ("buy-default", Action(type=ActionType("buy_line"))),
        ("buy-bool", Action(type=ActionType("buy_line"), path_index=True)),
        (
            "remove-id-precedence",
            Action(type=ActionType("remove_path"), path_id="p-id", path_index=2),
        ),
        ("pause", Action(type=ActionType("pause"))),
        ("resume", Action(type=ActionType("resume"))),
        ("noop", Action(type=ActionType("noop"))),
        ("unknown", Action(type=ActionType("mystery"))),
        ("non-dict", []),
    ]
    results = [
        {"label": label, "result": mediator_module.Mediator.apply_action(host, action)}
        for label, action in actions
    ]
    host.is_game_over = True
    terminal = mediator_module.Mediator.apply_action(
        host, Action(type=ActionType("noop"))
    )
    expected_results = [True, False, True, False, True, True, True, True, False, False]
    if [item["result"] for item in results] != expected_results or terminal:
        raise AssertionError("structured action branch or type semantics changed")
    records.append(
        support.record(
            "structured-actions",
            events,
            state={"results": results, "terminal": terminal},
        )
    )

    host.is_game_over = False
    host.is_paused = False

    def fail_pause(value: bool) -> None:
        support.emit(events, "action.partial-pause", value=value)
        host.is_paused = value
        raise LookupError("pause hook failed")

    host.set_paused = fail_pause
    failure = support.capture(
        lambda: mediator_module.Mediator.apply_action(
            host, Action(type=ActionType("pause"))
        )
    )
    if not host.is_paused:
        raise AssertionError(
            "structured action exception unexpectedly rolled back state"
        )
    records.append(
        support.record(
            "action-partial-failure",
            events,
            outcome=failure,
            state={"paused": host.is_paused},
        )
    )
    return {"events": events, "name": "speed-actions", "records": records}
