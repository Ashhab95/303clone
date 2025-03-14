
from typing import TypeVar
from abc import ABC, abstractmethod

from .database import db

class DatabaseEntity(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """ Returns the name of the entity. """
        pass

    T = TypeVar('T')
    def get_state(self, key: str, default: T = 0) -> T:
        """ Get the state for the given key. """
        state = db.get_state(self)
        if key in state:
            return state[key]
        return default

    def set_state(self, key: str, value : T) -> None:
        """ Set the state for the given key, updating the database. """
        state = db.get_state(self)
        state[key] = value
        db.update_state(self, state) # update database