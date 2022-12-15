import enum


class ShapeType(enum.Enum):
    RECT = "1"
    CIRCLE = "2"
    POLYGON = "3"


station_shape_list = [ShapeType.RECT, ShapeType.CIRCLE]
