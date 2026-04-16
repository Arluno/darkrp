"""
Network stub — multiplayer-ready architecture.
Will be expanded when multiplayer is enabled.
Currently runs everything locally but separates game state from rendering.
"""
import json
from game.settings import SERVER_HOST, SERVER_PORT, TICK_RATE


class NetState:
    """Shared game state that will be synced over the network later."""

    def __init__(self):
        self.players = {}  # player_id -> {x, y, angle, name}
        self.local_id = "local"

    def update_player(self, pid, x, y, angle, job=None):
        self.players[pid] = {"x": x, "y": y, "angle": angle, "job": job}

    def remove_player(self, pid):
        self.players.pop(pid, None)

    def serialize(self):
        return json.dumps(self.players)

    def deserialize(self, data):
        self.players = json.loads(data)


class NetworkManager:
    """
    Placeholder for future client/server networking.
    Currently just wraps local state.
    """

    def __init__(self):
        self.state = NetState()
        self.is_server = False
        self.is_connected = False

    def host_server(self):
        """TODO: Start a socket server on SERVER_HOST:SERVER_PORT."""
        print(f"[net] Server mode ready (will listen on {SERVER_HOST}:{SERVER_PORT})")
        self.is_server = True

    def connect(self, host=SERVER_HOST, port=SERVER_PORT):
        """TODO: Connect to a remote server."""
        print(f"[net] Client connect stub ({host}:{port})")
        self.is_connected = True

    def send_position(self, x, y, angle, job=None):
        """Send local player position (currently local-only)."""
        self.state.update_player(self.state.local_id, x, y, angle, job)

    def tick(self):
        """Called every server tick — will broadcast state later."""
        pass
