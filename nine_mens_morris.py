import random
import time
from enum import Enum
from yaspin import yaspin
from yaspin.spinners import Spinners
# from nine_mens_morris import Game, NineMensMorrisUI, Player, GamePhase
from simple_ai_models import SimpleAI


class Player:
    """Represent a player in the game.

    Attributes:
        name (str): Player display name.
        player_symbol (str): Single-character symbol placed on board (e.g. 'X' or 'O').
        pieces_in_hand (int): Pieces remaining to place during the placing phase.
        pieces_on_board (int): Pieces currently on the board.
        player_type (str): Type of player, either "human" or "ai".
    """

    def __init__(self, name, player_symbol, player_type="human"):
        self.name = name
        self.player_symbol = player_symbol
        self.pieces_in_hand = 9
        self.pieces_on_board = 0
        self.player_type = player_type  # or "ai"

    def place_piece(self):
        """Move a piece from the player's hand onto the board state tracking.

        Returns True if a piece was placed (i.e. there was at least one in hand),
        otherwise False.
        """
        if self.pieces_in_hand > 0:
            self.pieces_in_hand -= 1
            self.pieces_on_board += 1
            return True
        return False

    def remove_piece(self):
        """Decrease the on-board piece count when this player's piece is removed.

        Returns True if a piece was removed, False if none available.
        """
        if self.pieces_on_board > 0:
            self.pieces_on_board -= 1
            return True
        return False

class BoardManager():
    
    def __init__(self):
        self.board = self.make_new_board()

    @staticmethod
    def make_new_board():
        """Create a fresh empty board represented as a list of 24 positions.

        Each position holds a single-character symbol: '.' for empty, or
        the player's symbol (e.g. 'X' / 'O'). The board indices 0..23 follow
        a standard Nine Men's Morris layout mapping used across the module.
        """
        return list("." * 24)
    
    def is_position_empty(self, position):
        return self.board[position] == "."
    
    def who_on_position(self, position):
        return self.board[position]
    
    def get_players_positions(self, player_symbol):
        positions = []
        for i in range(len(self.board)):
            if self.who_on_position(i) == player_symbol:
                positions.append(i)
        return positions

    # Precomputed adjacency list for each board position. Used to validate legal moves during the MOVING phase (only adjacent moves allowed).
    adjacent_arrays = [[1, 9], [0, 2, 4], [1, 14],
                            [10, 4], [1, 3, 7, 5], [4, 13],
                            [7, 11], [4, 6, 8], [7, 12],
                            [0, 10, 21], [3, 9, 18, 11], [6, 10, 15],
                            [8, 13, 17], [5, 12, 20, 14], [2, 13, 23],
                            [11, 16], [15, 17, 19], [12, 16],
                            [10, 19], [16, 18, 22, 20], [13, 19],
                            [9, 22], [19, 21, 23], [14, 22],]

    def get_empty_positions(self):
        empty_positions = []
        for i in range(len(self.board)):
            if self.is_position_empty(i):
                empty_positions.append(i)
        return empty_positions
    
    def get_empty_adjacent_positions(self, position):
        empty_positions = []
        for adj in self.adjacent_arrays[position]:
            if self.is_position_empty(adj):
                empty_positions.append(adj)
        return empty_positions
    
    def add_player_piece(self, position, player_symbol):
        if self.is_position_empty(position):
            self.board[position] = player_symbol
            return True
        return False
    
    def remove_player_piece(self, position):
        if not self.is_position_empty(position):
            self.board[position] = "."
            return True
        return False
    
    def move_player_piece(self, from_position, to_position, player_symbol):
        # Validate the move: correct owner, destination empty, and positions adjacent
        if (
            self.board[from_position] == player_symbol
            and self.is_position_empty(to_position)
            and to_position in self.adjacent_arrays[from_position]
        ):
            self.board[from_position] = "."
            self.board[to_position] = player_symbol
            return True
        return False
    
    def fly_player_piece(self, from_position, to_position, player_symbol):
        # Flying allows jumping to any empty position (used when player has 3 pieces)
        if (self.board[from_position] == player_symbol and self.is_position_empty(to_position)):
            self.board[from_position] = "."
            self.board[to_position] = player_symbol
            return True
        return False

class GamePhase(Enum):
    PLACING = 1
    MOVING = 2
    FLYING = 3
    REMOVING_PIECE = 4
    GAME_OVER = 5

