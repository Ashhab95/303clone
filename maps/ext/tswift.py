import os
import csv
import random

import yt_dlp

# TODO: Replace with gevent compatible library.
#from youtubesearchpython import VideosSearch

from ...coord import Coord
from ...maps.base import Map
from ...tiles.map_objects import *
from ...resources import get_resource_path
from ...tiles.base import MapObject, Subject

class RandomMusicPlayingPressurePlate(MusicPlayingPressurePlate, Subject):
    def __init__(self, artist_name, songs):
        self.__songs = songs
        self.__artist_name = artist_name
        self.__chosen_song_name = ""
        MusicPlayingPressurePlate.__init__(self)
        Subject.__init__(self)  # initialize the observer list

    def get_chosen_song_name(self):
        return self.__chosen_song_name

    def player_entered(self, player) -> list[Message]:
        chosen_song_index = random.randint(0, len(self.__songs)-1)
        chosen_song_name = self.__songs[chosen_song_index][0]
        self.__chosen_song_name = chosen_song_name

        song_fname = f'tswift/{chosen_song_index}'
        song_path = get_resource_path(f'sound/{song_fname}')

        if not os.path.exists(get_resource_path('sound/tswift')):
            os.makedirs(get_resource_path('sound/tswift'))

        if not os.path.exists(song_path + ".mp3"):
            videosSearch = VideosSearch(chosen_song_name + " " + self.__artist_name, limit=10)
            result = videosSearch.result()
            url = result['result'][0]['link'] # type: ignore

            ydl_opts = {
                'download_ranges': yt_dlp.download_range_func(None, [(13, 14)]),
                'outtmpl': song_path,
                'final_ext': 'mp3',
                'format': 'bestaudio',
                'postprocessors': [{'key': 'FFmpegExtractAudio',
                                    'nopostoverwrites': False,
                                    'preferredcodec': 'mp3',
                                    'preferredquality': '0'}]
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(url)

        self.set_sound_path(song_fname)

        # Notify observers (the boards) that the chosen song has changed
        song_names: list[str] = [chosen_song_name] + random.sample([row[0] for row in self.__songs if row[0] != chosen_song_name], 3)
        pplate_texts = ["Yay, you got it!!"] + ["wrONG!!!"]*3
        names_and_texts = list(zip(song_names, pplate_texts))
        random.shuffle(names_and_texts)
        song_names, pplate_texts = zip(*names_and_texts)

        self.notify_each_by_type(song_names, Board)
        self.notify_each_by_type(pplate_texts, PressurePlate)

        return super().player_entered(player) + [DialogueMessage(self, player, f"Can you guess the song??", "sign")]

class TriviaHouse(Map):
    def __init__(self):
        with open(get_resource_path('tswift_songs.csv'), newline='') as csvfile:
            reader = csv.reader(csvfile)
            self.__songs: list[list[str]] = [row for row in reader]

        super().__init__(
            name="Trivia House",
            description="Welcome to the Trivia House! Step up to the platform to begin.",
            size=(15, 15),
            entry_point=Coord(14, 8),
            background_tile_image='wood_brown',
        )

    def get_objects(self) -> list[tuple[MapObject, Coord]]:
        objects: list[tuple[MapObject, Coord]] = []

        # pplate
        music_pplate = RandomMusicPlayingPressurePlate("Taylor Swift", list(self.__songs))
        objects.append((music_pplate, Coord(12, 8)))

        # four boards and pressure plates
        for i in range(4):
            board = Board()
            music_pplate.attach(board)
            objects.append((board, Coord(6, 5+i*3)))

            pplate = PressurePlate()
            music_pplate.attach(pplate)
            objects.append((pplate, Coord(4, 5+i*3)))

        # add a sign
        sign = Sign(text="Welcome to the Trivia House! Step up to the platform to begin.")
        objects.append((sign, Coord(12, 7)))

        # add a door
        door = Door('int_entrance', linked_room="Trottier Town")
        objects.append((door, Coord(14, 8)))

        return objects

if __name__ == '__main__':
    with open(get_resource_path('tswift_songs.csv'), newline='') as csvfile:
        reader = csv.reader(csvfile)
        songs: list[list[str]] = [row for row in reader]
    
    music_pplate = RandomMusicPlayingPressurePlate("Taylor Swift", list(songs))
    for i in range(10000):
        music_pplate.player_entered(None)