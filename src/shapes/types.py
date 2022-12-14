from enum import Enum

ShapeType = Enum("ShapeType", ["RECT", "CIRCLE", "LINE", "POLYGON"])
station_shape_list = [ShapeType.RECT, ShapeType.CIRCLE]
