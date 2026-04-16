import asyncio
import json
import math
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

TILE = 32
WORLD_W_TILES = 80
WORLD_H_TILES = 60
WORLD_W = WORLD_W_TILES * TILE
WORLD_H = WORLD_H_TILES * TILE
TICK_RATE = 20
PLAYER_SPEED = 180.0
PLAYER_HALF = 12.0
SALARY_INTERVAL_S = 30.0
HUNGER_DRAIN_PER_S = 0.7
THIRST_DRAIN_PER_S = 1.0
STARVATION_DAMAGE_PER_S = 1.2

JOBS = [
    {"name": "Citizen", "salary": 0, "color": "#b4b4b4"},
    {"name": "Police Officer", "salary": 15, "color": "#4682dc"},
    {"name": "Medic", "salary": 12, "color": "#dc3c3c"},
    {"name": "Mayor", "salary": 20, "color": "#b48c32"},
    {"name": "Gun Dealer", "salary": 10, "color": "#c87832"},
    {"name": "Chef", "salary": 8, "color": "#64b450"},
    {"name": "Thief", "salary": 10, "color": "#8c3c3c"},
    {"name": "Banker", "salary": 14, "color": "#32a064"},
]
JOB_CAPS = [None, 3, 2, 1, 2, 2, 2, 1]

ITEM_DEFS = {
    "food": {"name": "Food", "use": {"type": "consume", "hunger": 28}},
    "water": {"name": "Water", "use": {"type": "consume", "thirst": 34}},
    "medkit": {"name": "Medkit", "use": {"type": "consume", "hunger": 12, "thirst": 12, "health": 35}},
    "toolkit": {"name": "Toolkit", "use": {"type": "toolkit"}},
    "metal": {"name": "Metal", "use": {"type": "sell", "money": 60}},
    "soda": {"name": "Soda", "use": {"type": "consume", "thirst": 22, "hunger": 6}},
    "bandage": {"name": "Bandage", "use": {"type": "consume", "hunger": 10, "thirst": 6, "health": 18}},
    "battery": {"name": "Battery", "use": {"type": "sell", "money": 35}},
    "lockpick": {"name": "Lockpick", "use": {"type": "lockpick"}},
    "cuffs": {"name": "Cuffs", "use": {"type": "cuffs"}},
    "pistol": {
        "name": "Pistol",
        "use": {
            "type": "gun",
            "ammo": "pistol_ammo",
            "speed": 460.0,
            "projectile_life": 0.6,
            "cooldown": 0.17,
            "spread": 2.0,
            "pellets": 1,
            "damage": 18,
        },
    },
    "shotgun": {
        "name": "Shotgun",
        "use": {
            "type": "gun",
            "ammo": "shells",
            "speed": 390.0,
            "projectile_life": 0.43,
            "cooldown": 0.52,
            "spread": 9.0,
            "pellets": 6,
            "damage": 9,
        },
    },
    "pistol_ammo": {"name": "Pistol Ammo"},
    "shells": {"name": "Shotgun Shells"},
}

STARTING_ITEMS = [("food", 3), ("water", 2), ("medkit", 1), ("pistol", 1), ("pistol_ammo", 24)]
JOB_LOADOUTS = [
    [("food", 2), ("water", 1)],
    [("pistol", 1), ("pistol_ammo", 36), ("bandage", 2), ("water", 1), ("cuffs", 1)],
    [("medkit", 3), ("bandage", 4), ("water", 2)],
    [],
    [],
    [],
    [("lockpick", 2), ("metal", 2)],
    [],
]
TEAM_ITEM_IDS = sorted({iid for row in JOB_LOADOUTS for iid, _ in row})

