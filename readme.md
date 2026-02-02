# Nine men's morris

Nine Men's Morris — core game implementation and simple CLI UI.

This module implements a playable, text-based Nine Men's Morris game
including the `Player`, `Board`, `Game` classes and a minimal
`NineMensMorrisUI` command-line interface. The implementation focuses
on clarity and correctness for game rules; docstrings and inline
comments were added for maintainability.
"""

### Classes

#### Classes, defined as following:

1. Player: 
    - performs the turn
    - has a name and a symbol
    - identified as human or ai
    - tracks the number of stones on board and in-hand

2. BoardManager
    - keeps track of board: empty and filled places
    - does not know anything about the game rules
    - performs actions, like placing, removing and moving pieces as requested

3. GamePhase(Enum):
    - a simple Enum mapping to various game phases to avoid typos

4. Game
    - Game engine, knows the rules of the game
    - acts as a referree, giving turns, telling current phsase
    - categorizes actions into various categories, then perform the required actions

5. NineMensMorrisUI
    - UI to play the game
    - Draws the board
    - Prints user prompts
    - Collects user input
    - Declares winner
    - (designed using ANSCII commands to make it colorful and interactive)
