from event.event import Event
from event.type import KeyboardEventType


class KeyboardEvent(Event):
    def __init__(self, event_type: KeyboardEventType, key) -> None:
        super().__init__(event_type)
        self.key = key
