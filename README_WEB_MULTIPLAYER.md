# DarkRP Web Multiplayer (Render)

This project now includes a web multiplayer port running on FastAPI + WebSocket.
The desktop pygame version is still available via main.py.

## Local Run

1. Install dependencies:

   pip install -r requirements.txt

2. Start server:

   uvicorn server:app --host 0.0.0.0 --port 8000 --reload

3. Open browser:

   http://127.0.0.1:8000

4. Open multiple tabs/devices to test multiplayer.

## Deploy to Render

1. Push repository to GitHub.
2. Create Render Web Service from repo.
3. render.yaml is included and defines build/start commands.
4. After deploy, open your Render URL.

## Controls

- Move: WASD / Arrow keys
- Hotbar select: 1-5
- Use selected item: U
- Drop selected item: Q
- Pickup nearby item: G
- Police detain toggle (cuffs): Y
- Cuff sentence adjust: [ and ] (30s steps, max 10m)
- Buy property near door: E
- Sell owned property near door: F
- Lock/unlock owned property door: L
- Toggle inventory panel: Tab

## Ported Multiplayer Systems

- Job system with slot caps and salary ticks
- Team loadouts
- Hunger, thirst, health simulation
- Item use (consume/sell/toolkit/lockpick/cuffs/guns)
- Hotbar + inventory state sync
- Dropped world items and manual pickup
- Projectiles and player damage
- Police detain/arrest/jail with timer release
- Property buy/sell/lock
- Building/door state replication

## Notes

- This is a web-first multiplayer implementation designed for Render deployment.
- Visual style is simplified compared to pygame, but gameplay systems are server-authoritative.
