"""
Renderer — camera, tile drawing, roof occlusion (PZ style), indoor blackout.
"""
import math
import pygame
import game.settings as settings
from game.settings import TILE_SIZE, FURNITURE, JOBS, JOB_LOADOUTS, JOB_OUTFITS, JOB_MAX_PLAYERS, HOTBAR_SIZE, ITEM_DEFS
from game.world import TILE_DEFS


class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def follow(self, target_x, target_y):
        """Center on a target pixel position."""
        self.x = target_x - settings.SCREEN_WIDTH / 2
        self.y = target_y - settings.SCREEN_HEIGHT / 2

    def apply(self, px, py):
        """World coords → screen coords."""
        return int(px - self.x), int(py - self.y)


class Renderer:
    def __init__(self, screen, textures):
        self.screen = screen
        self.tex = textures
        self.camera = Camera()
        self._blackout = None
        self._job_button_rects = []  # list of (index, pygame.Rect)
        self._hotbar_rects = []      # list of (index, pygame.Rect)
        self._inv_rects = []         # list of (index, pygame.Rect)
        self._inv_hotbar_rects = []  # list of (index, pygame.Rect)
        self._inv_close_rect = None
        self._job_change_rect = None
        self._font_cache = {}
        self._scale_cache = {}
        self._rotate_cache = {}
        self._wall_rotate_cache = {}
        self._overlay_cache = {}

    def _get_font(self, name, size, bold=False):
        key = (name, size, bold)
        font = self._font_cache.get(key)
        if font is None:
            font = pygame.font.SysFont(name, size, bold=bold)
            self._font_cache[key] = font
        return font

    def _get_scaled_texture(self, tex_key, w, h, smooth=True):
        key = (tex_key, w, h, smooth)
        out = self._scale_cache.get(key)
        if out is None:
            base = self.tex[tex_key]
            if smooth:
                out = pygame.transform.smoothscale(base, (w, h))
            else:
                out = pygame.transform.scale(base, (w, h))
            self._scale_cache[key] = out
        return out

    def _get_rotated_cached(self, key_name, source, angle):
        a = int(angle) % 360
        key = (key_name, a)
        out = self._rotate_cache.get(key)
        if out is None:
            out = pygame.transform.rotate(source, a)
            self._rotate_cache[key] = out
        return out

    def _get_overlay(self, width, height, rgba):
        key = (width, height, rgba)
        surf = self._overlay_cache.get(key)
        if surf is None:
            surf = pygame.Surface((width, height), pygame.SRCALPHA)
            surf.fill(rgba)
            self._overlay_cache[key] = surf
        return surf

    @staticmethod
    def _shade(color, amount):
        return (
            max(0, min(255, color[0] + amount)),
            max(0, min(255, color[1] + amount)),
            max(0, min(255, color[2] + amount)),
        )

    def _make_player_job_body(self, job_idx):
        """Build a top-down body sprite for a specific job outfit."""
        size = 32
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))

        if not (0 <= job_idx < len(JOB_OUTFITS)):
            outfit = JOB_OUTFITS[0]
        else:
            outfit = JOB_OUTFITS[job_idx]

        clothes = outfit.get("clothes", (220, 220, 220))

        # Torso / legs
        pygame.draw.ellipse(s, self._shade(clothes, -20), (8, 15, 16, 12))
        pygame.draw.ellipse(s, clothes, (7, 10, 18, 12))

        # Arms
        pygame.draw.circle(s, self._shade(clothes, 8), (9, 16), 3)
        pygame.draw.circle(s, self._shade(clothes, 8), (23, 16), 3)

        return s

    def _make_player_job_head(self, job_idx):
        """Build a rotatable head sprite with optional hat for a job outfit."""
        size = 32
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))

        if not (0 <= job_idx < len(JOB_OUTFITS)):
            outfit = JOB_OUTFITS[0]
        else:
            outfit = JOB_OUTFITS[job_idx]

        hat = outfit.get("hat")
        skin = (220, 185, 155)

        # Head
        pygame.draw.circle(s, skin, (16, 10), 6)
        pygame.draw.circle(s, (180, 145, 120), (16, 10), 6, 1)

        # Face orientation hint (rotates with head)
        pygame.draw.polygon(s, (250, 250, 250), [(16, 2), (13, 6), (19, 6)])

        # Optional hat by style
        if hat:
            htype = hat.get("type", "cap")
            hcol = hat.get("color", (70, 70, 80))
            accent = hat.get("accent", (240, 240, 240))
            if htype == "police":
                pygame.draw.rect(s, hcol, (10, 2, 12, 4), border_radius=2)
                pygame.draw.rect(s, self._shade(hcol, -15), (11, 6, 10, 2), border_radius=1)
                pygame.draw.rect(s, (235, 215, 80), (15, 3, 2, 2))
            elif htype == "chef":
                pygame.draw.ellipse(s, hcol, (9, 0, 14, 7))
                pygame.draw.rect(s, self._shade(hcol, -10), (11, 5, 10, 2), border_radius=1)
            elif htype == "top":
                pygame.draw.rect(s, hcol, (12, 1, 8, 6))
                pygame.draw.rect(s, self._shade(hcol, 10), (10, 6, 12, 2))
            elif htype == "beanie":
                pygame.draw.ellipse(s, hcol, (10, 2, 12, 6))
            elif htype == "fedora":
                pygame.draw.ellipse(s, self._shade(hcol, 8), (9, 5, 14, 3))
                pygame.draw.rect(s, hcol, (11, 1, 10, 5))
            else:  # cap
                pygame.draw.ellipse(s, hcol, (10, 2, 12, 5))
                pygame.draw.rect(s, self._shade(hcol, -8), (12, 6, 8, 2), border_radius=1)
                pygame.draw.rect(s, accent, (15, 3, 2, 1))

        return s

    def get_job_button_at(self, pos):
        """Return clicked job index, or None if no job button was hit."""
        for idx, rect in self._job_button_rects:
            if rect.collidepoint(pos):
                return idx
        return None

    def get_hotbar_slot_at(self, pos):
        """Return clicked hotbar slot index, or None."""
        for idx, rect in self._hotbar_rects:
            if rect.collidepoint(pos):
                return idx
        return None

    def get_job_change_button_at(self, pos):
        """Return True if the HUD job-change button was clicked."""
        return bool(self._job_change_rect and self._job_change_rect.collidepoint(pos))

    def get_inventory_click_action(self, pos):
        """Return ('inv'|'hot'|'close', idx_or_none) for inventory overlay clicks."""
        if self._inv_close_rect and self._inv_close_rect.collidepoint(pos):
            return ("close", None)
        # Check hotbar first so it wins if any regions ever overlap.
        for idx, rect in self._inv_hotbar_rects:
            if rect.collidepoint(pos):
                return ("hot", idx)
        for idx, rect in self._inv_rects:
            if rect.collidepoint(pos):
                return ("inv", idx)
        return None

    def _get_player_building(self, world, player):
        """Return the building the player is inside, or None."""
        for bld in world.buildings:
            if bld.contains_pixel(player.x, player.y):
                return bld
        return None

    def draw_world(self, world):
        """Draw ground and wall layers (only visible tiles)."""
        cam = self.camera

        start_tx = max(0, int(cam.x // TILE_SIZE))
        start_ty = max(0, int(cam.y // TILE_SIZE))
        end_tx = min(world.width, int((cam.x + settings.SCREEN_WIDTH) // TILE_SIZE) + 2)
        end_ty = min(world.height, int((cam.y + settings.SCREEN_HEIGHT) // TILE_SIZE) + 2)

        for ty in range(start_ty, end_ty):
            for tx in range(start_tx, end_tx):
                sx, sy = cam.apply(tx * TILE_SIZE, ty * TILE_SIZE)

                # ground
                gt = world.ground[ty][tx]
                td = TILE_DEFS.get(gt)
                if td and td["tex"] in self.tex:
                    self.screen.blit(self.tex[td["tex"]], (sx, sy))

                # wall
                wt = world.walls[ty][tx]
                if wt is not None:
                    td = TILE_DEFS.get(wt)
                    if td and td["tex"] in self.tex:
                        rot = world.wall_rot[ty][tx]
                        if rot and wt >= 30:
                            ckey = (td["tex"], rot)
                            rotated = self._wall_rotate_cache.get(ckey)
                            if rotated is None:
                                rotated = pygame.transform.rotate(self.tex[td["tex"]], -rot * 90)
                                self._wall_rotate_cache[ckey] = rotated
                            self.screen.blit(rotated, (sx, sy))
                        else:
                            self.screen.blit(self.tex[td["tex"]], (sx, sy))

    def draw_roofs(self, world):
        """Draw roof layer — skip buildings where roof_visible is False (player inside)."""
        cam = self.camera

        start_tx = max(0, int(cam.x // TILE_SIZE))
        start_ty = max(0, int(cam.y // TILE_SIZE))
        end_tx = min(world.width, int((cam.x + settings.SCREEN_WIDTH) // TILE_SIZE) + 2)
        end_ty = min(world.height, int((cam.y + settings.SCREEN_HEIGHT) // TILE_SIZE) + 2)

        for bld in world.buildings:
            if not bld.roof_visible:
                continue
            for dy in range(bld.h):
                for dx in range(bld.w):
                    tx = bld.x + dx
                    ty = bld.y + dy
                    if start_tx <= tx < end_tx and start_ty <= ty < end_ty:
                        rt = world.roof[ty][tx]
                        if rt and rt in self.tex:
                            sx, sy = cam.apply(tx * TILE_SIZE, ty * TILE_SIZE)
                            self.screen.blit(self.tex[rt], (sx, sy))

    def draw_player(self, player):
        """Draw a fixed body with a rotating head (aim direction)."""
        jid = player.job if 0 <= player.job < len(JOB_OUTFITS) else 0
        body = self.tex.get(f"player_body_{jid}")
        head = self.tex.get(f"player_head_{jid}")

        # Fallback if textures missing.
        if body is None:
            body = self._make_player_job_body(jid)
        if head is None:
            head = self._make_player_job_head(jid)

        cx, cy = self.camera.apply(player.x, player.y)

        body_rect = body.get_rect(center=(cx, cy + 2))
        self.screen.blit(body, body_rect)

        rhead = self._get_rotated_cached(f"head_{jid}", head, player.angle)
        head_rect = rhead.get_rect(center=(cx, cy - 4))
        self.screen.blit(rhead, head_rect)

    def draw_held_item(self, player):
        """Draw selected hotbar item in front of the player."""
        idx = player.selected_hotbar
        if not (0 <= idx < len(player.hotbar)):
            return
        stack = player.hotbar[idx]
        if not stack:
            return

        idef = ITEM_DEFS.get(stack["id"])
        if idef is None:
            return
        tex_key = idef.get("tex")
        if not tex_key or tex_key not in self.tex:
            return

        sprite = self._get_scaled_texture(tex_key, 20, 20, smooth=True)
        sprite = self._get_rotated_cached(f"held_{tex_key}", sprite, player.angle)

        ang = math.radians(player.angle)
        fx = -math.sin(ang)
        fy = -math.cos(ang)
        hx = player.x + fx * 14
        hy = player.y + fy * 14

        sx, sy = self.camera.apply(hx, hy)
        rect = sprite.get_rect(center=(sx, sy))
        self.screen.blit(sprite, rect)

    def draw_dropped_items(self, dropped_items):
        """Draw dropped item entities on the ground."""
        if not dropped_items:
            return

        count_font = self._get_font("consolas", 11, bold=True)
        for it in dropped_items:
            item_id = it.get("id")
            idef = ITEM_DEFS.get(item_id)
            if idef is None:
                continue
            tex_key = idef.get("tex")
            if not tex_key or tex_key not in self.tex:
                continue

            sx, sy = self.camera.apply(it.get("x", 0), it.get("y", 0))
            # Ground shadow
            pygame.draw.ellipse(self.screen, (0, 0, 0, 90), (sx - 9, sy + 7, 18, 8))

            sprite = self._get_scaled_texture(tex_key, 18, 18, smooth=True)
            rect = sprite.get_rect(center=(sx, sy + 1))
            self.screen.blit(sprite, rect)

            count = int(it.get("count", 1))
            if count > 1:
                cnt = count_font.render(str(count), True, (255, 255, 255))
                self.screen.blit(cnt, (sx + 8, sy - 14))

    def draw_projectiles(self, projectiles):
        """Draw simple projectile tracers for fired guns."""
        if not projectiles:
            return
        for p in projectiles:
            sx, sy = self.camera.apply(p.get("x", 0), p.get("y", 0))
            pygame.draw.circle(self.screen, (255, 230, 120), (sx, sy), 2)

    def draw_indoor_blackout(self, world, inside_bld):
        """Black out everything outside the building the player is in."""
        cam = self.camera
        if self._blackout is None:
            self._blackout = pygame.Surface(
                (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        bo = self._blackout
        bo.fill((0, 0, 0, 255))

        # Cut out the building footprint (walls + interior)
        bx = inside_bld.x * TILE_SIZE
        by = inside_bld.y * TILE_SIZE
        bw = inside_bld.w * TILE_SIZE
        bh = inside_bld.h * TILE_SIZE

        sx, sy = cam.apply(bx, by)
        pygame.draw.rect(bo, (0, 0, 0, 0), (sx, sy, bw, bh))

        self.screen.blit(bo, (0, 0))

    def draw_interact_prompt(self, world, player):
        """Show prompt when near a building door."""
        bld = world.get_building_near(player.x, player.y)
        if bld is None:
            return

        font = self._get_font("consolas", 16)
        if bld.government:
            line1 = bld.name
            line2 = "Government Building"
            c1 = (220, 190, 50)
            c2 = (180, 160, 60)
        elif bld.owner is None:
            line1 = f"[E] Buy {bld.name}"
            line2 = f"Price: ${bld.price:,.0f}"
            c1 = (80, 220, 80)
            c2 = (200, 200, 200)
        elif bld.owner == "player":
            line1 = bld.name
            lock_action = "Unlock" if bld.locked else "Lock"
            state = "Locked" if bld.locked else "Unlocked"
            line2 = f"[F] Sell  [L] {lock_action} ({state})"
            c1 = (100, 180, 255)
            c2 = (200, 100, 100)
        else:
            line1 = f"{bld.name} — Owned"
            line2 = "Locked" if bld.locked else ""
            c1 = (200, 200, 200)
            c2 = (200, 200, 200)

        t1 = font.render(line1, True, c1)
        # Keep interact prompt above the hotbar area.
        hotbar_top_y = settings.SCREEN_HEIGHT - 74
        prompt_y = hotbar_top_y - 54
        self.screen.blit(t1, (settings.SCREEN_WIDTH // 2 - t1.get_width() // 2, prompt_y))
        if line2:
            t2 = font.render(line2, True, c2)
            self.screen.blit(t2, (settings.SCREEN_WIDTH // 2 - t2.get_width() // 2, prompt_y + 22))

    def draw_hud(self, player, inside_bld):
        """HUD with money, job, health/hunger/thirst bars."""
        font = self._get_font("consolas", 14)
        pos_text = font.render(
            f"X:{int(player.x // TILE_SIZE)} Y:{int(player.y // TILE_SIZE)}", True, (255, 255, 255))
        self.screen.blit(pos_text, (10, 10))

        # Money
        money_text = font.render(f"${player.money:,.0f}", True, (80, 220, 80))
        self.screen.blit(money_text, (settings.SCREEN_WIDTH - money_text.get_width() - 10, 10))

        # Job
        job_name, _, job_color = JOBS[player.job]
        job_text = font.render(f"Job: {job_name}", True, job_color)
        btn_font = self._get_font("consolas", 13, bold=True)
        btn_label = btn_font.render("Change", True, (230, 230, 240))
        btn_w = btn_label.get_width() + 16
        btn_h = 20
        btn_x = settings.SCREEN_WIDTH - btn_w - 10
        btn_y = 28
        self._job_change_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        pygame.draw.rect(self.screen, (35, 40, 58), self._job_change_rect, border_radius=5)
        pygame.draw.rect(self.screen, (95, 105, 135), self._job_change_rect, 1, border_radius=5)
        self.screen.blit(btn_label, (btn_x + 8, btn_y + 2))

        self.screen.blit(job_text, (btn_x - job_text.get_width() - 8, 30))

        # Owned property
        if player.owned_building:
            lock_state = "Locked" if player.owned_building.locked else "Unlocked"
            own_text = font.render(
                f"Property: {player.owned_building.name} [{lock_state}]  [L] toggle",
                True,
                (100, 180, 255),
            )
            self.screen.blit(own_text, (settings.SCREEN_WIDTH - own_text.get_width() - 10, 46))

        # Held item info
        held = None
        if 0 <= player.selected_hotbar < len(player.hotbar):
            held = player.hotbar[player.selected_hotbar]
        if held:
            held_name = held.get("name", "Item")
            held_count = held.get("count", 0)
            held_extra = ""
            idef = ITEM_DEFS.get(held.get("id"), {})
            use_cfg = idef.get("use", {})
            if use_cfg.get("type") == "gun":
                ammo_id = use_cfg.get("ammo")
                if ammo_id:
                    ammo_name = ITEM_DEFS.get(ammo_id, {}).get("name", "Ammo")
                    ammo_count = player.count_item(ammo_id)
                    held_extra = f"  {ammo_name}: {ammo_count}"
            elif use_cfg.get("type") == "cuffs":
                held_extra = "  [Y] detain/release  [ ] sentence (+/-30s, max 10:00)"
            held_text = font.render(
                f"Held: {held_name} x{held_count}{held_extra}  [U]/[RMB] use  [Q] drop  [G] pickup",
                True,
                (220, 220, 235),
            )
        else:
            held_text = font.render("Held: Empty  [G] pickup  [H] spawn test item", True, (170, 170, 180))
        self.screen.blit(held_text, (10, 46))

        if inside_bld:
            name_text = font.render(inside_bld.name, True, (255, 255, 100))
            self.screen.blit(name_text, (10, 28))

        if player.in_jail and player.arrest_until_ms > 0:
            remaining = max(0, (player.arrest_until_ms - pygame.time.get_ticks()) // 1000)
            mins = remaining // 60
            secs = remaining % 60
            jail_text = font.render(f"Jail Time: {mins:02d}:{secs:02d}", True, (230, 120, 120))
            self.screen.blit(jail_text, (10, 64))

        # Health / Hunger / Thirst bars — bottom left (kept above hotbar)
        bar_w, bar_h = 184, 12
        label_w = 56
        bar_gap = 6
        bar_x = 10
        hotbar_top_y = settings.SCREEN_HEIGHT - 74
        total_h = bar_h * 3 + bar_gap * 2
        start_y = hotbar_top_y - total_h - 8
        bar_y_health = start_y
        bar_y_hunger = start_y + bar_h + bar_gap
        bar_y_thirst = start_y + (bar_h + bar_gap) * 2

        # Health
        self._draw_stat_bar(bar_x, bar_y_health, bar_w, bar_h,
                            player.health / 100, (210, 70, 70), "Health", font, label_w)

        # Hunger
        self._draw_stat_bar(bar_x, bar_y_hunger, bar_w, bar_h,
                            player.hunger / 100, (200, 140, 50), "Hunger", font, label_w)
        # Thirst
        self._draw_stat_bar(bar_x, bar_y_thirst, bar_w, bar_h,
                            player.thirst / 100, (60, 150, 220), "Thirst", font, label_w)

    def _draw_stat_bar(self, x, y, w, h, fill, color, label, font, label_w=52):
        """Draw a labelled stat bar."""
        fill = max(0, min(1, fill))
        # Label (inline on the left)
        lbl = font.render(label, True, (220, 220, 220))
        self.screen.blit(lbl, (x, y + h // 2 - lbl.get_height() // 2))

        bx = x + label_w
        bw = max(12, w - label_w)
        # Background
        pygame.draw.rect(self.screen, (30, 30, 30), (bx, y, bw, h))
        # Fill
        if fill > 0:
            r = int(color[0] * (0.4 + 0.6 * fill))
            g = int(color[1] * (0.4 + 0.6 * fill))
            b = int(color[2] * (0.4 + 0.6 * fill))
            pygame.draw.rect(self.screen, (r, g, b), (bx, y, int(bw * fill), h))
        # Border
        pygame.draw.rect(self.screen, (100, 100, 100), (bx, y, bw, h), 1)

    def draw_job_menu(self, player, job_counts=None):
        """Draw the job selection overlay."""
        font_title = self._get_font("consolas", 20, bold=True)
        font_item = self._get_font("consolas", 16)
        font_small = self._get_font("consolas", 12)
        mouse_pos = pygame.mouse.get_pos()
        self._job_button_rects = []
        if job_counts is None:
            job_counts = [0] * len(JOBS)
        has_caps = any(cap is not None for cap in JOB_MAX_PLAYERS)

        row_h = 42
        menu_w, menu_h = 520, 34 + len(JOBS) * row_h
        mx = settings.SCREEN_WIDTH // 2 - menu_w // 2
        my = settings.SCREEN_HEIGHT // 2 - menu_h // 2

        # Dim background
        dim = self._get_overlay(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT, (0, 0, 0, 120))
        self.screen.blit(dim, (0, 0))

        # Panel
        pygame.draw.rect(self.screen, (25, 25, 35), (mx, my, menu_w, menu_h), border_radius=8)
        pygame.draw.rect(self.screen, (80, 80, 100), (mx, my, menu_w, menu_h), 2, border_radius=8)

        # Title
        title = font_title.render("Choose a Job", True, (255, 220, 80))
        self.screen.blit(title, (mx + menu_w // 2 - title.get_width() // 2, my + 6))

        hint_text = "Click a job"
        if has_caps:
            hint_text = "Click a job (full jobs are blocked)"
        hint = font_item.render(hint_text, True, (170, 170, 180))
        self.screen.blit(hint, (mx + menu_w - hint.get_width() - 12, my + 10))

        # List
        for i, (name, salary, color) in enumerate(JOBS):
            iy = my + 38 + i * row_h
            row_rect = pygame.Rect(mx + 6, iy - 2, menu_w - 12, row_h - 4)
            self._job_button_rects.append((i, row_rect))

            cap = JOB_MAX_PLAYERS[i]
            used = job_counts[i] if 0 <= i < len(job_counts) else 0
            is_current = (i == player.job)
            is_full = (cap is not None and used >= cap and not is_current)

            # Button state
            if is_current:
                row_color = (50, 50, 70)
            elif is_full:
                row_color = (55, 35, 35)
            else:
                row_color = (35, 35, 45)
            if row_rect.collidepoint(mouse_pos):
                if is_full:
                    row_color = (80, 40, 40)
                else:
                    row_color = (70, 70, 90)
            pygame.draw.rect(self.screen, row_color, row_rect, border_radius=4)
            pygame.draw.rect(self.screen, (90, 90, 110), row_rect, 1, border_radius=4)

            name_color = color if not is_full else (180, 120, 120)
            name_text = font_item.render(name, True, name_color)
            self.screen.blit(name_text, (mx + 14, iy))

            # Loadout preview
            loadout = JOB_LOADOUTS[i] if 0 <= i < len(JOB_LOADOUTS) else []
            if loadout:
                parts = []
                for item_id, cnt in loadout:
                    iname = ITEM_DEFS.get(item_id, {}).get("name", item_id)
                    parts.append(f"{iname}x{cnt}")
                loadout_text = "Loadout: " + ", ".join(parts)
            else:
                loadout_text = "Loadout: None"
            if len(loadout_text) > 62:
                loadout_text = loadout_text[:59] + "..."
            lo_color = (180, 180, 190) if not is_full else (165, 130, 130)
            lo_text = font_small.render(loadout_text, True, lo_color)
            self.screen.blit(lo_text, (mx + 14, iy + 19))

            if cap is None:
                slot_str = f"{used}/∞"
            else:
                slot_str = f"{used}/{cap}"
            sal_str = f"${salary}/pay" if salary > 0 else "No salary"
            right_str = f"{sal_str}  {slot_str}"
            if is_full:
                right_str += "  FULL"
            sal_color = (80, 220, 80) if salary > 0 else (120, 120, 120)
            if is_full:
                sal_color = (220, 120, 120)
            sal_text = font_item.render(right_str, True, sal_color)
            self.screen.blit(sal_text, (mx + menu_w - sal_text.get_width() - 12, iy + 2))

    def draw_build_menu(self, selection):
        """Draw the bottom build bar showing furniture items."""
        font = self._get_font("consolas", 12)
        bar_h = 56
        bar_y = settings.SCREEN_HEIGHT - bar_h
        # background bar
        bg = self._get_overlay(settings.SCREEN_WIDTH, bar_h, (20, 20, 30, 200))
        self.screen.blit(bg, (0, bar_y))

        # title
        title = font.render("BUILD  [B] close  [1-8/Scroll] select  [R] rotate  [LMB] place  [RMB] remove", True, (200, 200, 200))
        self.screen.blit(title, (10, bar_y + 2))

        # items
        item_size = 40
        margin = 6
        start_x = 10
        for i, (name, cost, tiles) in enumerate(FURNITURE):
            x = start_x + i * (item_size + margin)
            y = bar_y + 16

            # selection highlight
            if i == selection:
                pygame.draw.rect(self.screen, (255, 220, 80), (x - 2, y - 2, item_size + 4, item_size + 4), 2)

            # background
            pygame.draw.rect(self.screen, (40, 40, 50), (x, y, item_size, item_size))

            # texture preview (use first tile of the item)
            tile_id = tiles[0][2]
            td = TILE_DEFS.get(tile_id)
            if td and td["tex"] in self.tex:
                preview = self._get_scaled_texture(td["tex"], item_size - 4, item_size - 4, smooth=False)
                self.screen.blit(preview, (x + 2, y + 2))

            # cost label
            cost_t = font.render("Free" if cost == 0 else f"${cost}", True, (80, 220, 80))
            self.screen.blit(cost_t, (x, y + item_size + 1))

        # selected item name
        sel_name, sel_cost, _ = FURNITURE[selection]
        sel_t = font.render(f"{sel_name} — {'Free' if sel_cost == 0 else f'${sel_cost}'}", True, (255, 220, 80))
        self.screen.blit(sel_t, (settings.SCREEN_WIDTH - sel_t.get_width() - 10, bar_y + 4))

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
        min_dx = min(r[0] for r in rotated)
        min_dy = min(r[1] for r in rotated)
        return [(dx - min_dx, dy - min_dy, tid) for dx, dy, tid in rotated]

    def draw_build_cursor(self, world, player, build_selection=0, build_rotation=0):
        """Draw ghost furniture preview under the mouse cursor in build mode."""
        mx, my = pygame.mouse.get_pos()
        wx = mx + self.camera.x
        wy = my + self.camera.y
        tx = int(wx // TILE_SIZE)
        ty = int(wy // TILE_SIZE)

        _, _, tiles = FURNITURE[build_selection]
        rtiles = self._rotate_tiles(tiles, build_rotation)
        bld = player.owned_building
        rot_angle = -build_rotation * 90  # pygame rotates counter-clockwise

        all_valid = True
        for dx, dy, _ in rtiles:
            if not (bld and world.is_interior(bld, tx + dx, ty + dy)):
                all_valid = False
                break

        for dx, dy, tid in rtiles:
            ttx, tty = tx + dx, ty + dy
            sx, sy = self.camera.apply(ttx * TILE_SIZE, tty * TILE_SIZE)

            # Draw ghost texture
            td = TILE_DEFS.get(tid)
            if td and td["tex"] in self.tex:
                ghost = self.tex[td["tex"]].copy()
                if build_rotation != 0:
                    ghost = pygame.transform.rotate(ghost, rot_angle)
                # Tint green/red overlay
                tint = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                if all_valid:
                    tint.fill((80, 255, 80, 50))
                else:
                    tint.fill((255, 80, 80, 50))
                ghost.set_alpha(180)
                self.screen.blit(ghost, (sx, sy))
                self.screen.blit(tint, (sx, sy))
            else:
                # Fallback colored square
                color = (80, 255, 80, 100) if all_valid else (255, 80, 80, 100)
                cursor = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                cursor.fill(color)
                self.screen.blit(cursor, (sx, sy))

        # Draw outline around full footprint
        if rtiles:
            min_dx = min(r[0] for r in rtiles)
            min_dy = min(r[1] for r in rtiles)
            max_dx = max(r[0] for r in rtiles)
            max_dy = max(r[1] for r in rtiles)
            ox, oy = self.camera.apply((tx + min_dx) * TILE_SIZE, (ty + min_dy) * TILE_SIZE)
            ow = (max_dx - min_dx + 1) * TILE_SIZE
            oh = (max_dy - min_dy + 1) * TILE_SIZE
            outline_color = (80, 255, 80) if all_valid else (255, 80, 80)
            pygame.draw.rect(self.screen, outline_color, (ox, oy, ow, oh), 2)

    def draw_chat_bubbles(self, player):
        """Draw speech bubbles above the player."""
        if not player.chat_bubbles:
            return
        font = self._get_font("consolas", 13)
        sx, sy = self.camera.apply(player.x, player.y)
        # Stack bubbles upward, newest at bottom
        y_offset = -30
        for text, timer in reversed(player.chat_bubbles):
            # Fade out in the last 1000ms
            alpha = min(255, int(255 * timer / 1000))
            rendered = font.render(text, True, (20, 20, 30))
            tw, th = rendered.get_size()
            pad_x, pad_y = 8, 4
            bw = tw + pad_x * 2
            bh = th + pad_y * 2
            bx = sx - bw // 2
            by = sy + y_offset - bh

            # Bubble background
            bubble_surf = pygame.Surface((bw, bh + 6), pygame.SRCALPHA)
            pygame.draw.rect(bubble_surf, (255, 255, 255, alpha), (0, 0, bw, bh), border_radius=6)
            pygame.draw.rect(bubble_surf, (180, 180, 190, alpha), (0, 0, bw, bh), 1, border_radius=6)
            # Small triangle pointer
            pygame.draw.polygon(bubble_surf, (255, 255, 255, alpha), [
                (bw // 2 - 4, bh), (bw // 2 + 4, bh), (bw // 2, bh + 5)
            ])
            self.screen.blit(bubble_surf, (bx, by))

            # Text
            text_surf = rendered.copy()
            text_surf.set_alpha(alpha)
            self.screen.blit(text_surf, (bx + pad_x, by + pad_y))

            y_offset -= bh + 4

    def draw_chat_input(self, chat_text):
        """Draw the chat input bar at the bottom of the screen."""
        font = self._get_font("consolas", 16)
        bar_h = 32
        bar_y = settings.SCREEN_HEIGHT - bar_h
        bg = self._get_overlay(settings.SCREEN_WIDTH, bar_h, (10, 10, 20, 220))
        self.screen.blit(bg, (0, bar_y))

        label = font.render("Say: ", True, (180, 180, 180))
        self.screen.blit(label, (10, bar_y + 6))

        # Blinking cursor
        cursor_char = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        msg = font.render(chat_text + cursor_char, True, (255, 255, 255))
        self.screen.blit(msg, (10 + label.get_width(), bar_y + 6))

    def _draw_item_stack(self, screen, rect, stack, selected=False):
        """Draw one inventory/hotbar slot with optional item stack."""
        base = (30, 30, 40)
        pygame.draw.rect(screen, base, rect, border_radius=6)
        border = (90, 90, 110)
        if selected:
            border = (255, 220, 90)
        pygame.draw.rect(screen, border, rect, 2, border_radius=6)

        if stack is None:
            return

        item_def = ITEM_DEFS.get(stack["id"], {"name": "Item", "color": (150, 150, 150)})
        icon = pygame.Rect(rect.x + 6, rect.y + 6, rect.w - 12, rect.h - 24)
        tex_key = item_def.get("tex")
        if tex_key and tex_key in self.tex:
            icon_tex = self._get_scaled_texture(tex_key, icon.w, icon.h, smooth=True)
            screen.blit(icon_tex, icon)
            pygame.draw.rect(screen, (20, 20, 20), icon, 1, border_radius=4)
        else:
            pygame.draw.rect(screen, item_def["color"], icon, border_radius=4)
            pygame.draw.rect(screen, (20, 20, 20), icon, 1, border_radius=4)

        font_name = self._get_font("consolas", 11)
        font_cnt = self._get_font("consolas", 12, bold=True)
        short = item_def["name"][:8]
        txt = font_name.render(short, True, (230, 230, 235))
        screen.blit(txt, (rect.x + rect.w // 2 - txt.get_width() // 2, rect.y + rect.h - 16))

        cnt = font_cnt.render(str(stack["count"]), True, (255, 255, 255))
        screen.blit(cnt, (rect.right - cnt.get_width() - 5, rect.y + 3))

    def draw_hotbar(self, player):
        """Draw the bottom-center hotbar and store clickable hitboxes."""
        self._hotbar_rects = []
        slot_w, slot_h = 56, 56
        gap = 8
        total_w = HOTBAR_SIZE * slot_w + (HOTBAR_SIZE - 1) * gap
        sx = settings.SCREEN_WIDTH // 2 - total_w // 2
        sy = settings.SCREEN_HEIGHT - 74

        for i in range(HOTBAR_SIZE):
            r = pygame.Rect(sx + i * (slot_w + gap), sy, slot_w, slot_h)
            self._hotbar_rects.append((i, r))
            selected = (i == player.selected_hotbar)
            self._draw_item_stack(self.screen, r, player.hotbar[i], selected=selected)

            idx_font = self._get_font("consolas", 11)
            idx_txt = idx_font.render(str(i + 1), True, (200, 200, 210))
            self.screen.blit(idx_txt, (r.x + 4, r.y + 3))

    def draw_inventory(self, player, selected_slot=None):
        """Draw inventory overlay with clickable inventory and hotbar slots."""
        self._inv_rects = []
        self._inv_hotbar_rects = []
        self._inv_close_rect = None

        # Dim background
        dim = self._get_overlay(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT, (0, 0, 0, 140))
        self.screen.blit(dim, (0, 0))

        panel_w, panel_h = 520, 500
        px = settings.SCREEN_WIDTH // 2 - panel_w // 2
        py = settings.SCREEN_HEIGHT // 2 - panel_h // 2
        panel = pygame.Rect(px, py, panel_w, panel_h)
        pygame.draw.rect(self.screen, (24, 24, 34), panel, border_radius=10)
        pygame.draw.rect(self.screen, (85, 85, 110), panel, 2, border_radius=10)

        title_font = self._get_font("consolas", 22, bold=True)
        hint_font = self._get_font("consolas", 14)
        title = title_font.render("Inventory", True, (255, 220, 90))
        self.screen.blit(title, (px + 16, py + 10))
        hint = hint_font.render("[E]/[Tab]/[Esc] close   Click source slot, then destination slot", True, (180, 180, 190))
        self.screen.blit(hint, (px + 16, py + 38))

        self._inv_close_rect = pygame.Rect(px + panel_w - 34, py + 10, 24, 24)
        pygame.draw.rect(self.screen, (70, 35, 40), self._inv_close_rect, border_radius=4)
        x_font = self._get_font("consolas", 16, bold=True)
        x_txt = x_font.render("X", True, (255, 220, 220))
        self.screen.blit(x_txt, (self._inv_close_rect.x + 7, self._inv_close_rect.y + 3))

        cols = 5
        slot_w, slot_h = 84, 70
        gap = 10
        start_x = px + 20
        start_y = py + 74

        for i, stack in enumerate(player.inventory):
            row = i // cols
            col = i % cols
            r = pygame.Rect(start_x + col * (slot_w + gap), start_y + row * (slot_h + gap), slot_w, slot_h)
            self._inv_rects.append((i, r))
            selected = selected_slot == ("inv", i)
            self._draw_item_stack(self.screen, r, stack, selected=selected)

        hb_label = hint_font.render("Hotbar", True, (210, 210, 220))
        hb_y = py + panel_h - 94
        self.screen.blit(hb_label, (px + 20, hb_y - 20))

        hb_slot_w, hb_slot_h = 84, 70
        for i in range(HOTBAR_SIZE):
            r = pygame.Rect(px + 20 + i * (hb_slot_w + gap), hb_y, hb_slot_w, hb_slot_h)
            self._inv_hotbar_rects.append((i, r))
            selected = selected_slot == ("hot", i)
            self._draw_item_stack(self.screen, r, player.hotbar[i], selected=selected)

            idx_font = self._get_font("consolas", 11)
            idx_txt = idx_font.render(str(i + 1), True, (200, 200, 210))
            self.screen.blit(idx_txt, (r.x + 4, r.y + 3))

    def render_frame(self, world, player, build_mode=False, build_selection=0, build_rotation=0,
                     chat_active=False, chat_text="", job_menu_open=False, job_counts=None,
                     inventory_open=False, inventory_selected=None, dropped_items=None,
                     projectiles=None):
        """Full frame render."""
        self.camera.follow(player.x, player.y)
        inside_bld = self._get_player_building(world, player)

        self.draw_world(world)
        self.draw_dropped_items(dropped_items)
        self.draw_projectiles(projectiles)
        self.draw_player(player)
        self.draw_held_item(player)
        self.draw_chat_bubbles(player)
        self.draw_roofs(world)

        if inside_bld:
            self.draw_indoor_blackout(world, inside_bld)

        if build_mode:
            self.draw_build_cursor(world, player, build_selection, build_rotation)
            self.draw_build_menu(build_selection)
        else:
            self.draw_interact_prompt(world, player)

        self.draw_hud(player, inside_bld)

        if not build_mode:
            self.draw_hotbar(player)

        if chat_active:
            self.draw_chat_input(chat_text)

        if job_menu_open:
            self.draw_job_menu(player, job_counts)

        if inventory_open:
            self.draw_inventory(player, inventory_selected)
