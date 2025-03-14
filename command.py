from typing import TYPE_CHECKING
from abc import ABC, abstractmethod

from .message import Message, SenderInterface

if TYPE_CHECKING:
    from maps.base import Map
    from Player import HumanPlayer

class Command(SenderInterface, ABC):
    name = ''
    visibility = 'public'

    def get_name(self) -> str:
        return self.name

class MenuCommand(Command):
    @abstractmethod
    def execute(self, context: "Map", player: "HumanPlayer") -> list[Message]:
        """Execute the command using the provided context and return messages."""
        pass

class ChatCommand(Command):
    name = ''
    desc = ''
    visibility = 'public'

    @classmethod
    @abstractmethod
    def matches(cls, command_text: str) -> bool:
        """
        Returns True if the command_text matches the pattern for this command.
        """
        pass

    @abstractmethod
    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        """Execute the command using the provided context and return messages."""
        pass