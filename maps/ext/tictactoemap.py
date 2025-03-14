import enum

from ...coord import Coord
from ...maps.base import Map
from ...message import Message
from ...Player import HumanPlayer
from ...tiles.map_objects import *
from ...command import ChatCommand
from ...tiles.base import MapObject

class Mark(enum.Enum):
    X = "X"
    O = "O"
    EMPTY = " "

    def __str__(self):
        return self.value

class TicTacToeBoard:
    SIZE = 3

    def __init__(self):
        # Create a 3x3 grid initialized to EMPTY
        self.grid = [[Mark.EMPTY for _ in range(TicTacToeBoard.SIZE)] for _ in range(TicTacToeBoard.SIZE)]

    def place_mark(self, row: int, col: int, mark: Mark) -> bool:
        """Attempts to place a mark on the board at the given row and column.
        
        Returns True if the move was valid and applied, False otherwise.
        """
        if self.is_valid_position(row, col) and self.grid[row][col] == Mark.EMPTY:
            self.grid[row][col] = mark
            return True
        return False

    def is_valid_position(self, row: int, col: int) -> bool:
        """Checks whether the given (row, col) position is within bounds."""
        return 0 <= row < TicTacToeBoard.SIZE and 0 <= col < TicTacToeBoard.SIZE

    def is_full(self) -> bool:
        """Checks if the board is completely filled with marks."""
        for row in self.grid:
            for cell in row:
                if cell == Mark.EMPTY:
                    return False
        return True

    def has_winner(self, mark: Mark) -> bool:
        """Determines if the specified mark has a winning configuration."""
        # Check rows and columns
        for i in range(TicTacToeBoard.SIZE):
            if all(self.grid[i][j] == mark for j in range(TicTacToeBoard.SIZE)):
                return True
            if all(self.grid[j][i] == mark for j in range(TicTacToeBoard.SIZE)):
                return True

        # Check main diagonal
        if all(self.grid[i][i] == mark for i in range(TicTacToeBoard.SIZE)):
            return True

        # Check anti-diagonal
        if all(self.grid[i][TicTacToeBoard.SIZE - 1 - i] == mark for i in range(TicTacToeBoard.SIZE)):
            return True

        return False

    def __str__(self) -> str:
        """Creates a string representation of the board for display."""
        lines = []
        for i in range(TicTacToeBoard.SIZE):
            row_str = " | ".join(str(self.grid[i][j]) for j in range(TicTacToeBoard.SIZE))
            lines.append(" " + row_str)
            if i < TicTacToeBoard.SIZE - 1:
                lines.append("---+---+---")
        return "\n".join(lines)

class NewGameCommand(ChatCommand):
    name = 'new_game'
    desc = 'Start a new game of TicTacToe.'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith("new_game")
    
    def execute(self, command_text: str, context: "TicTacToeHouse", player: HumanPlayer) -> list[Message]:
        messages = []
        context.init_game_board()
        messages += context.send_message_to_players("A new game of Tic Tac Toe has started!")
        return messages

class PlaceMarkXCommand(ChatCommand):
    name = 'x'
    desc = 'Place an x (X#,#).'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith("x")
    
    def execute(self, command_text: str, context: "TicTacToeHouse", player: HumanPlayer) -> list[Message]:
        messages = []
        # Parse the position from the command (e.g., "X3:5")
        pos = int(command_text[1]), int(command_text[3])
        pos = (pos[0] + 15, pos[1] + 15)
        context.game_board.place_mark(pos[0], pos[1], Mark.X)
        context.add_to_grid(MapObject.get_obj('flower_large_red'), Coord(pos[0], pos[1]))
        context.placed_objects.append((MapObject.get_obj('plant'), Coord(pos[0], pos[1])))
        messages.append(ServerMessage(player, "You have selected X."))
        messages += context.send_grid_to_players()
        return messages

class PlaceMarkOCommand(ChatCommand):
    name = 'o'
    desc = 'Place an O (O#,#).'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith("o")
    
    def execute(self, command_text: str, context: "TicTacToeHouse", player: HumanPlayer) -> list[Message]:
        messages = []
        pos = int(command_text[1]), int(command_text[3])
        pos = (pos[0] + 15, pos[1] + 15)
        context.game_board.place_mark(pos[0], pos[1], Mark.O)
        context.add_to_grid(MapObject.get_obj('rock_1'), Coord(pos[0], pos[1]))
        context.placed_objects.append((MapObject.get_obj('rock_1'), Coord(pos[0], pos[1])))
        messages.append(ServerMessage(player, "You have selected O."))
        messages += context.send_grid_to_players()
        return messages

class TicTacToeHouse(Map):
    def __init__(self) -> None:
        super().__init__(
            name="Tic Tac Toe House",
            description="A house with a tic-tac-toe board on the floor.",
            size=(25, 25),
            entry_point=Coord(12+5, 6+5),
            background_tile_image='wood_brown',
            chat_commands=[NewGameCommand, PlaceMarkXCommand, PlaceMarkOCommand],
        )
        self.placed_objects = []
    
    def init_game_board(self):
        self.clear_board
        self.game_board = TicTacToeBoard()

    def get_objects(self) -> list[tuple[MapObject, Coord]]:
        objects: list[tuple[MapObject, Coord]] = []

        # add a door
        door = Door('int_entrance', linked_room="Trottier Town")
        objects.append((door, Coord(12+5, 6+5)))

        return objects

    def clear_board(self):
        # remove all squares from 10,10 to 12,12.
        for obj, coord in self.placed_objects:
            self.remove_from_grid(obj, coord)
