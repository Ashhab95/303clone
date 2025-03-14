# Do not modify this file.

import os
import time
import json
import random
import hashlib
import traceback
from queue import Queue

try:
    import tkinter as tk
    from tkinter.ttk import Frame, Label, Entry, Button
    from tkinter import simpledialog, messagebox, BOTH, X, LEFT
except:
    print("You must install python-tk witn your package manager.")

try:
    import requests # must install requests
    import websocket # must install websocket-client
    from pygame import mixer; mixer.init() # must install pygame
except:
    raise Exception("You must pip3 install requests websocket-client pygame Pillow")

from .version import VERSION
from .client_local import ResourceManager, ResourceType, Window, NetworkManager, GridWindow

TILE_SIZE = 32
NUM_ROWS, NUM_COLS = 15, 15

GRID_HEIGHT = 15 * TILE_SIZE
GRID_WIDTH = 15 * TILE_SIZE
if os.environ.get('LOCAL', False) == "True":
    SERVER_URL = 'localhost:8000'
    PROTOCOL = 'ws'
    WEB_PROTOCOL = 'http'
else:
    SERVER_URL = 'infinite-fortress-70189.herokuapp.com'
    PROTOCOL = 'wss'
    WEB_PROTOCOL = 'https'

class ResourceManagerServer(ResourceManager):
    @staticmethod
    def _get_resource_from_source(resource_type: ResourceType, name: str) -> bytes:
        # curl the image from webserver
        fname = name
        if '.' not in fname:
            fname += '.' + resource_type.extension

        url = f"{WEB_PROTOCOL}://{SERVER_URL.split(':')[0]}/{resource_type.value}/{fname}"
        print(url)
        response = requests.get(url)
        # check response code
        if response.status_code != 200:
            raise Exception(f"Could not load {name} from server. Status code: {response.status_code}")
        data = response.content
        return data

