
import os
import re
import csv
import base64
import traceback
from glob import glob
from datetime import datetime

import git
import requests
if os.environ["LOCAL"] == "True": # disable
    GITHUB_LOGIN = ""
    GITHUB_TOKEN = ""
else:
    GITHUB_LOGIN = os.environ['GITHUB_LOGIN']
    GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

from ..NPC import *
from ..coord import Coord
from ..database import db
from ..maps.base import Map
from ..command import ChatCommand
from ..tiles.map_objects import *
from ..tiles.base import MapObject
from ..message import Message, ServerMessage

class PullCommand(ChatCommand):
    name: str = 'pull'
    desc = 'Pull from your GitHub repository.'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith("pull")

    def execute(self, command_text: str, context: "Interior1", player) -> list[Message]:
        existing_repo = player.get_state('repo', None)
        if existing_repo is None:
            return [ServerMessage(player, "You must first register a GitHub repository at the registration desk before requesting to pull from it.")]

        cur_time = datetime.now()
        currently_testing = player.get_state('currently_testing', False)
        if currently_testing:
            delta_s = cur_time - datetime.fromisoformat(str(player.get_state('test_start')))
            if delta_s.total_seconds() < 60*5:
                return [ServerMessage(player, "You must wait until the current testing completes before starting a new test.")]

        # check how many times they've tested in past hour
        test_times = player.get_state('test_times', [])
        if len(test_times) >= 10:
            # check difference between the oldest test time and the current.
            first_test_time = datetime.fromisoformat(test_times[0])
            delta_s = cur_time - first_test_time
            if delta_s.total_seconds() < 60*60: # one hour
                remaining_minutes = 60 - delta_s.total_seconds()*60
                return [ServerMessage(player, f'Due to API rate limits, we are unable to process more than 10 requests per hour. Please wait {remaining_minutes+1} more minutes before requesting another test of your code.')]

            # the oldest is beyond an hour, so remove it
            player.set_state('test_times', test_times[1:])

        test_times.append(cur_time.isoformat())

        player.set_state('test_times', test_times)
        player.set_state('currently_testing', True)
        player.set_state('test_start', cur_time.isoformat())
        
        if not type(existing_repo) != tuple or len(existing_repo) != 2:
            player.set_state('currently_testing', False)
            return [ServerMessage(player, "Invalid repository information. Please register your repository again.")]

        repo_user, repo_name = existing_repo[0], existing_repo[1]

        success, err_msg = context.clone_repo(repo_user, repo_name, branch=player.get_state('branch', None))

        if not success:
            player.set_state('currently_testing', False)
            return [ServerMessage(player, err_msg)]
        
        try:
            context.store_files(player, repo_user, repo_name)
        except:
            player.set_state('currently_testing', False)
            return [ServerMessage(player, f"An error occurred while storing your files: {traceback.format_exc()}")]

        status, err = context.import_files(player, repo_user, repo_name)
        if not status:
            player.set_state('currently_testing', False)
            return [ServerMessage(player, err)]

        player.set_state('currently_testing', False)
        return [
            ServerMessage(player, "You have uploaded your code!"),
            ServerMessage(context, f"{player.get_name()} uploads their code."),
        ]

