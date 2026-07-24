"""Line, station, and economy progression state and pure policy."""

from collections.abc import Sequence


class NetworkProgression:
    """Own network-progression rules, counters, and explicitly updated caches."""

    def __init__(
        self,
        *,
        num_paths: int,
        path_unlock_milestones: Sequence[int],
        num_stations: int,
        initial_num_stations: int,
        station_unlock_milestones: Sequence[int],
    ) -> None:
        self.num_paths = num_paths
        self.path_unlock_milestones = sorted(path_unlock_milestones)
        self.path_purchase_prices = self.get_path_purchase_prices()
        self.num_stations = num_stations
        self.initial_num_stations = initial_num_stations
        self.station_unlock_milestones = sorted(station_unlock_milestones)

        self.deliveries = 0
        self.line_credits = 0
        self.purchased_num_paths = 1
        self.unlocked_num_paths = self.get_unlocked_num_paths()
        self.unlocked_num_stations = self.get_unlocked_num_stations()

    def get_path_purchase_prices(self) -> list[int]:
        if self.num_paths <= 1:
            return []
        return [
            self.path_unlock_milestones[index] - self.path_unlock_milestones[index - 1]
            for index in range(1, self.num_paths)
        ]

    def get_unlocked_num_stations(self) -> int:
        unlocked = self.initial_num_stations + sum(
            1
            for milestone in self.station_unlock_milestones
            if self.deliveries >= milestone
        )
        return min(unlocked, self.num_stations)

    def set_unlocked_num_stations(self, value: int) -> tuple[int, int]:
        previous = self.unlocked_num_stations
        self.unlocked_num_stations = value
        return previous, value

    def get_unlocked_num_paths(self) -> int:
        return min(max(1, self.purchased_num_paths), self.num_paths)

    def set_unlocked_num_paths(self, value: int) -> tuple[int, int]:
        previous = self.unlocked_num_paths
        self.unlocked_num_paths = value
        return previous, value

    def get_next_path_button_idx_to_purchase(self) -> int | None:
        if self.unlocked_num_paths >= self.num_paths:
            return None
        return self.unlocked_num_paths

    def get_purchase_price_for_path_button_idx(self, button_idx: int) -> int | None:
        if button_idx <= 0 or button_idx >= self.num_paths:
            return None
        return self.path_purchase_prices[button_idx - 1]

    def can_purchase_path_button_idx(self, button_idx: int) -> bool:
        return self.can_purchase_resolved_path_button_idx(
            button_idx,
            next_button_idx=self.get_next_path_button_idx_to_purchase(),
            price=self.get_purchase_price_for_path_button_idx(button_idx),
        )

    def can_purchase_resolved_path_button_idx(
        self,
        button_idx: int,
        *,
        next_button_idx: int | None,
        price: int | None,
    ) -> bool:
        """Evaluate a purchase using queries resolved by the owning facade."""

        if next_button_idx is None or next_button_idx != button_idx:
            return False
        return price is not None and self.line_credits >= price

    def record_path_purchase(self, price: int) -> None:
        """Apply a purchase already validated against the player-facing button."""

        self.line_credits -= price
        self.purchased_num_paths += 1

    def grant_free_path(self) -> bool:
        """Grant one line for free (a weekly NEW_LINE offer, GM-10d): unlock the next
        line without spending credits, capped at ``num_paths``. Returns True if a line
        was granted, False if already at the cap (a no-op). Mirrors
        ``record_path_purchase`` minus the credit spend, with the cap the purchase path
        gets implicitly (a purchase is only offered while below ``num_paths``)."""

        if self.purchased_num_paths >= self.num_paths:
            return False
        self.purchased_num_paths += 1
        return True

    def record_delivery(self) -> None:
        """Award one lifetime delivery and one spendable line credit."""

        self.deliveries += 1
        self.line_credits += 1
