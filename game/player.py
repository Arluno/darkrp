"""
Player — movement, collision, sprite rotation.
"""
import math
import pygame
from game.settings import (
    TILE_SIZE,
    PLAYER_SPEED,
    PLAYER_SIZE,
    STARTING_MONEY,
    HOTBAR_SIZE,
    INVENTORY_SIZE,
    ITEM_DEFS,
    STARTING_ITEMS,
)


class Player:
    def __init__(self, x, y):
        self.x = float(x)          # pixel position (center)
        self.y = float(y)
        self.speed = PLAYER_SPEED
        self.size = PLAYER_SIZE
        self.angle = 0.0            # degrees, 0 = up
        self.dx = 0.0
        self.dy = 0.0
        self.money = STARTING_MONEY
        self.owned_building = None    # can own 1 property at a time
        self.chat_bubbles = []        # list of (text, timer_ms)
        self.health = 100.0           # 0-100
        self.hunger = 100.0           # 0-100
        self.thirst = 100.0           # 0-100
        self.detained = False
        self.in_jail = False
        self.arrest_until_ms = 0
        self.jail_px = None
        self.jail_py = None
        self.job = 0                  # index into JOBS
        self.hotbar = [None] * HOTBAR_SIZE
        self.inventory = [None] * INVENTORY_SIZE
        self.selected_hotbar = 0

        # Starter items (prefer hotbar so player can use slots immediately)
        for item_id, count in STARTING_ITEMS:
            self.add_item(item_id, count, prefer_hotbar=True)

    @staticmethod
    def _new_stack(item_id, count):
        idef = ITEM_DEFS.get(item_id)
        if idef is None:
            return None
        return {"id": item_id, "name": idef["name"], "count": int(count)}

    def add_item(self, item_id, count=1, prefer_hotbar=False):
        """Add items into stacks. Returns True if all were added, False if full."""
        if item_id not in ITEM_DEFS or count <= 0:
            return False

        left = int(count)
        slots = [self.hotbar, self.inventory] if prefer_hotbar else [self.inventory, self.hotbar]

        # Fill existing stacks first
        for arr in slots:
            for stack in arr:
                if stack is not None and stack["id"] == item_id:
                    stack["count"] += left
                    return True

        # Then use empty slots
        for arr in slots:
            for i, stack in enumerate(arr):
                if stack is None:
                    arr[i] = self._new_stack(item_id, left)
                    return True

        return False

    def drop_selected_hotbar_item(self, count=1):
        """Remove item count from selected hotbar slot and return dropped item id."""
        idx = self.selected_hotbar
        if not (0 <= idx < len(self.hotbar)):
            return None
        stack = self.hotbar[idx]
        if stack is None:
            return None

        stack["count"] -= max(1, int(count))
        item_id = stack["id"]
        if stack["count"] <= 0:
            self.hotbar[idx] = None
        return item_id

    def count_item(self, item_id):
        """Count an item across hotbar and inventory."""
        total = 0
        for arr in (self.hotbar, self.inventory):
            for stack in arr:
                if stack is not None and stack["id"] == item_id:
                    total += stack["count"]
        return total

    def remove_item(self, item_id, count=1):
        """Remove item count across hotbar+inventory. Returns True if removed."""
        need = max(1, int(count))
        if self.count_item(item_id) < need:
            return False

        for arr in (self.hotbar, self.inventory):
            for i, stack in enumerate(arr):
                if need <= 0:
                    break
                if stack is None or stack["id"] != item_id:
                    continue
                take = min(need, stack["count"])
                stack["count"] -= take
                need -= take
                if stack["count"] <= 0:
                    arr[i] = None
            if need <= 0:
                break
        return need <= 0

    def remove_all_of_item(self, item_id):
        """Remove all stacks of a specific item."""
        for arr in (self.hotbar, self.inventory):
            for i, stack in enumerate(arr):
                if stack is not None and stack["id"] == item_id:
                    arr[i] = None

    def set_item_count(self, item_id, target_count, prefer_hotbar=False):
        """Set the total count of an item across inventory+hotbar."""
        target = max(0, int(target_count))
        current = self.count_item(item_id)
        if current < target:
            self.add_item(item_id, target - current, prefer_hotbar=prefer_hotbar)
        elif current > target:
            self.remove_item(item_id, current - target)

    def handle_input(self, keys, look_angle=None):
        """Read movement input and move relative to current look direction."""
        if look_angle is not None:
            self.angle = look_angle

        up = 0.0
        down = 0.0
        strafe = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            up += 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            down += 1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            strafe += 1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            strafe -= 1.0

        # W/S are absolute up/down, A/D are absolute left/right.
        self.dx = strafe
        self.dy = down - up

        # normalize diagonal
        length = math.hypot(self.dx, self.dy)
        if length > 0:
            self.dx /= length
            self.dy /= length

    def update(self, world):
        """Move with collision against the world."""
        half = self.size / 2

        # try X
        nx = self.x + self.dx * self.speed
        # check 4 corners
        if not (world.is_solid(nx - half, self.y - half, self) or
            world.is_solid(nx + half, self.y - half, self) or
            world.is_solid(nx - half, self.y + half, self) or
            world.is_solid(nx + half, self.y + half, self)):
            self.x = nx

        # try Y
        ny = self.y + self.dy * self.speed
        if not (world.is_solid(self.x - half, ny - half, self) or
            world.is_solid(self.x + half, ny - half, self) or
            world.is_solid(self.x - half, ny + half, self) or
            world.is_solid(self.x + half, ny + half, self)):
            self.y = ny

        # keep in bounds
        self.x = max(half, min(self.x, world.width * TILE_SIZE - half))
        self.y = max(half, min(self.y, world.height * TILE_SIZE - half))

    def get_rect(self):
        half = self.size / 2
        return pygame.Rect(self.x - half, self.y - half, self.size, self.size)
