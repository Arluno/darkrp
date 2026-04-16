"""
Main game loop — the engine that ties everything together.
"""
import math
import random
import pygame
import game.settings as settings
from game.settings import (
    FPS,
    TITLE,
    COLOR_BG,
    TILE_SIZE,
    FURNITURE,
    JOBS,
    JOB_LOADOUTS,
    JOB_MAX_PLAYERS,
    SALARY_INTERVAL,
    HUNGER_DRAIN_PER_MS,
    THIRST_DRAIN_PER_MS,
    STARVATION_DAMAGE_PER_MS,
    HOTBAR_SIZE,
    ITEM_DEFS,
)
from game.textures import generate_all, load_textures
from game.player import Player
from game.renderer import Renderer
from game.town import build_town
from game.network import NetworkManager


class Engine:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)

        # fullscreen desktop resolution
        info = pygame.display.Info()
        settings.SCREEN_WIDTH = info.current_w
        settings.SCREEN_HEIGHT = info.current_h
        self.screen = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.running = True

        # generate textures if needed, then load
        generate_all()
        textures = load_textures()

        # build world
        self.world = build_town()

        # spawn player in the middle of the intersection
        spawn_x = 40 * TILE_SIZE
        spawn_y = 30 * TILE_SIZE
        self.player = Player(spawn_x, spawn_y)
        self._team_item_ids = sorted({item_id for ld in JOB_LOADOUTS for item_id, _ in ld})
        self._apply_job_loadout(self.player.job, announce=False)

        # renderer
        self.renderer = Renderer(self.screen, textures)

        # network (stub)
        self.net = NetworkManager()

        # build mode
        self.build_mode = False
        self.build_selection = 0  # index into FURNITURE
        self.build_rotation = 0  # 0=0°, 1=90°CW, 2=180°, 3=270°CW

        # chat
        self.chat_active = False
        self.chat_text = ""
        self._chat_skip_text = False

        # job menu
        self.job_menu_open = False

        # salary timer
        self.salary_timer = SALARY_INTERVAL

        # inventory / hotbar
        self.inventory_open = False
        self.inventory_selected = None  # ("inv"|"hot", index)
        self._pickup_cycle = 0
        self.dropped_items = []  # {x, y, id, count, pickup_cd}
        self.projectiles = []    # {x, y, vx, vy, life}
        self.gun_cooldown = 0    # ms
        self.cuffs_seconds = 60

    def run(self):
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(FPS)
        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Chat input mode
            if self.chat_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.chat_text.strip():
                            self.player.chat_bubbles.append(
                                [self.chat_text.strip(), 4000])  # 4 seconds
                        self.chat_active = False
                        self.chat_text = ""
                    elif event.key == pygame.K_ESCAPE:
                        self.chat_active = False
                        self.chat_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.chat_text = self.chat_text[:-1]
                elif event.type == pygame.TEXTINPUT:
                    if self._chat_skip_text:
                        self._chat_skip_text = False
                    elif len(self.chat_text) < 80:
                        self.chat_text += event.text
                continue

            # Job menu mode
            if self.job_menu_open:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_j):
                        self.job_menu_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    clicked = self.renderer.get_job_button_at(event.pos)
                    if clicked is not None:
                        if self._can_take_job(clicked):
                            self.player.job = clicked
                            self._apply_job_loadout(clicked, announce=True)
                            self.job_menu_open = False
                        else:
                            self.player.chat_bubbles.append(["That job is full.", 2200])
                    else:
                        self.job_menu_open = False
                continue

            # Inventory mode
            if self.inventory_open:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_TAB, pygame.K_e):
                        self.inventory_open = False
                        self.inventory_selected = None
                    elif pygame.K_1 <= event.key < pygame.K_1 + HOTBAR_SIZE:
                        self.player.selected_hotbar = event.key - pygame.K_1
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = self.renderer.get_inventory_click_action(event.pos)
                    if action is None:
                        # Click outside closes inventory
                        self.inventory_open = False
                        self.inventory_selected = None
                    else:
                        kind, idx = action
                        if kind == "close":
                            self.inventory_open = False
                            self.inventory_selected = None
                        else:
                            self._handle_inventory_slot_click(kind, idx)
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.build_mode:
                        self.build_mode = False
                    else:
                        self.running = False
                elif event.key == pygame.K_e:
                    if not self._try_buy_property():
                        self.inventory_open = not self.inventory_open
                        self.inventory_selected = None
                elif event.key == pygame.K_TAB and not self.build_mode:
                    self.inventory_open = not self.inventory_open
                    self.inventory_selected = None
                elif event.key == pygame.K_f:
                    self._try_sell_property()
                elif event.key == pygame.K_b:
                    self._toggle_build_mode()
                elif event.key == pygame.K_r and self.build_mode:
                    self.build_rotation = (self.build_rotation + 1) % 4
                elif event.key == pygame.K_t and not self.build_mode:
                    self.chat_active = True
                    self.chat_text = ""
                    self._chat_skip_text = True
                elif event.key == pygame.K_j and not self.build_mode:
                    self.job_menu_open = True
                elif event.key == pygame.K_l and not self.build_mode:
                    self._toggle_lock()
                elif event.key == pygame.K_g and not self.build_mode:
                    self._pickup_nearby_item()
                elif event.key == pygame.K_h and not self.build_mode:
                    self._pickup_test_item()
                elif event.key == pygame.K_q and not self.build_mode:
                    self._drop_selected_item()
                elif event.key == pygame.K_u and not self.build_mode:
                    self._use_selected_item()
                elif event.key == pygame.K_y and not self.build_mode:
                    self._toggle_detain_with_cuffs()
                elif event.key == pygame.K_LEFTBRACKET and not self.build_mode:
                    self.cuffs_seconds = max(0, self.cuffs_seconds - 30)
                    self.player.chat_bubbles.append([f"Sentence: {self._format_sentence(self.cuffs_seconds)}", 1200])
                elif event.key == pygame.K_RIGHTBRACKET and not self.build_mode:
                    self.cuffs_seconds = min(600, self.cuffs_seconds + 30)
                    self.player.chat_bubbles.append([f"Sentence: {self._format_sentence(self.cuffs_seconds)}", 1200])
                elif pygame.K_1 <= event.key < pygame.K_1 + HOTBAR_SIZE and not self.build_mode:
                    self.player.selected_hotbar = event.key - pygame.K_1

            # Build mode: scroll to change selection
            if self.build_mode and event.type == pygame.MOUSEWHEEL:
                self.build_selection = (self.build_selection - event.y) % len(FURNITURE)

            # Build mode: number keys 1-8 to select
            if self.build_mode and event.type == pygame.KEYDOWN:
                idx = event.key - pygame.K_1
                if 0 <= idx < len(FURNITURE):
                    self.build_selection = idx

            # Build mode: click to place/remove
            if self.build_mode and event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                wx = mx + self.renderer.camera.x
                wy = my + self.renderer.camera.y
                tx = int(wx // TILE_SIZE)
                ty = int(wy // TILE_SIZE)
                bld = self.player.owned_building
                if bld:
                    if event.button == 1:  # left click = place
                        name, cost, tiles = FURNITURE[self.build_selection]
                        rtiles = self._rotate_tiles(tiles, self.build_rotation)
                        if self.player.money >= cost:
                            if len(rtiles) == 1:
                                _, _, tid = rtiles[0]
                                if self.world.place_furniture(bld, tx, ty, tid, self.build_rotation):
                                    self.player.money -= cost
                            else:
                                if self.world.place_multi_furniture(bld, tx, ty, rtiles, self.build_rotation):
                                    self.player.money -= cost
                    elif event.button == 3:  # right click = remove
                        if self.world.remove_furniture(bld, tx, ty):
                            pass  # no refund, keep it simple

            # Click hotbar slot to select
            if (not self.build_mode and not self.chat_active and
                    not self.job_menu_open and not self.inventory_open and
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                if self.renderer.get_job_change_button_at(event.pos):
                    self.job_menu_open = True
                    continue
                hidx = self.renderer.get_hotbar_slot_at(event.pos)
                if hidx is not None:
                    self.player.selected_hotbar = hidx

            # Right click = use selected hotbar item/tool
            if (not self.build_mode and not self.chat_active and
                    not self.job_menu_open and not self.inventory_open and
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
                self._use_selected_item()

    @staticmethod
    def _rotate_tiles(tiles, rotation):
        """Rotate tile offsets. rotation: 0=0°, 1=90°CW, 2=180°, 3=270°CW."""
        if rotation == 0:
            return tiles
        rotated = []
        for dx, dy, tid in tiles:
            for _ in range(rotation):
                dx, dy = -dy, dx
            rotated.append((dx, dy, tid))
        # Normalize so min offset is 0
        min_dx = min(r[0] for r in rotated)
        min_dy = min(r[1] for r in rotated)
        return [(dx - min_dx, dy - min_dy, tid) for dx, dy, tid in rotated]

    def _toggle_build_mode(self):
        """Toggle build mode — only works inside owned property."""
        if self.build_mode:
            self.build_mode = False
            return
        bld = self.player.owned_building
        if bld and bld.contains_pixel(self.player.x, self.player.y):
            self.build_mode = True

    def _toggle_lock(self):
        """Lock/unlock the player's owned building."""
        bld = self.player.owned_building
        if bld is None:
            return
        bld.locked = not bld.locked

    def _get_slots(self, kind):
        return self.player.inventory if kind == "inv" else self.player.hotbar

    def _handle_inventory_slot_click(self, kind, idx):
        slots = self._get_slots(kind)
        if not (0 <= idx < len(slots)):
            return

        if self.inventory_selected is None:
            if slots[idx] is not None:
                self.inventory_selected = (kind, idx)
            return

        skind, sidx = self.inventory_selected
        if skind == kind and sidx == idx:
            self.inventory_selected = None
            return

        self._move_or_merge_slot(skind, sidx, kind, idx)
        self.inventory_selected = None

    def _move_or_merge_slot(self, src_kind, src_idx, dst_kind, dst_idx):
        src_slots = self._get_slots(src_kind)
        dst_slots = self._get_slots(dst_kind)
        if not (0 <= src_idx < len(src_slots) and 0 <= dst_idx < len(dst_slots)):
            return

        src = src_slots[src_idx]
        dst = dst_slots[dst_idx]
        if src is None:
            return
        if dst is None:
            dst_slots[dst_idx] = src
            src_slots[src_idx] = None
            return
        if dst["id"] == src["id"]:
            dst["count"] += src["count"]
            src_slots[src_idx] = None
            return

        src_slots[src_idx], dst_slots[dst_idx] = dst, src

    def _pickup_test_item(self):
        """Temporary pickup action so inventory can be used now."""
        item_ids = list(ITEM_DEFS.keys())
        if not item_ids:
            return
        item_id = item_ids[self._pickup_cycle % len(item_ids)]
        self._pickup_cycle += 1
        if self.player.add_item(item_id, 1):
            name = ITEM_DEFS[item_id]["name"]
            self.player.chat_bubbles.append([f"Picked up {name}", 1800])
        else:
            self.player.chat_bubbles.append(["Inventory full", 1800])

    def _drop_selected_item(self):
        item_id = self.player.drop_selected_hotbar_item(1)
        if item_id is None:
            self.player.chat_bubbles.append(["No hotbar item selected", 1800])
            return
        # Drop in front of player so it appears in world.
        ang = math.radians(self.player.angle)
        fx = -math.sin(ang)
        fy = -math.cos(ang)
        drop_x = self.player.x + fx * 20
        drop_y = self.player.y + fy * 20
        self.dropped_items.append({
            "x": drop_x,
            "y": drop_y,
            "id": item_id,
            "count": 1,
            "pickup_cd": 350,
        })
        name = ITEM_DEFS.get(item_id, {}).get("name", "Item")
        self.player.chat_bubbles.append([f"Dropped {name}", 1800])

    def _update_dropped_items(self, dt):
        """Tick world drops (pickup cooldown only)."""
        if not self.dropped_items:
            return
        for it in self.dropped_items:
            it["pickup_cd"] = max(0, it.get("pickup_cd", 0) - dt)

    def _pickup_nearby_item(self):
        """Pick up the nearest dropped item in range when player presses G."""
        if not self.dropped_items:
            self.player.chat_bubbles.append(["No item nearby", 1200])
            return

        px, py = self.player.x, self.player.y
        pickup_r2 = 28 * 28
        best_i = None
        best_d2 = None
        for i, it in enumerate(self.dropped_items):
            if it.get("pickup_cd", 0) > 0:
                continue
            dx = px - it.get("x", 0)
            dy = py - it.get("y", 0)
            d2 = dx * dx + dy * dy
            if d2 <= pickup_r2 and (best_d2 is None or d2 < best_d2):
                best_d2 = d2
                best_i = i

        if best_i is None:
            self.player.chat_bubbles.append(["No item nearby", 1200])
            return

        it = self.dropped_items[best_i]
        if self.player.add_item(it["id"], it.get("count", 1)):
            name = ITEM_DEFS.get(it["id"], {}).get("name", "Item")
            self.player.chat_bubbles.append([f"Picked up {name}", 1400])
            self.dropped_items.pop(best_i)
        else:
            self.player.chat_bubbles.append(["Inventory full", 1400])

    def _is_police_with_cuffs(self):
        if self.player.job >= len(JOBS) or JOBS[self.player.job][0] != "Police Officer":
            return False
        idx = self.player.selected_hotbar
        if not (0 <= idx < len(self.player.hotbar)):
            return False
        stack = self.player.hotbar[idx]
        return bool(stack and stack.get("id") == "cuffs")

    def _get_police_building(self):
        for b in self.world.buildings:
            if b.name == "Police Dept":
                return b
        return None

    def _get_jail_pixel(self):
        b = self._get_police_building()
        if b is None:
            return self.player.x, self.player.y
        spawns = getattr(b, "jail_spawns", None) or [(b.x + b.w - 2, b.y + 2)]
        tx, ty = spawns[0]
        return tx * TILE_SIZE + TILE_SIZE / 2, ty * TILE_SIZE + TILE_SIZE / 2

    def _toggle_detain_with_cuffs(self):
        if not self._is_police_with_cuffs():
            return
        target = self._get_nearby_cuff_target()
        if target is None:
            self.player.chat_bubbles.append(["No player in cuff range", 1400])
            return
        target["detained"] = not target.get("detained", False)
        if target["detained"]:
            self.player.chat_bubbles.append([f"Detained {target['id']}", 1500])
        else:
            self.player.chat_bubbles.append([f"Released {target['id']}", 1500])

    def _get_nearby_cuff_target(self, radius=56):
        """Nearest non-local player in cuff range from network state."""
        local_id = self.net.state.local_id
        px, py = self.player.x, self.player.y
        r2 = radius * radius
        best = None
        best_d2 = None

        for pid, pdata in self.net.state.players.items():
            if pid == local_id:
                continue
            tx = pdata.get("x")
            ty = pdata.get("y")
            if tx is None or ty is None:
                continue
            dx = px - tx
            dy = py - ty
            d2 = dx * dx + dy * dy
            if d2 <= r2 and (best_d2 is None or d2 < best_d2):
                best_d2 = d2
                best = {
                    "id": pid,
                    "state": pdata,
                    "detained": bool(pdata.get("detained", False)),
                }
        return best

    @staticmethod
    def _format_sentence(seconds):
        s = max(0, int(seconds))
        return f"{s // 60}:{s % 60:02d}"

    def _use_selected_item(self):
        """Use selected hotbar item and apply its configured gameplay effect."""
        idx = self.player.selected_hotbar
        if not (0 <= idx < len(self.player.hotbar)):
            return
        stack = self.player.hotbar[idx]
        if not stack:
            self.player.chat_bubbles.append(["Empty hotbar slot", 1400])
            return

        item_id = stack["id"]
        idef = ITEM_DEFS.get(item_id, {})
        use_cfg = idef.get("use")
        if not use_cfg:
            self.player.chat_bubbles.append(["That item cannot be used", 1600])
            return

        use_type = use_cfg.get("type")
        used = False

        if use_type == "consume":
            hunger_gain = float(use_cfg.get("hunger", 0))
            thirst_gain = float(use_cfg.get("thirst", 0))
            health_gain = float(use_cfg.get("health", 0))
            old_health = self.player.health
            old_hunger = self.player.hunger
            old_thirst = self.player.thirst
            self.player.hunger = min(100.0, self.player.hunger + hunger_gain)
            self.player.thirst = min(100.0, self.player.thirst + thirst_gain)
            self.player.health = min(100.0, self.player.health + health_gain)
            used = ((self.player.hunger > old_hunger) or
                    (self.player.thirst > old_thirst) or
                    (self.player.health > old_health))
            if used:
                self.player.chat_bubbles.append([f"Used {idef.get('name', 'Item')}", 1400])
            else:
                self.player.chat_bubbles.append(["You are already full", 1400])

        elif use_type == "sell":
            gain = int(use_cfg.get("money", 0))
            if gain > 0:
                self.player.money += gain
                used = True
                self.player.chat_bubbles.append([f"Sold scrap for ${gain}", 1500])

        elif use_type == "toolkit":
            # Toolkit repairs survival stats and can only be used when not already full.
            if self.player.hunger < 100.0 or self.player.thirst < 100.0:
                self.player.hunger = min(100.0, self.player.hunger + 20)
                self.player.thirst = min(100.0, self.player.thirst + 20)
                used = True
                self.player.chat_bubbles.append(["Toolkit patched you up", 1500])
            else:
                self.player.chat_bubbles.append(["Toolkit not needed", 1400])

        elif use_type == "lockpick":
            bld = self.world.get_building_near(self.player.x, self.player.y)
            if bld is None:
                self.player.chat_bubbles.append(["No door nearby", 1400])
            elif not bld.locked:
                self.player.chat_bubbles.append(["Door is already unlocked", 1400])
            elif bld.owner == "player":
                self.player.chat_bubbles.append(["Use [L] to unlock your own door", 1600])
            else:
                bld.locked = False
                used = True
                self.player.chat_bubbles.append(["Lockpick success", 1500])

        elif use_type == "cuffs":
            if not self._is_police_with_cuffs():
                return
            target = self._get_nearby_cuff_target()
            if target is None:
                self.player.chat_bubbles.append(["No player in cuff range", 1400])
                return
            # Arrest for selected sentence (0-10 min).
            sentence_s = max(0, min(600, int(self.cuffs_seconds)))
            if sentence_s <= 0:
                self.player.chat_bubbles.append(["Set sentence with [ ] (max 10:00)", 1700])
                return

            now = pygame.time.get_ticks()
            state = target["state"]
            state["in_jail"] = True
            state["detained"] = False
            state["arrest_until_ms"] = now + sentence_s * 1000
            jail_px, jail_py = self._get_jail_pixel()
            state["jail_px"] = jail_px
            state["jail_py"] = jail_py
            state["x"] = jail_px
            state["y"] = jail_py
            self.player.chat_bubbles.append([
                f"Arrested {target['id']} for {self._format_sentence(sentence_s)}",
                1700,
            ])

        elif use_type == "gun":
            if self.gun_cooldown > 0:
                return
            ammo_id = use_cfg.get("ammo")
            if not ammo_id:
                self.player.chat_bubbles.append(["No ammo type configured", 1200])
                return
            if not self.player.remove_item(ammo_id, 1):
                ammo_name = ITEM_DEFS.get(ammo_id, {}).get("name", "Ammo")
                self.player.chat_bubbles.append([f"Out of {ammo_name}", 1400])
                return

            speed = float(use_cfg.get("speed", 12.0))
            life = int(use_cfg.get("projectile_life", 600))
            cooldown = int(use_cfg.get("cooldown", 200))
            spread = float(use_cfg.get("spread", 0.0))
            pellets = max(1, int(use_cfg.get("pellets", 1)))

            for _ in range(pellets):
                a = self.player.angle + random.uniform(-spread, spread)
                rad = math.radians(a)
                fx = -math.sin(rad)
                fy = -math.cos(rad)
                self.projectiles.append({
                    "x": self.player.x + fx * 16,
                    "y": self.player.y + fy * 16,
                    "vx": fx * speed,
                    "vy": fy * speed,
                    "life": life,
                })

            self.gun_cooldown = max(0, cooldown)
            # Guns are not consumed
            return

        if used:
            stack["count"] -= 1
            if stack["count"] <= 0:
                self.player.hotbar[idx] = None

    def _get_job_counts(self):
        """Return live player counts per job index."""
        counts = [0] * len(JOBS)
        local_id = self.net.state.local_id
        local_seen = False

        for pid, pdata in self.net.state.players.items():
            jid = pdata.get("job")
            if isinstance(jid, int) and 0 <= jid < len(JOBS):
                counts[jid] += 1
            if pid == local_id:
                local_seen = True

        # Safety fallback in case local player wasn't in net state yet.
        if not local_seen and 0 <= self.player.job < len(JOBS):
            counts[self.player.job] += 1

        return counts

    def _update_projectiles(self, dt):
        """Advance gun projectiles and remove expired/collided ones."""
        if not self.projectiles:
            return

        alive = []
        scale = dt / 16.6667
        for p in self.projectiles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue

            nx = p["x"] + p["vx"] * scale
            ny = p["y"] + p["vy"] * scale
            if self.world.is_solid(nx, ny):
                continue

            p["x"] = nx
            p["y"] = ny
            alive.append(p)

        self.projectiles = alive

    def _can_take_job(self, job_idx):
        """Whether the player can switch to the given job based on slot caps."""
        if not (0 <= job_idx < len(JOBS)):
            return False
        if job_idx == self.player.job:
            return True

        cap = JOB_MAX_PLAYERS[job_idx]
        if cap is None:
            return True
        if cap <= 0:
            return False

        counts = self._get_job_counts()
        return counts[job_idx] < cap

    def _apply_job_loadout(self, job_idx, announce=True):
        """Replace team-based items with the selected job's configured loadout."""
        if not (0 <= job_idx < len(JOB_LOADOUTS)):
            return

        # Remove all team-managed items first so jobs cannot stack infinite gear.
        for item_id in self._team_item_ids:
            self.player.remove_all_of_item(item_id)

        # Apply target loadout amounts.
        for item_id, count in JOB_LOADOUTS[job_idx]:
            self.player.set_item_count(item_id, count, prefer_hotbar=True)

        if announce:
            job_name = JOBS[job_idx][0]
            self.player.chat_bubbles.append([f"Loadout set for {job_name}", 1800])

    def _try_buy_property(self):
        """Buy the building near the player if affordable and unowned."""
        bld = self.world.get_building_near(self.player.x, self.player.y)
        if bld is None:
            return False
        if bld.government:
            return False
        if bld.owner is not None:
            return False
        if self.player.owned_building is not None:
            return False
        if self.player.money < bld.price:
            return False
        # purchase
        self.player.money -= bld.price
        bld.owner = "player"
        bld.locked = False
        self.player.owned_building = bld
        # remove sign tile
        if bld.sign_tx is not None:
            self.world.set_ground(bld.sign_tx, bld.sign_ty, 2)  # revert to sidewalk
        return True

    def _try_sell_property(self):
        """Sell the player's owned building (must be near it)."""
        bld = self.world.get_building_near(self.player.x, self.player.y)
        if bld is None:
            return
        if bld.owner != "player":
            return
        # sell for half price
        self.player.money += bld.price // 2
        bld.owner = None
        bld.locked = False
        self.player.owned_building = None
        self.build_mode = False
        # restore sign tile
        if bld.sign_tx is not None:
            self.world.set_ground(bld.sign_tx, bld.sign_ty, 23)  # sign_apt
        # remove all furniture
        for dy in range(1, bld.h - 1):
            for dx in range(1, bld.w - 1):
                tx = bld.x + dx
                ty = bld.y + dy
                wt = self.world.walls[ty][tx]
                if wt is not None and wt >= 30:
                    self.world.walls[ty][tx] = None
                    self.world.wall_rot[ty][tx] = 0
                    self.world.furniture_links.pop((tx, ty), None)

    def _update(self):
        now = pygame.time.get_ticks()
        if self.player.in_jail:
            if now >= self.player.arrest_until_ms:
                self.player.in_jail = False
                self.player.arrest_until_ms = 0
                # Release outside police door
                b = self._get_police_building()
                if b and b.door_tx is not None:
                    self.player.x = b.door_tx * TILE_SIZE + TILE_SIZE / 2
                    self.player.y = b.door_ty * TILE_SIZE + TILE_SIZE / 2
                self.player.chat_bubbles.append(["Sentence served", 1700])
            elif self.player.jail_px is not None:
                # Keep jailed player inside cell.
                self.player.x = self.player.jail_px
                self.player.y = self.player.jail_py

        keys = pygame.key.get_pressed()
        mx, my = pygame.mouse.get_pos()
        ox = mx - settings.SCREEN_WIDTH / 2
        oy = my - settings.SCREEN_HEIGHT / 2
        look_angle = math.degrees(math.atan2(-ox, -oy))
        if not self.chat_active and not self.player.detained and not self.player.in_jail:
            self.player.handle_input(keys, look_angle)
        else:
            self.player.dx = 0
            self.player.dy = 0
            self.player.angle = look_angle
        self.player.update(self.world)
        self.world.update_roofs(self.player.x, self.player.y)
        # tick chat bubbles
        dt = self.clock.get_time()
        self._update_dropped_items(dt)
        if self.gun_cooldown > 0:
            self.gun_cooldown = max(0, self.gun_cooldown - dt)
        self._update_projectiles(dt)
        for bubble in self.player.chat_bubbles:
            bubble[1] -= dt
        self.player.chat_bubbles = [b for b in self.player.chat_bubbles if b[1] > 0]
        # drain hunger/thirst
        self.player.hunger = max(0, self.player.hunger - dt * HUNGER_DRAIN_PER_MS)
        self.player.thirst = max(0, self.player.thirst - dt * THIRST_DRAIN_PER_MS)
        # starvation/dehydration damage
        if self.player.hunger <= 0:
            self.player.health = max(0, self.player.health - dt * STARVATION_DAMAGE_PER_MS)
        if self.player.thirst <= 0:
            self.player.health = max(0, self.player.health - dt * STARVATION_DAMAGE_PER_MS)
        # salary paycheck
        self.salary_timer -= dt
        if self.salary_timer <= 0:
            self.salary_timer += SALARY_INTERVAL
            salary = JOBS[self.player.job][1]
            if salary > 0:
                self.player.money += salary
        # network sync
        self.net.send_position(self.player.x, self.player.y, self.player.angle, self.player.job)

    def _draw(self):
        self.screen.fill(COLOR_BG)
        job_counts = self._get_job_counts()
        self.renderer.render_frame(self.world, self.player,
                                   self.build_mode, self.build_selection,
                                   self.build_rotation,
                                   self.chat_active, self.chat_text,
                                   self.job_menu_open,
                                   job_counts,
                                   self.inventory_open,
                                   self.inventory_selected,
                                   self.dropped_items,
                                   self.projectiles)
        pygame.display.flip()
