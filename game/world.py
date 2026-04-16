"""
Tile map and world — handles the grid, buildings, and collision.
"""
import pygame
from game.settings import TILE_SIZE, JOBS

# ── Tile types ──
# Each tile has: texture key, solid (collision), layer
TILE_DEFS = {
    0: {"tex": "grass",      "solid": False, "layer": "ground"},
    1: {"tex": "road",       "solid": False, "layer": "ground"},
    2: {"tex": "sidewalk",   "solid": False, "layer": "ground"},
    3: {"tex": "wood_floor", "solid": False, "layer": "ground"},
    4: {"tex": "tile_floor", "solid": False, "layer": "ground"},
    5: {"tex": "wall_brick", "solid": True,  "layer": "wall"},
    6: {"tex": "wall_white", "solid": True,  "layer": "wall"},
    7: {"tex": "wall_gray",  "solid": True,  "layer": "wall"},
    8: {"tex": "door",       "solid": False, "layer": "wall"},
    9: {"tex": "water",      "solid": True,  "layer": "ground"},
    10: {"tex": "crosswalk",      "solid": False, "layer": "ground"},
    11: {"tex": "crosswalk_h",    "solid": False, "layer": "ground"},
    13: {"tex": "wall_police",    "solid": True,  "layer": "wall"},
    14: {"tex": "wall_hospital",  "solid": True,  "layer": "wall"},
    15: {"tex": "wall_mayor",     "solid": True,  "layer": "wall"},
    16: {"tex": "wall_bank",      "solid": True,  "layer": "wall"},
    17: {"tex": "sign_police",    "solid": False, "layer": "ground"},
    18: {"tex": "sign_hospital",  "solid": False, "layer": "ground"},
    19: {"tex": "sign_mayor",     "solid": False, "layer": "ground"},
    20: {"tex": "sign_bank",      "solid": False, "layer": "ground"},
    21: {"tex": "sign_gun",       "solid": False, "layer": "ground"},
    22: {"tex": "sign_garage",    "solid": False, "layer": "ground"},
    23: {"tex": "sign_apt",       "solid": False, "layer": "ground"},
    24: {"tex": "sign_grocery",   "solid": False, "layer": "ground"},
    25: {"tex": "jail_bars",      "solid": True,  "layer": "wall"},
    26: {"tex": "jail_door",      "solid": True,  "layer": "wall"},
    # Furniture (wall layer, solid)
    30: {"tex": "furn_table",     "solid": True,  "layer": "wall"},
    31: {"tex": "furn_chair",     "solid": True,  "layer": "wall"},
    33: {"tex": "furn_shelf",     "solid": True,  "layer": "wall"},
    34: {"tex": "furn_counter",   "solid": True,  "layer": "wall"},
    36: {"tex": "furn_fridge",    "solid": True,  "layer": "wall"},
    37: {"tex": "furn_lamp",      "solid": False, "layer": "wall"},
    38: {"tex": "furn_bed_top",   "solid": True,  "layer": "wall"},
    39: {"tex": "furn_bed_bot",   "solid": True,  "layer": "wall"},
    40: {"tex": "furn_couch_l",   "solid": True,  "layer": "wall"},
    41: {"tex": "furn_couch_r",   "solid": True,  "layer": "wall"},
}


class Building:
    """A rectangular building footprint with a roof that hides when player enters."""

    def __init__(self, x, y, w, h, name="Building", government=False, price=0):
        # all in tile coords
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.name = name
        self.roof_visible = True
        # ownership
        self.government = government  # cannot be owned by players
        self.price = price            # purchase cost
        self.owner = None             # player who owns it (None = unowned)
        self.locked = False           # door locked?
        # door tile position (set by add_door)
        self.door_tx = None
        self.door_ty = None
        # sign tile position (for removal on purchase)
        self.sign_tx = None
        self.sign_ty = None

    def contains_pixel(self, px, py):
        """Check if a pixel position is inside this building footprint."""
        tx = px / TILE_SIZE
        ty = py / TILE_SIZE
        return self.x <= tx < self.x + self.w and self.y <= ty < self.y + self.h

    def get_roof_rect(self):
        return pygame.Rect(self.x * TILE_SIZE, self.y * TILE_SIZE,
                           self.w * TILE_SIZE, self.h * TILE_SIZE)


