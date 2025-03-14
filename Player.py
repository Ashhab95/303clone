from typing import Any, Literal, TYPE_CHECKING

from .message import *
from .coord import Coord
from .database_entity import DatabaseEntity
from .tiles.map_objects import CharacterMapObject

if TYPE_CHECKING:
    from maps.base import Map
    from tiles.base import MapObject

class Player(CharacterMapObject, SenderInterface, DatabaseEntity):
    """Player class that represents a player in the game. Contains information about the player's name,
       current position, and current room. Also contains methods to move the player and change rooms
    """
    
    def __init__(self, name: str, image: str = 'player1', facing_direction: Literal['up', 'down', 'left', 'right'] = 'down', passable: bool = True) -> None:
        super().__init__(image, passable=passable, facing_direction=facing_direction)

        self._name: str = name # handle
        self._current_position = Coord(0, 0)

    def update_position(self, new_position: Coord, map: "Map") -> None:
        """ Update the player's position and current room. """
        self._current_position: Coord = new_position
        self._current_room = map

    def get_name(self) -> str:
        """ Get the player's name. """
        return self._name

    def get_current_position(self) -> Coord:
        """ Get the player's current position. """
        return Coord.from_Coord(self._current_position)

    def get_current_room(self) -> 'Map':
        """ Get the player's current room. """
        return self._current_room

    def move(self, direction_s: Literal['up', 'down', 'left', 'right']) -> list[Message]:
        """ Move the player in the given direction. """

        assert self._current_room is not None

        update_facing_direction = self.get_facing_direction() != direction_s
        self.set_facing_direction(direction_s)
        messages = self._current_room.move(self, direction_s)
        if len(messages) == 0 and update_facing_direction:
            messages = self._current_room.send_grid_to_players()
        return messages

    def __str__(self) -> str:
        """ Return a string representation of the player. """
        return f'Player Handle: {self._name}; Map: {self._current_room.get_name() if self._current_room is not None else "None"}; Position: {self._current_position}; Image: {self.get_image_name()}'

    def change_room(self, new_room: 'Map', msg_to_cur_room: str = "", msg_to_new_room: str = "", entry_point = None) -> list[Message]:
        """ Change the player's current room to the given room at the given coordinate (if provided).
            Sends a message to the current room and the new room to inform them of the player's departure/arrival.
        """
        
        cur_room = self._current_room if hasattr(self, "_current_room") else None
        if cur_room is not None:
            cur_room.remove_player(self)
        
        #print("player change room type", type(new_room))
        
        if len(msg_to_cur_room) > 0:
            msg_to_cur_room = f"{self._name} leaves the room."
        if len(msg_to_new_room) > 0:
            msg_to_new_room = f"{self._name} enters the room."
        
        new_room.add_player(self, entry_point=entry_point)
        
        messages: list[Message] = []
        
        if cur_room is not None:
            messages.append(ServerMessage(cur_room, msg_to_cur_room)) # tell them the player left
            messages.extend(cur_room.send_grid_to_players()) # update their grid

        assert new_room is not None
        messages.append(ServerMessage(new_room, msg_to_new_room))
        messages.extend(new_room.send_grid_to_players()) # update their grid

        return messages

class HumanPlayer(Player, RecipientInterface):
    """ Represents a human player in the game. Contains information about the player's email,
        websocket state, and message sequence number.
    """

    def __init__(self, name: str, websocket_state: Any = None, email: str = "", image:str = 'player1', facing_direction: Literal['up', 'down', 'left', 'right'] = 'down', passable:bool = True) -> None:
        """ Initialize the human player. """
        self.__email: str = email
        self.__websocket_state = websocket_state
        self.__current_menu = None

        Player.__init__(self, name, image, facing_direction, passable)
        RecipientInterface.__init__(self)
    
    def get_websocket_state(self) -> None:
        """ Get the player's websocket state. """
        return self.__websocket_state

    def get_email(self) -> str:
        """ Get the player's email. """
        return self.__email

    def set_image_name(self, image: str) -> None:
        """ Set the player's image. """
        super().set_image_name(image)
        self.set_state('player_image', image)

    def update_info(self, name: str, websocket_state: Any) -> None:
        """ Update the player's name and websocket state. """
        self._name = name
        self.__websocket_state = websocket_state

    def execute_command(self, command_str: str) -> list[Message]:
        """ Execute a command for the player. """
        return self._current_room.execute_command(self, command_str)

    def change_room(self, new_room: 'Map', msg_to_player:str = "You leave the room.", msg_to_cur_room: str = "", msg_to_new_room: str = "", entry_point = None) -> list[Message]:
        """ Change the player's current room to the given room at the given coordinate (if provided)."""
        
        self.set_state("cur_room", new_room.get_name())
        messages: list[Message] = super().change_room(new_room, msg_to_cur_room, msg_to_new_room, entry_point)

        first_messages: list[Message] = []
        if self._current_room is not None:
            first_messages.append(ServerMessage(self, msg_to_player)) # tell the player they left
        first_messages.append(GridMessage(self)) # update their grid

        return first_messages + messages
    
    def set_current_menu(self, menu_obj: 'MapObject'):
        self.__current_menu = menu_obj

    def select_menu_option(self, option: str) -> list[Message]:
        """ Select a menu option. """
        assert self.__current_menu is not None
        return self.__current_menu.select_option(self, option)

    def interact(self) -> list[Message]:
        """ Interact with the object in front of the player. """
        assert self._current_room is not None

        return self._current_room.interact(self, facing_direction=self.get_facing_direction())
