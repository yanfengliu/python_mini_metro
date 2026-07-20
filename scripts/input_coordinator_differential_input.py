from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import input_coordinator_differential_support as support


def run_input_case() -> dict[str, Any]:
    import mediator as mediator_module

    host = support.bare_mediator()
    events: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    first = support.TraceStation("station-first", events, contains=False)
    second = support.TraceStation("station-second", events, contains=True)
    button = support.TraceButton("button-first", events, contains=True)
    host.stations = [first, second]
    host.buttons = [button]
    containing = mediator_module.Mediator.get_containing_entity(host, "probe")
    hit_state = {"selected": containing.name}
    if hit_state != {"selected": "station-second"}:
        raise AssertionError("station-first hit-test ordering changed")
    records.append(support.record("hit-test-order", events, state=hit_state))

    class EarlyMouseKind:
        MOUSE_DOWN = "early-down"
        MOUSE_MOTION = "early-motion"
        MOUSE_UP = "early-up"

    class LateMouseKind:
        MOUSE_DOWN = "down"
        MOUSE_MOTION = "motion"
        MOUSE_UP = "up"

    class StationType:
        def __init__(self, name: str):
            self.name = name

    class PathButtonType:
        pass

    class SpeedButtonType:
        pass

    class ButtonType:
        pass

    class DualButton(PathButtonType, SpeedButtonType):
        name = "dual"
        path = "path-dual"
        is_locked = True
        action = "speed_4"

    class LockedButton(PathButtonType):
        name = "locked"
        path = None
        is_locked = True

    class SpeedButton(SpeedButtonType):
        name = "speed"
        action = "speed_2"

    class HoverButton(ButtonType):
        name = "hover"

        def on_hover(self) -> None:
            support.emit(events, "mouse.hover", entity=self.name)

    station = StationType("station")
    dual = DualButton()
    locked = LockedButton()
    speed = SpeedButton()
    hover = HoverButton()
    draft = support.TraceDraft(events)
    entities = {
        "down": station,
        "dual": dual,
        "locked": locked,
        "speed": speed,
        "end": station,
        "abort": None,
        "add": station,
        "temporary": None,
        "hover": hover,
        "exit": None,
    }

    def containing_entity(position: str) -> Any:
        support.emit(events, "mouse.hit", position=position)
        if position == "down":
            mediator_module.MouseEventType = LateMouseKind
        return entities[position]

    host.get_containing_entity = containing_entity
    host.start_path_on_station = lambda value: support.emit(
        events, "mouse.start", entity=value.name
    )
    host.end_path_on_station = lambda value: support.emit(
        events, "mouse.end", entity=value.name
    )
    host.abort_path_creation = lambda: support.emit(events, "mouse.abort")
    host.add_station_to_path = lambda value: support.emit(
        events, "mouse.add", entity=value.name
    )
    host.remove_path = lambda path: support.emit(events, "mouse.remove", path=path)
    host.try_purchase_path_button = lambda value: support.emit(
        events, "mouse.purchase", entity=value.name
    )
    host.apply_speed_action = lambda action: support.emit(
        events, "mouse.speed", action=action
    )
    host.buttons = [
        support.TraceButton("exit-a", events),
        support.TraceButton("exit-b", events),
    ]
    host.is_mouse_down = False
    host.is_creating_path = False
    host.path_being_created = None

    patch_values = {
        "MouseEventType": EarlyMouseKind,
        "Station": StationType,
        "PathButton": PathButtonType,
        "SpeedButton": SpeedButtonType,
        "Button": ButtonType,
    }
    with support.patched(mediator_module, **patch_values):
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="down", position="down")
        )
        if not host.is_mouse_down:
            raise AssertionError("mouse down no longer precedes path start")

    with support.patched(
        mediator_module,
        MouseEventType=LateMouseKind,
        Station=StationType,
        PathButton=PathButtonType,
        SpeedButton=SpeedButtonType,
        Button=ButtonType,
    ):
        host.is_creating_path = False
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="up", position="dual")
        )
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="up", position="locked")
        )
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="up", position="speed")
        )

        host.is_creating_path = True
        host.path_being_created = draft
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="up", position="end")
        )
        host.is_creating_path = True
        host.path_being_created = draft
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="up", position="abort")
        )

        host.is_mouse_down = True
        host.is_creating_path = True
        host.path_being_created = draft
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="motion", position="add")
        )
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="motion", position="temporary")
        )

        host.is_mouse_down = False
        host.is_creating_path = False
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="motion", position="hover")
        )
        mediator_module.Mediator.react_mouse_event(
            host, SimpleNamespace(event_type="motion", position="exit")
        )

    mouse_names = [
        event["event"] for event in events if event["event"].startswith("mouse.")
    ]
    required = {
        "mouse.abort",
        "mouse.add",
        "mouse.end",
        "mouse.hover",
        "mouse.purchase",
        "mouse.remove",
        "mouse.speed",
        "mouse.start",
    }
    if not required.issubset(mouse_names):
        raise AssertionError("a mouse dispatch branch disappeared")
    if mouse_names.index("mouse.remove") > mouse_names.index("mouse.speed"):
        raise AssertionError("path-button precedence over speed-button changed")
    mouse_state = {
        "isCreating": host.is_creating_path,
        "isMouseDown": host.is_mouse_down,
        "requiredBranches": sorted(required),
    }
    records.append(support.record("mouse-branches", events, state=mouse_state))

    class LateKeyboard:
        pass

    class EarlyKeyboard:
        pass

    class RebindingMouseMeta(type):
        def __instancecheck__(cls, instance: Any) -> bool:
            support.emit(
                events, "dispatch.mouse-check", instance=type(instance).__name__
            )
            mediator_module.KeyboardEvent = LateKeyboard
            return False

    class RebindingMouse(metaclass=RebindingMouseMeta):
        pass

    host.react_mouse_event = lambda value: support.emit(
        events, "dispatch.mouse", value=type(value).__name__
    )
    host.react_keyboard_event = lambda value: support.emit(
        events, "dispatch.keyboard", value=type(value).__name__
    )
    with support.patched(
        mediator_module, MouseEvent=RebindingMouse, KeyboardEvent=EarlyKeyboard
    ):
        mediator_module.Mediator.react(host, LateKeyboard())

    class MouseClass:
        pass

    class KeyboardClass:
        pass

    class BothEvent(MouseClass, KeyboardClass):
        pass

    with support.patched(
        mediator_module, MouseEvent=MouseClass, KeyboardEvent=KeyboardClass
    ):
        mediator_module.Mediator.react(host, BothEvent())
    dispatch_events = [
        event["event"] for event in events if event["event"].startswith("dispatch.")
    ]
    if dispatch_events != [
        "dispatch.mouse-check",
        "dispatch.keyboard",
        "dispatch.mouse",
    ]:
        raise AssertionError("event global rebinding or mouse precedence changed")
    records.append(
        support.record("generic-event-dispatch", events, state=dispatch_events)
    )

    class KeyboardKind:
        KEY_UP = "up"

    class LateKeys:
        K_SPACE = 10
        K_1 = 11
        K_2 = 12
        K_3 = 13

    late_keys = LateKeys()

    class EarlyKeys:
        @property
        def K_SPACE(self) -> int:
            support.emit(events, "keyboard.pause-key")
            mediator_module.pygame = late_keys
            return 10

        K_1 = -1
        K_2 = -2
        K_3 = -3

    host.is_paused = False
    host.set_game_speed = lambda value: support.emit(
        events, "keyboard.speed", value=value
    )
    with support.patched(
        mediator_module, KeyboardEventType=KeyboardKind, pygame=late_keys
    ):
        mediator_module.Mediator.react_keyboard_event(
            host, SimpleNamespace(event_type="up", key=10)
        )
    with support.patched(
        mediator_module, KeyboardEventType=KeyboardKind, pygame=EarlyKeys()
    ):
        mediator_module.Mediator.react_keyboard_event(
            host, SimpleNamespace(event_type="up", key=13)
        )
    keyboard_state = {"paused": host.is_paused}
    speed_events = [event for event in events if event["event"] == "keyboard.speed"]
    if not host.is_paused or speed_events != [{"event": "keyboard.speed", "value": 4}]:
        raise AssertionError("keyboard pause or rebound speed mapping changed")
    records.append(support.record("keyboard-rebinding", events, state=keyboard_state))
    return {"events": events, "name": "input-dispatch", "records": records}
