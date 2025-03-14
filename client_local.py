
###
## Do not modify this file.
###

import os
import sys
import json
import time
import signal
import traceback
import threading
from abc import ABC
from enum import Enum
from pathlib import Path
from collections import defaultdict
from queue import Queue, PriorityQueue
from typing import Any, NoReturn, Union

try:
    import tkinter as tk
    from tkinter import NORMAL, font
except:
    print("You must install python-tk witn your package manager.")

try:
    import requests
    from pygame import mixer; mixer.init() # must install pygame
    from PIL.ImageFont import FreeTypeFont
    from PIL import Image, ImageTk, ImageFont, ImageDraw # must install Pillow
except:
    raise Exception("You must pip3 install requests websocket-client pygame Pillow")

from .util import shorten_lines
from .resources import get_resource_path

TILE_SIZE = 32
NUM_ROWS, NUM_COLS = 15, 15

GRID_HEIGHT = 15 * TILE_SIZE
GRID_WIDTH = 15 * TILE_SIZE

class ResourceType(Enum):
    IMAGE = 'image'
    FONT = 'font'
    SOUND = 'sound'

    @property
    def extension(self) -> str:
        extensions: dict[ResourceType, str] = {
            ResourceType.IMAGE: 'png',
            ResourceType.FONT: 'ttf',
            ResourceType.SOUND: 'mp3',
        }
        return extensions[self]

