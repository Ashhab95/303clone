import os
import time
import json
from abc import ABC, abstractmethod
from typing import Literal, TYPE_CHECKING

from .coord import Coord
from .resources import get_resource_path
if TYPE_CHECKING:
    from Player import HumanPlayer

class SenderInterface(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """ Returns the name of the sender. """
        pass

class RecipientInterface:
    def __init__(self) -> None:
        self._message_sequence_number: int = 0
    
    def get_and_increment_seq_num(self) -> int:
        """ Returns the sequence number of the recipient and increments it. """
        self._message_sequence_number += 1
        return self._message_sequence_number

class Message(ABC):
    """ A message to be sent between a sender and a recipient. The recipient can be
    a Map (i.e., a collection of HumanPlayers) or a HumanPlayer.
    """
    
    def __init__(self, sender: SenderInterface, recipient: RecipientInterface) -> None:
        """ Initializes the message with the sender and recipient. """
        if type(self) == Message:
            raise Exception("Message must be subclassed.")

        self.__sender: SenderInterface = sender
        self.__recipient: RecipientInterface = recipient
    
    def get_sender(self) -> SenderInterface:
        """ Returns the sender of the message. """
        return self.__sender

    def get_recipient(self) -> RecipientInterface:
        """ Returns the recipient of the message. """
        return self.__recipient

    def prepare(self) -> str:
        """ Returns a JSON string representation of the message. """
        return json.dumps({
            'classname': self.__class__.__name__,
            'handle': self.__sender.get_name(),
            'time': time.time(),
            'seq_num': self.__recipient.get_and_increment_seq_num() if hasattr(self.__recipient, 'get_and_increment_seq_num') else 0,
            **self._get_data(),
        })

    @abstractmethod
    def _get_data(self) -> dict:
        """ Returns the data to be sent in the message. """
        return {}

class ChatMessage(Message):
    """ A message to be displayed in the user's chat window. """

    def __init__(self, sender: SenderInterface, recipient: RecipientInterface, text: str) -> None:
        """ Initializes the chat message with the sender, recipient, and text. """
        self.__text: str = text
        super().__init__(sender, recipient)

    def _get_data(self) -> dict:
        return {
            'text': self.__text,
        }

class DialogueMessage(Message):
    """ A message to be displayed in the user's dialogue window. """
    def __init__(self, sender: SenderInterface, recipient: RecipientInterface, text: str, image: str, font: str = 'pkmn', bg_color: tuple = (255, 255, 255), text_color: tuple = (0, 0, 0)) -> None:
        """ Initializes the dialogue message with the sender, recipient, text, and image. """
        self.__text: str = text
        self.__image: str = image
        self.__font: str = font
        self.__bg_color: tuple = bg_color
        self.__text_color: tuple = text_color
        super().__init__(sender, recipient)

    def _get_data(self) -> dict:
        return {
            'dialogue_text': self.__text,
            'dialogue_image': self.__image,
            'dialogue_font': self.__font,
            'dialogue_bg_color': self.__bg_color,
            'dialogue_text_color': self.__text_color,
        }

class NPCMessage(DialogueMessage):
    """ A message to be displayed in the user's dialogue window from an NPC. """
    def __init__(self, sender: SenderInterface, recipient: RecipientInterface, text: str, image: str) -> None:
        """ Initializes the NPC message with the sender, recipient, text, and image. """
        self.__npc_name: str = sender.get_name()
        super().__init__(sender, recipient, text, image)
    
    def _get_data(self) -> dict:
        data: dict = super()._get_data()
        data['npc_name'] = self.__npc_name
        return data

class EmoteMessage(Message):
    """ A message to display an emote at a specific position. """
    def __init__(self, sender: SenderInterface, recipient: RecipientInterface, emote: str, emote_pos: Coord) -> None:
        """ Initializes the emote message with the sender, recipient, emote, and position. """
        self.__emote: str = emote
        self.__emote_pos: tuple[int, int] = emote_pos.to_tuple()
        super().__init__(sender, recipient)
    
    def _get_data(self) -> dict:
        return {
            'emote': self.__emote,
            'emote_pos': self.__emote_pos
        }

class ServerMessage(Message, SenderInterface):
    """ A message from the server to a recipient. """
    def __init__(self, recipient: RecipientInterface, text: str) -> None:
        """ Initializes the server message with the recipient and text. """
        self.__text: str = text
        Message.__init__(self, self, recipient)

    def get_name(self) -> Literal['***SERVER***']:
        return "***SERVER***"

    def _get_data(self) -> dict[str, str]:
        return {
            'text': self.__text,
        }
    
class GridMessage(Message, SenderInterface):
    """ A message to update the grid of a recipient. """
    def __init__(self, recipient: "HumanPlayer", send_desc : bool = True) -> None:
        """ Initializes the grid message with the recipient. """
        self.__send_desc: bool = send_desc
        self.__position: tuple[int, int] = recipient.get_current_position().to_tuple()
        self.__room_info: dict = recipient.get_current_room().get_info(recipient)
        Message.__init__(self, self, recipient)

    def get_name(self) -> Literal['***SERVER***']:
        return "***SERVER***"
    
    def _get_data(self) -> dict:
         data = dict(self.__room_info)
         data['position'] = self.__position
         if not self.__send_desc:
             del data['description']
         return data

class SoundMessage(Message, SenderInterface):
    """ A message to play a sound for a recipient. """
    def __init__(self, recipient, sound_path: str, volume: float = 0.5) -> None:
        """ Initializes the sound message with the recipient and sound path. """
        self.__sound_path: str = sound_path
        self.__volume: float = volume
        Message.__init__(self, self, recipient)

    def get_name(self) -> Literal['***SERVER***']:
        return "***SERVER***"
    
    def _get_data(self) -> dict:
        return {
            'sound_path': self.__sound_path,
            'volume': self.__volume,
        }

class MenuMessage(Message):
    """ A message to display a menu for a recipient. """
    def __init__(self, sender, recipient, menu_name: str, menu_options: list[str]) -> None:
        """ Initializes the menu message with the recipient, menu name, and options. """
        self.__menu_name: str = menu_name
        self.__menu_options: list[str] = menu_options
        Message.__init__(self, sender, recipient)

    def get_name(self) -> Literal['***SERVER***']:
        return "***SERVER***"
    
    def _get_data(self) -> dict:
        return {
            'menu_name': self.__menu_name,
            'menu_options': self.__menu_options,
        }

class FileMessage(Message):
    """ A message to download a file for a recipient. """
    def __init__(self, sender, recipient, file_path: str) -> None:
        """ Initializes the file message with the recipient and file path. """
        self.__file_path: str = file_path
        if not os.path.exists(get_resource_path(file_path)):
            print(f"File {file_path} does not exist.")
        Message.__init__(self, sender, recipient)

    def get_name(self) -> Literal['***SERVER***']:
        return "***SERVER***"
    
    def _get_data(self) -> dict:
        return {
            'file_path': self.__file_path,
        }