from abc import ABC
from enum import Enum

from geometry.point import Point


class EventType(Enum):
    MOUSE_DOWN = "1"
    MOUSE_UP = "2"
    MOUSE_MOTION = "3"


class Event(ABC):
    def __init__(self, event_type: EventType) -> None:
        self.event_type = event_type


class MouseEvent(Event):
    def __init__(self, event_type: EventType, position: Point) -> None:
        super().__init__(event_type)
        self.position = position
