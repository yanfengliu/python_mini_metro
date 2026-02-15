import pygame
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from utils import tuple_to_point


def convert_pygame_event(
    event: pygame.event.Event,
    mouse_position: tuple[int, int] | None = None,
):
    if event.type == pygame.MOUSEBUTTONDOWN:
        position = mouse_position if mouse_position is not None else pygame.mouse.get_pos()
        return MouseEvent(MouseEventType.MOUSE_DOWN, tuple_to_point(position))
    elif event.type == pygame.MOUSEBUTTONUP:
        position = mouse_position if mouse_position is not None else pygame.mouse.get_pos()
        return MouseEvent(MouseEventType.MOUSE_UP, tuple_to_point(position))
    elif event.type == pygame.MOUSEMOTION:
        position = mouse_position if mouse_position is not None else pygame.mouse.get_pos()
        return MouseEvent(MouseEventType.MOUSE_MOTION, tuple_to_point(position))
    elif event.type == pygame.KEYUP:
        return KeyboardEvent(KeyboardEventType.KEY_UP, event.key)
