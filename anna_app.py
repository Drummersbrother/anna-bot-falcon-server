import json
import os.path
from html import escape as htmlescape

import falcon
from jsonschema import validate, ValidationError

"""The main file for the webapp, run this with your favourite WSGI server."""

# The mapping of servenames to filepaths of static resources, will automatically use content-type headers for .html and .css files
static_mappings = {}


class LastOnlineList(object):
    """This class is a falcon resource that handles the "last-seen" list of users for an anna-bot server."""

    def __init__(self):
        """We have some internal state, such as the last given dict of servers and users."""

        # The dict of servers and users, format {"server_id": [{"username": , "icon_url": , "last_seen_time": }, ...], ...}
        self.server_user_list = {}

        # The json schema we validate out post data against
        self.post_json_schema = {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "required": ["servers", "auth_token"],
            "properties": {
                "servers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["server_id", "users"],
                        "properties": {
                            "server_id": {
                                "type": "string",
                                "pattern": "^[1-9][0-9]+$"},
                            "users": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["username", "icon_url", "last_seen_time"],
                                    "properties": {
                                        "username": {"type": "string"},
                                        "icon_url": {"type": "string"},
                                        "last_seen_time": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                "auth_token": {"type": "string"}
            }
        }

        # The config for this resource
        with open("config.json", mode="r", encoding="utf-8") as config_file:
            self.config = json.load(config_file)

        # We load the html files
        with open(os.path.join("html_files",
                               self.config["last_online_list"]["static_html_filename"])) as static_html_file:
            self.static_html = static_html_file.read()

        with open(os.path.join("html_files",
                               self.config["last_online_list"]["list_entry_html_filename"])) as list_entry_html_file:
            self.dynamic_html = list_entry_html_file.read()

        # We read and create a static mapping for the css stylesheet we have (if any)
        if "stylesheet_filename_servename_mapping" in self.config["last_online_list"]:
            global static_mappings
            static_mappings.update(self.config["last_online_list"]["stylesheet_filename_servename_mapping"])

    @staticmethod
    def log_info(*objects):
        print("LastOnlineList: " + ", ".join([repr(x) for x in objects]))

    def on_post(self, req: falcon.Request, resp):
        """Handles getting data from anna-bot."""

        # We check that we got a valid json input
        try:
            data = req.bounded_stream.read().decode()
            # Double loads because the data will be double encoded (once in the request, once after the stream.read().decode())
            new_user_data = json.loads(json.loads(data))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # We didn't get valid json, so we return bad request
            resp.body = "Invalid json."
            resp.status = falcon.HTTP_BAD_REQUEST

            # We log
            self.log_info("Got invalid json in update attempt")
            return

        # We validate the json with our schema
        try:
            validate(new_user_data, self.post_json_schema)
        except ValidationError:
            # The json was valid json, but not valid against the schema
            resp.body = "Invalid json format."
            resp.status = falcon.HTTP_BAD_REQUEST

            # We log
            self.log_info("Got invalid data against schema in update attempt")
            return


        # We check the auth token against the config
        if not self.config["last_online_list"]["post_auth_token"] == new_user_data["auth_token"]:
            # We send back a http 401 status code, as the auth token wasn't correct
            resp.body = "Incorrect auth token."
            resp.status = falcon.status_codes.HTTP_FORBIDDEN

            # We log
            self.log_info("Got unauthorised user-data update attempt.")
            return

        # We update our server and user list
        self.server_user_list = {(server["server_id"]): (server["users"]) for server in new_user_data["servers"]}

        # We return a successful code
        resp.status = falcon.status_codes.HTTP_OK
        resp.content_type = "text/plain"
        resp.body = "Successfully updated user and last-seen list."

        # We log
        self.log_info("Updated users with authenticated post request.")

    def on_get(self, req, resp):
        """This is what actually serves the resource and displays the website and list."""

        # We get the server id parameter as a string, if there isn't a server_id parameter, or it doesn't exist in the server_user_list, we return a 404
        requested_server_id = req.params.get("serverid")

        # If the parameter didn't exist, it's None
        if requested_server_id is None:
            # We give back a 404
            resp.body = "That server hasn't enabled this feature."
            resp.status = falcon.status_codes.HTTP_NOT_FOUND

            # We log
            self.log_info("Got invalid server id in get request.")
            return

        # We check that the serverid parameter wasn't given multiple times, and then passed to us as a list
        if isinstance(requested_server_id, list):
            # We give back a 404
            resp.body = "That server hasn't enabled this feature."
            resp.status = falcon.status_codes.HTTP_NOT_FOUND

            # We log
            self.log_info("Got invalid server id in get request.")
            return

        # We check that the specified server id is a key in the server_user_list
        if not requested_server_id in self.server_user_list:
            # We give back a 404
            resp.body = "That server hasn't enabled this feature."
            resp.status = falcon.status_codes.HTTP_NOT_FOUND

            # We log
            self.log_info("Got invalid server id in get request.")
            return

        # We create the html response
        # We begin by creating a list of user entries, sorted by escaped lowercase username alphabetically
        user_sorted_list = sorted(self.server_user_list[requested_server_id],
                                  key=lambda user: htmlescape(user["username"].lower(), quote=True))

        # We create a list of the list_entry html file, and format each one according to the user_sorted_list
        list_entries_html = [
            self.dynamic_html.format(x["icon_url"], htmlescape(x["username"], quote=True), x["last_seen_time"]) for _, x
            in enumerate(user_sorted_list)]

        # We set the content_type header
        resp.content_type = "text/html"

        # We format the static html with the list entries
        resp.body = self.static_html.format("".join(list_entries_html))

        # We return successfully, and we log it
        resp.status = falcon.HTTP_OK

        self.log_info("Served userlist page for server id {0}.".format(requested_server_id))


class StaticResource(object):
    """This class is used for a resource that is static."""

    def __init__(self, file_path: str):
        """Initialises the resource."""

        # We read and store the content of the file we are serving
        with open(file_path, mode="r") as serve_file:
            self.content = serve_file.read()

        # We define the content type to use
        if file_path.endswith(".css"):
            self.content_type = "text/css"
        elif file_path.endswith(".html"):
            self.content_type = "text/html"
        else:
            self.content_type = "text/plain"

    def on_get(self, req, resp):
        """We serve the content."""

        # Set the content type and status code
        resp.content_type = self.content_type
        resp.status = falcon.HTTP_OK

        # Set the response body
        resp.body = self.content


# The falcon API instance
app = falcon.API()

# The last-seen list resource
last_seen_resource = LastOnlineList()

# The static resources
for serve_name, filepath in static_mappings.items():
    # We add a static route and log it
    print("Added static route /static/{0} to filepath {1}.".format(serve_name, filepath))
    app.add_route("/static/" + str(serve_name), StaticResource(filepath))

# We add the routes
app.add_route("/lastseen", last_seen_resource)
