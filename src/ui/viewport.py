from dataclasses import dataclass


@dataclass(frozen=True)
class ViewportTransform:
    scale: float
    offset_x: int
    offset_y: int
    width: int
    height: int

    def map_window_to_virtual(
        self, x: int, y: int, virtual_width: int, virtual_height: int
    ) -> tuple[int, int] | None:
        within_x = self.offset_x <= x < (self.offset_x + self.width)
        within_y = self.offset_y <= y < (self.offset_y + self.height)
        if not (within_x and within_y):
            return None

        virtual_x = int((x - self.offset_x) / self.scale)
        virtual_y = int((y - self.offset_y) / self.scale)

        # Clamp right/bottom edges when rounding pushes to boundary.
        virtual_x = min(max(virtual_x, 0), virtual_width - 1)
        virtual_y = min(max(virtual_y, 0), virtual_height - 1)
        return (virtual_x, virtual_y)


def get_viewport_transform(
    window_width: int,
    window_height: int,
    virtual_width: int,
    virtual_height: int,
) -> ViewportTransform:
    scale = min(window_width / virtual_width, window_height / virtual_height)
    viewport_width = int(virtual_width * scale)
    viewport_height = int(virtual_height * scale)
    offset_x = (window_width - viewport_width) // 2
    offset_y = (window_height - viewport_height) // 2
    return ViewportTransform(
        scale=scale,
        offset_x=offset_x,
        offset_y=offset_y,
        width=viewport_width,
        height=viewport_height,
    )
