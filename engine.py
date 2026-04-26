"""
Go Engine & AI Architecture Report
==================================

a) AI Strategy and Why You Chose It:
We implemented Monte Carlo Tree Search (MCTS) utilizing the UCB1 formula for 
tree traversal, supplemented by an Opening Book and two custom simulation 
heuristics (Eye-Protection and Atari-Capture). We chose MCTS because classic 
Minimax with Alpha-Beta pruning fails catastrophically on the 9x9 Go board due 
to the massive branching factor and the near-impossibility of writing an 
accurate static evaluation function for unfinished mid-game territory. MCTS 
elegantly bypasses this by statistically sampling random future paths to the 
end of the game. Because it doesn't require hardcoded weights, it scales 
dynamically with CPU limits, allowing stronger AI just by increasing time limits.

b) Interesting Design Decisions & Challenges:
- Design Decision (Separation of Concerns): We strictly decoupled the logic 
  into engine.py (ruleset/scoring), gui.py (Tkinter visual layer), and ai.py 
  (MCTS). This allowed MCTS to run tens of thousands of headless board copies 
  without causing the Tkinter mainloop() to hang or drag.
- Challenge (The Rollout Quality vs Speed tradeoff): Purely random MCTS 
  rollouts struggled immensely because the ghost players would randomly fill 
  their own single-point "eyes", effectively committing suicide and destroying 
  their own territories at the end of simulations. 
- Solution: We injected "Smart Heuristics" into the simulation loop. We added 
  a quick-check algorithm to prevent playing into completely surrounded friendly 
  spaces, and a localized override to instantly capture 1-liberty opponent 
  stones. The challenge was that calculating liberties during the fast-forward 
  phase heavily tanked the simulation speed. We resolved this by gating the 
  capture-check behind a simple adjacency scan, preserving our iteration volume 
  while massively increasing realistic play.

c) Testing Methodology Beyond Provided Suites:
1. Positional Superko Verification: We tested the history_set hash manually in 
   "Human vs Human" mode by forcing classic repeating snapback loops. We 
   verified the engine accurately blocked the immediate recapture strings.
2. AI Trap Testing: We evaluated the UCB1 algorithm's exploration balance by 
   artificially trapping the AI in a setup where a highly tempting "capture" 
   move actually resulted in a massive loss of territory on the next turn. By 
   forcing the timer to 20s, we verified that the MCTS correctly identified 
   the statistical trap and avoided the capture in favor of solid structure.
3. Scoring Edge Cases: The Chinese Area Scoring was tested via the Flood-Fill 
   algorithm. We specifically tested highly fragmented boards with scattered, 
   unconnected stones to ensure that "contested" empty territory (touching both 
   Black and White) mathematically evaluated to 0 points.
"""

