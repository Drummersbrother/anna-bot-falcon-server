import json

import falcon
from falconjsonio.schema import request_schema

"""The main file for the webapp, run this with your favourite WSGI server."""

# The json schema we accept from anna-bot about last online times
anna_bot_json_schema = {
    "type": "object",
    "properties": {
        "servers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "pattern": "^[1-9][0-9]+$"},
                    "users": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "icon_url": {"type": "string"},
                                "last_seen_time": {"type": "string"}
                            },
                            "required": ["username", "icon_url", "last_seen_time"]
                        }
                    },
                    "required": ["server_id", "users"]
                }
            }
        },
        "auth_token": {"type": "string"}
    },
    "required": ["servers", "auth_token"]
}


class LastOnlineList(object):
    """This class is a falcon resource that handles the "last-seen" list of users for an anna-bot server."""

    def __init__(self):
        """We have some internal state, such as the last given dict of servers and users."""

        # The dict of servers and users, format {"server_id": [{"username": , "icon_url": , "last_seen_time": }, ...], ...}
        self.server_user_list = {}

        # The config for this resource
        with open("config.json", mode="r", encoding="utf-8") as config_file:
            self.config = json.load(config_file)

    @request_schema(anna_bot_json_schema)
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        """Handles getting data from anna-bot."""

        # The json we got from anna-bot, this will be valid, as we use falconjsonio to validate and send error messages if it's not valid
        new_user_data = req.context["doc"]

        # We check the auth token against the config
        if not self.config["last_online_list"]["post_auth_token"] == new_user_data["auth_token"]:
            # We send back a http 401 status code, as the auth token wasn't correct
            resp.body = "Incorrect auth token."
            resp.status = falcon.status_codes.HTTP_FORBIDDEN

            # We log
            print("Got unauthorised user-data update attempt.")
            return

        # We update our server and user list
        # We do this by just using dict.update as it overwrites existing keys with the new value, and is also performant and simple
        self.server_user_list.update({(server["server_id"]): (server["users"]) for server in new_user_data["servers"]})

        # We log
        print("Updated users with authenticated post request.")

    def on_get(self, req: falcon.Request, resp: falcon.Response):
        """This is what actually serves the resource and displays the website and list."""
