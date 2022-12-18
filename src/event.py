from __future__ import annotations

from abc import ABC
from enum import Enum

from geometry.point import Point


class MouseEventType(Enum):
    MOUSE_DOWN = "1"
    MOUSE_UP = "2"
    MOUSE_MOTION = "3"


class KeyboardEventType(Enum):
    KEY_DOWN = "1"
    KEY_UP = "2"


class Event(ABC):
    def __init__(self, event_type: MouseEventType | KeyboardEventType) -> None:
        self.event_type = event_type


class MouseEvent(Event):
    def __init__(self, event_type: MouseEventType, position: Point) -> None:
        super().__init__(event_type)
        self.position = position


class KeyboardEvent(Event):
    def __init__(self, event_type: KeyboardEventType, key) -> None:
        super().__init__(event_type)
        self.key = key
