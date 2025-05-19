# handling path
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

# start of code

from api import StaticStationGame
from timer_util import Timer

"""
Example:
    A static AI agent that creates 3 paths that go through certain stations in order.
        (does not update the paths)
"""

timer = Timer()
game = StaticStationGame(gamespeed=50, visuals=True)

timer.start()

print(game.run(
    ([0, 2, 4, 6, 8], True),
    ([0, 1, 3, 5, 7], True),
    ([1, 3, 7, 9, 5], True)
))

print("v=True, Time taken:", timer.end())

game.visuals = False

timer.start()

print(game.run(
    ([0, 2, 4, 6, 8], True),
    ([0, 1, 3, 5, 7], True),
    ([1, 3, 7, 9, 5], True)
))

print("v=False, Time taken:", timer.end())