import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from engine import GoEngine
from ai import GoAI

class GoGUI:
    def __init__(self, root, size=9):
        self.root = root
        self.root.title("Go Engine 9x9")
        
        self.size = size
        self.engine = GoEngine(size)
        self.ai = GoAI(time_limit=5, iteration_cap=30000)
        
        self.cell_size = 50
        self.margin = 30
        self.board_size = (self.size - 1) * self.cell_size + 2 * self.margin
        
        # Setup UI
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(side=tk.TOP, fill=tk.X, pady=5, padx=10)
        
        self.game_mode = tk.StringVar(value="Human vs Human")
        modes = ["Human vs Human", "AI plays White", "AI plays Black", "AI vs AI"]
        self.mode_dropdown = ttk.Combobox(self.button_frame, textvariable=self.game_mode, values=modes, state="readonly", width=17)
        self.mode_dropdown.pack(side=tk.LEFT, padx=5)
        self.mode_dropdown.bind("<<ComboboxSelected>>", self.on_mode_change)
        
        # 3 buttons evenly spread out
        self.pass_btn = tk.Button(self.button_frame, text="Pass (Concede)", command=self.pass_turn)
        self.pass_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.undo_btn = tk.Button(self.button_frame, text="Undo", command=self.undo_move)
        self.undo_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.reset_btn = tk.Button(self.button_frame, text="Reset", command=self.reset_game)
        self.reset_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.info_frame = tk.Frame(root)
        self.info_frame.pack(side=tk.TOP, fill=tk.X, pady=5, padx=10)
        
        self.black_info = tk.Label(self.info_frame, text="Black\nCaptures: 0\nStones: 0\nScore: 0", font=("Helvetica", 10), justify=tk.LEFT)
        self.black_info.pack(side=tk.LEFT, anchor="w")
        
        self.turn_label = tk.Label(self.info_frame, text="Turn: Black", font=("Helvetica", 14, "bold"))
        self.turn_label.pack(side=tk.LEFT, expand=True)

        self.white_info = tk.Label(self.info_frame, text="White\nCaptures: 0\nStones: 0\nScore: 2.5", font=("Helvetica", 10), justify=tk.RIGHT)
        self.white_info.pack(side=tk.RIGHT, anchor="e")
        
        self.canvas = tk.Canvas(root, width=self.board_size, height=self.board_size, bg="#dcba82")
        self.canvas.pack()
        
        self.canvas.bind("<Button-1>", self.on_click)
        
        self.draw_board()

    def draw_board(self):
        self.canvas.delete("all")
        
        # Draw grid lines
        for i in range(self.size):
            # Horizontal
            y = self.margin + i * self.cell_size
            self.canvas.create_line(self.margin, y, self.board_size - self.margin, y, fill="black")
            # Vertical
            x = self.margin + i * self.cell_size
            self.canvas.create_line(x, self.margin, x, self.board_size - self.margin, fill="black")
            
        # Draw star points (hoshi) for 9x9
        stars = [(2, 2), (2, 6), (6, 2), (6, 6), (4, 4)]
        if self.size == 9:
            for r, c in stars:
                x = self.margin + c * self.cell_size
                y = self.margin + r * self.cell_size
                self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="black")
                
        # Draw stones
        board = self.engine.get_board()
        last_move = self.engine.get_last_move()
        
        stone_radius = self.cell_size * 0.4
        
        for r in range(self.size):
            for c in range(self.size):
                if board[r][c] != 0:
                    x = self.margin + c * self.cell_size
                    y = self.margin + r * self.cell_size
                    color = "black" if board[r][c] == 1 else "white"
                    outline = "gray" if color == "black" else "black"
                    self.canvas.create_oval(x - stone_radius, y - stone_radius, 
                                            x + stone_radius, y + stone_radius, 
                                            fill=color, outline=outline)
                                            
                    # Highlight last move
                    if last_move == (r, c):
                        self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="red", outline="red")
                        
        self.update_labels()
        self.check_ai_turn()

    def update_labels(self):
        if self.engine.is_game_over():
            winner = self.engine.winner
            self.turn_label.config(text=f"Game Over: {winner} Wins!")
        else:
            turn_text = "Black" if self.engine.get_current_player() == 1 else "White"
            self.turn_label.config(text=f"Turn: {turn_text}")
            
        scores, _, b_stones, w_stones = self.engine.compute_score()
        b_caps = self.engine.captures[1]
        w_caps = self.engine.captures[2]
        
        self.black_info.config(text=f"Black\nCaptures: {b_caps}\nStones: {b_stones}\nEst. Score: {scores[1]}")
        self.white_info.config(text=f"White\nCaptures: {w_caps}\nStones: {w_stones}\nEst. Score: {scores[2]}")

    def on_click(self, event):
        if self.engine.is_game_over():
            return
            
        # Guard against clicking during AI turn
        mode = self.game_mode.get()
        cp = self.engine.current_player
        if mode == "AI vs AI": return
        if mode == "AI plays White" and cp == 2: return
        if mode == "AI plays Black" and cp == 1: return
            
        # Calculate row and col based on click position
        c = round((event.x - self.margin) / self.cell_size)
        r = round((event.y - self.margin) / self.cell_size)
        
        # Ensure click falls roughly near an intersection
        if 0 <= r < self.size and 0 <= c < self.size:
            # Check proximity to intersection to avoid placing when clicking in the middle of a square
            x_int = self.margin + c * self.cell_size
            y_int = self.margin + r * self.cell_size
            dist_sq = (event.x - x_int)**2 + (event.y - y_int)**2
            
            if dist_sq <= (self.cell_size * 0.45)**2: # Click must be within 45% of cell size to intersection
                if self.engine.is_legal_move(r, c):
                    self.engine.place_stone(r, c)
                    self.draw_board()
                else:
                    self.show_illegal_move_warning(r, c)

    def pass_turn(self):
        if self.engine.is_game_over():
            return
            
        # As per rule: Passing means conceding the game.
        # We process the final score and end.
        self.engine.pass_turn()
        self.draw_board()
        self.show_game_over()
        
    def show_game_over(self):
        scores, winner = self.engine.final_scores, self.engine.winner
        msg = f"Game Over (Player Passed / Conceded)!\n\n"
        msg += f"Black Score: {scores[1]}\n"
        msg += f"White Score: {scores[2]} (includes 2.5 komi)\n\n"
        msg += f"Winner: {winner}!"
        
        messagebox.showinfo("Game Over", msg)
        
    def reset_game(self):
        self.engine = GoEngine(self.size)
        self.draw_board()

    def show_illegal_move_warning(self, r, c):
        x = self.margin + c * self.cell_size
        y = self.margin + r * self.cell_size
        
        # Draw a bold red 'X'
        line1 = self.canvas.create_line(x - 15, y - 15, x + 15, y + 15, fill="red", width=3)
        line2 = self.canvas.create_line(x - 15, y + 15, x + 15, y - 15, fill="red", width=3)
        
        # Remove this warning graphic after 400 milliseconds
        self.root.after(400, lambda: self.canvas.delete(line1, line2))

    def undo_move(self):
        if self.engine.is_game_over():
            return
            
        mode = self.game_mode.get()
        if mode == "Human vs Human":
            if self.engine.undo():
                self.draw_board()
        elif mode in ["AI plays White", "AI plays Black"]:
            # In AI vs Human, we must undo TWO moves (the AI's move, and your previous move)
            # Otherwise, you undo the AI's move, it becomes the AI's turn again, and it instantly plays!
            if len(self.engine.state_stack) >= 2:
                self.engine.undo()
                self.engine.undo()
                self.draw_board()

    def on_mode_change(self, event):
        self.reset_game()

    def check_ai_turn(self):
        if self.engine.is_game_over():
            return
            
        mode = self.game_mode.get()
        cp = self.engine.current_player
        
        is_ai_turn = False
        if mode == "AI vs AI":
            is_ai_turn = True
        elif mode == "AI plays White" and cp == 2:
            is_ai_turn = True
        elif mode == "AI plays Black" and cp == 1:
            is_ai_turn = True
            
        if is_ai_turn:
            self.root.after(50, self.do_ai_turn)
            
    def do_ai_turn(self):
        if self.engine.is_game_over():
            return
            
        # Visual wait indication
        self.turn_label.config(text=f"Turn: {'Black' if self.engine.get_current_player() == 1 else 'White'} (Thinking...)")
        self.root.update()
            
        move = self.ai.get_best_move(self.engine)
        if move is None or move == "PASS":
            self.engine.ai_skip_turn()  # Skip turn only; game ends if both sides pass consecutively
        else:
            self.engine.place_stone(move[0], move[1])
            
        self.draw_board()


if __name__ == "__main__":
    root = tk.Tk()
    app = GoGUI(root)
    root.mainloop()
