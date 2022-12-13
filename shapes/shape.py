from abc import ABC, abstractmethod


class Shape(ABC):
    def __init__(self, type):
        self.type = type

    @abstractmethod
    def draw(self, surface, position):
        pass