class NetworkManagerServer(NetworkManager):
    def __init__(self, root_window, resource_manager) -> None:
        self._root_window = root_window
        self._resource_manager = resource_manager
        self.__send_socket = websocket.WebSocket()
        self.__send_socket.connect(f"{PROTOCOL}://{SERVER_URL}/submit")

    def send(self, data_dict, ws=None):
        data_dict["VERSION"] = str(VERSION)
        data_dict.update(self._data_dict)
        data_s = json.dumps(data_dict)

        if ws is None:
            ws = self.__send_socket
        
        ws.send(data_s)

    def send_and_receive(self, data_dict):
        data_dict["VERSION"] = str(VERSION)
        data_s = json.dumps(data_dict)

        print("Connecting to", f"{PROTOCOL}://{SERVER_URL}/submit")

        ws = websocket.WebSocket()
        ws.connect(f"{PROTOCOL}://{SERVER_URL}/submit")

        #print("Sending", data_s)
        
        ws.send(data_s)
        print("Waiting for response")
        response = ws.recv()
        ws.close()

        assert len(response) > 0
        print("Received:", response)
        response = json.loads(response)
        
        return response

    def rcv_thread(self, messages: tk.Listbox, grid_updates: Queue, text_queue: Queue, menu_queue: Queue):
        self._messages = messages
        self._grid_updates = grid_updates
        self._text_queue = text_queue
        self._menu_queue = menu_queue
        
        def on_open(ws) -> None:
            self.send({
                "type": "register",
            }, ws)
            print("Sent register")

        def on_error(ws, error):
            print("Error:", traceback.format_exc())
            self.insert_message(messages, f"*** ERROR ***: {error}")

        def on_close(ws, close_status_code, close_msg):
            print("Closing.")
            self.insert_message(messages, f"*** SERVER ***: Connection closed by server: {close_msg} ({close_status_code})")

        def on_message(ws, message):
            while len(text_queue.queue) > 0:
                # pause thread for a second
                time.sleep(1)
            
            self.on_message(message)

        print("Starting receive thread")
        ws_rcv = websocket.WebSocketApp(f"{PROTOCOL}://{SERVER_URL}/receive",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
        ws_rcv.run_forever(ping_interval=3, skip_utf8_validation=True)

class AuthWindow(Window):
    def __init__(self, root_window, network_manager, resource_manager):
        self.__network_manager = network_manager
        self.__resource_manager = resource_manager
        self.__auth_dict = {}
        if os.path.exists("auth.json") or os.path.exists("303MUD/auth.json"):
            status = self.load_saved_auth()
            if not status:
                print("Error using saved auth")
                self.__auth_dict = {}
            return

        WINDOW_WIDTH = 620
        WINDOW_HEIGHT = 640
        super().__init__(root_window, title="Welcome to the COMP 303 Virtual World!", width=WINDOW_WIDTH, height=WINDOW_HEIGHT, offset_x=0, offset_y=0)

        auth_frame = tk.Frame(self._window)
        auth_frame.pack(fill=BOTH, expand=True)

        frame0 = Frame(auth_frame)
        frame0.pack(fill=X)
        img0 = self.__resource_manager.get_image('tile/ext_decor/tree_large_2')
        imageLabel = Label(frame0, image=img0) # type: ignore
        imageLabel.pack(side=tk.TOP, pady=16)

        frame1 = Frame(auth_frame)
        frame1.pack(fill=X)

        lbl1 = Label(frame1, text="Username (public)", width=15)
        lbl1.pack(side=LEFT, padx=25, pady=10)

        self.__entry1 = Entry(frame1)
        self.__entry1.pack(fill=X, padx=25, expand=True)

        frame2 = Frame(auth_frame)
        frame2.pack(fill=X)

        lbl2 = Label(frame2, text="McGill email (private)", width=15)
        lbl2.pack(side=LEFT, padx=25, pady=10)

        self.__entry2 = Entry(frame2)
        self.__entry2.pack(fill=X, padx=25, expand=True)

        # Variable to store the selected image path
        self.__selected_image = tk.StringVar()
        self.__selected_image.set("player1")  # Default selection

        # Container for radio buttons
        radio_frame = tk.LabelFrame(auth_frame, text="Choose Your Player Image")
        radio_frame.pack(padx=10, pady=10, fill="x")

        # Dictionary to hold references to PhotoImage objects to prevent garbage collection
        self.photo_images = {}

        # Create two frames within radio_frame for two rows
        row_frames = [tk.Frame(radio_frame) for _ in range(2)]
        for frame in row_frames:
            frame.pack(pady=0, anchor="center")

        # Create radio buttons for player images arranged in two rows of five
        for i in range(1, 11):
            image_path = f"character/player{i}/down1"
            image = self.__resource_manager.get_image(image_path)
            self.photo_images[i] = image  # Keep a reference to prevent garbage collection

            radio_btn = tk.Radiobutton(
                row_frames[(i - 1) // 5],  # Select the appropriate row frame
                #text=f"Player {i}",
                variable=self.__selected_image,
                value=f'player{i}',
                image=image,
                compound="top"
            )

            # Pack the radio button to the left within its row frame
            radio_btn.pack(side="left", padx=10, pady=0)

        frame3 = Frame(auth_frame)
        frame3.pack(fill=X)

        btn = Button(frame3, text="Register for a new account", command=self.on_submit)
        btn.pack(padx=5, pady=10)

        frame4 = Frame(auth_frame)
        frame4.pack(fill=X)
        credits = "The COMP 303 Virtual World is based on work done by Jonathan Campbell and many past TAs, CAs, and TEAM Mentors in COMP 202, including "
        names = ["Alex B.", "Charlotte S.", "Dasha B.", "Emma T.", "Hamza J.", "Jenny Y.", "Kadence C.", "Ken S.", "Lucas C.", "Morgan C.", "Naomie L.", "Nikola K.", "Victor C.", "Vivian L.", "Angela H.", "Michael H.", "Zachary D.", "Alexa I.", "Julia H.", "Laura R."]

        random.shuffle(names)
        credits += ', '.join(names)
        credits += '\n' + '\n'.join([
            'Sprites by Scarloxy (https://scarloxy.itch.io), '
            'Shade (https://merchant-shade.itch.io), '
            'Sharm (https://opengameart.org/content/tiny-16-basic); '
            'City theme by Jan Hehr (https://janhehr.itch.io/city-date); '
            'Upload House theme (The Blue Valley) by Karsten Koch; '
            'Pokémon Font by Phantom47',
            'Determination font by Haley Wakamatsu',
            'Circus Tent vector by amandalamsyah (Vecteezy)',
        ])
        lbl4 = Label(frame4, text=credits, wraplength=WINDOW_WIDTH-40, anchor="center", justify="center")
        lbl4.pack(fill=tk.X, expand=True)

        self._window.bind('<Return>', self.on_submit)
        self._window.mainloop()

    def load_saved_auth(self):
        if os.path.exists("auth.json"):
            self.__auth_dict = json.load(open('auth.json'))
        elif os.path.exists("303MUD/auth.json"):
            self.__auth_dict = json.load(open('303MUD/auth.json'))
        assert all(x in self.__auth_dict for x in ['email', 'password'])
        email, password = self.__auth_dict['email'], self.__auth_dict['password']
        ticket = self.get_ticket(email, password, '')
        self.__auth_dict['ticket'] = ticket
        return len(ticket) > 0
        
    def get_ticket(self, email, password, player_image) -> str:
        response = self.__network_manager.send_and_receive({
            'type': 'register',
            'email': email,
            'password': password,
            'player_image': player_image
        })
        
        if 'text' in response and response['text'].startswith('Error'):
            messagebox.showerror("Error", response['text'][7:])
            return ""
        
        ticket = response['text']
        return ticket

    def on_submit(self, *args, **kwargs):
        def process_inputs(handle, email, player_image):
            response = self.__network_manager.send_and_receive({
                'type': 'register',
                'handle': handle,
                'email': email,
                'player_image': player_image,
            })
            assert 'text' in response, response
            if response['text'].startswith('Error'):
                messagebox.showerror("Error", response['text'][7:])
                return {}
            else:
                messagebox.showinfo("Account created", response['text'])
            
            password = simpledialog.askstring("Enter password", "Please enter your password (sent to you by email)", parent=self._window, show="*")
            if not password or len(password) == 0:
                messagebox.showerror("Error in password entry.")
                return {}
            password = str(hashlib.sha256(bytes(password, 'utf-8')).digest())

            ticket = self.get_ticket(email, password, player_image)
            if len(ticket) == 0:
                return {}

            auth_dict = {'email': email, 'password': password}
            json.dump(auth_dict, open('auth.json', 'w'))

            auth_dict['ticket'] = ticket
            self._window.destroy()
            return auth_dict

        self.__auth_dict = process_inputs(self.__entry1.get(), self.__entry2.get(), self.__selected_image.get())
        self._window.quit()

    def get_auth_dict(self):
        return dict(self.__auth_dict)

def start():
    root_window = tk.Tk()
    root_window.title('infinite-fortress-70189')
    root_window.withdraw()

    resource_manager = ResourceManagerServer()
    network_manager = NetworkManagerServer(root_window, resource_manager)

    auth_window = AuthWindow(root_window, network_manager, resource_manager) # blocks until closed
    auth_dict = auth_window.get_auth_dict()
    network_manager.update_data(auth_dict)

    if len(auth_dict) > 0:
        print("Logged in successfully")

        main_window = GridWindow(root_window, network_manager, resource_manager)
        main_window.start()

if __name__ == '__main__':
    start()
