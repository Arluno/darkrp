"""
Procedural texture generator — creates all tile PNGs at startup.
"""
import os
import pygame
from game.settings import TILE_SIZE, JOB_OUTFITS

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "textures")


def _ensure_dir():
    os.makedirs(ASSET_DIR, exist_ok=True)


def _save(surface: pygame.Surface, name: str):
    pygame.image.save(surface, os.path.join(ASSET_DIR, name))


def _make_grass():
    """Green grass tile with subtle variation."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((58, 120, 50))
    import random
    rng = random.Random(42)
    for _ in range(40):
        x = rng.randint(0, TILE_SIZE - 1)
        y = rng.randint(0, TILE_SIZE - 1)
        shade = rng.randint(-15, 15)
        s.set_at((x, y), (58 + shade, 120 + shade, 50 + shade))
    _save(s, "grass.png")


def _make_road():
    """Dark asphalt road tile."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((70, 70, 75))
    import random
    rng = random.Random(99)
    for _ in range(25):
        x = rng.randint(0, TILE_SIZE - 1)
        y = rng.randint(0, TILE_SIZE - 1)
        shade = rng.randint(-5, 5)
        s.set_at((x, y), (70 + shade, 70 + shade, 75 + shade))
    _save(s, "road.png")


def _make_sidewalk():
    """Light concrete sidewalk."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((180, 175, 165))
    import random
    rng = random.Random(55)
    for _ in range(20):
        x = rng.randint(0, TILE_SIZE - 1)
        y = rng.randint(0, TILE_SIZE - 1)
        shade = rng.randint(-8, 8)
        s.set_at((x, y), (180 + shade, 175 + shade, 165 + shade))
    # grid lines
    for i in range(0, TILE_SIZE, TILE_SIZE // 2):
        pygame.draw.line(s, (160, 155, 145), (i, 0), (i, TILE_SIZE - 1))
        pygame.draw.line(s, (160, 155, 145), (0, i), (TILE_SIZE - 1, i))
    _save(s, "sidewalk.png")


def _make_wood_floor():
    """Interior wood floor."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((160, 120, 80))
    import random
    rng = random.Random(77)
    plank_h = TILE_SIZE // 4
    for i in range(4):
        y = i * plank_h
        shade = rng.randint(-12, 12)
        pygame.draw.rect(s, (160 + shade, 120 + shade, 80 + shade), (0, y, TILE_SIZE, plank_h))
        pygame.draw.line(s, (130, 95, 60), (0, y), (TILE_SIZE, y))
    _save(s, "wood_floor.png")


