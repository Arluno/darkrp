# ── Game Settings ──

# Window
SCREEN_WIDTH = 0   # set at runtime (fullscreen)
SCREEN_HEIGHT = 0  # set at runtime (fullscreen)
FPS = 60
TITLE = "DarkRP 2D"

# Tiles
TILE_SIZE = 32

# Player
PLAYER_SPEED = 3.0
PLAYER_SIZE = 24
STARTING_MONEY = 5000

# Colors
COLOR_BG = (40, 40, 40)

# Network (future multiplayer)
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 7777
TICK_RATE = 20

# Furniture catalog: (name, cost, [(dx, dy, tile_id), ...])
FURNITURE = [
    ("Table",    0, [(0, 0, 30)]),
    ("Chair",    0, [(0, 0, 31)]),
    ("Bed",      0, [(0, 0, 38), (0, 1, 39)]),
    ("Shelf",    0, [(0, 0, 33)]),
    ("Counter",  0, [(0, 0, 34)]),
    ("Couch",    0, [(0, 0, 40), (1, 0, 41)]),
    ("Fridge",   0, [(0, 0, 36)]),
    ("Lamp",     0, [(0, 0, 37)]),
]

# Jobs: (name, salary_per_tick, color)
JOBS = [
    ("Citizen",      0,   (180, 180, 180)),
    ("Police Officer", 15, (70, 130, 220)),
    ("Medic",        12,  (220, 60, 60)),
    ("Mayor",        20,  (180, 140, 50)),
    ("Gun Dealer",   10,  (200, 120, 50)),
    ("Chef",          8,  (100, 180, 80)),
    ("Thief",        10,  (140, 60, 60)),
    ("Banker",       14,  (50, 160, 100)),
]
# Team loadouts aligned with JOBS order: [(item_id, count), ...]
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
# Outfit definitions aligned with JOBS order
JOB_OUTFITS = [
    {"clothes": (235, 235, 235), "hat": None},  # Citizen
    {"clothes": (70, 120, 210), "hat": {"type": "police", "color": (35, 60, 120)}},  # Police Officer
    {"clothes": (210, 70, 70), "hat": {"type": "cap", "color": (220, 220, 220), "accent": (200, 50, 50)}},  # Medic
    {"clothes": (175, 140, 65), "hat": {"type": "top", "color": (40, 40, 40)}},  # Mayor
    {"clothes": (165, 95, 55), "hat": {"type": "beanie", "color": (60, 60, 65)}},  # Gun Dealer
    {"clothes": (235, 235, 235), "hat": {"type": "chef", "color": (245, 245, 245)}},  # Chef
    {"clothes": (120, 55, 55), "hat": {"type": "beanie", "color": (45, 45, 50)}},  # Thief
    {"clothes": (55, 150, 105), "hat": {"type": "fedora", "color": (50, 60, 70)}},  # Banker
]
# Maximum players per job index (None = unlimited)
JOB_MAX_PLAYERS = [None, 3, 2, 1, 2, 2, 2, 1]
SALARY_INTERVAL = 30000  # ms between paychecks

# Survival rates
HUNGER_DRAIN_PER_MS = 0.0007
THIRST_DRAIN_PER_MS = 0.0010
STARVATION_DAMAGE_PER_MS = 0.0012

# Inventory / hotbar
HOTBAR_SIZE = 5
INVENTORY_SIZE = 20

# Item definitions for inventory and hotbar UI
ITEM_DEFS = {
    "food": {
        "name": "Food",
        "color": (200, 140, 70),
        "tex": "item_food",
        "use": {"type": "consume", "hunger": 28},
    },
    "water": {
        "name": "Water",
        "color": (70, 150, 220),
        "tex": "item_water",
        "use": {"type": "consume", "thirst": 34},
    },
    "medkit": {
        "name": "Medkit",
        "color": (210, 70, 70),
        "tex": "item_medkit",
        "use": {"type": "consume", "hunger": 12, "thirst": 12, "health": 35},
    },
    "toolkit": {
        "name": "Toolkit",
        "color": (140, 140, 150),
        "tex": "item_toolkit",
        "use": {"type": "toolkit"},
    },
    "metal": {
        "name": "Metal",
        "color": (170, 170, 180),
        "tex": "item_metal",
        "use": {"type": "sell", "money": 60},
    },
    "soda": {
        "name": "Soda",
        "color": (235, 120, 90),
        "tex": "item_soda",
        "use": {"type": "consume", "thirst": 22, "hunger": 6},
    },
    "bandage": {
        "name": "Bandage",
        "color": (220, 220, 205),
        "tex": "item_bandage",
        "use": {"type": "consume", "hunger": 10, "thirst": 6, "health": 18},
    },
    "battery": {
        "name": "Battery",
        "color": (120, 210, 90),
        "tex": "item_battery",
        "use": {"type": "sell", "money": 35},
    },
    "lockpick": {
        "name": "Lockpick",
        "color": (180, 180, 185),
        "tex": "item_lockpick",
        "use": {"type": "lockpick"},
    },
    "cuffs": {
        "name": "Cuffs",
        "color": (150, 150, 160),
        "tex": "item_cuffs",
        "use": {"type": "cuffs"},
    },
    "pistol": {
        "name": "Pistol",
        "color": (70, 70, 80),
        "tex": "item_pistol",
        "use": {
            "type": "gun",
            "ammo": "pistol_ammo",
            "speed": 14.0,
            "projectile_life": 600,
            "cooldown": 170,
            "spread": 2.0,
            "pellets": 1,
        },
    },
    "shotgun": {
        "name": "Shotgun",
        "color": (95, 80, 60),
        "tex": "item_shotgun",
        "use": {
            "type": "gun",
            "ammo": "shells",
            "speed": 12.0,
            "projectile_life": 430,
            "cooldown": 520,
            "spread": 9.0,
            "pellets": 6,
        },
    },
    "pistol_ammo": {
        "name": "Pistol Ammo",
        "color": (230, 190, 90),
        "tex": "item_pistol_ammo",
    },
    "shells": {
        "name": "Shotgun Shells",
        "color": (220, 60, 60),
        "tex": "item_shells",
    },
}

# Item stacks granted at spawn
STARTING_ITEMS = [
    ("food", 3),
    ("water", 2),
    ("medkit", 1),
    ("pistol", 1),
    ("pistol_ammo", 24),
]
