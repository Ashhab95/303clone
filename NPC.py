import math
import random
from typing import Literal

from .message import *
from .coord import MOVE_TO_DIRECTION
from .Player import Player, HumanPlayer

class NPC(Player):
    """ Represents a non-player character in the game."""
    def __init__(self, name: str, image: str, encounter_text : str, facing_direction: Literal['up', 'down', 'left', 'right'] = 'down', staring_distance: int = 0, bg_music='') -> None:
        """ Initialize the NPC with the given name, image, and facing direction.
            encounter_text: text that will be displayed when the player interacts with the NPC.
            staring_distance: the distance at which the NPC will start moving towards the player if facing in their direction.
        """
        self.__staring_distance: int = staring_distance
        self.__encounter_text: str = encounter_text
        self.__bg_music: str = bg_music
        super().__init__(
            name=name,
            image=image,
            facing_direction=facing_direction,
            passable=False,
        )

    #def fire_event(self, clock):
    #    pass
    
    #def handle_event(self, command):
    #    pass
    
    def player_moved(self, player: Player) -> list[Message]:
        """ Handle the event of the player moving. In the default case,
            the NPC will move towards the player if they are in range and have not yet interacted with the NPC,
            and then send their encounter text to the player.
        """

        if type(player) != HumanPlayer:
            return []

        if self.__staring_distance == 0: # don't interact with player if staring distance is 0
            return []
        
        messages: list[Message] = []

        # sound message
        if self.__bg_music != '':
            dist = self._current_position.distance(player.get_current_position())
            # make the volume louder as the distance is smaller, exponential decay
            decay_rate = 0.15  # adjust this rate to fit your needs
            volume = math.exp(-decay_rate * dist)
            messages.append(SoundMessage(player, self.__bg_music, volume=volume))

        # check if player is in range
        direction = MOVE_TO_DIRECTION[self.get_facing_direction()]
        for k in range(1, self.__staring_distance + 1):
            if player.get_current_position() == self._current_position + direction * k:
                break
        else:
            return messages

        if self.done_talking(player):
            return messages
        
        # player is in range

        # emote first.
        messages.append(EmoteMessage(self, player, 'exclamation', emote_pos=self._current_position))

        # then movement towards player until it is one square away.
        dist = self._current_position.distance(player.get_current_position())
        while dist > (1 + self.num_rows):
            # move towards player
            result = self.move(self.get_facing_direction())
            new_dist = self._current_position.distance(player.get_current_position())
            assert new_dist < dist, f"Distance did not decrease: {dist} -> {new_dist} and position: {self._current_position}; messages: {result}"
            dist = new_dist
            messages += result

        interact_messages: list[Message] = self.player_interacted(player)
        messages.extend(interact_messages)

        # mark that we have talked to the player
        talked_to_players = self.get_state('talked_to_players', [])
        talked_to_players.append(player.get_email())
        self.set_state('talked_to_players', talked_to_players)

        return messages

    def done_talking(self, player) -> bool:
        talked_to_players = self.get_state('talked_to_players', [])
        return player.get_email() in talked_to_players
        
    def player_interacted(self, player: HumanPlayer) -> list[Message]:
        """ Handle the event of the player interacting with the NPC. In the default case,
            the NPC will send their encounter text to the player.
        """
        return [DialogueMessage(self, player, self.__encounter_text, self.get_image_name())]

class Professor(NPC):
    def __init__(self, encounter_text: str, staring_distance: int = 0, facing_direction: Literal['up', 'down', 'left', 'right'] ='down') -> None:
        super().__init__(
            name="Professor",
            image='prof',
            encounter_text=encounter_text,
            facing_direction=facing_direction,
            staring_distance=staring_distance,
        )

class WalkingProfessor(Professor):
    def __init__(self, encounter_text: str, staring_distance: int = 0, facing_direction: Literal['up', 'down', 'left', 'right'] ='down') -> None:
        super().__init__(
            encounter_text=encounter_text,
            facing_direction=facing_direction,
            staring_distance=staring_distance,
        )
    
    def update(self) -> list["Message"]:
        """ Move in a random direction. """
        direction: Literal["up", "down", "left", "right"] = random.choice(['up', 'down', 'left', 'right'])
        print(f"Moving {direction}")
        return self.move(direction)
    