class ResourceManager:
    """ A class to manage resources such as images, fonts, and sounds. """
    _cache: dict = {}

    def __init__(self):
        self.__load_cache()

    def __load_resource(self, resource_type: ResourceType, file_path: Path) -> Union[ImageTk.PhotoImage, ImageFont.FreeTypeFont, Path]:
        """ Load a resource from disk and return a usable object. """
        if resource_type == ResourceType.IMAGE:
            original_image = Image.open(file_path)
            new_size: tuple[int, int] = (original_image.width * 2, original_image.height * 2)
            resized_image = original_image.resize(new_size, Image.Resampling.NEAREST)  # Use NEAREST for pixel art
            return ImageTk.PhotoImage(resized_image)
        elif resource_type == ResourceType.FONT:
            return ImageFont.truetype(font=str(file_path), size=20)
        elif resource_type == ResourceType.SOUND:
            return file_path

    def __load_cache(self) -> None:
        """ Load all resources from the resources folder into the cache. """
        for rsrc_type in ResourceType:
            ResourceManager._cache[rsrc_type] = {}

            folder_path = Path(f'rsrc_cache/{rsrc_type.name.lower()}')
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                return
            
            resource_dir = Path("rsrc_cache") / rsrc_type.value
            print(resource_dir)
            for file_path in resource_dir.rglob("*"):
                if file_path.is_dir():
                    continue
                relative_path = file_path.relative_to(resource_dir).with_suffix("")
                print("Loading from cache", relative_path)
                if file_path.stem.startswith('.'):
                    continue
                rsrc = self.__load_resource(rsrc_type, file_path)
                ResourceManager._cache[rsrc_type][str(relative_path)] = rsrc
                ResourceManager._cache[rsrc_type][str(file_path.relative_to(resource_dir))] = rsrc

    def _get_resource_from_source(self, resource_type: ResourceType, name: str) -> bytes:
        fname = name
        if '.' not in fname:
            fname += '.' + resource_type.extension
        data = open(get_resource_path(f'{resource_type.name.lower()}/{fname}'), 'rb').read()
        return data

    def __get_resource(self, resource_type: ResourceType, name: str) -> Any:
        """ Get a resource from the cache or load it from disk if it doesn't exist. """

        if resource_type in ResourceManager._cache and name in ResourceManager._cache[resource_type]:
            return ResourceManager._cache[resource_type][name]
        
        # get image from folder
        data = self._get_resource_from_source(resource_type, name)

        # save to disk
        fname = name
        if '.' not in fname:
            fname += '.' + resource_type.extension

        file_path = Path(f'rsrc_cache/{resource_type.name.lower()}/{fname}')
        print("Saving to cache", file_path)
        dirname = os.path.dirname(file_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(file_path, 'wb') as f:
            f.write(data)

        # load into cache
        if resource_type not in ResourceManager._cache:
            ResourceManager._cache[resource_type] = {}
        ResourceManager._cache[resource_type][name] = self.__load_resource(resource_type, file_path)

        print("New resource name:", name)
        return ResourceManager._cache[resource_type][name]

    def get_image(self, name: str) -> ImageTk.PhotoImage:
        """ Get an image resource by name. """
        return self.__get_resource(ResourceType.IMAGE, name)

    def get_sound(self, name: str) -> Path:
        """ Get a sound resource by name. """
        return self.__get_resource(ResourceType.SOUND, name)
    
    def get_font(self, name: str) -> ImageFont.FreeTypeFont:
        """ Get a font resource by name. """
        return self.__get_resource(ResourceType.FONT, name)

    def render_font(self, font: ImageFont.FreeTypeFont, text: str, type_ : str = "normal", bg_color: tuple = (255, 255, 255), text_color: tuple = (0, 0, 0)) -> Image.Image:
        """
        Render multi-line text into an image with a transparent background.

        Parameters:
        - font_path: Path to the TrueType font file.
        - text: The text string to render, can include multiple lines separated by '\n'.
        - type_: Type of rendering, "normal" or "bold".

        Returns:
        - A PIL Image object with the rendered text.
        """
        
        # Split text into lines
        lines = text.split('\n') if text else ['']
        
        # Get font metrics
        ascent, descent = font.getmetrics()
        # Define line spacing (adjust as needed)
        line_spacing = 4  # pixels

        # Calculate width and height
        max_width = 0
        for line in lines:
            # Use getbbox for accurate measurement
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            if line_width > max_width:
                max_width = line_width

        # Calculate line height based on font metrics
        line_height = ascent + descent + line_spacing
        total_height = line_height * len(lines)

        # Create a transparent image
        image = Image.new(mode='RGB', size=(max_width, total_height), color=(*bg_color, 0))
        draw = ImageDraw.Draw(image)

        # Render each line
        for idx, line in enumerate(lines):
            y_position = idx * line_height
            if type_ == "normal":
                draw.text((0, y_position), line, font=font, fill=text_color)
            elif type_ == "bold":
                # Simulate bold by adding a stroke
                draw.text((0, y_position), line, font=font, fill=text_color, stroke_width=1, stroke_fill='black')
            else:
                raise ValueError("Unsupported type_ value. Use 'normal' or 'bold'.")

        return image

class AudioPlayer:
    """ A class to manage audio playback. """
    current_sound: Path = ""
    current_sound_playing: bool = False

    @staticmethod
    def set_sound(file_path: Path) -> None:
        """ Set the sound file to be played. """
        if file_path != AudioPlayer.current_sound:
            mixer.music.load(file_path)
            AudioPlayer.current_sound_playing = False
            AudioPlayer.current_sound = file_path
        else:
            AudioPlayer.current_sound_playing = True

    @staticmethod
    def play_sound(volume: float) -> None:
        """ Play the currently set sound file. """
        mixer.music.set_volume(volume) #.5)
        if AudioPlayer.current_sound_playing:
            return
        mixer.music.play(-1)

    @staticmethod
    def stop_sound() -> None:
        """ Stop the currently playing sound. """
        mixer.music.stop()

class NetworkManager:
    """ A class to manage network communication. """

    def __init__(self, root_window: tk.Tk, server_inbox: Queue, server_outbox: Queue, resource_manager: ResourceManager) -> None:
        self._root_window: tk.Tk = root_window
        self.__server_inbox = server_inbox
        self.__server_outbox = server_outbox
        self._resource_manager = resource_manager
        self._data_dict = {}

    def download_file(self, path):
        # curl the file
        url = f"https://infinite-fortress-70189.herokuapp.com/{path}"
        print(url)
        response = requests.get(url)
        # check response code
        if response.status_code != 200:
            raise Exception(f"Could not load {path} from server. Status code: {response.status_code}")
        data = response.content
        
        # get stem of path
        stem = os.path.basename(path)
        # save to disk
        with open(stem, 'wb') as f:
            f.write(data)
        print(f"Downloaded {path} to {stem}")

    def update_data(self, data_dict: dict) -> None:
        self._data_dict = data_dict

    def send(self, data_dict, ws=None):
        data_dict.update(self._data_dict)
        self.__server_inbox.put(data_dict)

    def insert_message(self, messages: tk.Listbox, message: str) -> None:
        """ Insert a message into the message listbox. """
        lines = message.split('\n')

        short_lines = shorten_lines(lines, 75)
        for line in short_lines:
            messages.insert(tk.END, line)

        messages.yview(tk.END)

    def on_message(self, message: bytes) -> None:
        """ Handle a message from the server. """

        try:
            data = json.loads(message)
        except:
            print(f"Bad message (encoding): {message}")
            return
        
        if 'classname' not in data:
            print(f"Bad message (no class name): {message}")
            return

        print("Received message of type", data['classname'])

        if data['classname'] == 'GridMessage':
            self._grid_updates.put((data['seq_num'], 'grid', (data['grid'], data['room_name'], data['position'], data['bg_music'])))
            if 'description' in data:
                self.insert_message(self._messages, data['room_name'])
                self.insert_message(self._messages, data['description'])
        elif data['classname'] == 'EmoteMessage':
            self._grid_updates.put((data['seq_num'], 'emote', (data['emote'], data['emote_pos'])))
        elif data['classname'] == 'DialogueMessage':
            # TODO: Add npc_name and dialogue_image.
            lines = data['dialogue_text'].split('\n')
            short_lines = shorten_lines(lines, 35)
            font = data.get('dialogue_font', 'pkmn')
            bg_color = tuple(data.get('dialogue_bg_color', (255, 255, 255)))
            text_color = tuple(data.get('dialogue_text_color', (0, 0, 0)))
            self._text_queue.put(('\n'.join(short_lines), font, bg_color, text_color))
        elif data['classname'] in ['ChatMessage', 'ServerMessage']:
            if data.get('text', '') == 'disconnect':
                self._root_window.destroy()
            elif 'room_name' in data:
                self.insert_message(self._messages, f"[{data['room_name']}] {data['handle']}: {data['text']}")
            else:
                self.insert_message(self._messages, f"{data['handle']}: {data['text']}")
        elif data['classname'] == 'SoundMessage':
            sound_path = data['sound_path']
            sound_file = self._resource_manager.get_sound(sound_path)
            volume = data.get('volume', 0.5)
            
            AudioPlayer.set_sound(sound_file)

            # Start playing the sound in a separate thread
            play_thread = threading.Thread(target=AudioPlayer.play_sound, args=(volume,))
            play_thread.start()
        elif data['classname'] == 'MenuMessage':
            # spawn menu window with the given menu_name and menu_options
            menu_name = data['menu_name']
            menu_options = data['menu_options']
            self._menu_queue.put((menu_name, menu_options))
            #menu_window = MenuWindow(self._root_window, self, self._resource_manager, menu_name, menu_options)
            #menu_window.run()
        elif data['classname'] == 'FileMessage':
            self.download_file(data['file_path'])
        else:
            print(f"Bad message (unknown class name): {message}")

    def rcv_thread(self, messages: tk.Listbox, grid_updates: Queue, text_queue: Queue, menu_queue: Queue) -> NoReturn:
        """ A thread to receive and parse messages from the server. """

        self._messages = messages
        self._grid_updates = grid_updates
        self._text_queue = text_queue
        self._menu_queue = menu_queue

        while True:
            if self.__server_outbox.empty():
                time.sleep(0.1)
            if len(self._text_queue.queue) > 0:
                time.sleep(1)
            message = self.__server_outbox.get()
            self.on_message(message)

class Window(ABC):
    """ A class to manage a window. Sets up the window and provides a base for subclasses. """
    def __init__(self, root_window: tk.Tk, title: str, width: int, height: int, offset_x: int, offset_y: int, bg_color: str = "white") -> None:
        """ Initialize the window. """
        self._width: int = width
        self._height: int = height

        screen_width: int = root_window.winfo_screenwidth()
        screen_height: int = root_window.winfo_screenheight()

        main_x = int((screen_width/2) - (GRID_WIDTH/2))
        main_y = int((screen_height/2) - (GRID_HEIGHT/2))

        offset_x = main_x + offset_x
        offset_y = main_y + offset_y

        self._window = tk.Toplevel(root_window)
        self._window.title(title)
        self._window.geometry(f"{width}x{height}+{offset_x}+{offset_y}")
        self._window.configure(bg=bg_color)
        self._window.resizable(False, False)
    
    def update_color(self, bg_color: str) -> None:
        """ Update the background color of the window. """
        self._window.configure(bg=bg_color)

class DialagueBox(Window):
    """ A class to manage a dialogue box. """
    def __init__(self, root_window, resource_manager) -> None:
        """ Initialize the dialogue box. """

        super().__init__(root_window, title="Dialogue", width=GRID_WIDTH, height=120, offset_x=0, offset_y=-150)

        self.__border_frame = tk.Frame(self._window, bg="#FF0000")
        self.__border_frame.place(relx=0.5, rely=1.0, anchor='s', x=0, y=-10)  # Positioned at the bottom center
        self.__resource_manager = resource_manager

        self.__text_queue = Queue()
        self.__current_text = ""
        self.__current_index = 0
        self.__is_typing = False

        self.__typing_speed = 50  # milliseconds per character

        self.__text_font: FreeTypeFont = self.__resource_manager.get_font('pkmn')
        self.__current_font = None
        self.__bg_color = None
        self.__text_color = None

        self.__text_label = tk.Label(self._window, text="", wraplength=self._width-40, justify="left", bg='white', fg="#000000", anchor="nw")
        self.__text_label.place(x=20, y=5, width=self._width-40, height=self._height-20)

        indicator_font = font.Font(family="Consolas", size=10, slant="italic")
        self.__indicator_label = tk.Label(self._window, text="Press [return] to continue!", bg='white', fg="#000000", font=indicator_font)

        self.__indicator_x: int = self._width - 140
        self.__indicator_y: int = self._height - 20

        self.__monitor_queue()

    def get_text_queue(self) -> Queue:
        """ Get the text queue. """
        return self.__text_queue

    def is_typing(self) -> bool:
        """ Check if the dialogue box is currently typing. """
        return self.__is_typing

    def start(self) -> None:
        """Start processing the text queue."""
        if not self.__is_typing and len(self.__text_queue.queue) > 0:
            self.__current_text, font, self.__bg_color, self.__text_color = self.__text_queue.get()
            self.__current_font = self.__resource_manager.get_font(font)

            # change self.__border_frame to specified bg_color
            r, g, b = self.__bg_color
            hex_color = "#%02x%02x%02x" % (r, g, b)
            print("Changing border color to", hex_color)
            self.update_color(hex_color)
            self.__border_frame.config(bg=hex_color)
            self.__text_label.config(bg=hex_color)
            self.__indicator_label.config(bg=hex_color)

            # change text color
            r, g, b = self.__text_color
            hex_color = "#%02x%02x%02x" % (r, g, b)
            self.__text_label.config(fg=hex_color)
            self.__indicator_label.config(fg=hex_color)

            self.__current_index = 0
            self.__text_label.config(text="")
            self.__hide_indicator()  # Ensure indicator is hidden before typing
            self.__is_typing = True
            self.__partial_text = ""
            self.__type_character()

    def __type_character(self) -> None:
        """Display text one character at a time."""
        if self.__current_index < len(self.__current_text):
            # Append next character
            next_char = self.__current_text[self.__current_index]

            self.__partial_text += next_char
            image_text = self.__resource_manager.render_font(self.__current_font, self.__partial_text, bg_color=self.__bg_color, text_color=self.__text_color)

            # display image in label
            self.tk_image = ImageTk.PhotoImage(image_text)
            self.__text_label.config(image=self.tk_image) # type: ignore
            self.__current_index += 1

            # Schedule next character
            self._window.after(self.__typing_speed, self.__type_character)
        else:
            # Typing complete
            #self.__is_typing = False
            self.__show_indicator()

    def __show_indicator(self) -> None:
        """Show the 'Press Return to continue...' indicator."""
        self.__indicator_label.place(x=self.__indicator_x, y=self.__indicator_y)

    def __hide_indicator(self) -> None:
        """Hide the 'Press Return to continue...' indicator."""
        self.__indicator_label.place_forget()

    def on_return(self, event) -> None:
        """Handle Return key press."""
        self.__is_typing = False
        if (len(self.__text_queue.queue) > 0 or self.__text_label.cget("image")):
            if self.__text_label.cget("image"):
                # Clear current text
                self.__text_label.config(image="")
                self.__hide_indicator()
                # Start next text
                self.start()
            else:
                # If text is already cleared, just start next
                self.start()
    
    def __monitor_queue(self) -> None:
        """Continuously monitor the queue and start processing if not already."""
        if not self.__is_typing and len(self.__text_queue.queue) > 0:
            self.start()
        # Check again after a short delay
        self._window.after(10, self.__monitor_queue)

class MessageWindow(Window):
    """ A class to manage a message window. """
    def __init__(self, root_window: tk.Tk, network_manager: NetworkManager) -> None:
        """ Initialize the message window. """

        super().__init__(root_window, title="Messages", width=GRID_WIDTH, height=150, offset_x=0, offset_y=GRID_HEIGHT+50)

        self._window.rowconfigure(0, weight=1)  # The listbox frame
        self._window.rowconfigure(1, weight=0)  # The entry frame
        self._window.columnconfigure(0, weight=1)

        messages_frame = tk.Frame(master=self._window)
        scrollbar = tk.Scrollbar(master=messages_frame)
        self.__messages = tk.Listbox(
            master=messages_frame,
            yscrollcommand=scrollbar.set
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.__messages.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        messages_frame.grid(row=0, column=0, padx=2, pady=2, sticky="nsew")

        entry_frame = tk.Frame(master=self._window)
        text_input = tk.Entry(master=entry_frame)
        text_input.pack(fill=tk.BOTH, expand=True)
        entry_frame.grid(row=1, column=0, pady=5, padx=20, sticky="ew")

        self.__setup_text_input(text_input, network_manager)

    def get_messages(self) -> tk.Listbox:
        """ Get the listbox of messages. """
        return self.__messages

    def __setup_text_input(self, text_input: tk.Entry, network_manager: NetworkManager) -> None:
        def send_from_input_field():
            text = text_input.get()
            text_input.delete(0, tk.END)
            network_manager.send({
                'text': text,
            })

        text_input.bind("<Return>", lambda x: send_from_input_field())

        default_text = "Type your message here. Then press return to send."
        text_input.insert(0, default_text)

        def clear_placeholder(event):
            if text_input.get() == default_text:
                text_input.delete(0, tk.END)
        text_input.bind("<FocusIn>", clear_placeholder)
        
        def delete_field(event):
            text_input.configure(state=NORMAL)
            text_input.delete(0, tk.END)
            text_input.unbind('<Button-1>', delete_field_id)

        delete_field_id = text_input.bind('<Button-1>', delete_field)

class GridWindow(Window):
    """ A class to manage the grid window. """
    def __init__(self, root_window: tk.Tk, network_manager: NetworkManager, resource_manager: ResourceManager) -> None:
        """ Initialize the grid window. """

        super().__init__(root_window, title="Grid", width=GRID_WIDTH, height=GRID_HEIGHT, offset_x=0, offset_y=0)

        def handle_sigint(signum, frame):
            self.__on_closing()
            sys.exit(0)
        signal.signal(signal.SIGINT, handle_sigint)
        root_window.protocol("WM_DELETE_WINDOW", self.__on_closing)
        self._window.protocol("WM_DELETE_WINDOW", self.__on_closing)
        root_window.createcommand('::tk::mac::Quit', self.__on_closing)

        self.__root_window = root_window

        self.__last_move_time = 0
        self.__cur_grid = None
        self.__cur_room_name = None
        self.__image_refs = defaultdict(list)
        self.__grid_updates = PriorityQueue()
        #self.drawn_players = {}
        #self.movements = Queue() # TODO: Dict of queues for each sprite.
        self.__emotes = Queue()
        self.__emote_refs = {}
        self.__THROTTLE_INTERVAL = 0.15

        self.__canvas1, self.__canvas2 = self.__create_canvases()
        self.__message_window = MessageWindow(root_window, network_manager)
        self.__dialogue_window = DialagueBox(root_window, resource_manager)
        self.__setup_canvases()
        self.__network_manager = network_manager
        self.__resource_manager = resource_manager

        self.__menu_queue = Queue()
        self.__rcv_t = threading.Thread(target=network_manager.rcv_thread, args=(self.__message_window.get_messages(), self.__grid_updates, self.__dialogue_window.get_text_queue(), self.__menu_queue))
        self.__rcv_t.daemon = True

    def __on_closing(self):
        print("Disconnecting from server")
        self.__network_manager.send({
            'type': 'disconnect',
        })
        time.sleep(0.1)
        self.__root_window.destroy()

    def __create_canvases(self) -> tuple[tk.Canvas, tk.Canvas]:
        frm_main = tk.Frame(master=self._window, borderwidth=0, relief='flat', highlightthickness=0)
        frm_main.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        canvas = tk.Canvas(master=frm_main, width=GRID_WIDTH, height=GRID_HEIGHT, bg="white", borderwidth=0, highlightthickness=0)
        canvas2 = tk.Canvas(master=frm_main, width=GRID_WIDTH, height=GRID_HEIGHT, bg="white", borderwidth=0, highlightthickness=0)

        canvas.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        canvas2.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")  # Example placement
        tk.Misc.lift(canvas)

        return canvas, canvas2

    def __setup_canvases(self) -> None:
        tk.Misc.lift(self.__canvas1)

        # when users click on the image_label, it should gain focus
        self.__canvas1.bind('<Button-1>', lambda x: self.__canvas1.focus_set())

        # give it focus by default
        self.__canvas1.focus_set()

        # when users press the arrow keys when the image_label has focus, the command should be sent to the server
        def send_command(event):
            current_time = time.time()
        
            # Check if enough time has passed since the last move
            if current_time - self.__last_move_time < self.__THROTTLE_INTERVAL:
                # Throttle: ignore this keypress
                print(f"Ignored {event.keysym} keypress to throttle.")
                return
            
            # Update the last move time
            self.__last_move_time = current_time

            self.__network_manager.send({
                'move': event.keysym,
            })
        for arrow_key in ['Up', 'Down', 'Left', 'Right', 'space']:
            self.__canvas1.bind(f'<{arrow_key}>', send_command)
        
        self.__canvas1.bind('<Return>', lambda x: self.__dialogue_window.on_return(x))

        # unbind all from canvas2 
        for arrow_key in ['Up', 'Down', 'Left', 'Right', 'space', '<Button-1>']:
            self.__canvas2.bind(f'<{arrow_key}>', lambda x: None)
    
    def __del__(self) -> None:
        if self.__rcv_t.is_alive():
            self.__rcv_t.join()
    
    def __draw_grid(self, cur_grid, new_grid, image_refs, cur_room_name, new_room_name, position) -> tuple[defaultdict[Any, list], list]:
        print("drawing grid with center at", position)

        movements = []

        grid_height = len(new_grid)
        grid_width  = len(new_grid[0]) if grid_height else 0

        # Camera (window) in terms of tile counts
        camera_width  = NUM_COLS
        camera_height = NUM_ROWS

        # Desired camera origin, then clamp
        desired_camera_x = position[1] - camera_width // 2
        desired_camera_y = position[0] - camera_height // 2

        camera_x = max(0, min(desired_camera_x, grid_width  - camera_width))
        camera_y = max(0, min(desired_camera_y, grid_height - camera_height))

        # Clear the (second) canvas
        self.__canvas2.delete("all")
        new_image_refs = defaultdict(list)

        PADDING = 6
        row_start = max(0, camera_y - PADDING)
        row_end   = min(grid_height, camera_y + camera_height + PADDING)

        col_start = max(0, camera_x - PADDING)
        col_end   = min(grid_width, camera_x + camera_width + PADDING)
        for tile_row in range(row_start, row_end):
            for tile_col in range(col_start, col_end):
                # Draw the tile. The key is the canvas offset:
                canvas_x = (tile_col - camera_x) * TILE_SIZE
                canvas_y = (tile_row - camera_y) * TILE_SIZE

                cell = new_grid[tile_row][tile_col]  # list of (image_name, z_index)
                for (image_name, z_index) in cell:
                    if not image_name:
                        continue
                    image = self.__resource_manager.get_image(image_name)

                    # On-canvas position
                    canvas_x = (tile_col - camera_x) * TILE_SIZE
                    canvas_y = (tile_row - camera_y) * TILE_SIZE
                    if 'character/player' in image_name:
                        canvas_y -= TILE_SIZE
                    
                    image_id = self.__canvas2.create_image(canvas_x, canvas_y, image=image, anchor=tk.NW)
                    if z_index <= -1:
                        self.__canvas2.tag_lower(image_id)

                    new_image_refs[(tile_col, tile_row)].append((image, image_id, image_name))

        # Swap the canvases
        self.__canvas1, self.__canvas2 = self.__canvas2, self.__canvas1
        self.__setup_canvases()

        return new_image_refs, movements
    
    '''
    def animate(self):
        # The following function was written by ChatGPT. That's why it is crap.

        #print("Setting vars")
        current_move = None
        max_steps = 4
        step_counter = 4
        move_direction = None
        player_img = None
        room_name = None

        def get_direction(start_tile, end_tile):
            start_x, start_y = start_tile
            end_x, end_y = end_tile
            if start_x < end_x:
                return "down"
            elif start_x > end_x:
                return "up"
            elif start_y < end_y:
                return "right"
            elif start_y > end_y:
                return "left"
            raise ValueError(f"Invalid move: {start_tile} to {end_tile}")

        def get_sprite_name(player_img, move_direction, frame_index):
            assert 0 <= frame_index < 4
            assert move_direction in ["up", "down", "left", "right"], f"Invalid move_direction: {move_direction}"
            assert player_img in ["player1", "player2", "player3", "player4", "prof"], f"Invalid player_img: {player_img}"
            return f"character/{player_img}/{move_direction}{frame_index+1}"

        def start_move(move):
            print("Starting", move[2], "move at", move[0], "to", move[1])
            nonlocal current_move, move_direction, step_counter, player_img, room_name
            (start_tile, end_tile, player, cur_room_name) = move
            move_direction = get_direction(start_tile, end_tile)  # e.g. "up", "down", "left", "right"
            step_counter = 0
            #max_steps = 4  # how many sub-frames you want for the move
            current_move = (start_tile, end_tile)
            player_img = player
            room_name = cur_room_name
            if room_name != self.cur_room_name:
                current_move = None
        
        def animate_player_step():
            nonlocal step_counter
            #print("Animation:", step_counter, max_steps)
            if step_counter < max_steps:
                # 1) Calculate fractional position
                fraction = step_counter / float(max_steps)
                # 2) Lerp from start_tile to end_tile in pixel space
                start_tile_x, start_tile_y = current_move[0]
                end_tile_x, end_tile_y = current_move[1]

                #print("Starting at", start_tile_x, start_tile_y, "and ending at", end_tile_x, end_tile_y)

                current_px_x = start_tile_x*TILE_SIZE + (end_tile_x - start_tile_x)*TILE_SIZE*fraction
                current_px_y = start_tile_y*TILE_SIZE + (end_tile_y - start_tile_y)*TILE_SIZE*fraction

                # 3) Cycle sprite
                frame_index = step_counter % 4
                sprite_name = get_sprite_name(player_img, move_direction, frame_index)  
                # e.g. for "up" + frame_index 0 → "up1.png", index 1 → "up2.png", etc.
                
                #image_id = canvas.create_image(j*32, i*32, image=image, anchor=tk.NW)
                #image_refs[(j, i)].append((image, image_id))

                # 4) Update the canvas image to the new position and sprite
                #print(self.drawn_players[player_img], current_px_y, current_px_x, get_image(sprite_name))
                self.canvas.coords(self.drawn_players[player_img], current_px_y, current_px_x)
                self.canvas.itemconfig(self.drawn_players[player_img], image=get_image(sprite_name))

                #bring player to front
                self.canvas.tag_raise(self.drawn_players[player_img])

                # 5) Increment step
                step_counter += 1
            else:
                # Finalize at the exact end tile pixel
                #print("Finishing move (1)")
                finish_current_move()
        
        def finish_current_move():
            nonlocal current_move, player_img
            (start_tile, end_tile) = current_move

            # Place the player exactly on the end tile in pixel coordinates
            end_tile_x, end_tile_y = end_tile
            final_px_x = end_tile_x * TILE_SIZE
            final_px_y = end_tile_y * TILE_SIZE
            self.canvas.coords(self.drawn_players[player_img], final_px_y, final_px_x)

            current_move = None

            if len(self.movements.queue) > 0:
                # Start the next move right away
                next_move = self.movements.get()
                #print("Finished move; next:", next_move)
                start_move(next_move)
            else:
                pass
                # No more moves, revert to idle sprite (e.g., "down1.png")
                #print("Finished move; no more moves")
                #self.canvas.itemconfig(self.drawn_players[player_img], image=get_image(f'character/{player_img}/down1')) #sprite_dict["down1"])
        
        def animate_loop():
            nonlocal current_move
            delay_ms = 8
            # 1. If the player is currently in the middle of a move, animate that step.
            if current_move is not None and step_counter <= max_steps:
                if room_name != self.cur_room_name:
                    current_move = None
                else:
                    #print("Animating step")
                    animate_player_step()
                    delay_ms = 48
                    #self.window.after(48, animate_loop, movements)  # ~60 FPS or slower for simpler animation
            # 2. Else, if we have moves in the queue, pop the next one and start animating it.
            elif len(self.movements.queue) > 0:
                #print("Starting move")
                # dequeue from movements
                movement = self.movements.get()
                start_move(movement)
                delay_ms = 48
            self.window.after(delay_ms, animate_loop)  # ~60 FPS or slower for simpler animation
            # 3. Otherwise, if no moves are left, ensure the player is in the idle sprite.
            #print("Move ended")
        
        try:
            #print("Starting animation loop")
            animate_loop()
        except:
            print(traceback.format_exc())
    '''
    
    def __draw_emotes(self) -> None:
        def delete_emote(emote_id, pos):
            self.__canvas1.delete(emote_id)
            del self.__emote_refs[pos]
        
        def draw_emote():
            while not self.__emotes.empty():
                emote, (i, j) = self.__emotes.get()
                i -= 1
                print("Drawing emote", emote, "at", i, j)
                image = self.__resource_manager.get_image(f'emote/{emote}')
                image_id = self.__canvas1.create_image(j*TILE_SIZE, i*TILE_SIZE, image=image, anchor=tk.NW)
                self.__emote_refs[(i, j)] = image_id
                self.__canvas1.tag_raise(image_id)
                self.__canvas1.after(2000, delete_emote, image_id, (i, j))
        
        try:
            draw_emote()
        except:
            print(traceback.format_exc())
        self._window.after(16, self.__draw_emotes)

    def __check_for_grid_updates(self) -> None:
        try:
            # get all elements from the grid_updates queue
            while not self.__grid_updates.empty():
                timestamp, update_type, data = self.__grid_updates.get()
                if update_type == 'grid':
                    new_grid, room_name, position, bg_music = data
                    if self.__cur_room_name != room_name:
                        AudioPlayer.stop_sound()
                        if len(bg_music) > 0:
                            sound_file = self.__resource_manager.get_sound(bg_music)
                            
                            AudioPlayer.set_sound(sound_file)

                            # Start playing the sound in a separate thread
                            play_thread = threading.Thread(target=AudioPlayer.play_sound, args=(0.5,))
                            play_thread.start()

                    self.__image_refs, movements = self.__draw_grid(self.__cur_grid, new_grid, self.__image_refs, self.__cur_room_name, room_name, position)

                    #print("Movements:", movements)
                    #for movement in movements:
                    #    self.movements.put(movement)
                    self.__cur_grid = new_grid
                    self.__cur_room_name = room_name
                elif update_type == 'emote':
                    self.__emotes.put(data)
                else:
                    raise ValueError(f"Invalid update type: {update_type}")
        except:
            print(traceback.format_exc())
        self._window.after(16, self.__check_for_grid_updates)

    def __check_for_menus(self) -> None:
        try:
            while not self.__menu_queue.empty():
                menu_name, menu_options = self.__menu_queue.get()
                menu_window = MenuWindow(self.__root_window, self.__network_manager, self.__resource_manager, menu_name, menu_options)
                menu_window.run()
        except:
            print(traceback.format_exc())
        self._window.after(64, self.__check_for_menus)

    def start(self) -> None:
        self.__rcv_t.start()
        self._window.after(32, self.__check_for_grid_updates)
        self._window.after(16, self.__draw_emotes)
        self._window.after(66, self.__check_for_menus)
        #self.window.after(16, self.animate)
        self._window.mainloop()

class MenuWindow(Window):
    def __init__(self, root_window: tk.Tk, network_manager: NetworkManager, resource_manager: ResourceManager, name: str, options: list[str]) -> None:
        self.__root_window = root_window
        self.__menu_options = options
        self.__network_manager = network_manager
        self.__resource_manager = resource_manager
        self.__selected_index = 0

        super().__init__(root_window, title="Menu", width=GRID_WIDTH//2, height=GRID_HEIGHT//2, offset_x=GRID_WIDTH//4, offset_y=GRID_HEIGHT//4)

        # Create a list to hold the Label widgets for each option
        self.__option_labels, self.__image_refs = self.__create_option_labels()

        # Bind the arrow keys and return key
        self._window.bind("<Up>", self.__on_up)
        self._window.bind("<Down>", self.__on_down)
        self._window.bind("<Return>", self.__on_return)

        # Ensure the window has focus so key events are captured.
        self._window.focus_set()

    def __create_option_labels(self):
        """Create and pack a label for each menu option."""
        option_labels, images = [], {}
        for index, option in enumerate(self.__menu_options):
            prefix = "X " if index == self.__selected_index else "  "
            label_image = self.__resource_manager.render_font(self.__resource_manager.get_font('pkmn'), prefix + option)
            tk_image = ImageTk.PhotoImage(label_image)
            label = tk.Label(self._window,
                             image=tk_image,
                             anchor="w",
                             padx=20,
                             pady=5)
            label.pack(fill='x')
            option_labels.append(label)
            images[index] = tk_image
        return option_labels, images

    def __update_labels(self):
        """Refresh the label text so that the selected option is marked with an X."""
        for index, label in enumerate(self.__option_labels):
            prefix = "X " if index == self.__selected_index else "  "
            label_image = self.__resource_manager.render_font(self.__resource_manager.get_font('pkmn'), prefix + self.__menu_options[index])
            tk_image = ImageTk.PhotoImage(label_image)
            label.config(image=tk_image)
            self.__image_refs[index] = tk_image

    def __on_up(self, event):
        """Move the selection up."""
        if self.__selected_index > 0:
            self.__selected_index -= 1
            self.__update_labels()

    def __on_down(self, event):
        """Move the selection down."""
        if self.__selected_index < len(self.__menu_options) - 1:
            self.__selected_index += 1
            self.__update_labels()

    def __on_return(self, event):
        """Send the selected option and close the window."""
        selected_option = self.__menu_options[self.__selected_index]
        self.__network_manager.send({
            'menu_option': selected_option,
        })
        self._window.destroy()

    def run(self):
        """Start the Tkinter main loop."""
        self.__root_window.after(0, self._window.mainloop)

def start() -> None:
    """ Start the client. """

    LOCAL = True

    root_window = tk.Tk()
    root_window.title('LOCAL')
    root_window.withdraw()

    resource_manager = ResourceManager()

    from .server_local import ChatBackend
    server = ChatBackend()
    server_inbox, server_outbox = server.start()
    network_manager = NetworkManager(root_window, server_inbox, server_outbox, resource_manager)

    main_window = GridWindow(root_window, network_manager, resource_manager)
    main_window.start()

if __name__ == '__main__':
    start()
