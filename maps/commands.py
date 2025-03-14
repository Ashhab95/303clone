import os
import csv
from typing import TYPE_CHECKING

from ..database import db
from ..command import ChatCommand
from ..resources import get_resource_path
from ..message import FileMessage, Message, ServerMessage

if TYPE_CHECKING:
    from maps.base import Map
    from Player import HumanPlayer

class ListCommand(ChatCommand):
    """ Command to list all available commands. """

    name = 'list'
    desc = 'List all available commands.'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text == "list"

    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        return [ServerMessage(player, context.list_commands(player))]

class EmailTestCommand(ChatCommand):
    """ Command to send a test email to the admin. Admin-only command. """

    name = 'email_test'
    desc = 'Send a test email to the admin.'
    visibility = 'admin'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith('email_test')

    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        result = db_module.send_email("jonathan.campbell@mcgill.ca", "test message")
        return [ServerMessage(player, f"Email sent: {result}")]

class GetStateCommand(ChatCommand):
    """ Command to set a state for a player. Admin-only command. """

    name = 'get_state'
    desc = 'Get a state for a player.'
    visibility = 'admin'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith('get_state')
    
    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        _, handle, k = command_text.split("#")
        db_users = db.get_all_users()
        for user in db_users:
            if user.name == handle:
                state = db.get_state(user, "Users")
                if k not in state:
                    msg = f'State: {handle}: {k} not found. Full state: {state}.'
                else:
                    msg = f'State: {handle}: {k}->{state[k]}.'
                break
        else:
            msg = f"{handle} not found; available user handles: {', '.join([user.name for user in db_users])}"
        return [ServerMessage(player, msg)]

class SetStateCommand(ChatCommand):
    """ Command to set a state for a player. Admin-only command. """

    name = 'set_state'
    desc = 'Set a state for a player.'
    visibility = 'admin'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith('set_state')
    
    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        _, handle, k, v = command_text.split("#")
        if v.lower() in ["true", "false"]:
            v = bool(v.capitalize())
        elif v.isdecimal():
            v = int(v)

        db_users = db.get_all_users()
        for user in db_users:
            if user.name == handle:
                state = db.get_state(user, "Users")
                print(f"Existing state for {user.name}:", state)
                state[k] = v
                db.update_state(user, state, "Users")
                msg = f'State updated: {handle}: {k}->{v}.'
                break
        else:
            msg = f"{handle} not found"
        return [ServerMessage(player, msg)]

class DeleteStateCommand(ChatCommand):
    """ Command to delete a state for a player. Admin-only command. """

    name = 'delete_state'
    desc = 'Delete a state for a player.'
    visibility = 'admin'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith('delete_state')
    
    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        _, handle, k = command_text.split("#")
        db_users = db.get_all_users()
        for user in db_users:
            if user.name == handle:
                state = db.get_state(user, "Users")
                del state[k]
                db.update_state(user, state, "Users")
                msg = 'updated'
                break
        else:
            msg = f"{handle} not found"
        return [ServerMessage(player, msg)]

class MessageCommand(ChatCommand):
    """ Command to send a message to another player. """

    name = 'message'
    desc = 'Send a message to another player.'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith('message')
    
    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        command = command_text[len("message ")-1:]
        space = command.find(" ")
        handle = command[:space]
        message = command[space+1:]

        for client in context.get_human_players():
            if client.get_name().lower() == handle.lower():
                break
        else:
            return [ServerMessage(player, f"Couldn't find {handle} in the current room.")]

        return [
            ServerMessage(client, f"{player.get_name()} sends you a message: {message}"),
            ServerMessage(player, f"Message sent to {handle}."),
        ]

class GetProposalsCommand(ChatCommand):
    name = 'get_proposals'
    desc = 'Get proposals for a student to review.'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.startswith('get_propo')
    
    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        # load the review_assignments.csv file as a dict
        assignments = {}
        with open("review_assignments.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                assignments[row["Student"]] = row
        
        # get the row for the student.
        email = player.get_email()
        if email not in assignments:
            return [ServerMessage(player, f"No proposals found for {email}.")]
        
        archive_filename = assignments[email]["Filenames"]
        if not os.path.exists(get_resource_path(f"proposals/{archive_filename}.zip")):
            return [ServerMessage(player, f"Archive file {archive_filename} not found.")]

        db.log("get_proposals", f"{player.get_name()} downloaded {archive_filename}.zip")

        return [
            ServerMessage(player, f"Downloading file."),
            FileMessage(self, player, f"proposals/{archive_filename}.zip"),
        ]

class GetTAReviewCommand(ChatCommand):
    name = 'get_review'
    desc = 'Get reviews for your proposal.'

    @classmethod
    def matches(cls, command_text: str) -> bool:
        return command_text.lower().startswith('get_review')
    
    def execute(self, command_text: str, context: "Map", player: "HumanPlayer") -> list[Message]:
        # get student's group
        with open("groups.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Email"] == player.get_email():
                    group = row["Group"]
                    break
            else:
                return [ServerMessage(player, f"Group not found for {player.get_email()}")]
        
        # get the PDF filename for the student's group
        with open("proposal_zip_by_group.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["group"] == group:
                    archive_filename = row["filename"]
                    break
            else:
                return [ServerMessage(player, f"file for group {group} not found.")]

        db.log("get_review", f"{player.get_name()} downloaded {archive_filename}.zip")

        return [
            ServerMessage(player, f"Downloading file."),
            FileMessage(self, player, f"proposals/reviews/{archive_filename}.zip"),
        ]