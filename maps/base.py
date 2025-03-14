
from ..coord import *
from ..NPC import NPC
from ..message import *
from ..maps.commands import *
from ..command import ChatCommand
from ..Player import Player, HumanPlayer
from ..database_entity import DatabaseEntity
from ..tiles.base import Tile, MapObject, Exit

class Map(RecipientInterface, DatabaseEntity):
    """ Base class for a map in the game. Contains information about the map's name, size, entry point,
        description, background music, and commands.
    """
    
    NEXT_ID = 0
    
    def __init__(self, name: str, description: str, size: tuple[int, int], entry_point: Coord, background_music: str = "", background_tile_image: str = 'wood_brown', chat_commands: list[type[ChatCommand]] = []) -> None:
        """ Initialize a new map.
        
        Arguments:
            name: the name of the map
            description: the description of the map
            size: the size of the map in rows and columns
            entry_point: the coordinate where players enter the map
            background_music: the background music for the map
            background_tile_image: the image for the background tiles
            commands: the list of chat commands available in the map
        """
        MapObject.load_objects()
        self.__room_id = Map.NEXT_ID
        Map.NEXT_ID += 1

        self.__name: str = name
        self.__description: str = description
        self.__clients: list[Player] = []
        self.__background_music: str = background_music
        self.__entry_point: Coord = entry_point # where players start upon entering the room
        self.__npcs: list[NPC] = []
        self.__exits: list[Exit] = []
        self._map_rows, self._map_cols = size
        self.__tilemap = [ [ [] for _ in range(self._map_cols) ] for _ in range(self._map_rows) ]
        self.__objects: set[MapObject] = set()
        self.__exits: list[Exit] = []
        self.__setup_tilemap(background_tile_image)

        self.__commands: list[type[ChatCommand]] = [ListCommand, EmailTestCommand, GetStateCommand, SetStateCommand, DeleteStateCommand, MessageCommand, GetProposalsCommand, GetTAReviewCommand] + chat_commands

        RecipientInterface.__init__(self)
    
    def get_objects(self) -> list[tuple[MapObject, Coord]]:
        """ Get the objects that are placed on the map. Must be implemented by subclasses. """
        raise NotImplementedError

    def __setup_tilemap(self, background_tile_image: str):
        objects = self.get_objects()

        # background
        if len(background_tile_image) > 0:
            bg = MapObject.get_obj(background_tile_image)
            for i in range(self._map_rows):
                for j in range(self._map_cols):
                    objects.append((bg, Coord(i, j)))

        for object, coord in objects:
            object.set_position(coord)
            if isinstance(object, NPC):
                self.__npcs.append(object)
                #print("Type is NPC... changing coord to", coord)
                object.change_room(self, entry_point=coord)
                #self.add_player(object, entry_point=coord)
            else:
                self.__add_to_tilemap(object, coord)
            self.__objects.add(object)
        
        for map_object in self.__objects:
            self.__exits.extend(map_object.get_exits())

    def get_exits(self) -> list[Exit]:
        """ Returns a list of exits from the map. """
        return list(self.__exits)

    def get_name(self) -> str:
        """ Returns the name of the map. """
        return self.__name

    def get_room_id(self) -> int:
        """ Returns the ID of the room. """
        return self.__room_id

    def get_clients(self) -> list["Player"]:
        """ Returns the list of clients (human players) in the map. """
        return list(self.__clients)

    def get_human_players(self) -> list[HumanPlayer]:
        """ Returns the list of human players in the map. """
        return [player for player in self.__clients if type(player) == HumanPlayer]

    def remove_client(self, client: "Player") -> None:
        """ Remove a client from the map. """
        assert client in self.__clients, f"Client {client.get_name()} is not in {self.get_name()}"
        self.__clients.remove(client)

    def __repr__(self) -> str:
        """ Returns a string representation of the map. """
        return str(self)

    def get_description(self, player: "HumanPlayer") -> str:
        """ Returns the description of the map. """
        s = self.__description

        if len(self.__clients) > 0:
            player_names = [player.get_name() for player in self.__clients if player.get_current_room() == self]
            s += f' The following users are here: ' + ', '.join(player_names) + "."
        return s

    def list_commands(self, player: "HumanPlayer") -> str:
        """ Returns a list of commands available in the map. """
        cmds: str = ''
        for command in self.__commands:
            if command.visibility == 'admin' and player.get_name() not in ["jcampbell", "admin"]:
                continue
            cmds += f"{command.name}: {command.desc}\n"
        return cmds[:-1]

    def execute_command(self, player: "HumanPlayer", command_s: str) -> list[Message]:
        """ Execute a command for the player, taking the command string as input, and finding the
            appropriate command class to instantiate.
        """
        
        command_s_lower = command_s.lower()
        for command_cls in self.__commands:
            if command_cls.matches(command_s_lower):
                # Instantiate the command
                command_obj: ChatCommand = command_cls()
                break
        else:
            return [ServerMessage(player, f"Invalid command. The following commands are available:\n{self.list_commands(player)}")]
        
        return command_obj.execute(command_s, self, player)

    def __str__(self) -> str:
        """ Returns a string representation of the map. """
        '''
        s = ''
        for row in self.__tilemap:
            for cell in row:
                for tile in cell:
                    image = tile.get_image_name()
                    if len(image) > 0:
                        image = image.split('/')[-1]
                        s += image
                s += "-"
            s += '\n'
        return f'{self.__name}\n{s}'
        '''
        return self.__name

    def __add_to_tilemap(self, map_object: MapObject, start_pos: Coord) -> None:
        for a in range(map_object.num_rows):
            for b in range(map_object.num_cols):
                try:
                    self.__tilemap[start_pos.y + a][start_pos.x + b].append(Tile(map_object, Coord(a, b)))
                except:
                    raise Exception(f'Error adding {type(map_object)} to {start_pos.y + a}, {start_pos.x + b}')

    def __remove_from_tilemap(self, map_obj: MapObject, start_pos: Coord) -> bool:
        removed = False
        for a in range(map_obj.num_rows):
            for b in range(map_obj.num_cols):
                for tile in list(self.__tilemap[start_pos.y + a][start_pos.x + b]):
                    if tile.get_obj() == map_obj: # TODO: Equality?
                        self.__tilemap[start_pos.y + a][start_pos.x + b].remove(tile)
                        removed = True
                        break
        return removed

    def __get_tile_cell(self, coord: Coord) -> list[Tile]:
        return self.__tilemap[coord.y][coord.x]

    def remove_first_from_grid(self, map_obj: MapObject) -> tuple[bool, str]:
        """
        Remove the first instance of the object from the grid.
        Return a tuple of (status, error message).
        """
        remove_pos = None
        # find first position of object in tilemap
        for i in range(self._map_rows):
            for j in range(self._map_cols):
                for tile in self.__tilemap[i][j]:
                    if tile.get_obj() == map_obj:
                        remove_pos = Coord(i, j)
                        break
                if remove_pos is not None:
                    break
            if remove_pos is not None:
                break
        else:
            return False, "Object cannot be removed because it is not in the cell."
        return self.remove_from_grid(map_obj, remove_pos)

    def remove_from_grid(self, map_obj: MapObject, start_pos: Coord) -> tuple[bool, str]:
        """
        Remove an object from the grid at the given position.
        Return a tuple of (status, error message).
        """        
        status = self.__remove_from_tilemap(map_obj, start_pos)
        if not status:
            return False, "Object cannot be removed because it is not in the cell."
        else:
            self.__objects.remove(map_obj)
        return True, ""

    def add_to_grid(self, map_obj: MapObject, start_pos: Coord) -> None:
        """ Add an object to the grid at the given position. """
        self.__add_to_tilemap(map_obj, start_pos)
        self.__objects.add(map_obj)
    
    def map_to_images(self) -> list[list[str]]:
        """ Convert the map to a list of image names. """

        image_map = []
        for row in self.__tilemap:
            image_row = []
            for cell in row:
                image_col = []
                for tile in cell:
                    image = tile.get_image_name()
                    if len(image) > 0:
                        image_col.append((image, tile.get_z_index()))
                image_row.append(image_col)
            image_map.append(image_row)
        return image_map

    def get_info(self, player: "HumanPlayer") -> dict:
        """ Get the information about the map (to be used when sending to the client). """
        return {
            'room_name': self.__name,
            'grid': self.map_to_images(),
            'bg_music': self.__background_music,
            'description': self.get_description(player),
        }

    def send_grid_to_players(self) -> list[Message]:
        """ Return a list of grid messages to send to the players in the map. """
        messages = []
        for player in self.__clients:
            if type(player) == HumanPlayer:
                messages.append(GridMessage(player, send_desc=False))
        return messages

    def send_message_to_players(self, message: str) -> list[Message]:
        """ Return a list of server messages to send to the players in the map. """
        messages = []
        for player in self.__clients:
            if type(player) == HumanPlayer:
                messages.append(ServerMessage(player, message))
        return messages

    def add_player(self, player: "Player", entry_point = None) -> None:
        """ Add a player to the map at the entry point (if given). If no entry point is given,
            the player is added at the default entry point.
        """
        assert player not in self.__clients, f"Player {player.get_name()} is already in {self.get_name()}."
        self.__clients.append(player)
        if entry_point is None:
            entry_point = self.__entry_point
        self.add_to_grid(player, entry_point)
        player.update_position(entry_point, self)

    def remove_player(self, player: "HumanPlayer") -> None:
        """ Remove a player from the map. """
        for player_ in self.get_human_players():
            if player.get_name() == player_.get_name():
                self.__clients.remove(player_)
                self.remove_from_grid(player_, player_.get_current_position())
                break

    def update(self) -> list[Message]:
        """ Called every second; anything that happens in the room autonomously (i.e., without needing
            player input) should be implemented here. A list of messages should be returned.
        """
        messages = []
        for object in self.__objects:
            messages.extend(object.update())
        return messages

    def move(self, player: "Player", direction_s: str) -> list[Message]:
        """ Move the player in the given direction. """

        new_position: Coord = player.get_current_position() + MOVE_TO_DIRECTION[direction_s]
        if not (0 <= new_position.y + (player.num_rows - 1) < self._map_rows and 0 <= new_position.x + (player.num_cols - 1) < self._map_cols):
            return []
        
        new_cell = self.__get_tile_cell(new_position)
        #print("Moving to", new_position, "which contains:")
        for tile in new_cell:
            if not tile.is_passable():
                return []

        status, err = self.remove_from_grid(player, player.get_current_position())
        if not status and type(player) == HumanPlayer:
            return [ServerMessage(player, err)]
        self.add_to_grid(player, new_position)
        
        player.update_position(new_position, self)
        grid_messages = self.send_grid_to_players() # update with player's movement to new space

        tile_messages = []
        for tile in new_cell:
            tile_messages.extend(tile.player_entered(player))

        npc_messages = []
        for npc in self.__npcs:
            npc_messages.extend(npc.player_moved(player))

        return grid_messages + tile_messages + npc_messages

    def interact(self, player: "HumanPlayer", facing_direction: str) -> list[Message]:
        """ Called when the player wants to interact with the object in front of them. """

        new_position: Coord = player.get_current_position() + MOVE_TO_DIRECTION[facing_direction]
        if not (0 <= new_position.y + (player.num_rows - 1) < self._map_rows and 0 <= new_position.x + (player.num_cols - 1) < self._map_cols):
            return [ServerMessage(player, "You cannot interact in that direction.")]
        
        new_cell = self.__get_tile_cell(new_position)
        tile_messages = []
        for tile in new_cell:
            tile_messages.extend(tile.player_interacted(player))
        return tile_messages