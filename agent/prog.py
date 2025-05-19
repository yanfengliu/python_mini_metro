# handling path
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

# start of code

from api import ProgressiveStationGame


gamespeed = 100
in_game_break_time = (999999999999999999999/gamespeed) * 1000 # stop periodic yielding

game = ProgressiveStationGame(gamespeed=gamespeed, yield_interval_ms=in_game_break_time, visuals=True)

simulation = game.run()


"""
Example:
    A progressive AI agent that creates one path that goes through all stations in order.
        (updates the path every time a new station spawns)
    and clears the path if there are more than 5 stations.
"""

def do_actions():
    print("station cnt:", len(game.stations))

    if len(game.stations) < 2:
        return

    if len(game.stations) == 2:
        game.initialize_paths(
            ([i for i in range(len(game.stations))], False),
        )
    elif len(game.stations) >= 5:
        for i in range(len(game.paths)):
            game.delete_path(i)
    else:
        game.recreate_path(0, ([i for i in range(len(game.stations))], True))

try:
    while True:
        next(simulation)
        do_actions()
except StopIteration as score:
    print("Score:", score)


