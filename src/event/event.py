from __future__ import annotations

from abc import ABC

from event.type import KeyboardEventType, MouseEventType


class Event(ABC):
    def __init__(self, event_type: MouseEventType | KeyboardEventType) -> None:
        self.event_type = event_type
