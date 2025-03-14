
import random

from ..coord import *
from ..NPC import Professor
from ..maps.base import Map
from ..command import MenuCommand
from ..tiles.map_objects import *
from ..tiles.base import MapObject
from ..maps.map_helper import is_large_tree_area

class TellJokeCommand(MenuCommand):
    def execute(self, context: "Map", player: "HumanPlayer") -> list[Message]:
        num_jokes_told_to_player = player.get_state('num_jokes_received', 0)
        player.set_state('num_jokes_received', num_jokes_told_to_player+1)
        
        num_jokes_told = context.get_state('num_jokes_told', 0)
        context.set_state('num_jokes_told', num_jokes_told+1)
        
        return [ServerMessage(player, "Why did the scarecrow win an award? Because he was outstanding in his field!")]

class CircusTent(Building):
    def __init__(self, linked_room_str: str = "") -> None:
        super().__init__('circus_tent', door_position=Coord(3, 1), linked_room_str=linked_room_str)

class TrottierTown(Map):
    def __init__(self) -> None:
        super().__init__(
            name="Trottier Town",
            size=(60, 40),
            entry_point=Coord(60-6-2-15-9, 13),
            description="description here",
            background_tile_image='grass',
            background_music='blithe',
        )

    def get_objects(self) -> list[tuple[MapObject, Coord]]:
        objects: list[tuple[MapObject, Coord]] = []

        NUM_WATER_ROWS = 6

        water_spaces = []
        # water in last two rows
        for j in range(self._map_cols):
            for i in range(self._map_rows-NUM_WATER_ROWS, self._map_rows):
                objects.append((Water(), Coord(i, j)))
                water_spaces.append(Coord(i, j))

        NUM_WALKWAY_ROWS = 25

        # all trees except for the a space in the middle, and small path up to it
        empty_spaces = [
            Rect(Coord(7, 7), Coord(self._map_rows-NUM_WATER_ROWS-NUM_WALKWAY_ROWS, 30)), # midpoint is 13, 13
            Rect(Coord(self._map_rows-NUM_WATER_ROWS-NUM_WALKWAY_ROWS, 11), Coord(self._map_rows-NUM_WATER_ROWS, 14)),
            Rect(Coord(self._map_rows-NUM_WATER_ROWS-(NUM_WALKWAY_ROWS//4), 14), Coord(self._map_rows-NUM_WATER_ROWS-(NUM_WALKWAY_ROWS//4)+2, 31)),
            Rect(Coord(43, 28), Coord(48, 32)),
        ]
        print(self._map_rows-NUM_WATER_ROWS-(NUM_WALKWAY_ROWS//4))

        tree_spaces = []
        large_tree_positions = []
        tree_types = ["tree_small_1","tree_large_1", "tree_large_2","mapletree_small_1", "mapletree_large_2"]
        random.seed(64)
        TREE_SPARSITY = 0.95  # probability in (0-1) of placing a tree

        for i in range(self._map_rows-1):
            for j in range(self._map_cols-1):
                if any(rect.top_left.y <= i <= rect.bottom_right.y and rect.top_left.x <= j <= rect.bottom_right.x for rect in empty_spaces):
                    continue
                # if already a tree there, skip
                if Coord(i, j) in tree_spaces + water_spaces:
                    continue

                if random.random() < TREE_SPARSITY:
                    # choose a tree type
                    tree_type=random.choices(tree_types, weights=[6, 3, 4, 2, 2], k=1)[0]
                    if "_small_" in tree_type and is_large_tree_area(large_tree_positions,i, j):
                        continue 
                    elif "_large_" in tree_type:
                        large_tree_positions.append((i, j))
                    tree = MapObject.get_obj(tree_type)
                    tree_spaces.append(Coord(i, j))
                    objects.append((tree, Coord(i, j)))
        random.seed(None)
        
        for j in range(self._map_cols):
            start_y, start_x = 0, j
            objects.append((MapObject.get_obj('tree_small_1'), Coord(start_y, start_x)))

        # add a building
        building1 = GreenHouseLarge(linked_room_str="Interior1")
        building_pos1 = Coord(11, 11)
        objects.append((building1, building_pos1))

        building2 = PurpleHouseSmall(linked_room_str="Tic tac toe House")
        building_pos2 = Coord(22, 8)
        objects.append((building2, building_pos2))

        building = GreenHouseLarge(linked_room_str="Trivia House")
        objects.append((building, Coord(21, 17)))

        building = PurpleHouseSmall(linked_room_str="Example House")
        objects.append((building, Coord(22, 25)))

        sign = Sign(text="Welcome to Trottier Town!")
        objects.append((sign, Coord(27, 13)))

        sign = Sign(text="Upload House\nWhere dreams come true...")
        objects.append((sign, building_pos1 + Coord(7, 1)))

        # add the npc
        prof = Professor(
            encounter_text="Test encounter text.",
            staring_distance=3,
        )
        objects.append((prof, Coord(8, 8)))

        #computer = Computer(menu_name="Select an option", menu_options={
        #    "Tell me a joke": TellJokeCommand()
        #})
        #objects.append((computer, Coord(60-6-2-15-9-3, 13)))

        objects.append((CircusTent(linked_room_str="Funhouse"), Coord(43, 29)))

        return objects