# Building coordinates copied from the desktop layout footprint.
BUILDINGS = [
    {"id": "house1", "name": "House 1", "x": 10, "y": 19, "w": 10, "h": 8, "door": (14, 26), "government": False, "price": 1500, "owner": None, "locked": False},
    {"id": "house2", "name": "House 2", "x": 22, "y": 19, "w": 10, "h": 8, "door": (26, 26), "government": False, "price": 1200, "owner": None, "locked": False},
    {"id": "house3", "name": "House 3", "x": 29, "y": 10, "w": 8, "h": 7, "door": (36, 13), "government": False, "price": 800, "owner": None, "locked": False},
    {"id": "police", "name": "Police Dept", "x": 43, "y": 19, "w": 12, "h": 8, "door": (43, 22), "government": True, "price": 0, "owner": None, "locked": False, "jail_spawns": [(52, 21), (52, 24)]},
    {"id": "mayor", "name": "Mayor Office", "x": 57, "y": 19, "w": 10, "h": 8, "door": (61, 26), "government": True, "price": 0, "owner": None, "locked": False},
    {"id": "bank", "name": "Bank", "x": 10, "y": 33, "w": 12, "h": 8, "door": (15, 33), "government": True, "price": 0, "owner": None, "locked": False},
    {"id": "house4", "name": "House 4", "x": 24, "y": 33, "w": 8, "h": 7, "door": (27, 33), "government": False, "price": 800, "owner": None, "locked": False},
    {"id": "house5", "name": "House 5", "x": 43, "y": 33, "w": 10, "h": 8, "door": (47, 33), "government": False, "price": 1000, "owner": None, "locked": False},
    {"id": "hospital", "name": "Hospital", "x": 55, "y": 33, "w": 12, "h": 8, "door": (60, 33), "government": True, "price": 0, "owner": None, "locked": False},
]

JAIL_WALLS = [
    {"x": 48, "y": 20, "w": 1, "h": 6, "doors": [(48, 22)]},
    {"x": 50, "y": 20, "w": 1, "h": 6, "doors": [(50, 21), (50, 24)]},
    {"x": 51, "y": 23, "w": 3, "h": 1, "doors": []},
]
JAIL_DOORS = {(48, 22), (50, 21), (50, 24)}


def _deg_to_dir(angle_deg: float) -> tuple[float, float]:
    rad = math.radians(angle_deg)
    return -math.sin(rad), -math.cos(rad)


def _stack(item_id: str, count: int) -> dict:
    return {"id": item_id, "name": ITEM_DEFS[item_id]["name"], "count": int(count)}


def _count_item(player: dict, item_id: str) -> int:
    total = 0
    for arr_name in ("hotbar", "inventory"):
        for st in player[arr_name]:
            if st and st["id"] == item_id:
                total += int(st["count"])
    return total


def _remove_item(player: dict, item_id: str, count: int) -> bool:
    need = max(1, int(count))
    if _count_item(player, item_id) < need:
        return False
    for arr_name in ("hotbar", "inventory"):
        arr = player[arr_name]
        for i, st in enumerate(arr):
            if not st or st["id"] != item_id:
                continue
            take = min(need, int(st["count"]))
            st["count"] -= take
            need -= take
            if st["count"] <= 0:
                arr[i] = None
            if need <= 0:
                return True
    return True


def _add_item(player: dict, item_id: str, count: int, prefer_hotbar: bool = False) -> bool:
    if item_id not in ITEM_DEFS or count <= 0:
        return False
    left = int(count)
    order = ["hotbar", "inventory"] if prefer_hotbar else ["inventory", "hotbar"]
    for arr_name in order:
        arr = player[arr_name]
        for st in arr:
            if st and st["id"] == item_id:
                st["count"] += left
                return True
    for arr_name in order:
        arr = player[arr_name]
        for i, st in enumerate(arr):
            if st is None:
                arr[i] = _stack(item_id, left)
                return True
    return False


def _set_item_count(player: dict, item_id: str, target: int, prefer_hotbar: bool = False) -> None:
    target = max(0, int(target))
    current = _count_item(player, item_id)
    if current < target:
        _add_item(player, item_id, target - current, prefer_hotbar)
    elif current > target:
        _remove_item(player, item_id, current - target)


def _remove_all(player: dict, item_id: str) -> None:
    for arr_name in ("hotbar", "inventory"):
        arr = player[arr_name]
        for i, st in enumerate(arr):
            if st and st["id"] == item_id:
                arr[i] = None


