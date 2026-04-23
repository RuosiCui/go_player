import random
import time
import math
from engine import GoEngine

class MCTSNode:
    def __init__(self, snapshot, move=None, parent=None):
        self.snapshot = snapshot
        self.move = move
        self.parent = parent
        self.children = []
        self.visits = 0
        self.wins = 0
        self.player_just_moved = 1 if snapshot['current_player'] == 2 else 2
        self.untried_moves = self._get_legal_moves()
        
    def _get_legal_moves(self):
        eng = GoEngine()
        eng.size = len(self.snapshot['board'])
        eng.board = [row[:] for row in self.snapshot['board']]
        eng.current_player = self.snapshot['current_player']
        eng.history_set = set(self.snapshot['history_set'])
        eng.game_over = self.snapshot['game_over']
        
        if eng.game_over:
            return []
            
        legal = []
        for r in range(eng.size):
            for c in range(eng.size):
                if eng.board[r][c] == 0 and eng.is_legal_move(r, c):
                    legal.append((r, c))
                    
        # In MCTS, we represent a pass as None
        if not legal:
            legal.append(None)
        return legal


class GoAI:
    def __init__(self, time_limit=1.5, iteration_cap=200000):
        # Time limit serves as a stopwatch; iteration_cap serves as a goal tracker.
        self.time_limit = time_limit
        self.iteration_cap = iteration_cap

    def get_best_move(self, engine):
        # Opening Book Heuristic: Restrict to 1-space radius around the four (3,3) star points
        empty_count = sum(row.count(0) for row in engine.board)
        if empty_count >= (engine.size * engine.size) - 1:
            valid_openings = set()
            # The four (3,3) "star points" on a 9x9 board in 0-indexed coordinates
            star_points = [(2, 2), (2, 6), (6, 2), (6, 6)]
            
            for sr, sc in star_points:
                # 1 extra space in all directions (3x3 grid around the center)
                for r in range(sr - 1, sr + 2):
                    for c in range(sc - 1, sc + 2):
                        if 0 <= r < engine.size and 0 <= c < engine.size:
                            if engine.board[r][c] == 0 and engine.is_legal_move(r, c):
                                valid_openings.add((r, c))
                                
            if valid_openings:
                chosen = random.choice(list(valid_openings))
                print(f"Opening Book triggered (Star Point Cluster). Chosen move: {chosen}")
                return chosen

        # Instant Capture Override: If there is a free kill, take it instantly and skip MCTS.
        # If there are multiple kills, prioritize the one that kills the MOST stones.
        opponent = 2 if engine.current_player == 1 else 1
        best_capture_move = None
        max_capture_size = 0
        
        for r in range(engine.size):
            for c in range(engine.size):
                if engine.board[r][c] == 0:
                    adjacents = engine._get_adjacent(r, c)
                    has_opponent_adj = any(engine.board[ar][ac] == opponent for ar, ac in adjacents)
                    
                    if has_opponent_adj and engine.is_legal_move(r, c):
                        current_capture_size = 0
                        # Check how many stones this move would actually capture
                        for ar, ac in adjacents:
                            if engine.board[ar][ac] == opponent:
                                grp, libs = engine._get_group_and_liberties(engine.board, ar, ac)
                                if len(libs) == 1:
                                    current_capture_size += len(grp)
                                    
                        if current_capture_size > max_capture_size:
                            max_capture_size = current_capture_size
                            best_capture_move = (r, c)
                            
        if best_capture_move:
            print(f"Instant Capture Override! Slaughtered {max_capture_size} stones at {best_capture_move}")
            return best_capture_move

        # Instant Escape Override: If our group is in Atari, try to save it!
        # If multiple groups are in Atari, prioritize saving the largest one.
        me = engine.current_player
        best_escape_move = None
        max_escape_size = 0
        
        checked_groups = set()
        for r in range(engine.size):
            for c in range(engine.size):
                if engine.board[r][c] == me and (r, c) not in checked_groups:
                    grp, libs = engine._get_group_and_liberties(engine.board, r, c)
                    checked_groups.update(grp)
                    
                    if len(libs) == 1:
                        # We are in Atari! Gather the only escape coordinate.
                        lr, lc = list(libs)[0]
                        if engine.is_legal_move(lr, lc):
                            # Test if playing here actually gives us more liberties (avoiding 'ladders')
                            test_board = [row[:] for row in engine.board]
                            test_board[lr][lc] = me
                            grp_after, libs_after = engine._get_group_and_liberties(test_board, lr, lc)
                            if len(libs_after) > 1:
                                if len(grp) > max_escape_size:
                                    max_escape_size = len(grp)
                                    best_escape_move = (lr, lc)
                                    
        if best_escape_move:
            print(f"Instant Escape Override! Escaped with {max_escape_size} stones at {best_escape_move}")
            return best_escape_move

        root_snapshot = engine._create_snapshot()
        root = MCTSNode(root_snapshot)
        
        start_time = time.time()
        iterations = 0
        
        # Keep simulating until either the time runs out, OR we reach our exact iteration goal
        while time.time() - start_time < self.time_limit and iterations < self.iteration_cap:
            node = self.select(root)
            winner_val = self.simulate(node.snapshot)
            self.backpropagate(node, winner_val)
            iterations += 1
            
        if not root.children:
            return None # Fallback pass
            
        # Select best move based on most visits, but FILTER OUT pure self-ataris!
        sorted_children = sorted(root.children, key=lambda c: c.visits, reverse=True)
        me = engine.current_player
        
        for child in sorted_children:
            if child.move is None:
                continue
            r, c = child.move
            
            # Create a shallow engine copy for testing the actual board state of this move
            test_eng = GoEngine()
            test_eng.size = engine.size
            test_eng.board = [row[:] for row in engine.board]
            test_eng.current_player = engine.current_player
            test_eng.history_set = set(engine.history_set)
            test_eng.captures = dict(engine.captures)
            
            caps_before = test_eng.captures[me]
            test_eng.place_stone(r, c)
            caps_after = test_eng.captures[me]
            
            grp, libs = test_eng._get_group_and_liberties(test_eng.board, r, c)
            
            # If the move leaves us with 1 liberty AND it didn't capture/kill any opponent stones doing it
            if len(libs) == 1 and caps_after == caps_before:
                print(f"Anti-Self-Atari Guard activated! Rejected suicidal choice: {child.move}")
                continue # Skip this move, keep going down the sorted list
                
            print(f"MCTS finished in {iterations} iterations. Chosen move: {child.move}. Win rate expectation: {child.wins/child.visits:.2f}")
            return child.move
            
        # Fallback if somehow EVERYTHING was filtered
        best_child = sorted_children[0]
        print(f"MCTS finished in {iterations} iterations. Chosen move: {best_child.move} (Fallback).")
        return best_child.move

    def select(self, node):
        while not node.snapshot['game_over']:
            if node.untried_moves:
                return self.expand(node)
            else:
                if not node.children: 
                    return node # terminal
                # Standard UCB1 formula to balance exploration vs exploitation
                exploration_constant = 1.41
                node = max(node.children, key=lambda c: (c.wins / c.visits) + exploration_constant * math.sqrt(math.log(node.visits) / c.visits))
        return node

    def expand(self, node):
        move = random.choice(node.untried_moves)
        node.untried_moves.remove(move)
        
        # Apply the move
        eng = GoEngine()
        eng.size = len(node.snapshot['board'])
        eng.board = [row[:] for row in node.snapshot['board']]
        eng.current_player = node.snapshot['current_player']
        eng.history_set = set(node.snapshot['history_set'])
        eng.captures = dict(node.snapshot['captures'])
        
        if move is None:
            eng.pass_turn()
        else:
            eng.place_stone(move[0], move[1])
            
        child = MCTSNode(eng._create_snapshot(), move=move, parent=node)
        node.children.append(child)
        return child

    def simulate(self, snapshot):
        eng = GoEngine()
        eng.size = len(snapshot['board'])
        eng.board = [row[:] for row in snapshot['board']]
        eng.current_player = snapshot['current_player']
        eng.history_set = set(snapshot['history_set'])
        eng.captures = dict(snapshot['captures'])
        
        depth = 0
        max_depth = 40 # Limit depth so simulation doesn't stall for too long
        
        # Play random moves but avoid filling own eyes so territory evaluates properly
        while not eng.game_over and depth < max_depth:
            legal = []
            capture_move = None
            opponent = 2 if eng.current_player == 1 else 1
            
            for r in range(eng.size):
                if capture_move: break
                for c in range(eng.size):
                    if capture_move: break
                    if eng.board[r][c] == 0:
                        
                        # Heuristic: Do NOT play into our own single-point eyes
                        adjacents = eng._get_adjacent(r, c)
                        is_own_eye = True
                        has_opponent_adj = False
                        
                        for ar, ac in adjacents:
                            if eng.board[ar][ac] != eng.current_player:
                                is_own_eye = False
                            if eng.board[ar][ac] == opponent:
                                has_opponent_adj = True
                                
                        if is_own_eye:
                            continue
                            
                        # Quick check logic for speed over perfect bounds
                        if eng.is_legal_move(r, c):
                            # Rule 1 Heuristic: Atari Capture. If this move kills an opponent, take it!
                            if has_opponent_adj:
                                for ar, ac in adjacents:
                                    if eng.board[ar][ac] == opponent:
                                        grp, libs = eng._get_group_and_liberties(eng.board, ar, ac)
                                        # If the opponent group has 1 liberty left, this empty spot IS that liberty.
                                        if len(libs) == 1:
                                            capture_move = (r, c)
                                            break
                                            
                            if not capture_move:
                                legal.append((r, c))
            
            if capture_move:
                eng.place_stone(capture_move[0], capture_move[1])
            elif not legal:
                eng.pass_turn()
            else:
                move = random.choice(legal)
                eng.place_stone(move[0], move[1])
            depth += 1
            
        scores, winner, b_stones, w_stones = eng.compute_score()
        
        if winner == "Black": return 1
        elif winner == "White": return 2
        return 0

    def backpropagate(self, node, winner_val):
        while node is not None:
            node.visits += 1
            if node.player_just_moved == winner_val:
                node.wins += 1
            elif winner_val == 0:
                node.wins += 0.5 # Ties
            node = node.parent
