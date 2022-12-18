from geometry.type import ShapeType

# game
framerate = 60

# screen
screen_width = 1920
screen_height = 1080

# station
num_stations = 10
station_size = 30
station_capacity = 12
station_color = (0, 0, 0)
station_shape_type_list = [ShapeType.RECT, ShapeType.CIRCLE]
station_passengers_per_row = 4

# passenger
passenger_size = 5
passenger_color = (128, 128, 128)
passenger_spawning_start_step = 1
passenger_spawning_interval_step = 10 * framerate
passenger_display_buffer = 3 * passenger_size

# metro
num_metros = 4
metro_size = 30
metro_color = (200, 200, 200)
metro_capacity = 6
metro_speed_per_ms = 150 / 1000  # pixels / ms
metro_passengers_per_row = 3

# path
num_path = 3
path_width = 10