class GoEngine:
    def __init__(self, size=9):
        self.size = size
        # 0 = empty, 1 = Black, 2 = White
        self.board = [[0 for _ in range(size)] for _ in range(size)]
        self.current_player = 1 # Black plays first
        self.history_set = set() # For Superko rule
        self.history_set.add(self._board_to_tuple(self.board))
        self.game_over = False
        self.captures = {1: 0, 2: 0} # 1: Black's captures, 2: White's captures
        
        self.last_move = None # To highlight the most recent move
        self.winner = None
        self.final_scores = {1: 0, 2: 2.5} # White gets 2.5 komi
        self.state_stack = []

    def _create_snapshot(self):
        return {
            'board': [row[:] for row in self.board],
            'current_player': self.current_player,
            'history_set': set(self.history_set),
            'game_over': self.game_over,
            'captures': dict(self.captures),
            'last_move': self.last_move,
            'winner': self.winner,
            'final_scores': dict(self.final_scores)
        }

    def undo(self):
        if not self.state_stack:
            return False
            
        state = self.state_stack.pop()
        self.board = state['board']
        self.current_player = state['current_player']
        self.history_set = state['history_set']
        self.game_over = state['game_over']
        self.captures = state['captures']
        self.last_move = state['last_move']
        self.winner = state['winner']
        self.final_scores = state['final_scores']
        return True

    def _board_to_tuple(self, board):
        return tuple(tuple(row) for row in board)

    def get_board(self):
        return self.board

    def get_current_player(self):
        return self.current_player

    def is_game_over(self):
        return self.game_over
        
    def get_last_move(self):
        return self.last_move

    def pass_turn(self):
        """As per rules, passing means conceding the game and immediately ends it."""
        self.state_stack.append(self._create_snapshot())
        self.game_over = True
        self.compute_score()

    def get_opponent(self, player):
        return 2 if player == 1 else 1

    def _get_adjacent(self, r, c):
        adj = []
        if r > 0: adj.append((r-1, c))
        if r < self.size - 1: adj.append((r+1, c))
        if c > 0: adj.append((r, c-1))
        if c < self.size - 1: adj.append((r, c+1))
        return adj

    def _get_group_and_liberties(self, board, r, c):
        """Returns (set of coordinates in the group, set of liberty coordinates)"""
        color = board[r][c]
        if color == 0:
            return set(), set()
            
        group = set()
        liberties = set()
        queue = [(r, c)]
        
        while queue:
            curr_r, curr_c = queue.pop()
            if (curr_r, curr_c) in group:
                continue
            group.add((curr_r, curr_c))
            
            for adj_r, adj_c in self._get_adjacent(curr_r, curr_c):
                if board[adj_r][adj_c] == 0:
                    liberties.add((adj_r, adj_c))
                elif board[adj_r][adj_c] == color and (adj_r, adj_c) not in group:
                    queue.append((adj_r, adj_c))
                    
        return group, liberties

    def is_legal_move(self, r, c):
        if self.game_over:
            return False
            
        if not (0 <= r < self.size and 0 <= c < self.size):
            return False
            
        if self.board[r][c] != 0:
            return False # Intersection is already occupied

        # Simulate the move
        sim_board = [row[:] for row in self.board]
        sim_board[r][c] = self.current_player
        opponent = self.get_opponent(self.current_player)
        
        # Check captures first
        captured_stones = 0
        for adj_r, adj_c in self._get_adjacent(r, c):
            if sim_board[adj_r][adj_c] == opponent:
                grp, libs = self._get_group_and_liberties(sim_board, adj_r, adj_c)
                if len(libs) == 0:
                    # Opponent group is captured! Remove it.
                    captured_stones += len(grp)
                    for grp_r, grp_c in grp:
                        sim_board[grp_r][grp_c] = 0
                        
        # Now check if our own group has 0 liberties (Suicide rule)
        my_grp, my_libs = self._get_group_and_liberties(sim_board, r, c)
        if len(my_libs) == 0:
            # Suicide is only legal if it captures opponent stones. 
            # In our simulation, opponent stones were already removed if captured.
            # If after removal we STILL have 0 liberties, it was a true suicide.
            return False

        # Ko rule: Check if board state has occurred before
        sim_state = self._board_to_tuple(sim_board)
        if sim_state in self.history_set:
            return False
            
        return True

    def place_stone(self, r, c):
        if not self.is_legal_move(r, c):
            return False
            
        # Move is legal, save state
        self.state_stack.append(self._create_snapshot())
            
        # Move is legal, update actual state
        opponent = self.get_opponent(self.current_player)
        self.board[r][c] = self.current_player
        
        # Handle captures
        captured_this_turn = 0
        for adj_r, adj_c in self._get_adjacent(r, c):
            if self.board[adj_r][adj_c] == opponent:
                grp, libs = self._get_group_and_liberties(self.board, adj_r, adj_c)
                if len(libs) == 0:
                    captured_this_turn += len(grp)
                    for grp_r, grp_c in grp:
                        self.board[grp_r][grp_c] = 0
                        
        self.captures[self.current_player] += captured_this_turn
        self.history_set.add(self._board_to_tuple(self.board))
        self.last_move = (r, c)
        
        # Switch turn
        self.current_player = self.get_opponent(self.current_player)
        return True

    def compute_score(self):
        """Calculates Chinese area scoring using Flood Fill."""
        black_stones = 0
        white_stones = 0
        
        # Count stones on board
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == 1:
                    black_stones += 1
                elif self.board[r][c] == 2:
                    white_stones += 1
                    
        # Find territories
        visited_empty = set()
        black_territory = 0
        white_territory = 0
        
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == 0 and (r, c) not in visited_empty:
                    # Flood fill empty region
                    region = set()
                    touches_black = False
                    touches_white = False
                    queue = [(r, c)]
                    
                    while queue:
                        curr_r, curr_c = queue.pop()
                        if (curr_r, curr_c) in region:
                            continue
                        region.add((curr_r, curr_c))
                        visited_empty.add((curr_r, curr_c))
                        
                        for adj_r, adj_c in self._get_adjacent(curr_r, curr_c):
                            if self.board[adj_r][adj_c] == 0 and (adj_r, adj_c) not in region:
                                queue.append((adj_r, adj_c))
                            elif self.board[adj_r][adj_c] == 1:
                                touches_black = True
                            elif self.board[adj_r][adj_c] == 2:
                                touches_white = True
                                
                    if touches_black and not touches_white:
                        black_territory += len(region)
                    elif touches_white and not touches_black:
                        white_territory += len(region)
                        
        self.final_scores[1] = black_stones + black_territory
        self.final_scores[2] = white_stones + white_territory + 2.5 # Komi
        
        if self.final_scores[1] > self.final_scores[2]:
            self.winner = "Black"
        elif self.final_scores[2] > self.final_scores[1]:
            self.winner = "White"
        else:
            self.winner = "Tie" # Should not happen with 2.5 komi

        return self.final_scores, self.winner, black_stones, white_stones
