import math

import pygame
from config import screen_width, screen_height

def lerp_color(a, b, t):
    return tuple((a[i] + (b[i] - a[i]) * t) for i in range(3))

def draw_wave_surface(screen, time, base_y, i=0):
    y_ratio = base_y / screen_height

    base_y = screen_height * y_ratio
    
    wave_height = 5 + 5 * y_ratio
    wave_length = 100 + 50 * y_ratio
    direction = 1 if i % 2 else -1
    points = []


    for x in range(0, screen_width + 5, 5):
        y = base_y + math.sin((x + direction * time) / wave_length * 2 * math.pi) * wave_height
        points.append((x, y))

    # Add corners to make a filled polygon (sea)
    points.append((screen_width, screen_height))
    points.append((0, screen_height))

    pygame.draw.polygon(screen, lerp_color((117, 182, 255), (23, 133, 255), y_ratio), points)

def draw_waves(screen, time):
    for i in range(1, 5):
        height = i / 5 * screen_height
        draw_wave_surface(screen, (time + 0.6 * i) * 0.025 * (1 + i / 10), height, i)