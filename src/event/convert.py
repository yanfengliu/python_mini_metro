import pygame

from event.event import Event
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from utils import tuple_to_point


def convert_pygame_event(event: pygame.event.Event):
    if event.type == pygame.MOUSEBUTTONDOWN:
        mouse_position = tuple_to_point(pygame.mouse.get_pos())
        return MouseEvent(MouseEventType.MOUSE_DOWN, mouse_position)
    elif event.type == pygame.MOUSEBUTTONUP:
        mouse_position = tuple_to_point(pygame.mouse.get_pos())
        return MouseEvent(MouseEventType.MOUSE_UP, mouse_position)
    elif event.type == pygame.MOUSEMOTION:
        mouse_position = tuple_to_point(pygame.mouse.get_pos())
        return MouseEvent(MouseEventType.MOUSE_MOTION, mouse_position)
    elif event.type == pygame.KEYUP:
        return KeyboardEvent(KeyboardEventType.KEY_UP, event.key)
