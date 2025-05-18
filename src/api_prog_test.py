from api import ProgressiveStationGame


gamespeed = 50
in_game_break_time = (999999999999999999999/gamespeed) * 1000 # stop periodic yielding

game = ProgressiveStationGame(gamespeed=gamespeed, yield_interval_ms=in_game_break_time, visuals=True)

simulation = game.run()

def do_actions():
    if len(game.stations) < 2:
        return

    if len(game.paths) == 0:
        game.initialize_paths(
            ([i for i in range(len(game.stations))], True),
        )
    else:
        game.recreate_path(0, ([i for i in range(len(game.stations))], True))

try:
    while True:
        next(simulation)
        do_actions()
except StopIteration as score:
    print("Score:", score)


