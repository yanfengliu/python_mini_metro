from geometry.type import ShapeType

# game
framerate = 60

# screen
screen_width = 1920
screen_height = 1080
screen_color = (255, 255, 255)
border_padding = 100

# airport
num_airports = 10
airport_size = 30
airport_capacity = 12
airport_color = (0, 0, 0)
airport_shape_type_list = [
    ShapeType.RECT,
    ShapeType.CIRCLE,
    ShapeType.TRIANGLE,
    ShapeType.CROSS,
]
airport_passengers_per_row = 4
airport_spawn_interval = 1250

# passenger
passenger_size = 5
passenger_color = (128, 128, 128)
passenger_spawning_start_step = 1
passenger_spawning_interval_step = 10 * framerate
passenger_display_buffer = 3 * passenger_size

# plane
num_planes = 4
plane_size = 30
plane_color = (200, 200, 200)
plane_capacity = 6
plane_speed_per_ms = 150 / 1000  # pixels / ms
plane_passengers_per_row = 3

# path
num_paths = 3
path_width = 10
path_order_shift = 10

# button
button_color = (180, 180, 180)
button_size = 30

# path button
path_button_buffer = 20
path_button_dist_to_bottom = 50
path_button_start_left = 500
path_button_cross_size = 25
path_button_cross_width = 5

# text
score_font_size = 50
score_display_coords = (20, 20)

airport_max_passengers = 6
overcrowd_time_limit_ms = 20_000  # 20 seconds