class RegisterRepoCommand(ChatCommand):
    name = 'repo'
    desc = 'Register your GitHub repository.'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith("repo")

    def is_repo_valid(self, context, player: "HumanPlayer", repo_url, player_github_username):
        repo_user, repo_name = repo_url.split('/')
        
        # load partners csv
        groups_by_email = {}
        with open('groups.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                groups_by_email[row['Email']] = row['Group']
        player_group = groups_by_email.get(player.get_email(), None)
        player_partner_emails = {k: v for k, v in groups_by_email.items() if v == player_group}

        # check if already registered
        registered_repos = context.get_state('repos', [])
        for registered_email, registered_repo_user, registered_repo_name in registered_repos:
            if registered_repo_user == repo_user and registered_repo_name == repo_name:
                # trying to register one that registered_email had already registered
                
                # find the partners of this email.
                for partner_email in player_partner_emails:
                    if registered_email == partner_email:
                        return "" # was registered by a partner of this player.
                else:
                    return f"Error: This repository has already been registered by {registered_email}."

        '''
        # check if we already have access to it
        repos = requests.get('https://api.github.com/user/repos?per_page=100&sort=updated', auth=(GITHUB_LOGIN, GITHUB_TOKEN)).json()
        for repo in repos:
            if repo['full_name'].lower() == repo_url.lower():
                # check if this is attached to anyone else.

                registered_repos = self.get_state('repos', [])
                for email, repo_user_2, repo_name_2 in registered_repos:
                    if repo_user_2 == repo_user and repo_name_2 == repo_name:
                        if player.email == email:
                            return "" # it's the same player's own repo, somehow
                        else:
                            partners = self.get_state('partners', {})
                            for partner1_email, partner2_email in partners.items():
                                if email == partner1_email and player.email == partner2_email:
                                    return ""
                            else:
                                return f"This repository has already been registered by {email}. They must give you permission by registering you as a partner before you can register it as well."
                db.log("repo auth", f"{repo_url} {player.email} duplicate?")
                return ""
                #else:
                #    return f"Unknown error :O"
        '''

        # check if public
        response = requests.get(url='https://api.github.com/repos/'+repo_url)
        response = response.json()
        
        if 'message' not in response or response['message'] != "Not Found":
            return f"The repository {repo_url} was public. Your repo must be private, with comp303bot added as a collaborator."
        
        # check invites
        invites = requests.get('https://api.github.com/user/repository_invitations', auth=(GITHUB_LOGIN, GITHUB_TOKEN)).json()
        for invite in invites:
            if invite['repository']['full_name'] == repo_url:
                break
        else:
            return f"comp303bot could not find an invitation to {repo_url}. Did you invite them as a collaborator?"
        
        # accept invitation
        accept_invite = requests.patch(invite['url'], auth=(GITHUB_LOGIN, GITHUB_TOKEN))
        if accept_invite.status_code != 204:
            return f"comp303bot found an invitation to {repo_url}, but could not accept it (error code {accept_invite.status_code})."
        
        # now invite them to our own repository.
        response = requests.put(f'https://api.github.com/repos/COMP303W25/303MUD/collaborators/{player_github_username}', auth=(GITHUB_LOGIN, GITHUB_TOKEN), data='{"permission": "pull"}')
        print(response)

        return ""

    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        existing_repo = player.get_state('repo', None)
        if existing_repo is not None:
            return [ServerMessage(player, f'You have already registered the repository {existing_repo}. To change it, please make a private post on the discussion board.')]

        command_args = command_text.split(' ')
        if len(command_args) != 3:
            return [ServerMessage(player, "Invalid command. Please use the format /repo <username> github.com/username/reponame")]
        _, player_github_username, repo = command_args

        if repo.endswith('.git'):
            repo_url = repo[:-4]

        REPO_PATTERN = r'^https?://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$'
        if not bool(re.match(REPO_PATTERN, repo)):
            return [ServerMessage(player, "Invalid GitHub repository link. Make sure that it is of the form https://github.com/username/reponame")]

        repo_url = repo.split('github.com/')[-1]
        error = self.is_repo_valid(context, player, repo_url, player_github_username)
        if len(error) > 0:
            return [ServerMessage(player, error)]

        repo_user, repo_name = repo_url.split('/')
        player.set_state('repo', [repo_user, repo_name])
        registered_repos = context.get_state('repos', [])
        registered_repos.append((player.get_email(), repo_user, repo_name))
        context.set_state('repos', registered_repos)
        db.log("repo", f"{player.get_email()} registers a repository: {repo_user}/{repo_name}")
        return [
            ServerMessage(player, f"You have registered the repository {repo_user}/{repo_name}."),
            ServerMessage(context, f"{player.get_name()} registers a repository."),
        ]

class Interior1(Map):
    def __init__(self) -> None:
        super().__init__(
            name="Interior 1",
            size=(15, 15),
            entry_point=Coord(14, 8),
            description="room description here",
            background_music='blue_val',
            background_tile_image='wood_brown',
            chat_commands=[PullCommand, RegisterRepoCommand],
        )

    def get_objects(self) -> list[tuple[MapObject, Coord]]:
        objects: list[tuple[MapObject, Coord]] = []

        # add prof behind counter
        pull_prof = Professor(
            encounter_text="Hi! Welcome to the Upload Counter! Please come back later :)"
        )
        objects.append((pull_prof, Coord(1, 7)))
        
        # add counters
        pull_counter = YellowCounter(pull_prof)
        objects.append((pull_counter, Coord(0, 6)))

        register_prof = Professor(
            facing_direction='right',
            encounter_text="Hi! Welcome to the Registration Desk! To register your repository, please type /repo <username> github.com/username/reponame."
        )
        objects.append((register_prof, Coord(y=7, x=1)))

        registration_counter = YellowCounter(register_prof)
        objects.append((registration_counter, Coord(6, 0)))

        # add a plant
        plant = MapObject.get_obj('plant')
        objects.append((plant, Coord(3, 3)))

        # add a door
        door = Door('int_entrance', linked_room="Trottier Town")
        objects.append((door, Coord(14, 8)))

        return objects

    def clone_repo(self, repo_user, repo_name, branch=None):
        REPO_DIR = f'./repo/{repo_user}/{repo_name}'
        if not os.path.exists(REPO_DIR):
            os.makedirs(REPO_DIR)

        # try to clone
        if branch != "None":
            try:
                repo = git.Repo.clone_from(f"https://{GITHUB_LOGIN}:{GITHUB_TOKEN}@github.com/{repo_user}/{repo_name}.git", REPO_DIR, branch=branch)
            except:
                return False, f"The repository {repo_name} and branch {branch} could not be accessed. Make sure that you did not make any typos. Error traceback:\n{traceback.format_exc()}"
        else:
            try:
                repo = git.Repo.clone_from(f"https://{GITHUB_LOGIN}:{GITHUB_TOKEN}@github.com/{repo_user}/{repo_name}.git", REPO_DIR)
            except:
                return False, f"The repository {repo_name} could not be accessed. Make sure that you did not make any typos and that you have added 303bot as a collaborator. Error traceback:\n{traceback.format_exc()}"

        assert os.path.exists(REPO_DIR)

        for fname in list(glob(f"{REPO_DIR}/*")):
            if fname.endswith('.o'):
                os.remove(fname)

        return True, ""

    def store_files(self, player, repo_user, repo_name):
        REPO_DIR = f'./repo/{repo_user}/{repo_name}'
        # store the files at REPO_DIR into the player's state.
        # first encode the file into base64
        b64_data = {}
        for fname in list(glob(f"{REPO_DIR}/**/*.py", recursive=True)):
            with open(fname, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
                b64_data[fname] = b64
        player.set_state('repo_files', b64_data)

    def import_files(self, player, repo_user, repo_name):
        return True, "" # TODO
