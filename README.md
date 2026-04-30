# 9x9 Go Engine with MCTS AI (Multi-Core)

A fully-featured, GUI-based 9x9 Go engine built entirely in standard Python. It features a custom Monte Carlo Tree Search (MCTS) AI enhanced with multi-core Root Parallelism, tactical override heuristics, and true eye detection.

## Prerequisites

This application runs on **pure Python** with **zero external dependencies**. No `pip install` is required. It uses only the Python standard library (`tkinter`, `multiprocessing`, `math`, `random`, `time`).

- **Python Version:** Python 3.7 or higher

> **Note:** `tkinter` comes pre-installed with most Python distributions. If you encounter a `ModuleNotFoundError` for `tkinter`, install it via your system package manager (e.g., `sudo apt-get install python3-tk` on Ubuntu/Debian).

## How to Run

Navigate to the project folder and run:

```bash
python gui.py
```

*(On some systems, use `python3 gui.py` instead.)*

## File Structure

| File | Description |
|------|-------------|
| `engine.py` | Core Go rules engine — board state, legal move validation (including suicide and positional superko), stone placement, capture handling, undo/redo, and Chinese Area Scoring via flood-fill. |
| `ai.py` | MCTS AI with UCB1 tree policy, multi-core Root Parallelism, and layered tactical heuristics (Opening Book, Instant Capture/Escape, True Eye Protection, Anti-Self-Atari Guard). |
| `gui.py` | Tkinter-based graphical interface — interactive board rendering, click-to-place stones, game mode selection, score display, undo, and pass/concede. |

## Game Modes

Use the dropdown menu at the top of the window to select a mode:

| Mode | Description |
|------|-------------|
| **Human vs Human** | Two players alternate clicking to place stones. |
| **AI plays White** | Human plays Black, AI plays White. |
| **AI plays Black** | AI plays Black, Human plays White. |
| **AI vs AI** | Both sides are controlled by the AI. |

## Controls

| Button | Action |
|--------|--------|
| **Pass (Concede)** | Ends the game immediately. Final scores are calculated and the winner is displayed. |
| **Undo** | Reverts the last move. In AI modes, undoes both the AI's move and your previous move so it returns to your turn. |
| **Reset** | Clears the board and starts a new game. |

## Go Rules Implemented

- **Board:** 9×9 grid, Black plays first
- **Captures:** Groups with zero liberties are removed from the board
- **Suicide Rule:** A move that leaves your own group with zero liberties (without capturing any opponent stones) is illegal
- **Positional Superko:** Any board state that has previously occurred in the game is illegal to repeat
- **Scoring:** Chinese Area Scoring (stones on board + surrounded territory). White receives 2.5 komi (compensation for playing second)
- **Pass:** Passing concedes the game and triggers final scoring

## AI Architecture

The AI uses a multi-layered decision pipeline. Before each move, the following checks run in order:

1. **Opening Book** — On the very first move, randomly selects from curated 3-3 and 3-4 star point positions.
2. **Instant Capture Override** — If an opponent group of 2+ stones has only 1 liberty, capture it immediately without running MCTS.
3. **Instant Escape Override** — If one of the AI's own groups is in atari, attempt to extend it (only if extending gains more than 1 liberty, to avoid ladder traps).
4. **Pass Override** — If all remaining legal moves are true eyes or pure self-ataris, pass instead of self-destructing.
5. **MCTS with Root Parallelism** — Spawns independent MCTS trees across all available CPU cores. Each core runs UCB1-guided tree search with smart rollouts (true eye protection + atari capture heuristic). Results are aggregated by merging visit/win counts across all cores.
6. **Anti-Self-Atari Guard** — After MCTS selects the best move, a final safety check rejects any move that would place the AI into atari without capturing anything.

## Configuration

AI parameters are set in `gui.py` (line 14):

```python
self.ai = GoAI(time_limit=5, iteration_cap=30000)
```

| Parameter | Description |
|-----------|-------------|
| `time_limit` | Maximum seconds the AI is allowed to think per move. |
| `iteration_cap` | Maximum total MCTS iterations across all cores. |

The number of CPU cores used is auto-detected in `ai.py` (line 366):

```python
num_cores = max(1, min(16, multiprocessing.cpu_count() - 1))
```

This automatically uses all available cores minus one (reserved for the OS and GUI). To force a specific number, replace the expression with a constant (e.g., `num_cores = 4`).