class Game():
    """Encapsulate game state and rules for Nine Men's Morris.

    The `Game` object tracks players, the board, the active phase, and
    provides handler methods for player actions. It does not perform I/O
    itself — that logic is in `NineMensMorrisUI`.
    """

    def __init__(self, player_1, player_2):
        self.player1 = player_1
        self.player2 = player_2
        self.board_manager = BoardManager()
        self.current_player = self.player1  # Initialize with player1
        # `opponent_player` is computed via property to avoid inconsistent state
        # Start in the PLACING phase until players exhaust pieces_in_hand
        self.current_phase = GamePhase.PLACING
        self.selected_piece = None  # To track the piece selected for moving or flying
        self.game_history = []
        self.legal_moves = []
        # Reset players' pieces
        self.player1.pieces_in_hand = 9
        self.player1.pieces_on_board = 0
        self.player2.pieces_in_hand = 9
        self.player2.pieces_on_board = 0

    def switch_player(self):
        # Toggle only the authoritative `current_player` state. The
        # `opponent_player` property computes the opponent on access.
        self.current_player = self.player2 if self.current_player is self.player1 else self.player1

    @property
    def opponent_player(self):
        """Return the player who is not the current player.

        Computed on each access to avoid duplication of mutable state.
        """
        return self.player2 if self.current_player is self.player1 else self.player1
    
    def update_game_phase(self):
        """Calculates and updates the phase for the CURRENT player."""
        
        # 1. Check for Game Over
        if self.check_win_condition():
            self.current_phase = GamePhase.GAME_OVER
            return
            
        # 2. Check for Placing
        if self.current_player.pieces_in_hand > 0:
            self.current_phase = GamePhase.PLACING
        
        # 3. Check for Flying
        elif self.current_player.pieces_on_board == 3:
            self.current_phase = GamePhase.FLYING
        
        # 4. Default to Moving
        else:
            self.current_phase = GamePhase.MOVING
    
    def get_allowed_moves(self, position_just_placed):
        """
        Returns a list of allowed move positions for the current player,
        based on the current game phase and the given position.
        """
        if self.current_phase == GamePhase.PLACING:
            return self.board_manager.get_empty_positions()
        if self.current_phase == GamePhase.FLYING:
            return self.board_manager.get_empty_positions()
        if self.current_phase == GamePhase.MOVING:
            return self.board_manager.get_empty_adjacent_positions(position_just_placed)
        return []
    
    mills_arrays = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11],
        [12, 13, 14], [15, 16, 17], [18, 19, 20], [21, 22, 23],
        [0, 9, 21], [3, 10, 18], [6, 11, 15], [1, 4, 7],
        [16, 19, 22], [8, 12, 17], [5, 13, 20], [2, 14, 23],
        ]
    
    def is_position_part_of_mill(self, location):
        """Return True if the given location is part of a completed mill.

        A mill is three aligned pieces of the same symbol. Empty squares
        cannot be part of a mill.
        """
        symbol_at_pos = self.board_manager.who_on_position(location)
        if symbol_at_pos == ".":
            return False

        for mill in self.mills_arrays:
            if location in mill:
                # All positions in this mill must match the symbol at `location`.
                if all(self.board_manager.board[pos] == symbol_at_pos for pos in mill):
                    return True
        return False

    def get_allowed_removals(self):
        """
        Returns a list of positions from which the current player can remove
        an opponent's piece. If the opponent has pieces not in mills, only those
        can be removed.
        """
        opponent_positions = self.board_manager.get_players_positions(self.opponent_player.player_symbol)
        non_mill_positions = []
        for pos in opponent_positions:
            if not self.is_position_part_of_mill(pos):
                non_mill_positions.append(pos)
        if non_mill_positions:
            return non_mill_positions
        return opponent_positions
    
    def check_win_condition(self):
        """
        Check if the current player has won the game.
        A player wins if, the phase is either moving or flying, and the opponent has less than 3 pieces on board
        or cannot make any valid moves.
        """
        #!! Commenting this out! for testing purposes
        # Cannot win while removing a piece
        # if self.current_phase == GamePhase.REMOVING_PIECE:
        #     return False
        
        # Check if opponent's pieces are less than 3 on board only after player and oppenent have placed all pieces
        if self.current_player.pieces_in_hand == 0 and self.opponent_player.pieces_in_hand == 0:
            if self.opponent_player.pieces_on_board < 3:
                print(f"{self.current_player.name} ({self.current_player.player_symbol}) wins! Opponent has less than 3 pieces on board.")
                return True
            
        # Win if opponent does not have any valid moves
        opponent_positions = self.board_manager.get_players_positions(self.opponent_player.player_symbol)
        if opponent_positions == []:
            return False
        for pos in opponent_positions:
            if self.get_allowed_moves(pos):
                return False
        
        #! Experimental
        # If any of the players still have pieces in hand, the game cannot be over
        if self.current_player.pieces_in_hand >= 0 or self.opponent_player.pieces_in_hand >= 0:
            return False
        
        print(f"{self.current_player.name} ({self.current_player.player_symbol}) wins by blocking opponent's moves!")
        return True
    
    def finalize_turn(self, position):
        """
        Finalizes the turn after a successful action (placing, moving, or flying).
        Checks for mill formation and updates the game phase and current player.
        """
        # Check if anyone Won the game
        if self.check_win_condition():
            self.current_phase = GamePhase.GAME_OVER
            return
        
        # Check for mill formation
        if self.is_position_part_of_mill(position):
            self.current_phase = GamePhase.REMOVING_PIECE
        else:
            self.switch_player()
            self.update_game_phase()
    
    def handle_placing(self, position):
        """Handle an attempted placement on `position` by the current player.

        Returns True for a successful placement, False otherwise.
        """
        if self.board_manager.add_player_piece(position, self.current_player.player_symbol):
            self.current_player.place_piece()

            self.finalize_turn(position)
            return True
        return False
    
    def handle_moving(self, position):
        """
        Handles the moving phase: select a piece, deselect, or move to an adjacent empty position.
        """
        # Select a piece to move
        if self.selected_piece is None:
            if self.board_manager.who_on_position(position) == self.current_player.player_symbol:
                # Check if adjacent empty positions exist
                if self.board_manager.get_empty_adjacent_positions(position):
                    self.selected_piece = position
                    return True
            return False

        # Deselect the selected piece
        if position == self.selected_piece:
            self.selected_piece = None
            return True

        # Attempt to move to an adjacent empty position
        if (self.board_manager.move_player_piece(self.selected_piece, position, self.current_player.player_symbol)):
            self.finalize_turn(position)
            self.selected_piece = None
            return True

        return False

    def handle_flying(self, position):
        """
        Handles the flying phase: select a piece, deselect, or move to any empty position.
        """
        # Select a piece to fly
        if self.selected_piece is None:
            if self.board_manager.who_on_position(position) == self.current_player.player_symbol:
                self.selected_piece = position
                return True
            return False

        # Deselect the selected piece
        if position == self.selected_piece:
            self.selected_piece = None
            return True

        # Attempt to fly to any empty position
        if self.board_manager.fly_player_piece(self.selected_piece, position, self.current_player.player_symbol):
            self.finalize_turn(position)
            self.selected_piece = None
            return True

        return False
    
    def handle_removing_piece(self, position):
        """Attempt to remove an opponent piece at `position`.

        Only positions returned by `get_allowed_removals` may be removed.
        After a successful removal we switch turn back to the player who
        had just formed the mill (the removal is a 'temporary' state).
        """
        if position in self.get_allowed_removals():
            if self.board_manager.remove_player_piece(position):
                self.opponent_player.remove_piece()
                
                #!!! Temporarily checking: if self.update_game_phase() here causes issues?
                # After removing a piece the removing player keeps the turn flow
                # by switching back to the other player (the attacker).
                # self.switch_player()
                # After a removal, update the phase for the now-current player
                # self.update_game_phase()
                # Check if win condition met after removal
                self.check_win_condition()
                
                self.finalize_turn(position)
                
                return True
        return False
    
    def handle_action(self, position):
        """Dispatch the player's action depending on the current phase.

        Returns True if the action was valid and applied, False otherwise.
        """
        
        if self.current_phase == GamePhase.PLACING:
            self.record_game_action(position)
            return self.handle_placing(position)

        elif self.current_phase == GamePhase.MOVING:
            self.record_game_action(position)
            return self.handle_moving(position)
        
        elif self.current_phase == GamePhase.REMOVING_PIECE:
            self.record_game_action(position)
            return self.handle_removing_piece(position)

        elif self.current_phase == GamePhase.FLYING:
            self.record_game_action(position)
            return self.handle_flying(position)


        
        return False
    
    def record_game_action(self, position):
        """Record the action taken by the current player at `position`.
        """
        # store a shallow copy of the board list to avoid later mutations
        self.game_history.append([self.board_manager.board.copy(), self.current_player, self.current_phase, position])
        print(f"Recorded action at position {position}. History length: {len(self.game_history)}")
        
    def undo_action(self):
        """Undo the last game action, restoring the previous state.

        This is a placeholder for future implementation.
        """
        if not self.game_history:
            return False
        last_state = self.game_history.pop()
        # restore copies to avoid keeping references to old mutable lists
        self.board_manager.board = last_state[0].copy()
        self.current_player = last_state[1]
        self.current_phase = last_state[2]
        return True

    def possible_legal_moves(self):
        """Get all possible moves for the current player based on the game phase.

        Returns a list of valid positions the current player can move to.
        """
        possible_moves = []
        if self.current_phase == GamePhase.PLACING:
            possible_moves = self.board_manager.get_empty_positions()
            
        elif self.current_phase == GamePhase.MOVING:
            player_positions = self.board_manager.get_players_positions(self.current_player.player_symbol)
            if self.selected_piece is None:
                # List all pieces that have at least one adjacent empty position
                for pos in player_positions:
                    if len(self.board_manager.get_empty_adjacent_positions(pos)) > 0:
                        possible_moves.append(pos)
            else:
                # List all empty adjacent positions for the selected piece
                possible_moves = self.board_manager.get_empty_adjacent_positions(self.selected_piece)
                
        elif self.current_phase == GamePhase.FLYING:
            if self.selected_piece is None:
                player_positions = self.board_manager.get_players_positions(self.current_player.player_symbol)
                if self.selected_piece is None:
                    # List all pieces that can fly
                    for pos in player_positions:
                        possible_moves.append(pos)
            else:
                # List all empty positions for flying
                possible_moves = self.board_manager.get_empty_positions()
                
        elif self.current_phase == GamePhase.REMOVING_PIECE:
            possible_moves = self.get_allowed_removals()
        return list(set(possible_moves))  # Remove duplicates

