
class Coord:
    """ A class to represent a coordinate. """

    def __init__(self, y: int, x: int) -> None:
        """ Initializes the coordinate with the given y and x values. """
        self.y: int = y
        self.x: int = x
    
    @classmethod
    def from_Coord(cls, coord) -> 'Coord':
        """ Create a new Coord object from another Coord object. A copy constructor. """
        return cls(coord.y, coord.x)

    def __add__(self, other) -> "Coord":
        """ Adds the current coordinate with the given one and returns a new coordinate. """
        return Coord(self.y + other.y, self.x + other.x)
    
    def __iadd__(self, other) -> "Coord":
        """ Adds the current coordinate with the given one and returns the current coordinate. """
        self.y += other.y
        self.x += other.x
        return self

    def __mul__(self, other) -> "Coord":
        """ Multiplies the current coordinate with the given number and returns a new coordinate. """
        assert type(other) == int
        return Coord(self.y * other, self.x * other)

    def __eq__(self, other) -> bool:
        """ Returns True if the current coordinate is equal to the given one. """
        return self.y == other.y and self.x == other.x
    
    def __repr__(self) -> str:
        """ Returns a string representation of the coordinate. """
        return f'Coord({self.y}, {self.x})'
    
    def distance(self, other) -> int:
        """ Returns the Manhattan distance between the current coordinate and the given one. """
        return abs(self.y - other.y) + abs(self.x - other.x)
    
    def to_tuple(self) -> tuple[int, int]:
        """ Returns a tuple representation of the coordinate. """
        return self.y, self.x

MOVE_TO_DIRECTION: dict[str, Coord] = {
    'left': Coord(0, -1),
    'right': Coord(0, 1),
    'up': Coord(-1, 0),
    'down': Coord(1, 0),
}

class Rect:
    """ A class to represent a rectangle. """
    def __init__(self, top_left: Coord, bottom_right: Coord) -> None:
        """ Initializes the rectangle with the given top left and bottom right coordinates. """
        self.top_left: Coord = top_left
        self.bottom_right: Coord = bottom_right