def _make_tile_floor():
    """Interior tile floor (kitchen/bathroom style)."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((210, 210, 215))
    half = TILE_SIZE // 2
    pygame.draw.rect(s, (200, 200, 205), (0, 0, half, half))
    pygame.draw.rect(s, (220, 220, 225), (half, 0, half, half))
    pygame.draw.rect(s, (220, 220, 225), (0, half, half, half))
    pygame.draw.rect(s, (200, 200, 205), (half, half, half, half))
    # grout lines
    pygame.draw.line(s, (170, 170, 175), (half, 0), (half, TILE_SIZE))
    pygame.draw.line(s, (170, 170, 175), (0, half), (TILE_SIZE, half))
    _save(s, "tile_floor.png")


def _make_wall(name, color):
    """Generic wall tile."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill(color)
    # brick pattern
    brick_h = TILE_SIZE // 4
    brick_w = TILE_SIZE // 2
    import random
    rng = random.Random(hash(name))
    for row in range(4):
        offset = (brick_w // 2) if row % 2 else 0
        for col in range(-1, 3):
            x = col * brick_w + offset
            y = row * brick_h
            shade = rng.randint(-10, 10)
            c = (min(255, max(0, color[0] + shade)),
                 min(255, max(0, color[1] + shade)),
                 min(255, max(0, color[2] + shade)))
            pygame.draw.rect(s, c, (x + 1, y + 1, brick_w - 2, brick_h - 2))
    _save(s, name)


def _make_roof():
    """Dark roof tile."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((90, 60, 55))
    import random
    rng = random.Random(33)
    for y in range(0, TILE_SIZE, 4):
        shade = rng.randint(-8, 8)
        pygame.draw.rect(s, (90 + shade, 60 + shade, 55 + shade), (0, y, TILE_SIZE, 4))
    _save(s, "roof.png")


def _make_door():
    """Door tile — brown door filling the full tile."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    # door frame
    pygame.draw.rect(s, (100, 70, 40), (0, 0, TILE_SIZE, TILE_SIZE))
    # door panel
    pygame.draw.rect(s, (140, 95, 55), (2, 2, TILE_SIZE - 4, TILE_SIZE - 4))
    # handle
    pygame.draw.circle(s, (200, 180, 50), (TILE_SIZE - 6, TILE_SIZE // 2), 2)
    _save(s, "door.png")


def _make_jail_bars():
    """Jail bars tile with vertical steel bars."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (70, 75, 85), (0, 0, TILE_SIZE, TILE_SIZE))
    pygame.draw.rect(s, (55, 60, 68), (0, 0, TILE_SIZE, 4))
    pygame.draw.rect(s, (55, 60, 68), (0, TILE_SIZE - 4, TILE_SIZE, 4))
    for x in (6, 12, 18, 24):
        pygame.draw.rect(s, (170, 176, 188), (x, 0, 3, TILE_SIZE))
        pygame.draw.rect(s, (120, 126, 138), (x + 1, 0, 1, TILE_SIZE))
    _save(s, "jail_bars.png")


def _make_jail_door():
    """Jail door tile with barred window and lock plate."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (90, 95, 105), (0, 0, TILE_SIZE, TILE_SIZE))
    pygame.draw.rect(s, (120, 126, 138), (2, 2, TILE_SIZE - 4, TILE_SIZE - 4), 1)
    pygame.draw.rect(s, (62, 66, 74), (8, 7, 16, 10))
    for x in (10, 14, 18, 22):
        pygame.draw.rect(s, (165, 171, 183), (x, 7, 2, 10))
    pygame.draw.rect(s, (188, 154, 70), (24, 16, 4, 6), border_radius=1)
    _save(s, "jail_door.png")


def _make_player():
    """Simple top-down player sprite."""
    size = 32
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    # body
    pygame.draw.circle(s, (50, 100, 200), (size // 2, size // 2), 10)
    # head
    pygame.draw.circle(s, (220, 185, 155), (size // 2, size // 2 - 4), 6)
    # direction indicator (small triangle pointing up)
    pygame.draw.polygon(s, (255, 255, 255), [
        (size // 2, 2),
        (size // 2 - 4, 10),
        (size // 2 + 4, 10),
    ])
    _save(s, "player.png")


def _shade(color, amount):
    return (
        max(0, min(255, color[0] + amount)),
        max(0, min(255, color[1] + amount)),
        max(0, min(255, color[2] + amount)),
    )


def _draw_hat(surface, hat):
    if not hat:
        return
    htype = hat.get("type", "cap")
    hcol = hat.get("color", (70, 70, 80))
    accent = hat.get("accent", (240, 240, 240))
    if htype == "police":
        pygame.draw.rect(surface, hcol, (10, 2, 12, 4), border_radius=2)
        pygame.draw.rect(surface, _shade(hcol, -15), (11, 6, 10, 2), border_radius=1)
        pygame.draw.rect(surface, (235, 215, 80), (15, 3, 2, 2))
    elif htype == "chef":
        pygame.draw.ellipse(surface, hcol, (9, 0, 14, 7))
        pygame.draw.rect(surface, _shade(hcol, -10), (11, 5, 10, 2), border_radius=1)
    elif htype == "top":
        pygame.draw.rect(surface, hcol, (12, 1, 8, 6))
        pygame.draw.rect(surface, _shade(hcol, 10), (10, 6, 12, 2))
    elif htype == "beanie":
        pygame.draw.ellipse(surface, hcol, (10, 2, 12, 6))
    elif htype == "fedora":
        pygame.draw.ellipse(surface, _shade(hcol, 8), (9, 5, 14, 3))
        pygame.draw.rect(surface, hcol, (11, 1, 10, 5))
    else:  # cap
        pygame.draw.ellipse(surface, hcol, (10, 2, 12, 5))
        pygame.draw.rect(surface, _shade(hcol, -8), (12, 6, 8, 2), border_radius=1)
        pygame.draw.rect(surface, accent, (15, 3, 2, 1))


def _make_job_outfit_textures():
    """Generate PNG body/head textures for each job outfit."""
    skin = (220, 185, 155)
    for i, outfit in enumerate(JOB_OUTFITS):
        clothes = outfit.get("clothes", (220, 220, 220))
        hat = outfit.get("hat")

        # Body
        b = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        b.fill((0, 0, 0, 0))
        pygame.draw.ellipse(b, _shade(clothes, -20), (8, 15, 16, 12))
        pygame.draw.ellipse(b, clothes, (7, 10, 18, 12))
        pygame.draw.circle(b, _shade(clothes, 8), (9, 16), 3)
        pygame.draw.circle(b, _shade(clothes, 8), (23, 16), 3)
        _save(b, f"player_body_{i}.png")

        # Head (rotatable)
        h = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        h.fill((0, 0, 0, 0))
        pygame.draw.circle(h, skin, (16, 10), 6)
        pygame.draw.circle(h, (180, 145, 120), (16, 10), 6, 1)
        if i == 0:
            # Citizen head: bald scalp highlight.
            pygame.draw.circle(h, (245, 220, 190), (16, 6), 2)
        else:
            pygame.draw.polygon(h, (250, 250, 250), [(16, 2), (13, 6), (19, 6)])
        _draw_hat(h, hat)
        _save(h, f"player_head_{i}.png")


def _make_water():
    """Water tile."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((40, 90, 180))
    import random
    rng = random.Random(88)
    for _ in range(15):
        x = rng.randint(0, TILE_SIZE - 4)
        y = rng.randint(0, TILE_SIZE - 1)
        pygame.draw.line(s, (70, 120, 210), (x, y), (x + 3, y))
    _save(s, "water.png")


def _make_crosswalk():
    """Zebra crossing — white stripes on road (horizontal stripes for N-S crossing)."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((70, 70, 75))
    stripe_h = 4
    gap = 4
    y = 2
    while y + stripe_h <= TILE_SIZE:
        pygame.draw.rect(s, (235, 235, 235), (4, y, TILE_SIZE - 8, stripe_h))
        y += stripe_h + gap
    _save(s, "crosswalk.png")


def _make_crosswalk_h():
    """Zebra crossing — vertical stripes for E-W crossing."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((70, 70, 75))
    stripe_w = 4
    gap = 4
    x = 2
    while x + stripe_w <= TILE_SIZE:
        pygame.draw.rect(s, (235, 235, 235), (x, 4, stripe_w, TILE_SIZE - 8))
        x += stripe_w + gap
    _save(s, "crosswalk_h.png")


def _make_roof_color(name, color):
    """Generic colored roof tile."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill(color)
    import random
    rng = random.Random(hash(name))
    for y in range(0, TILE_SIZE, 4):
        shade = rng.randint(-6, 6)
        c = tuple(max(0, min(255, color[i] + shade)) for i in range(3))
        pygame.draw.rect(s, c, (0, y, TILE_SIZE, 4))
    _save(s, name)


def _sign_base():
    """Create sign tile base — sidewalk background with wooden post."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE))
    s.fill((180, 175, 165))
    for i in range(0, TILE_SIZE, TILE_SIZE // 2):
        pygame.draw.line(s, (160, 155, 145), (i, 0), (i, TILE_SIZE - 1))
        pygame.draw.line(s, (160, 155, 145), (0, i), (TILE_SIZE - 1, i))
    cx = TILE_SIZE // 2
    pygame.draw.rect(s, (100, 70, 40), (cx - 1, TILE_SIZE // 2, 3, TILE_SIZE // 2))
    return s


def _sign_board(s, bg_color):
    """Draw a sign board on a sign base, return (bx, by, bw, bh, cx, cy)."""
    bw, bh = 22, 14
    bx = TILE_SIZE // 2 - bw // 2
    by = TILE_SIZE // 2 - bh
    pygame.draw.rect(s, (30, 30, 30), (bx - 1, by - 1, bw + 2, bh + 2))
    pygame.draw.rect(s, bg_color, (bx, by, bw, bh))
    return bx, by, bw, bh, bx + bw // 2, by + bh // 2


def _make_sign_police():
    s = _sign_base()
    bx, by, bw, bh, cx, cy = _sign_board(s, (40, 70, 170))
    pygame.draw.polygon(s, (255, 255, 255), [
        (cx - 4, cy - 5), (cx + 4, cy - 5),
        (cx + 4, cy + 1), (cx, cy + 5), (cx - 4, cy + 1)
    ])
    _save(s, "sign_police.png")


def _make_sign_hospital():
    s = _sign_base()
    bx, by, bw, bh, cx, cy = _sign_board(s, (240, 240, 245))
    pygame.draw.rect(s, (200, 40, 40), (cx - 1, cy - 4, 3, 9))
    pygame.draw.rect(s, (200, 40, 40), (cx - 4, cy - 1, 9, 3))
    _save(s, "sign_hospital.png")


def _make_sign_mayor():
    s = _sign_base()
    bx, by, bw, bh, cx, cy = _sign_board(s, (140, 45, 50))
    pygame.draw.polygon(s, (220, 190, 50), [
        (cx, cy - 5), (cx + 2, cy - 1), (cx + 5, cy),
        (cx + 2, cy + 2), (cx + 3, cy + 5),
        (cx, cy + 3), (cx - 3, cy + 5),
        (cx - 2, cy + 2), (cx - 5, cy), (cx - 2, cy - 1)
    ])
    _save(s, "sign_mayor.png")


def _make_sign_bank():
    s = _sign_base()
    bx, by, bw, bh, cx, cy = _sign_board(s, (40, 100, 55))
    pygame.draw.rect(s, (220, 200, 50), (cx - 4, cy - 4, 2, 8))
    pygame.draw.rect(s, (220, 200, 50), (cx + 2, cy - 4, 2, 8))
    pygame.draw.rect(s, (220, 200, 50), (cx - 5, cy - 5, 10, 2))
    pygame.draw.rect(s, (220, 200, 50), (cx - 5, cy + 3, 10, 2))
    _save(s, "sign_bank.png")


def _make_sign_gun():
    s = _sign_base()
    bx, by, bw, bh, cx, cy = _sign_board(s, (60, 60, 65))
    pygame.draw.circle(s, (255, 80, 80), (cx, cy), 4, 1)
    pygame.draw.line(s, (255, 80, 80), (cx, cy - 5), (cx, cy + 5), 1)
    pygame.draw.line(s, (255, 80, 80), (cx - 5, cy), (cx + 5, cy), 1)
    _save(s, "sign_gun.png")


def _make_sign_garage():
    s = _sign_base()
    bx, by, bw, bh, cx, cy = _sign_board(s, (200, 130, 40))
    pygame.draw.line(s, (255, 230, 80), (cx - 4, cy - 4), (cx + 4, cy + 4), 2)
    pygame.draw.circle(s, (255, 230, 80), (cx - 4, cy - 4), 2)
    pygame.draw.circle(s, (255, 230, 80), (cx + 4, cy + 4), 2)
    _save(s, "sign_garage.png")


def _make_sign_apt():
    s = _sign_base()
    bx, by, bw, bh, cx, cy = _sign_board(s, (120, 85, 55))
    pygame.draw.polygon(s, (255, 255, 255), [
        (cx, cy - 5), (cx - 5, cy - 1), (cx + 5, cy - 1)
    ])
    pygame.draw.rect(s, (255, 255, 255), (cx - 3, cy - 1, 6, 6))
    _save(s, "sign_apt.png")


def _make_sign_grocery():
    s = _sign_base()
    bx, by, bw, bh, cx, cy = _sign_board(s, (50, 140, 60))
    pygame.draw.rect(s, (255, 255, 255), (cx - 4, cy - 2, 8, 5))
    pygame.draw.line(s, (255, 255, 255), (cx - 5, cy - 3), (cx - 4, cy - 2), 2)
    pygame.draw.circle(s, (255, 255, 255), (cx - 2, cy + 5), 1)
    pygame.draw.circle(s, (255, 255, 255), (cx + 2, cy + 5), 1)
    _save(s, "sign_grocery.png")


# ── Furniture textures ──

def _make_furn_table():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (140, 95, 55), (4, 6, 24, 20))
    pygame.draw.rect(s, (120, 80, 45), (4, 6, 24, 20), 1)
    _save(s, "furn_table.png")


def _make_furn_chair():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (130, 85, 50), (8, 10, 16, 16))
    pygame.draw.rect(s, (110, 70, 40), (8, 10, 16, 4))
    _save(s, "furn_chair.png")


def _make_furn_bed():
    """Bed top half (pillow end)."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (80, 60, 45), (2, 0, 28, TILE_SIZE))  # frame
    pygame.draw.rect(s, (200, 210, 230), (4, 2, 24, TILE_SIZE - 2))  # sheet
    pygame.draw.rect(s, (230, 230, 240), (6, 4, 20, 10))  # pillow
    _save(s, "furn_bed_top.png")


def _make_furn_bed_bot():
    """Bed bottom half (foot end)."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (80, 60, 45), (2, 0, 28, TILE_SIZE))  # frame
    pygame.draw.rect(s, (200, 210, 230), (4, 0, 24, TILE_SIZE - 2))  # sheet
    pygame.draw.rect(s, (80, 60, 45), (2, TILE_SIZE - 3, 28, 3))  # footboard
    _save(s, "furn_bed_bot.png")


def _make_furn_shelf():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (110, 75, 45), (4, 2, 24, 28))  # frame
    for y in [2, 10, 18, 26]:
        pygame.draw.rect(s, (90, 60, 35), (4, y, 24, 2))  # shelves
    # books
    for x, c in [(7, (180, 50, 50)), (11, (50, 50, 180)), (15, (50, 150, 50)), (19, (180, 150, 50))]:
        pygame.draw.rect(s, c, (x, 12, 3, 6))
    _save(s, "furn_shelf.png")


def _make_furn_counter():
    """Counter — seamless edges so they connect when placed side by side."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (170, 170, 175), (0, 8, TILE_SIZE, 18))  # body full width
    pygame.draw.rect(s, (190, 190, 195), (0, 8, TILE_SIZE, 4))   # top surface
    pygame.draw.line(s, (140, 140, 145), (0, 8), (TILE_SIZE, 8))  # top edge
    pygame.draw.line(s, (140, 140, 145), (0, 25), (TILE_SIZE, 25))  # bottom edge
    _save(s, "furn_counter.png")


def _make_furn_couch():
    """Couch left half."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (80, 60, 120), (2, 6, TILE_SIZE - 2, 22))  # base
    pygame.draw.rect(s, (100, 80, 150), (4, 8, TILE_SIZE - 4, 16))  # cushion
    pygame.draw.rect(s, (70, 50, 110), (2, 6, TILE_SIZE - 2, 4))    # back
    pygame.draw.rect(s, (70, 50, 110), (2, 6, 4, 22))  # left arm
    _save(s, "furn_couch_l.png")


def _make_furn_couch_r():
    """Couch right half."""
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (80, 60, 120), (0, 6, TILE_SIZE - 2, 22))  # base
    pygame.draw.rect(s, (100, 80, 150), (0, 8, TILE_SIZE - 4, 16))  # cushion
    pygame.draw.rect(s, (70, 50, 110), (0, 6, TILE_SIZE - 2, 4))    # back
    pygame.draw.rect(s, (70, 50, 110), (TILE_SIZE - 6, 6, 4, 22))  # right arm
    _save(s, "furn_couch_r.png")


def _make_furn_fridge():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (220, 225, 230), (6, 2, 20, 28))
    pygame.draw.rect(s, (200, 205, 210), (6, 2, 20, 28), 1)
    pygame.draw.line(s, (180, 185, 190), (6, 16), (26, 16), 1)  # split
    pygame.draw.rect(s, (160, 165, 170), (22, 8, 2, 5))  # handle top
    pygame.draw.rect(s, (160, 165, 170), (22, 19, 2, 5))  # handle bot
    _save(s, "furn_fridge.png")


def _make_furn_lamp():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    cx, cy = TILE_SIZE // 2, TILE_SIZE // 2
    pygame.draw.circle(s, (255, 240, 140, 80), (cx, cy), 10)  # glow
    pygame.draw.circle(s, (255, 230, 100), (cx, cy), 5)
    pygame.draw.rect(s, (80, 60, 40), (cx - 1, cy + 5, 3, 8))  # post
    _save(s, "furn_lamp.png")


# ── Inventory item textures ──

def _make_item_food():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    # Bread loaf
    pygame.draw.ellipse(s, (185, 120, 70), (5, 10, 22, 13))
    pygame.draw.ellipse(s, (155, 95, 55), (5, 10, 22, 13), 1)
    pygame.draw.line(s, (215, 165, 110), (10, 13), (10, 20), 1)
    pygame.draw.line(s, (215, 165, 110), (16, 12), (16, 21), 1)
    pygame.draw.line(s, (215, 165, 110), (22, 13), (22, 20), 1)
    _save(s, "item_food.png")


def _make_item_water():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    # Bottle
    pygame.draw.rect(s, (85, 175, 230), (11, 8, 10, 18), border_radius=3)
    pygame.draw.rect(s, (60, 130, 190), (11, 8, 10, 18), 1, border_radius=3)
    pygame.draw.rect(s, (70, 70, 90), (13, 5, 6, 3), border_radius=1)
    pygame.draw.rect(s, (180, 230, 255), (13, 11, 2, 11))
    _save(s, "item_water.png")


def _make_item_medkit():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (230, 230, 235), (6, 9, 20, 15), border_radius=3)
    pygame.draw.rect(s, (180, 180, 190), (6, 9, 20, 15), 1, border_radius=3)
    pygame.draw.rect(s, (205, 60, 60), (14, 11, 4, 11))
    pygame.draw.rect(s, (205, 60, 60), (11, 14, 11, 4))
    _save(s, "item_medkit.png")


def _make_item_toolkit():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (105, 110, 120), (6, 12, 20, 12), border_radius=2)
    pygame.draw.rect(s, (70, 75, 85), (6, 12, 20, 12), 1, border_radius=2)
    pygame.draw.rect(s, (130, 135, 145), (12, 9, 8, 4), border_radius=2)
    pygame.draw.line(s, (220, 185, 70), (10, 18), (22, 18), 2)
    _save(s, "item_toolkit.png")


def _make_item_metal():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (160, 165, 170), (7, 11, 18, 11), border_radius=2)
    pygame.draw.rect(s, (120, 125, 130), (7, 11, 18, 11), 1, border_radius=2)
    pygame.draw.line(s, (210, 215, 220), (9, 13), (23, 13), 1)
    pygame.draw.line(s, (210, 215, 220), (9, 16), (23, 16), 1)
    _save(s, "item_metal.png")


def _make_item_soda():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (230, 105, 80), (11, 7, 10, 18), border_radius=3)
    pygame.draw.rect(s, (180, 70, 55), (11, 7, 10, 18), 1, border_radius=3)
    pygame.draw.rect(s, (210, 210, 220), (13, 5, 6, 2))
    pygame.draw.rect(s, (255, 230, 210), (14, 10, 2, 11))
    _save(s, "item_soda.png")


def _make_item_bandage():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (228, 225, 205), (7, 12, 18, 8), border_radius=4)
    pygame.draw.rect(s, (185, 180, 160), (7, 12, 18, 8), 1, border_radius=4)
    pygame.draw.rect(s, (230, 210, 160), (14, 13, 4, 6), border_radius=1)
    _save(s, "item_bandage.png")


def _make_item_battery():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (100, 190, 80), (10, 8, 12, 17), border_radius=2)
    pygame.draw.rect(s, (70, 130, 60), (10, 8, 12, 17), 1, border_radius=2)
    pygame.draw.rect(s, (230, 230, 235), (13, 6, 6, 2))
    pygame.draw.rect(s, (35, 35, 40), (12, 14, 8, 1))
    _save(s, "item_battery.png")


def _make_item_lockpick():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.line(s, (180, 185, 195), (9, 22), (21, 10), 3)
    pygame.draw.line(s, (120, 125, 135), (12, 24), (23, 13), 1)
    pygame.draw.circle(s, (180, 185, 195), (8, 23), 2)
    _save(s, "item_lockpick.png")


def _make_item_pistol():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (70, 75, 85), (8, 12, 16, 5), border_radius=1)
    pygame.draw.rect(s, (50, 55, 65), (20, 12, 5, 2), border_radius=1)
    pygame.draw.polygon(s, (70, 75, 85), [(12, 17), (18, 17), (16, 24), (10, 24)])
    _save(s, "item_pistol.png")


def _make_item_shotgun():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    pygame.draw.rect(s, (90, 80, 60), (5, 15, 18, 3), border_radius=1)
    pygame.draw.rect(s, (55, 60, 70), (16, 13, 10, 3), border_radius=1)
    pygame.draw.rect(s, (95, 85, 65), (9, 16, 3, 7), border_radius=1)
    _save(s, "item_shotgun.png")


def _make_item_pistol_ammo():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    for x in (10, 14, 18):
        pygame.draw.rect(s, (220, 180, 90), (x, 10, 3, 10), border_radius=1)
        pygame.draw.rect(s, (165, 130, 65), (x, 18, 3, 2), border_radius=1)
    _save(s, "item_pistol_ammo.png")


def _make_item_shells():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    for x in (11, 17):
        pygame.draw.rect(s, (210, 55, 55), (x, 10, 4, 10), border_radius=1)
        pygame.draw.rect(s, (215, 190, 95), (x, 18, 4, 2), border_radius=1)
    _save(s, "item_shells.png")


def _make_item_cuffs():
    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    # left cuff
    pygame.draw.circle(s, (155, 160, 170), (11, 16), 5, 2)
    # right cuff
    pygame.draw.circle(s, (155, 160, 170), (21, 16), 5, 2)
    # chain
    pygame.draw.line(s, (175, 180, 190), (15, 16), (17, 16), 2)
    pygame.draw.circle(s, (200, 205, 215), (11, 16), 1)
    pygame.draw.circle(s, (200, 205, 215), (21, 16), 1)
    _save(s, "item_cuffs.png")


def generate_all():
    """Generate every texture PNG. Call once at startup."""
    _ensure_dir()
    _make_grass()
    _make_road()
    _make_sidewalk()
    _make_wood_floor()
    _make_tile_floor()
    _make_wall("wall_brick.png", (150, 75, 60))
    _make_wall("wall_white.png", (230, 225, 220))
    _make_wall("wall_gray.png", (140, 140, 145))
    _make_wall("wall_police.png", (55, 75, 165))
    _make_wall("wall_hospital.png", (240, 242, 245))
    _make_wall("wall_mayor.png", (135, 50, 50))
    _make_wall("wall_bank.png", (45, 105, 60))
    _make_roof()
    _make_roof_color("roof_police.png", (40, 55, 120))
    _make_roof_color("roof_hospital.png", (180, 185, 190))
    _make_roof_color("roof_mayor.png", (100, 38, 40))
    _make_roof_color("roof_bank.png", (35, 75, 45))
    _make_door()
    _make_jail_bars()
    _make_jail_door()
    _make_player()
    _make_job_outfit_textures()
    _make_water()
    _make_crosswalk()
    _make_crosswalk_h()
    _make_sign_police()
    _make_sign_hospital()
    _make_sign_mayor()
    _make_sign_bank()
    _make_sign_gun()
    _make_sign_garage()
    _make_sign_apt()
    _make_sign_grocery()
    _make_furn_table()
    _make_furn_chair()
    _make_furn_bed()
    _make_furn_bed_bot()
    _make_furn_shelf()
    _make_furn_counter()
    _make_furn_couch()
    _make_furn_couch_r()
    _make_furn_fridge()
    _make_furn_lamp()
    _make_item_food()
    _make_item_water()
    _make_item_medkit()
    _make_item_toolkit()
    _make_item_metal()
    _make_item_soda()
    _make_item_bandage()
    _make_item_battery()
    _make_item_lockpick()
    _make_item_pistol()
    _make_item_shotgun()
    _make_item_pistol_ammo()
    _make_item_shells()
    _make_item_cuffs()
    print("[textures] All textures generated.")


def load_textures() -> dict[str, pygame.Surface]:
    """Load all PNGs from the asset dir into a dict keyed by name (no ext)."""
    textures = {}
    for fname in os.listdir(ASSET_DIR):
        if fname.endswith(".png"):
            key = fname.replace(".png", "")
            textures[key] = pygame.image.load(os.path.join(ASSET_DIR, fname)).convert_alpha()
    return textures
