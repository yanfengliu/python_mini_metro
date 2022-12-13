class Station:
    def __init__(self, position, shape) -> None:
        self.position = position
        self.shape = shape
        self.capacity = 10

    def draw(self, surface):
        self.shape.draw(surface, self.position)
