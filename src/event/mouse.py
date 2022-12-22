from event.event import Event
from event.type import MouseEventType
from geometry.point import Point


class MouseEvent(Event):
    def __init__(self, event_type: MouseEventType, position: Point) -> None:
        super().__init__(event_type)
        self.position = position
