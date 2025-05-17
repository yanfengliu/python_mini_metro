from api import StaticStationGame


game = StaticStationGame(gamespeed=100, visuals=True)

print(game.run(
    ([0, 2, 4, 6, 8], True)
))
game.visuals = False
print(game.run(
    ([0, 2, 4, 6, 8], True)
))