from ..coord import Coord
from ..tiles.base import MapObject

def fill_area(objects: list[tuple[MapObject, Coord]], object_fill, start: Coord, end: Coord) -> None:    
    """
    fill an area with a specified object
    usage example:
    fill_area(objects, MapObject.get_obj('rock_1'), Coord(37, 14),Coord(37, 19))
    """
    # handle cases of filling as a line of tiles
    if start.x == end.x:  # vertical line
        end.x+=1
    elif start.y == end.y:  # horizontal line
        end.y+=1

    for x in range(start.y, end.y):
        for y in range(start.x, end.x):
            coord = Coord(x, y)
            objects.append((object_fill, coord))

def is_large_tree_area(positions, x, y) -> bool:
    """ 
    check if the position overlaps with upper 2 vertical and 
    2 horizontal spaces of a large tree
    """
    for tx, ty in positions:
        if (x >= tx and x < tx + 2) and (y >= ty and y < ty + 3):
            return True
    return False