def _get_job_counts(players: dict[str, dict]) -> list[int]:
    counts = [0] * len(JOBS)
    for p in players.values():
        j = p.get("job", 0)
        if isinstance(j, int) and 0 <= j < len(JOBS):
            counts[j] += 1
    return counts


def _can_take_job(players: dict[str, dict], pid: str, job_idx: int) -> bool:
    if not (0 <= job_idx < len(JOBS)):
        return False
    p = players.get(pid)
    if p is None:
        return False
    if p["job"] == job_idx:
        return True
    cap = JOB_CAPS[job_idx]
    if cap is None:
        return True
    if cap <= 0:
        return False
    counts = _get_job_counts(players)
    return counts[job_idx] < cap


def _apply_job_loadout(player: dict, job_idx: int) -> None:
    for iid in TEAM_ITEM_IDS:
        _remove_all(player, iid)
    for iid, c in JOB_LOADOUTS[job_idx]:
        _set_item_count(player, iid, c, prefer_hotbar=True)


def _tile_center(tx: int, ty: int) -> tuple[float, float]:
    return tx * TILE + TILE / 2, ty * TILE + TILE / 2


def _door_rect(tx: int, ty: int) -> tuple[float, float, float, float]:
    return tx * TILE, ty * TILE, TILE, TILE


def _inside_rect(px: float, py: float, rx: float, ry: float, rw: float, rh: float) -> bool:
    return rx <= px < rx + rw and ry <= py < ry + rh


def _is_police(player: dict) -> bool:
    j = player.get("job", 0)
    return isinstance(j, int) and 0 <= j < len(JOBS) and JOBS[j]["name"] == "Police Officer"


def _building_near(px: float, py: float, radius: float = 48.0) -> dict | None:
    rr = radius * radius
    for b in BUILDINGS:
        tx, ty = b["door"]
        dx = px - (tx * TILE + TILE / 2)
        dy = py - (ty * TILE + TILE / 2)
        if dx * dx + dy * dy <= rr:
            return b
    return None


