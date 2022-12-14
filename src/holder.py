from abc import ABC, abstractmethod


class Holder(ABC):
    def __init__(self, shape) -> None:
        self.shape = shape
        self.passengers = []
        self.capacity = 0
        self.id = "Base holder, which should NOT be instantiated."

    def __repr__(self) -> str:
        return self.id

    @abstractmethod
    def draw(self, surface):
        pass

    def has_room(self, requested_num=1):
        return self.capacity - len(self.passengers) >= requested_num

    def add_passenger(self, passenger):
        if self.has_room():
            self.passengers.append(passenger)
            passenger.set_holder(self)
        else:
            raise RuntimeError(f"{self} has no room for {passenger}.")

    def move_passenger(self, passenger, holder):
        if passenger in self.passengers:
            if holder.has_room():
                self.passengers.remove(passenger)
                holder.add_passenger(passenger)
            else:
                raise RuntimeError(f"{holder} has no room for {passenger}.")
        else:
            raise LookupError(f"{passenger} is not in {self}.")
