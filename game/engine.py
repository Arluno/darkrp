"""
Multiplayer game client - connects to server.py via WebSocket.
All game logic runs on the server; this client sends inputs and renders state.
"""
import math
import sys
import pygame
import game.settings as settings
from game.settings import (
    FPS,
    TITLE,
    COLOR_BG,
    TILE_SIZE,
    JOBS,
    JOB_OUTFITS,
    HOTBAR_SIZE,
    ITEM_DEFS,
    INVENTORY_SIZE,
)
from game.textures import generate_all, load_textures
from game.player import Player
from game.renderer import Renderer
from game.town import build_town
from game.network import NetworkManager


DEFAULT_SERVER = "ws://localhost:10000/ws"


class Engine:
    def __init__(self):
        if not pygame.get_init():
            pygame.init()
        pygame.display.set_caption(TITLE)

        info = pygame.display.Info()
        settings.SCREEN_WIDTH = info.current_w
        settings.SCREEN_HEIGHT = info.current_h
        self.screen = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.running = True

        generate_all()
        textures = load_textures()

        self.world = build_town()

        spawn_x = 40 * TILE_SIZE
        spawn_y = 30 * TILE_SIZE
        self.player = Player(spawn_x, spawn_y)

        self.renderer = Renderer(self.screen, textures)

        # Network
        self.net = NetworkManager()
        server_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER
        player_name = sys.argv[2] if len(sys.argv) > 2 else "Player"
        self.net.connect(server_url, player_name)

        # UI state (local only)
        self.chat_active = False
        self.chat_text = ""
        self._chat_skip_text = False
        self.job_menu_open = False
        self.inventory_open = False
        self.inventory_selected = None
        self._selected_hotbar = 0
        self._current_job = 0
        self.build_mode = False
        self.build_selection = 0
        self.build_rotation = 0

    def run(self):
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(FPS)
        self.net.disconnect()
        pygame.quit()

    # -- Events -------------------------------------------------------

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Chat input mode
            if self.chat_active:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if self.chat_text.strip():
                            self.net.send_action("chat", text=self.chat_text.strip())
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
                        self._current_job = clicked
                        self.job_menu_open = False
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
                        self._selected_hotbar = event.key - pygame.K_1
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = self.renderer.get_inventory_click_action(event.pos)
                    if action is None:
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
                    self.running = False
                elif event.key == pygame.K_e:
                    self.net.send_action("buy")
                    self.inventory_open = not self.inventory_open
                    self.inventory_selected = None
                elif event.key == pygame.K_TAB:
                    self.inventory_open = not self.inventory_open
                    self.inventory_selected = None
                elif event.key == pygame.K_f:
                    self.net.send_action("sell")
                elif event.key == pygame.K_t:
                    self.chat_active = True
                    self.chat_text = ""
                    self._chat_skip_text = True
                elif event.key == pygame.K_j:
                    self.job_menu_open = True
                elif event.key == pygame.K_l:
                    self.net.send_action("lock")
                elif event.key == pygame.K_g:
                    self.net.send_action("pickup")
                elif event.key == pygame.K_q:
                    self.net.send_action("drop")
                elif event.key == pygame.K_u:
                    self.net.send_action("use")
                elif event.key == pygame.K_y:
                    self.net.send_action("detain")
                elif event.key == pygame.K_LEFTBRACKET:
                    self.net.send_action("sentence_down")
                elif event.key == pygame.K_RIGHTBRACKET:
                    self.net.send_action("sentence_up")
                elif pygame.K_1 <= event.key < pygame.K_1 + HOTBAR_SIZE:
                    self._selected_hotbar = event.key - pygame.K_1

            # Click hotbar / job change button
            if (not self.chat_active and not self.job_menu_open and
                    not self.inventory_open and
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                if self.renderer.get_job_change_button_at(event.pos):
                    self.job_menu_open = True
                    continue
                hidx = self.renderer.get_hotbar_slot_at(event.pos)
                if hidx is not None:
                    self._selected_hotbar = hidx

            # Right click = use
            if (not self.chat_active and not self.job_menu_open and
                    not self.inventory_open and
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 3):
                self.net.send_action("use")

    def _handle_inventory_slot_click(self, kind, idx):
        if self.inventory_selected is None:
            slots = self.player.inventory if kind == "inv" else self.player.hotbar
            if 0 <= idx < len(slots) and slots[idx] is not None:
                self.inventory_selected = (kind, idx)
            return

        skind, sidx = self.inventory_selected
        if skind == kind and sidx == idx:
            self.inventory_selected = None
            return

        self.net.send_action("inv_swap",
                             src_kind="inventory" if skind == "inv" else "hotbar",
                             src_idx=sidx,
                             dst_kind="inventory" if kind == "inv" else "hotbar",
                             dst_idx=idx)
        self.inventory_selected = None

    # -- Update: send input + sync from server -----------------------

    def _update(self):
        keys = pygame.key.get_pressed()
        mx, my = pygame.mouse.get_pos()
        ox = mx - settings.SCREEN_WIDTH / 2
        oy = my - settings.SCREEN_HEIGHT / 2
        look_angle = math.degrees(math.atan2(-ox, -oy))

        key_state = {
            "up": bool(keys[pygame.K_w] or keys[pygame.K_UP]),
            "down": bool(keys[pygame.K_s] or keys[pygame.K_DOWN]),
            "left": bool(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            "right": bool(keys[pygame.K_d] or keys[pygame.K_RIGHT]),
        }

        if not self.chat_active:
            self.net.send_input(key_state, look_angle,
                                self._current_job, self._selected_hotbar)
        else:
            self.net.send_input(
                {"up": False, "down": False, "left": False, "right": False},
                look_angle, self._current_job, self._selected_hotbar)

        # Sync local player object from server state
        state = self.net.state
        you = state.you
        me = state.players.get(state.local_id)

        if me:
            self.player.x = me.get("x", self.player.x)
            self.player.y = me.get("y", self.player.y)
            self.player.angle = me.get("angle", self.player.angle)
            self.player.job = me.get("job", self.player.job)
            self.player.health = me.get("health", self.player.health)
            self.player.hunger = me.get("hunger", self.player.hunger)
            self.player.thirst = me.get("thirst", self.player.thirst)
            self.player.money = me.get("money", self.player.money)
            self.player.detained = me.get("detained", False)
            self.player.in_jail = me.get("in_jail", False)
            # Server sends chat_bubbles as [[text, remaining_seconds], ...]
            self.player.chat_bubbles = [
                [t, s * 1000] for t, s in me.get("chat_bubbles", [])
            ]

        if you:
            hotbar = you.get("hotbar")
            if hotbar is not None:
                self.player.hotbar = hotbar
            inv = you.get("inventory")
            if inv is not None:
                self.player.inventory = inv
            self.player.selected_hotbar = you.get(
                "selected_hotbar", self._selected_hotbar)
            self.player.health = you.get("health", self.player.health)
            self.player.hunger = you.get("hunger", self.player.hunger)
            self.player.thirst = you.get("thirst", self.player.thirst)
            self.player.money = you.get("money", self.player.money)
            self._current_job = you.get("job", self._current_job)
            self.player.job = self._current_job

        # Sync building ownership to world objects
        for bdata in state.buildings:
            for bld in self.world.buildings:
                if bld.name == bdata.get("name"):
                    owner_id = bdata.get("owner")
                    if owner_id == state.local_id:
                        bld.owner = "player"
                        self.player.owned_building = bld
                    elif owner_id:
                        bld.owner = owner_id
                    else:
                        bld.owner = None
                        if self.player.owned_building == bld:
                            self.player.owned_building = None
                    bld.locked = bdata.get("locked", False)

        self.world.update_roofs(self.player.x, self.player.y)

    # -- Draw ---------------------------------------------------------

    def _get_job_counts(self):
        counts = [0] * len(JOBS)
        for pdata in self.net.state.players.values():
            jid = pdata.get("job")
            if isinstance(jid, int) and 0 <= jid < len(JOBS):
                counts[jid] += 1
        return counts

    def _draw(self):
        self.screen.fill(COLOR_BG)
        state = self.net.state

        dropped = state.dropped_items
        projectiles = state.projectiles
        job_counts = self._get_job_counts()

        self.renderer.render_frame(
            self.world, self.player,
            self.build_mode, self.build_selection, self.build_rotation,
            self.chat_active, self.chat_text,
            self.job_menu_open, job_counts,
            self.inventory_open, self.inventory_selected,
            dropped, projectiles)

        # Draw other players
        self._draw_other_players()

        # Connection status overlay
        if not state.connected:
            font = pygame.font.SysFont("consolas", 18)
            txt = font.render("Connecting to server...", True, (255, 100, 100))
            self.screen.blit(txt, (settings.SCREEN_WIDTH // 2 - txt.get_width() // 2,
                                   settings.SCREEN_HEIGHT // 2))

        pygame.display.flip()

    def _draw_other_players(self):
        state = self.net.state
        cam = self.renderer.camera

        for pid, pdata in state.players.items():
            if pid == state.local_id:
                continue

            px = pdata.get("x", 0)
            py = pdata.get("y", 0)
            sx, sy = cam.apply(px, py)

            if sx < -50 or sx > settings.SCREEN_WIDTH + 50:
                continue
            if sy < -50 or sy > settings.SCREEN_HEIGHT + 50:
                continue

            job_idx = pdata.get("job", 0)
            angle = pdata.get("angle", 0)
            name = pdata.get("name", pid[:6])
            health = pdata.get("health", 100)
            detained = pdata.get("detained", False)
            in_jail = pdata.get("in_jail", False)

            # Body
            body = self.renderer._make_player_job_body(job_idx)
            self.screen.blit(body,
                (sx - body.get_width() // 2, sy - body.get_height() // 2 + 2))

            # Head (rotated)
            head = self.renderer._make_player_job_head(job_idx)
            rotated = pygame.transform.rotate(head, angle)
            self.screen.blit(rotated,
                (sx - rotated.get_width() // 2,
                 sy - rotated.get_height() // 2 - 4))

            # Name tag
            font = self.renderer._get_font("consolas", 12, bold=True)
            ntxt = font.render(name, True, (255, 255, 255))
            nout = font.render(name, True, (0, 0, 0))
            self.screen.blit(nout, (sx - ntxt.get_width() // 2 + 1,
                                    sy - 24 + 1))
            self.screen.blit(ntxt, (sx - ntxt.get_width() // 2, sy - 24))

            # Health bar
            bar_w, bar_h = 28, 4
            bx = sx - bar_w // 2
            by = sy + 16
            pygame.draw.rect(self.screen, (30, 30, 30),
                             (bx, by, bar_w, bar_h))
            hp_fill = max(0, min(1, health / 100))
            if hp_fill > 0:
                pygame.draw.rect(self.screen, (210, 70, 70),
                                 (bx, by, int(bar_w * hp_fill), bar_h))

            # Detained / jail indicator
            if detained or in_jail:
                pygame.draw.circle(self.screen, (242, 191, 91),
                                   (sx, sy), 18, 2)

            # Chat bubbles
            bubbles = pdata.get("chat_bubbles", [])
            if bubbles:
                bfont = self.renderer._get_font("consolas", 13)
                y_off = -32
                for text, timer in reversed(bubbles):
                    alpha = min(255, int(255 * timer))
                    rendered = bfont.render(text, True, (20, 20, 30))
                    tw, th = rendered.get_size()
                    pad_x, pad_y = 8, 4
                    bw = tw + pad_x * 2
                    bh = th + pad_y * 2
                    bbx = sx - bw // 2
                    bby = sy + y_off - bh

                    bsurf = pygame.Surface((bw, bh + 6), pygame.SRCALPHA)
                    pygame.draw.rect(bsurf, (255, 255, 255, alpha),
                                     (0, 0, bw, bh), border_radius=6)
                    pygame.draw.polygon(bsurf, (255, 255, 255, alpha), [
                        (bw // 2 - 4, bh),
                        (bw // 2 + 4, bh),
                        (bw // 2, bh + 5)])
                    self.screen.blit(bsurf, (bbx, bby))

                    tsurf = rendered.copy()
                    tsurf.set_alpha(alpha)
                    self.screen.blit(tsurf, (bbx + pad_x, bby + pad_y))
                    y_off -= bh + 4
