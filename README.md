# python_mini_metro
Python implementation for Mini Metro. The goal of this `ai` branch is to test the abilities of ChatGPT 4.0 and have it write as much code and doc as possible.

## Player action options:

Create a new subway line: Players can create a new subway line by connecting unconnected stations. They are limited by the number of lines available.
Add a train: Players can add a train to a line to increase its capacity and efficiency.
Add carriages: Players can add carriages to a train to increase its capacity.
Modify lines: Players can modify existing lines by adding or removing stations or changing the line's route.
Use upgrades: As the game progresses, players earn upgrades, like additional lines, trains, carriages, or unique upgrades like tunnels, bridges, and interchange stations. Players can apply these upgrades to improve their network.

## Goal

The goal of Mini Metro is to build and maintain an efficient subway network to transport passengers to their desired stations while avoiding overcrowding.

## Win conditions

Mini Metro does not have a specific win condition. The objective is to transport as many passengers as possible and keep the city moving. Players try to achieve a high score by maximizing the number of passengers transported.

## Lose conditions

The game ends when one of the stations becomes overcrowded for an extended period. This is represented by a station's passenger capacity circle filling up entirely.

# Roadmap

To start, let's break down the game into its main components and create a plan for implementing each component. We can organize the project into the following classes:

* Game: Represents the main game loop and game state management.
* City: Represents the city map and handles the creation and management of stations.
* Station: Represents individual stations and their properties, such as location, station type, and passenger capacity.
* Line: Represents subway lines and their properties, such as the list of stations it connects and the trains running on it.
* Train: Represents individual trains and their properties, such as their current position, speed, capacity, and the line they're on.
* Passenger: Represents individual passengers and their properties, such as their current location, destination, and waiting time.
We can also create some utility classes and functions for handling game-related calculations, like pathfinding and distance calculations.

Here's a plan to implement each component:

1. Define the classes and their properties.
1. Implement the methods for each class to handle their respective logic.
1. Create a game loop in the Game class that handles user input, updates the game state, and renders the game.
1. Implement the logic for generating new stations in the City class.
1. Implement the logic for creating and managing lines in the Line class.
1. Implement the logic for moving trains along lines and picking up/dropping off passengers in the Train class.
1. Implement the logic for managing passengers in the Passenger class.
1. Implement the logic for handling upgrades and game progression in the Game class.
1. Add graphical representation and user interface for the game.
