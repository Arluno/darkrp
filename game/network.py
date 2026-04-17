"""
Network client — connects the pygame client to server.py via WebSocket.
Runs the WebSocket in a background thread so the pygame main loop stays synchronous.
"""
import json
import threading
import queue
import websockets.sync.client as ws_client


class NetState:
    """Shared game state received from the server."""

    def __init__(self):
        self.local_id = None
        self.players = {}       # pid -> {x, y, angle, job, health, ...}
        self.buildings = []     # list of building dicts
        self.dropped_items = [] # list of {x, y, id, count}
        self.projectiles = []   # list of {x, y}
        self.you = {}           # personal state (health, inventory, etc.)
        self.jobs = []          # job list from server
        self.world = {"w": 2560, "h": 1920, "tile": 32}
        self.map_data = None    # {w, h, ground, walls} received once
        self.connected = False


class NetworkManager:
    """
    WebSocket client that runs in a background thread.
    The pygame main loop calls send_*() and reads state from self.state.
    """

    def __init__(self):
        self.state = NetState()
        self._ws = None
        self._thread = None
        self._send_queue = queue.Queue()
        self._running = False

    def connect(self, url: str, name: str = "Player"):
        """Start background thread that connects and processes messages."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run, args=(url, name), daemon=True)
        self._thread.start()

    def disconnect(self):
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

    def _run(self, url: str, name: str):
        """Background thread: connect, send join, then loop recv/send."""
        try:
            self._ws = ws_client.connect(url, close_timeout=2)
            self.state.connected = True
            # Send join
            self._ws.send(json.dumps({"type": "join", "name": name}))

            while self._running:
                # Drain outgoing queue
                while not self._send_queue.empty():
                    try:
                        msg = self._send_queue.get_nowait()
                        self._ws.send(msg)
                    except queue.Empty:
                        break

                # Receive with short timeout so we can also send
                try:
                    raw = self._ws.recv(timeout=0.02)
                    self._handle_message(raw)
                except TimeoutError:
                    pass

        except Exception as e:
            print(f"[net] Connection error: {e}")
        finally:
            self.state.connected = False
            self._running = False

    def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        mtype = msg.get("type")

        if mtype == "welcome":
            self.state.local_id = msg.get("id")

        elif mtype == "map":
            self.state.map_data = {
                "w": msg.get("w", 80),
                "h": msg.get("h", 60),
                "ground": msg.get("ground", ""),
                "walls": msg.get("walls", ""),
            }

        elif mtype == "state":
            self.state.players = msg.get("players", {})
            self.state.buildings = msg.get("buildings", [])
            self.state.dropped_items = msg.get("dropped_items", [])
            self.state.projectiles = msg.get("projectiles", [])
            self.state.you = msg.get("you", {})
            self.state.world = msg.get("world", self.state.world)
            if msg.get("jobs"):
                self.state.jobs = msg["jobs"]

        elif mtype == "error":
            print(f"[net] Server error: {msg.get('msg')}")

    def send(self, obj: dict):
        """Queue a message to send to the server."""
        if self._running:
            self._send_queue.put(json.dumps(obj))

    def send_input(self, keys: dict, angle: float, job: int, selected_hotbar: int):
        """Send player input to the server."""
        self.send({
            "type": "input",
            "keys": keys,
            "angle": angle,
            "job": job,
            "selected_hotbar": selected_hotbar,
        })

    def send_action(self, action: str, **kwargs):
        """Send a game action to the server."""
        msg = {"type": "action", "action": action}
        msg.update(kwargs)
        self.send(msg)
