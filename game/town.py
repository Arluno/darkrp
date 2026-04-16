"""
Town map builder — lays out the small DarkRP-style town.

Legend (tile IDs from world.py):
  0 = grass, 1 = road, 2 = sidewalk
  3 = wood_floor, 4 = tile_floor
  5 = wall_brick, 6 = wall_white, 7 = wall_gray
  8 = door, 9 = water
"""
from game.world import World, Building
from game.settings import TILE_SIZE

MAP_W = 80
MAP_H = 60


def build_town() -> World:
    world = World(MAP_W, MAP_H)

    # ── 1. Fill everything with grass ──
    # (already default 0)

    # ── 2. Roads (two crossing roads) ──
    # Horizontal road at row 28-31
    for y in range(28, 32):
        for x in range(MAP_W):
            world.set_ground(x, y, 1)
    # Vertical road at col 38-41
    for y in range(MAP_H):
        for x in range(38, 42):
            world.set_ground(x, y, 1)

    # ── 3. Sidewalks along roads (stop at road edges) ──
    # Horizontal sidewalks (along the horizontal road)
    for x in range(MAP_W):
        # Skip where vertical road is (cols 38-41) — those get crosswalks
        if 38 <= x <= 41:
            continue
        for sy in [27, 32]:
            world.set_ground(x, sy, 2)

    # Vertical sidewalks (along the vertical road)
    for y in range(MAP_H):
        # Skip where horizontal road is (rows 28-31) — those get crosswalks
        if 28 <= y <= 31:
            continue
        for sx in [37, 42]:
            world.set_ground(sx, y, 2)

    # ── 3b. Zebra crosswalks at the intersection ──
    # Crossing the horizontal road (north-south, at vertical sidewalk columns)
    for y in range(28, 32):
        world.set_ground(37, y, 10)
        world.set_ground(42, y, 10)
    # Crossing the vertical road (east-west, at horizontal sidewalk rows)
    for x in range(38, 42):
        world.set_ground(x, 27, 11)
        world.set_ground(x, 32, 11)

    # ── 4. Buildings (flush against sidewalks, doors on sidewalk) ──
    # Roads: rows 28-31 (H), cols 38-41 (V)
    # Sidewalks: rows 27,32 (H), cols 37,42 (V)
    # Each gov building has its own wall color + sign tile on sidewalk

    # ═══ TOP-LEFT QUADRANT ═══
    house1 = Building(10, 19, 10, 8, "House 1", price=1500)
    world.add_building(house1, wall_id=7, floor_id=3)
    world.add_door(14, 26, house1)
    world.set_ground(15, 27, 23)
    house1.sign_tx, house1.sign_ty = 15, 27

    house2 = Building(22, 19, 10, 8, "House 2", price=1200)
    world.add_building(house2, wall_id=6, floor_id=3)
    world.add_door(26, 26, house2)
    world.set_ground(27, 27, 23)
    house2.sign_tx, house2.sign_ty = 27, 27

    house3 = Building(29, 10, 8, 7, "House 3", price=800)
    world.add_building(house3, wall_id=6, floor_id=3)
    world.add_door(36, 13, house3)
    world.set_ground(37, 14, 23)
    house3.sign_tx, house3.sign_ty = 37, 14

    # ═══ TOP-RIGHT QUADRANT ═══
    # Police Dept — blue walls
    police = Building(43, 19, 12, 8, "Police Dept", government=True)
    world.add_building(police, wall_id=13, floor_id=4, roof_tex="roof_police")
    world.add_door(43, 22, police)
    world.set_ground(42, 23, 17)  # sign_police on sidewalk
    # Jail block (right side): hallway gate + two cell doors
    for ty in range(20, 26):
        world.set_wall(48, ty, 25)
    world.set_wall(48, 22, 26)

    for ty in range(20, 26):
        world.set_wall(50, ty, 25)
    world.set_wall(50, 21, 26)
    world.set_wall(50, 24, 26)

    for tx in range(51, 54):
        world.set_wall(tx, 23, 25)
    # Jail spawn points (tile coords) used by arrest system
    police.jail_spawns = [(52, 21), (52, 24)]

    # Mayor Office — maroon walls
    mayor = Building(57, 19, 10, 8, "Mayor Office", government=True)
    world.add_building(mayor, wall_id=15, floor_id=4, roof_tex="roof_mayor")
    world.add_door(61, 26, mayor)
    world.set_ground(62, 27, 19)  # sign_mayor on sidewalk

    # ═══ BOTTOM-LEFT QUADRANT ═══
    # Bank — green walls
    bank = Building(10, 33, 12, 8, "Bank", government=True)
    world.add_building(bank, wall_id=16, floor_id=4, roof_tex="roof_bank")
    world.add_door(15, 33, bank)
    world.set_ground(16, 32, 20)  # sign_bank on sidewalk

    house4 = Building(24, 33, 8, 7, "House 4", price=800)
    world.add_building(house4, wall_id=6, floor_id=3)
    world.add_door(27, 33, house4)
    world.set_ground(28, 32, 23)
    house4.sign_tx, house4.sign_ty = 28, 32

    # ═══ BOTTOM-RIGHT QUADRANT ═══
    house5 = Building(43, 33, 10, 8, "House 5", price=1000)
    world.add_building(house5, wall_id=7, floor_id=3)
    world.add_door(47, 33, house5)
    world.set_ground(48, 32, 23)
    house5.sign_tx, house5.sign_ty = 48, 32

    # Hospital — white walls
    hospital = Building(55, 33, 12, 8, "Hospital", government=True)
    world.add_building(hospital, wall_id=14, floor_id=4, roof_tex="roof_hospital")
    world.add_door(60, 33, hospital)
    world.set_ground(61, 32, 18)  # sign_hospital on sidewalk

    # ── 5. Small park with water (pond) ──
    for py in range(45, 49):
        for px in range(15, 22):
            world.set_ground(px, py, 9)
    # grass border already there

    return world
