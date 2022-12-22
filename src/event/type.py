from enum import Enum


class MouseEventType(Enum):
    MOUSE_DOWN = "1"
    MOUSE_UP = "2"
    MOUSE_MOTION = "3"


class KeyboardEventType(Enum):
    KEY_DOWN = "1"
    KEY_UP = "2"