def _is_solid(px: float, py: float, player: dict) -> bool:
    if px < 0 or py < 0 or px >= WORLD_W or py >= WORLD_H:
        return True

    tx = int(px // TILE)
    ty = int(py // TILE)

    for jw in JAIL_WALLS:
        if jw["x"] <= tx < jw["x"] + jw["w"] and jw["y"] <= ty < jw["y"] + jw["h"]:
            if (tx, ty) in jw.get("doors", []):
                if (tx, ty) in JAIL_DOORS and _is_police(player):
                    return False
                return True
            return True

    for b in BUILDINGS:
        bx, by = b["x"] * TILE, b["y"] * TILE
        bw, bh = b["w"] * TILE, b["h"] * TILE
        if not _inside_rect(px, py, bx, by, bw, bh):
            continue
        border = (
            px < bx + TILE or
            px >= bx + bw - TILE or
            py < by + TILE or
            py >= by + bh - TILE
        )
        if border:
            dtx, dty = b["door"]
            dx, dy, dw, dh = _door_rect(dtx, dty)
            if _inside_rect(px, py, dx, dy, dw, dh):
                if b.get("locked"):
                    if b.get("owner") == player["id"]:
                        return False
                    return True
                return False
            return True
    return False


def _move_player(player: dict, dt: float) -> None:
    if player.get("in_jail"):
        player["x"] = player.get("jail_x", player["x"])
        player["y"] = player.get("jail_y", player["y"])
        return
    if player.get("detained"):
        return

    keys = player["keys"]
    dx = (1.0 if keys.get("right") else 0.0) - (1.0 if keys.get("left") else 0.0)
    dy = (1.0 if keys.get("down") else 0.0) - (1.0 if keys.get("up") else 0.0)
    if dx != 0.0 or dy != 0.0:
        length = math.hypot(dx, dy)
        dx /= length
        dy /= length

    nx = player["x"] + dx * PLAYER_SPEED * dt
    ny = player["y"]
    if not (
        _is_solid(nx - PLAYER_HALF, ny - PLAYER_HALF, player) or
        _is_solid(nx + PLAYER_HALF, ny - PLAYER_HALF, player) or
        _is_solid(nx - PLAYER_HALF, ny + PLAYER_HALF, player) or
        _is_solid(nx + PLAYER_HALF, ny + PLAYER_HALF, player)
    ):
        player["x"] = nx

    nx = player["x"]
    ny = player["y"] + dy * PLAYER_SPEED * dt
    if not (
        _is_solid(nx - PLAYER_HALF, ny - PLAYER_HALF, player) or
        _is_solid(nx + PLAYER_HALF, ny - PLAYER_HALF, player) or
        _is_solid(nx - PLAYER_HALF, ny + PLAYER_HALF, player) or
        _is_solid(nx + PLAYER_HALF, ny + PLAYER_HALF, player)
    ):
        player["y"] = ny

    player["x"] = max(PLAYER_HALF, min(WORLD_W - PLAYER_HALF, player["x"]))
    player["y"] = max(PLAYER_HALF, min(WORLD_H - PLAYER_HALF, player["y"]))


def _nearest_other(players: dict[str, dict], source_id: str, radius: float = 56.0, require_detained: bool = False) -> dict | None:
    src = players.get(source_id)
    if src is None:
        return None
    best = None
    best_d2 = None
    rr = radius * radius
    for pid, p in players.items():
        if pid == source_id:
            continue
        if require_detained and not p.get("detained"):
            continue
        dx = src["x"] - p["x"]
        dy = src["y"] - p["y"]
        d2 = dx * dx + dy * dy
        if d2 <= rr and (best_d2 is None or d2 < best_d2):
            best_d2 = d2
            best = p
    return best


def _player_payload(p: dict) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "x": p["x"],
        "y": p["y"],
        "angle": p["angle"],
        "job": p["job"],
        "health": p["health"],
        "hunger": p["hunger"],
        "thirst": p["thirst"],
        "money": p["money"],
        "detained": bool(p.get("detained")),
        "in_jail": bool(p.get("in_jail")),
    }


def _new_player(pid: str) -> dict:
    p = {
        "id": pid,
        "name": f"Player-{pid[:4]}",
        "x": WORLD_W * 0.5 + (hash(pid) % 120 - 60),
        "y": WORLD_H * 0.5 + (hash(pid[::-1]) % 120 - 60),
        "angle": 0.0,
        "job": 0,
        "keys": {"up": False, "down": False, "left": False, "right": False},
        "health": 100.0,
        "hunger": 100.0,
        "thirst": 100.0,
        "money": 5000,
        "owned_building_id": None,
        "detained": False,
        "in_jail": False,
        "arrest_until": 0.0,
        "jail_x": None,
        "jail_y": None,
        "cuffs_sentence": 60,
        "gun_cd": 0.0,
        "salary_t": SALARY_INTERVAL_S,
        "selected_hotbar": 0,
        "hotbar": [None] * 5,
        "inventory": [None] * 20,
    }
    for iid, c in STARTING_ITEMS:
        _add_item(p, iid, c, prefer_hotbar=True)
    _apply_job_loadout(p, p["job"])
    return p


def _handle_use_item(players: dict[str, dict], pid: str, dropped_items: list, projectiles: list) -> None:
    p = players.get(pid)
    if p is None:
        return
    idx = p["selected_hotbar"]
    if not (0 <= idx < len(p["hotbar"])):
        return
    st = p["hotbar"][idx]
    if not st:
        return
    iid = st["id"]
    idef = ITEM_DEFS.get(iid, {})
    use = idef.get("use")
    if not use:
        return
    ut = use.get("type")
    consumed = False

    if ut == "consume":
        p["hunger"] = min(100.0, p["hunger"] + float(use.get("hunger", 0.0)))
        p["thirst"] = min(100.0, p["thirst"] + float(use.get("thirst", 0.0)))
        p["health"] = min(100.0, p["health"] + float(use.get("health", 0.0)))
        consumed = True
    elif ut == "sell":
        p["money"] += int(use.get("money", 0))
        consumed = True
    elif ut == "toolkit":
        if p["hunger"] < 100.0 or p["thirst"] < 100.0:
            p["hunger"] = min(100.0, p["hunger"] + 20.0)
            p["thirst"] = min(100.0, p["thirst"] + 20.0)
            consumed = True
    elif ut == "lockpick":
        b = _building_near(p["x"], p["y"])
        if b and b.get("locked") and b.get("owner") != p["id"]:
            b["locked"] = False
            consumed = True
    elif ut == "cuffs":
        if not _is_police(p):
            return
        target = _nearest_other(players, pid)
        if target is None:
            return
        sentence = max(0, min(600, int(p.get("cuffs_sentence", 60))))
        if sentence <= 0:
            return
        pb = next((b for b in BUILDINGS if b["id"] == "police"), None)
        if not pb:
            return
        spawns = pb.get("jail_spawns", [(52, 21)])
        tx, ty = spawns[int(time.time()) % len(spawns)]
        jx, jy = _tile_center(tx, ty)
        target["in_jail"] = True
        target["detained"] = False
        target["arrest_until"] = time.time() + sentence
        target["jail_x"] = jx
        target["jail_y"] = jy
        target["x"] = jx
        target["y"] = jy
    elif ut == "gun":
        if p["gun_cd"] > 0:
            return
        ammo = use.get("ammo")
        if not ammo or not _remove_item(p, ammo, 1):
            return
        pellets = max(1, int(use.get("pellets", 1)))
        spread = float(use.get("spread", 0.0))
        speed = float(use.get("speed", 460.0))
        life = float(use.get("projectile_life", 0.6))
        damage = float(use.get("damage", 10))
        for _ in range(pellets):
            a = p["angle"] + (spread * (2.0 * (time.time() % 1.0) - 1.0))
            fx, fy = _deg_to_dir(a)
            projectiles.append({
                "x": p["x"] + fx * 16.0,
                "y": p["y"] + fy * 16.0,
                "vx": fx * speed,
                "vy": fy * speed,
                "life": life,
                "owner": p["id"],
                "damage": damage,
            })
        p["gun_cd"] = float(use.get("cooldown", 0.17))
        return

    if consumed:
        st["count"] -= 1
        if st["count"] <= 0:
            p["hotbar"][idx] = None


def _tick(players: dict[str, dict], dropped_items: list, projectiles: list, dt: float) -> None:
    now = time.time()
    for p in players.values():
        if p["in_jail"]:
            if now >= p.get("arrest_until", 0.0):
                p["in_jail"] = False
                p["arrest_until"] = 0.0
                pb = next((b for b in BUILDINGS if b["id"] == "police"), None)
                if pb:
                    p["x"], p["y"] = _tile_center(pb["door"][0], pb["door"][1])
            else:
                p["x"] = p.get("jail_x", p["x"])
                p["y"] = p.get("jail_y", p["y"])

        _move_player(p, dt)

        p["hunger"] = max(0.0, p["hunger"] - HUNGER_DRAIN_PER_S * dt)
        p["thirst"] = max(0.0, p["thirst"] - THIRST_DRAIN_PER_S * dt)
        if p["hunger"] <= 0.0:
            p["health"] = max(0.0, p["health"] - STARVATION_DAMAGE_PER_S * dt)
        if p["thirst"] <= 0.0:
            p["health"] = max(0.0, p["health"] - STARVATION_DAMAGE_PER_S * dt)

        p["salary_t"] -= dt
        if p["salary_t"] <= 0.0:
            p["salary_t"] += SALARY_INTERVAL_S
            p["money"] += int(JOBS[p["job"]]["salary"])

        p["gun_cd"] = max(0.0, p["gun_cd"] - dt)

    alive_projectiles = []
    for pr in projectiles:
        pr["life"] -= dt
        if pr["life"] <= 0:
            continue
        nx = pr["x"] + pr["vx"] * dt
        ny = pr["y"] + pr["vy"] * dt
        owner = players.get(pr.get("owner"))
        if owner and _is_solid(nx, ny, owner):
            continue
        hit = None
        for pid, p in players.items():
            if pid == pr.get("owner"):
                continue
            if p.get("in_jail"):
                continue
            dx = p["x"] - nx
            dy = p["y"] - ny
            if dx * dx + dy * dy <= 14 * 14:
                hit = p
                break
        if hit:
            hit["health"] = max(0.0, hit["health"] - float(pr.get("damage", 10.0)))
            continue
        pr["x"] = nx
        pr["y"] = ny
        alive_projectiles.append(pr)
    projectiles[:] = alive_projectiles

    for d in dropped_items:
        d["pickup_cd"] = max(0.0, d.get("pickup_cd", 0.0) - dt)


app = FastAPI(title="DarkRP Web Multiplayer")
web_dir = Path(__file__).parent / "web"
app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")

clients: dict[str, WebSocket] = {}
players: dict[str, dict] = {}
dropped_items: list[dict] = []
projectiles: list[dict] = []
state_lock = asyncio.Lock()


async def _broadcast_state() -> None:
    if not clients:
        return

    dead = []
    base = {
        "type": "state",
        "ts": int(time.time() * 1000),
        "world": {"w": WORLD_W, "h": WORLD_H, "tile": TILE},
        "jobs": JOBS,
        "players": {pid: _player_payload(p) for pid, p in players.items()},
        "dropped_items": dropped_items,
        "projectiles": [{"x": p["x"], "y": p["y"]} for p in projectiles],
        "buildings": [
            {
                "id": b["id"],
                "name": b["name"],
                "x": b["x"],
                "y": b["y"],
                "w": b["w"],
                "h": b["h"],
                "door": b["door"],
                "government": b["government"],
                "price": b["price"],
                "owner": b.get("owner"),
                "locked": bool(b.get("locked")),
            }
            for b in BUILDINGS
        ],
    }

    for pid, ws in clients.items():
        try:
            you = players.get(pid)
            payload = dict(base)
            payload["you"] = {
                "id": pid,
                "health": you.get("health", 0.0) if you else 0.0,
                "hunger": you.get("hunger", 0.0) if you else 0.0,
                "thirst": you.get("thirst", 0.0) if you else 0.0,
                "money": you.get("money", 0) if you else 0,
                "job": you.get("job", 0) if you else 0,
                "inventory": you.get("inventory", []) if you else [],
                "hotbar": you.get("hotbar", []) if you else [],
                "selected_hotbar": you.get("selected_hotbar", 0) if you else 0,
                "detained": bool(you.get("detained")) if you else False,
                "in_jail": bool(you.get("in_jail")) if you else False,
                "arrest_remaining": max(0.0, (you.get("arrest_until", 0.0) - time.time())) if you else 0.0,
                "cuffs_sentence": you.get("cuffs_sentence", 60) if you else 60,
            }
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.append(pid)

    for pid in dead:
        clients.pop(pid, None)
        players.pop(pid, None)


@app.on_event("startup")
async def startup() -> None:
    async def game_loop() -> None:
        last = time.perf_counter()
        while True:
            await asyncio.sleep(1.0 / TICK_RATE)
            now = time.perf_counter()
            dt = now - last
            last = now
            async with state_lock:
                _tick(players, dropped_items, projectiles, dt)
                await _broadcast_state()

    asyncio.create_task(game_loop())


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(web_dir / "index.html")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    pid = uuid.uuid4().hex[:8]

    async with state_lock:
        clients[pid] = ws
        players[pid] = _new_player(pid)

    try:
        await ws.send_text(json.dumps({"type": "welcome", "id": pid}))

        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            if not isinstance(data, dict):
                continue

            async with state_lock:
                p = players.get(pid)
                if p is None:
                    continue

                mtype = data.get("type")
                if mtype == "join":
                    name = str(data.get("name", "")).strip()
                    p["name"] = name[:20] if name else p["name"]

                elif mtype == "input":
                    keys = data.get("keys", {})
                    if isinstance(keys, dict):
                        p["keys"] = {
                            "up": bool(keys.get("up")),
                            "down": bool(keys.get("down")),
                            "left": bool(keys.get("left")),
                            "right": bool(keys.get("right")),
                        }
                    angle = data.get("angle")
                    if isinstance(angle, (int, float)):
                        p["angle"] = float(angle)
                    selected = data.get("selected_hotbar")
                    if isinstance(selected, int) and 0 <= selected < len(p["hotbar"]):
                        p["selected_hotbar"] = selected

                    job = data.get("job")
                    if isinstance(job, int) and _can_take_job(players, pid, job):
                        if p["job"] != job:
                            p["job"] = job
                            _apply_job_loadout(p, job)

                elif mtype == "action":
                    action = str(data.get("action", "")).lower()
                    if action == "use":
                        _handle_use_item(players, pid, dropped_items, projectiles)

                    elif action == "drop":
                        idx = p["selected_hotbar"]
                        if 0 <= idx < len(p["hotbar"]) and p["hotbar"][idx]:
                            item_id = p["hotbar"][idx]["id"]
                            p["hotbar"][idx]["count"] -= 1
                            if p["hotbar"][idx]["count"] <= 0:
                                p["hotbar"][idx] = None
                            fx, fy = _deg_to_dir(p["angle"])
                            dropped_items.append({
                                "x": p["x"] + fx * 20.0,
                                "y": p["y"] + fy * 20.0,
                                "id": item_id,
                                "count": 1,
                                "pickup_cd": 0.35,
                            })

                    elif action == "pickup":
                        best_i = None
                        best_d2 = None
                        for i, it in enumerate(dropped_items):
                            if it.get("pickup_cd", 0.0) > 0:
                                continue
                            dx = p["x"] - it["x"]
                            dy = p["y"] - it["y"]
                            d2 = dx * dx + dy * dy
                            if d2 <= 28 * 28 and (best_d2 is None or d2 < best_d2):
                                best_d2 = d2
                                best_i = i
                        if best_i is not None:
                            it = dropped_items[best_i]
                            if _add_item(p, it["id"], int(it.get("count", 1)), prefer_hotbar=True):
                                dropped_items.pop(best_i)

                    elif action == "detain":
                        idx = p["selected_hotbar"]
                        if 0 <= idx < len(p["hotbar"]) and p["hotbar"][idx] and p["hotbar"][idx]["id"] == "cuffs" and _is_police(p):
                            t = _nearest_other(players, pid)
                            if t is not None:
                                t["detained"] = not bool(t.get("detained"))

                    elif action == "sentence_up":
                        p["cuffs_sentence"] = min(600, int(p.get("cuffs_sentence", 60)) + 30)
                    elif action == "sentence_down":
                        p["cuffs_sentence"] = max(0, int(p.get("cuffs_sentence", 60)) - 30)

                    elif action == "buy":
                        b = _building_near(p["x"], p["y"])
                        if b and not b["government"] and b.get("owner") is None and p.get("owned_building_id") is None and p["money"] >= int(b["price"]):
                            p["money"] -= int(b["price"])
                            b["owner"] = p["id"]
                            b["locked"] = False
                            p["owned_building_id"] = b["id"]

                    elif action == "sell":
                        b = _building_near(p["x"], p["y"])
                        if b and b.get("owner") == p["id"]:
                            p["money"] += int(b["price"]) // 2
                            b["owner"] = None
                            b["locked"] = False
                            p["owned_building_id"] = None

                    elif action == "lock":
                        b = _building_near(p["x"], p["y"])
                        if b and b.get("owner") == p["id"]:
                            b["locked"] = not bool(b.get("locked"))

    except WebSocketDisconnect:
        pass
    finally:
        async with state_lock:
            clients.pop(pid, None)
            player = players.pop(pid, None)
            if player and player.get("owned_building_id"):
                for b in BUILDINGS:
                    if b["id"] == player["owned_building_id"]:
                        b["owner"] = None
                        b["locked"] = False
