import enum


class ShapeType(enum.Enum):
    RECT = "1"
    CIRCLE = "2"
    LINE = "3"
    POLYGON = "4"


station_shape_list = [ShapeType.RECT, ShapeType.CIRCLE]
