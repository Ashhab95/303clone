import os, pickle
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database_entity import DatabaseEntity

class Database:
    MAPPING = {
        "HumanPlayer": ("user_state.pkl", False),
        "Map": ("map_state.pkl", True),
        "NPC": ("npc_state.pkl", True),
    }

    def __init__(self) -> None:
        for filename, _ in self.MAPPING.values():
            if not os.path.exists(filename):
                with open(filename, "wb") as f:
                    pickle.dump({}, f)

    def get_data_for_object(self, obj: "DatabaseEntity"):
        class_hierarchy = [cls.__name__ for cls in obj.__class__.__mro__ if cls is not object]
        for entity_type, data in self.MAPPING.items():
            if str(entity_type) in class_hierarchy:
                return data
        assert False, f"Could not find entity class for {type(obj)}"

    def get_state(self, obj: "DatabaseEntity") -> dict:
        """ Get the state of the object from the database.. """
        filename, _ = self.get_data_for_object(obj)
        with open(filename, "rb") as f:
            data = pickle.load(f)
        return data.get(obj.get_name(), {})
    
    def update_state(self, obj: "DatabaseEntity", state: dict) -> None:
        """ Update the state of the object in the database. """
        filename, _ = self.get_data_for_object(obj)
        with open(filename, "rb") as f:
            data = pickle.load(f)
        data[obj.get_name()] = state
        with open(filename, "wb") as f:
            pickle.dump(data, f)
    
    def log(self, email, message):
        print("LOCAL DB LOG", email, message)

db = Database()