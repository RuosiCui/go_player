# 9x9 Go Engine with MCTS Artificial Intelligence

This is a fully-featured, GUI-based 9x9 Go Engine built entirely in standard Python. It features a custom-built Monte Carlo Tree Search (MCTS) Artificial Intelligence capable of playing either Black or White.

## Prerequisites

This application runs natively on pure Python and has **zero external dependencies**. No `pip install` commands are required! 
It utilizes the `tkinter` graphics library, which comes pre-installed as a standard library in almost all Python distributions.

*   **Python Version:** Python 3.7 or higher.

## How to Run

To launch the Go application, navigate to the folder containing the source files and run the main GUI script:

```bash
python gui.py
```
*(Depending on your system, you may need to use `python3 gui.py`)*

## How to Play

Upon launching the application, you will see the 9x9 Go board. 
Black always plays the first move.

### 1. Selecting Game Modes
In the top-left corner, use the dropdown menu to select your desired game mode:
*   **Human vs Human:** Pass the mouse back and forth to play against a friend.
*   **AI plays White:** Play as Black (you go first). The computer will automatically calculate and respond to your moves.
*   **AI plays Black:** Play as White. The computer will immediately play the first move.
*   **AI vs AI:** Watch the computer play a full game against itself.

**Note:** If you change the game mode mid-game, the board will automatically reset to a fresh game.

### 2. Placing Stones
Simply click anywhere on a grid intersection to place a stone. The engine will instantly mathematically verify your move.
*   **Illegal Moves:** If you attempt to place a stone on an occupied space, trigger Positional Superko (repeating a past board state exactly), or commit Suicide (playing into a spot yielding 0 liberties without capturing), the engine will block your move and briefly flash a red **"X"** on the screen.

### 3. Ending the Game
In this ruleset, you cannot arbitrarily "Pass" your turn to skip a move. 
If you can no longer legally play anywhere on the board without committing suicide, or if you believe the game is structurally over, click the **Pass (Concede)** button at the top of the screen. 

This will instantly end the game. The engine will use a Flood-fill algorithm to calculate the final Chinese Area Score automatically (with a 2.5 Komi advantage already applied to White) and declare the winner!

## Architecture Summary
*   **`engine.py`**: The mathematical core. Contains the board state, superko hashes, liberty calculations, and area scoring.
*   **`ai.py`**: The Artificial Intelligence. Runs Monte Carlo Tree Search with an Opening Book hook and UCB1 formulas.
*   **`gui.py`**: The Tkinter graphical interface. Processes user clicks and safely handles AI asynchronous thinking loops.