class NineMensMorrisUI():
    # ANSI Color Constants
    RED = "\033[91m"    # Player X
    BLUE = "\033[94m"   # Player O
    GREEN = "\033[92m"  # Selected Piece
    YELLOW = "\033[93m" # Legal Move Hints
    RESET = "\033[0m"
    CLEAR = "\033[H\033[J" # Cursor to top + Clear screen

    def __init__(self, game_type="ai_vs_ai", ai_model=SimpleAI):
        self.game_type = game_type.lower()
        self.ai_model = ai_model
        if self.game_type == "human_vs_human":
            # Input player names if desired
            player_1_name = input("Enter name for Player 1 (X) [Press Enter for default]: ")
            player_2_name = input("Enter name for Player 2 (O) [Press Enter for default]: ")
            player_1 = Player(player_1_name if player_1_name else "Player 1", "X", player_type="human")
            player_2 = Player(player_2_name if player_2_name else "Player 2", "O", player_type="human")
        elif self.game_type == "human_vs_ai":
            # Input player name if desired
            player_1_name = input("Enter name for Player 1 (X) [Press Enter for default]: ")
            player_1 = Player(player_1_name if player_1_name else "Player 1", "X", player_type="human")
            player_2 = Player("AI", "O", player_type="ai")
        else:  # Default to AI vs AI
            player_1 = Player("AI 1", "X", player_type="ai")
            player_2 = Player("AI 2", "O", player_type="ai")
        self.game = Game(player_1, player_2)
        self.run_game_loop()

    def draw_colored_board(self):
        """Processes board state with colors and hints before drawing."""
        raw_board = self.game.board_manager.board
        legal_moves = self.game.possible_legal_moves()
        display_chars = []

        for i, char in enumerate(raw_board):
            # 1. Highlight Selected Piece
            if i == self.game.selected_piece:
                display_chars.append(f"{self.GREEN}#{self.RESET}")
            # 2. Color Player Pieces
            elif char == "X":
                display_chars.append(f"{self.RED}X{self.RESET}")
            elif char == "O":
                display_chars.append(f"{self.BLUE}O{self.RESET}")
            # 3. Show Hints for Legal Moves (dots become ?)
            elif i in legal_moves:
                display_chars.append(f"{self.YELLOW}?{self.RESET}")
            # 4. Standard Empty Spot
            else:
                display_chars.append(".")

        # The actual board template using display_chars
        drawn_board = f''' 
            {display_chars[0]} --------------------- {display_chars[1]} --------------------- {display_chars[2]} 
            |                       |                       |
            |       {display_chars[3]} ------------- {display_chars[4]} ------------- {display_chars[5]}       |
            |       |               |               |       |
            |       |        {display_chars[6]} ---- {display_chars[7]} ---- {display_chars[8]}        |       |
            |       |        |             |        |       |
            {display_chars[9]} ----- {display_chars[10]} ------ {display_chars[11]}             {display_chars[12]} ------ {display_chars[13]} ----- {display_chars[14]}
            |       |        |             |        |       |
            |       |        {display_chars[15]} ---- {display_chars[16]} ---- {display_chars[17]}        |       |
            |       |               |               |       |
            |       {display_chars[18]} ------------- {display_chars[19]} ------------- {display_chars[20]}       |
            |                       |                       |
            {display_chars[21]} --------------------- {display_chars[22]} --------------------- {display_chars[23]} 
            '''
        print(drawn_board)

    def print_game_status(self):
        p = self.game.current_player
        opp = self.game.opponent_player
        print(f" {self.RED if p.player_symbol == 'X' else self.BLUE}{p.name}{self.RESET} Turn | Phase: {self.game.current_phase.name}")
        print(f" Stones -> Hand: {p.pieces_in_hand} | Board: {p.pieces_on_board} | Opponent Board: {opp.pieces_on_board}")
        print("-" * 50)

    def print_user_prompt(self):
        if self.game.current_phase == GamePhase.PLACING:
            print("Place a piece on an empty position (0-23).")
        elif self.game.current_phase == GamePhase.MOVING:
            if self.game.selected_piece is None:
                print("Select one of your pieces to move (0-23).")
            else:
                print(f"Selected piece at {self.game.selected_piece}. Choose an adjacent empty position to move to (0-23), or select the same piece to deselect.")
        elif self.game.current_phase == GamePhase.FLYING:
            if self.game.selected_piece is None:
                print("Select one of your pieces to fly (0-23).")
            else:
                print(f"Selected piece at {self.game.selected_piece}. Choose any empty position to fly to (0-23), or select the same piece to deselect.")
        elif self.game.current_phase == GamePhase.REMOVING_PIECE:
            print("Remove one of your opponent's pieces from the board (0-23).")
        
        elif self.game.current_phase == GamePhase.GAME_OVER:
            print(f"Game Over. {self.game.current_player.name} ({self.game.current_player.player_symbol}) wins!")

    def run_game_loop(self):
        while True:
            # Clear terminal for a "Game App" feel
            print(self.CLEAR, end="") 
            
            self.draw_colored_board()
            self.print_game_status()
            self.print_user_prompt()

            try:
                # Add legal move hint to the input line
                moves = self.game.possible_legal_moves()
                print(f"{self.YELLOW}Legal Moves:{self.RESET} {moves}")
                if self.game.current_player.player_type == "ai":
                    with yaspin(Spinners.dots, text=f"{self.game.current_player.name} is thinking...") as spinner:
                        time.sleep(random.uniform(0.5, 1))  # Simulate thinking time
                        inp = self.ai_model(moves)
                        spinner.ok("✅ ")
                
                elif self.game.current_player.player_type == "human":        
                    inp = input("\nAction (0-23) or 'q' to quit: ").lower()
                print(f"{self.game.current_player.name} chooses position: {inp}")
                if inp == 'q': break
                
                position = int(inp)
                if not (0 <= position <= 23): raise ValueError
            except ValueError:
                input("Invalid input! Press Enter to try again...")
                continue

            if not self.game.handle_action(position):
                input(f"{self.RED}Invalid move!{self.RESET} Press Enter to try again...")
            
            if self.game.current_phase == GamePhase.GAME_OVER:
                print(self.CLEAR, end="")
                self.draw_colored_board()
                print(f"\n🏆 CONGRATULATIONS! {self.game.current_player.name} WINS! 🏆")
                break


if __name__ == "__main__":
    NineMensMorrisUI(game_type="human_vs_ai", ai_model=SimpleAI)