class World:
    def __init__(self, width, height):
        self.width = width      # in tiles
        self.height = height
        self.ground = [[0] * width for _ in range(height)]   # ground layer
        self.walls  = [[None] * width for _ in range(height)] # wall/furniture layer
        self.wall_rot = [[0] * width for _ in range(height)]  # rotation per wall tile (0-3)
        self.roof   = [[None] * width for _ in range(height)] # roof layer
        self.buildings: list[Building] = []
        self.furniture_links = {}  # (tx,ty) -> list of (tx,ty) in same piece

    def set_ground(self, x, y, tile_id):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.ground[y][x] = tile_id

    def set_wall(self, x, y, tile_id):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.walls[y][x] = tile_id

    def set_roof(self, x, y, val):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.roof[y][x] = val

    def is_solid(self, px, py, actor=None):
        """Check collision at pixel position."""
        tx = int(px // TILE_SIZE)
        ty = int(py // TILE_SIZE)
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return True  # out of bounds = solid

        # check wall layer first
        wt = self.walls[ty][tx]
        if wt is not None:
            d = TILE_DEFS.get(wt)
            if d and d["solid"]:
                # Jail doors are passable for police officers only.
                if wt == 26 and actor is not None and hasattr(actor, "job"):
                    j = actor.job
                    if isinstance(j, int) and 0 <= j < len(JOBS) and JOBS[j][0] == "Police Officer":
                        return False
                return True

        # check ground
        gt = self.ground[ty][tx]
        d = TILE_DEFS.get(gt)
        if d and d["solid"]:
            return True

        # locked owned homes block the door tile
        for bld in self.buildings:
            if bld.locked and bld.door_tx == tx and bld.door_ty == ty:
                return True

        return False

    def update_roofs(self, player_px, player_py):
        """Hide roofs of buildings the player is inside (PZ style)."""
        for b in self.buildings:
            b.roof_visible = not b.contains_pixel(player_px, player_py)

    def add_building(self, bld: Building, wall_id=5, floor_id=3, roof_tex="roof", roof=True):
        """Stamp a building onto the map: walls on border, floor inside, roof on top."""
        self.buildings.append(bld)
        for dy in range(bld.h):
            for dx in range(bld.w):
                tx = bld.x + dx
                ty = bld.y + dy
                # floor everywhere inside
                self.set_ground(tx, ty, floor_id)
                # walls on the border
                if dx == 0 or dy == 0 or dx == bld.w - 1 or dy == bld.h - 1:
                    self.set_wall(tx, ty, wall_id)
                else:
                    # roof only on interior tiles (inside the walls)
                    if roof:
                        self.set_roof(tx, ty, roof_tex)

    def add_door(self, tx, ty, bld=None):
        """Place a door (walkable gap in a wall). Optionally link to building."""
        self.set_wall(tx, ty, 8)
        if bld:
            bld.door_tx = tx
            bld.door_ty = ty

    def get_building_near(self, px, py, radius=48):
        """Find building whose door is within radius pixels of a position."""
        for bld in self.buildings:
            if bld.door_tx is not None:
                dx = px - (bld.door_tx * TILE_SIZE + TILE_SIZE / 2)
                dy = py - (bld.door_ty * TILE_SIZE + TILE_SIZE / 2)
                if (dx * dx + dy * dy) < radius * radius:
                    return bld
        return None

    def is_interior(self, bld, tx, ty):
        """Check if tile (tx,ty) is inside the building and not a wall/door."""
        if not (bld.x < tx < bld.x + bld.w - 1 and bld.y < ty < bld.y + bld.h - 1):
            return False
        wt = self.walls[ty][tx]
        if wt is not None:
            return False
        return True

    def place_furniture(self, bld, tx, ty, tile_id, rotation=0):
        """Place furniture inside an owned building. Returns True on success."""
        if not self.is_interior(bld, tx, ty):
            return False
        self.set_wall(tx, ty, tile_id)
        self.wall_rot[ty][tx] = rotation
        return True

    def place_multi_furniture(self, bld, tx, ty, tiles, rotation=0):
        """Place multi-tile furniture. tiles is [(dx,dy,tile_id),...]. Returns True on success."""
        # Check all tiles are valid
        for dx, dy, tid in tiles:
            if not self.is_interior(bld, tx + dx, ty + dy):
                return False
        # Place all and link positions
        positions = [(tx + dx, ty + dy) for dx, dy, _ in tiles]
        for dx, dy, tid in tiles:
            self.set_wall(tx + dx, ty + dy, tid)
            self.wall_rot[ty + dy][tx + dx] = rotation
        for pos in positions:
            self.furniture_links[pos] = positions
        return True

    def remove_furniture(self, bld, tx, ty):
        """Remove furniture from a tile if it's furniture (id >= 30). Also removes linked tiles."""
        if not (bld.x < tx < bld.x + bld.w - 1 and bld.y < ty < bld.y + bld.h - 1):
            return False
        wt = self.walls[ty][tx]
        if wt is not None and wt >= 30:
            # Remove linked group if any
            group = self.furniture_links.pop((tx, ty), None)
            self.walls[ty][tx] = None
            self.wall_rot[ty][tx] = 0
            if group:
                for gx, gy in group:
                    if (gx, gy) != (tx, ty):
                        self.walls[gy][gx] = None
                        self.wall_rot[gy][gx] = 0
                        self.furniture_links.pop((gx, gy), None)
            return True
        return False
