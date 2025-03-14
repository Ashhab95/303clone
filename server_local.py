# -*- coding: utf-8 -*-

# Do not start this file. This file will be automatically called when you start client_local.py.

import os
import re
import time
import traceback
import threading
from queue import Queue
from collections import defaultdict

LOCAL = True
os.environ['LOCAL'] = "True"

from .NPC import *
from .message import *
from .maps.base import Map
from .Player import HumanPlayer
from .tiles.base import MapObject
from .util import get_subclasses_from_folders

class ChatBackend(object):
    STARTING_ROOM = "Trottier Town"

    def __init__(self):
        classes = get_subclasses_from_folders([Map, MapObject])
        MapObject.load_objects(classes[MapObject])

        self.__rooms: dict[str, Map] = self.__gen_layout(classes[Map])
        self.__players: list[HumanPlayer] = []
        self.__create_player()

        self.__message_inbox = Queue()
        self.__message_outbox = Queue()
        
        self.__rcv_t = threading.Thread(target=self.__run, args=(self.__message_inbox, self.__players[0]))
        self.__rcv_t.daemon = True

        self.__event_t = threading.Thread(target=self.__event_loop)
        self.__event_t.daemon = True

    def __gen_layout(self, room_classes) -> dict[str, Map]:
        # get rooms from defined classes
        all_rooms: dict[str, Map] = {}
        for room_name, room_class in room_classes.items(): # + subclasses:
            #print("Initializing room:", room_name)
            if '_' in room_name:
                room_name = room_name.replace("_", " ")
            else:
                room_name = re.sub(r"(\w)([A-Z])", r"\1 \2", room_name)
            words = room_name.split()
            for i, word in enumerate(words):
                if 1 < len(word) <= 3 and not word.isupper():
                    words[i] = words[i].lower()
            room_name = ' '.join(words)
            room_name = room_name[0].upper() + room_name[1:]

            # initialize room
            all_rooms[room_name] = room_class()
        
        # set exits
        exits = defaultdict(list)
        for room_name, room in all_rooms.items():
            for exit in room.get_exits():
                if len(exit.linked_map) == 0:
                    continue
                key = tuple(sorted([room_name, exit.linked_map]))
                exits[key].append((room_name, exit.door, exit.door_position))
        
        for (loc1_s, loc2_s), doors in exits.items():
            if len(doors) != 2:
                print(f"Expected 2 doors, got {len(doors)}, for {loc1_s} and {loc2_s}.")
                continue
            
            # Identify doors by their originating room.
            # Note that key (loc1_s, loc2_s) is sorted, so loc1_s is the alphabetically first room.
            # However, the stored room name may not be in that order.
            door_info1, door_info2 = doors
            room_from1, door1, door1_pos = door_info1
            room_from2, door2, door2_pos = door_info2

            # Now, decide which door belongs to which room:
            if room_from1 == loc1_s:
                # door1 came from loc1, door2 from loc2
                door1.connect_to(all_rooms[loc2_s], door2_pos)
                door2.connect_to(all_rooms[loc1_s], door1_pos)
            elif room_from1 == loc2_s:
                # door1 came from loc2, door2 from loc1
                door1.connect_to(all_rooms[loc1_s], door2_pos)
                door2.connect_to(all_rooms[loc2_s], door1_pos)
            else:
                raise ValueError("Unexpected room names in door pairing.")
        
        return all_rooms

    def __send_messages_to_recipients(self, messages: list[Message]):
        for x in messages:
            assert isinstance(x, Message), x
        for message in messages:
            recipient = message.get_recipient()
            if isinstance(recipient, Map):
                recipients: list[HumanPlayer] = [x for x in list(recipient.get_clients()) if type(x) is HumanPlayer]
            elif type(recipient) == HumanPlayer:
                recipients: list[HumanPlayer] = [recipient]
            else:
                continue
            
            for recipient in recipients:
                self.__send(recipient, message.prepare())

    def __send_message(self, message: Message):
        self.__send_messages_to_recipients([message])

    def __create_player(self):
        room = self.__rooms[ChatBackend.STARTING_ROOM]
        new_player = HumanPlayer(websocket_state=None, name="Local user", email="") # type: ignore
        new_player.change_room(room)
        self.__players.append(new_player)
        print("New player added:", new_player)
        return new_player

    def __send(self, player, message):
        self.__message_outbox.put(message)
    
    def __parse_message(self, data_d, player: HumanPlayer):
        print("Parsing message:", data_d)

        messages: list[Message] = []

        try:
            if 'move' in data_d:
                key = data_d['move'].lower()
                if key in ['left', 'right', 'up', 'down']:
                    messages = player.move(key)
                elif key == 'space':
                    messages = player.interact()
                else:
                    messages = [ServerMessage(player, 'Invalid direction.')]
            elif 'menu_option' in data_d:
                messages = player.select_menu_option(data_d['menu_option'])
            elif 'text' in data_d:
                if len(data_d['text']) > 0 and data_d['text'][0] == '/': # server command
                    # execute command
                    messages: list[Message] = player.execute_command(data_d['text'][1:])

                    notices = player.get_state('notices', [])
                    if len(notices) > 0:
                        notice_msg = "Notices:\n"
                        for notice in notices:
                            notice_msg += notice + "\n"
                        messages += [ServerMessage(player, notice_msg)]
                        player.set_state('notices', [])

                else: # regular message
                    messages = [ChatMessage(player, player.get_current_room(), data_d['text'])]
        except:
            messages = [ServerMessage(player, 'An error occurred processing your command: ' + traceback.format_exc())]

        self.__send_messages_to_recipients(messages)
    
    def __run(self, message_inbox: Queue, player: HumanPlayer):
        self.__send_message(GridMessage(player))
        while True:
            if message_inbox.empty():
                time.sleep(0.1)
            message = message_inbox.get()
            self.__parse_message(message, player)
    
    def __event_loop(self):
        while True:
            for room in self.__rooms.values():
                messages = room.update()
                self.__send_messages_to_recipients(messages)

            time.sleep(1)

    def start(self) -> tuple[Queue, Queue]:
        """ Start the backend thread with a single player. Should only be called once."""
        self.__rcv_t.start()
        self.__event_t.start()
        return self.__message_inbox, self.__message_outbox