from api import StaticStationGame


game = StaticStationGame(gamespeed=20, visuals=False)

# print(game.stations)
# print(game.paths)
# print(game.current_score)

print("Stations:")
for s in game.stations:
    print(s.position.left, s.position.top)

print("\nPaths:")
for p in game.paths:
    print(p.path_order, p.is_looped)

score = game.run(
    ([0, 2, 4, 6, 8], True),
    ([0, 1, 3, 5, 7, 9], True),
)

print(score)