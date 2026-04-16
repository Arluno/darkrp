const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const statusEl = document.getElementById('status');
const nameEl = document.getElementById('name');
const jobEl = document.getElementById('job');
const statsEl = document.getElementById('stats');
const hotbarEl = document.getElementById('hotbar');
const invEl = document.getElementById('inv');
const lobbyEl = document.getElementById('lobby');
const lobbyNameEl = document.getElementById('lobbyName');
const playBtn = document.getElementById('playBtn');
const playerCountEl = document.getElementById('playerCount');

let inLobby = true;

// ── Tile map (received from server) ──
let tileMap = null; // { w, h, ground:Uint8Array, walls:Uint8Array }

// Tile color palette matching desktop textures.py
const TILE_COLORS = {
  0:  '#3a7832',  // grass
  1:  '#46464b',  // road
  2:  '#b4afa5',  // sidewalk
  3:  '#a07850',  // wood_floor
  4:  '#d2d2d7',  // tile_floor
  5:  '#964b3c',  // wall_brick
  6:  '#e6e1dc',  // wall_white
  7:  '#8c8c91',  // wall_gray
  8:  '#8c5f37',  // door
  9:  '#285ab4',  // water
  10: '#46464b',  // crosswalk (drawn with stripes)
  11: '#46464b',  // crosswalk_h
  13: '#374ba5',  // wall_police
  14: '#f0f2f5',  // wall_hospital
  15: '#873232',  // wall_mayor
  16: '#2d693c',  // wall_bank
  17: '#b4afa5',  // sign (police)
  18: '#b4afa5',  // sign (hospital)
  19: '#b4afa5',  // sign (mayor)
  20: '#b4afa5',  // sign (bank)
  23: '#b4afa5',  // sign (house)
  25: '#464b55',  // jail_bars
  26: '#5a5f69',  // jail_door
};
const WALL_COLORS = { ...TILE_COLORS };

// Pre-render tile canvases for performance
const tileCanvasCache = {};
function getTileCanvas(id, isWall) {
  const key = (isWall ? 'w' : 'g') + id;
  if (tileCanvasCache[key]) return tileCanvasCache[key];
  const c = document.createElement('canvas');
  c.width = 32; c.height = 32;
  const x = c.getContext('2d');
  const color = (isWall ? WALL_COLORS[id] : TILE_COLORS[id]) || '#3a7832';
  x.fillStyle = color;
  x.fillRect(0, 0, 32, 32);

  // Add texture detail
  if (!isWall) {
    if (id === 0) { // grass noise
      x.fillStyle = 'rgba(0,0,0,0.06)';
      for (let i = 0; i < 20; i++) x.fillRect(Math.random()*30, Math.random()*30, 2, 2);
      x.fillStyle = 'rgba(255,255,255,0.05)';
      for (let i = 0; i < 12; i++) x.fillRect(Math.random()*30, Math.random()*30, 2, 1);
    } else if (id === 1) { // road noise
      x.fillStyle = 'rgba(255,255,255,0.04)';
      for (let i = 0; i < 10; i++) x.fillRect(Math.random()*30, Math.random()*30, 2, 2);
    } else if (id === 2 || id === 17 || id === 18 || id === 19 || id === 20 || id === 23) { // sidewalk grid
      x.strokeStyle = 'rgba(0,0,0,0.08)';
      x.lineWidth = 1;
      x.strokeRect(0.5, 0.5, 31, 31);
    } else if (id === 3) { // wood planks
      x.strokeStyle = 'rgba(0,0,0,0.12)';
      x.lineWidth = 1;
      for (let py = 6; py < 32; py += 8) { x.beginPath(); x.moveTo(0,py); x.lineTo(32,py); x.stroke(); }
    } else if (id === 4) { // tile floor checkerboard
      x.fillStyle = 'rgba(0,0,0,0.05)';
      x.fillRect(0, 0, 16, 16); x.fillRect(16, 16, 16, 16);
    } else if (id === 9) { // water waves
      x.strokeStyle = 'rgba(255,255,255,0.2)';
      x.lineWidth = 1;
      for (let i = 0; i < 3; i++) {
        const wy = 8 + i * 10;
        x.beginPath(); x.moveTo(4, wy); x.quadraticCurveTo(16, wy-4, 28, wy); x.stroke();
      }
    } else if (id === 10) { // crosswalk N-S stripes
      x.fillStyle = '#e8e8e8';
      for (let sy = 2; sy < 32; sy += 8) x.fillRect(4, sy, 24, 4);
    } else if (id === 11) { // crosswalk E-W stripes
      x.fillStyle = '#e8e8e8';
      for (let sx = 2; sx < 32; sx += 8) x.fillRect(sx, 4, 4, 24);
    }
  } else {
    // Wall detail — brick pattern
    if ([5,6,7,13,14,15,16].includes(id)) {
      x.strokeStyle = 'rgba(0,0,0,0.15)';
      x.lineWidth = 1;
      for (let row = 0; row < 4; row++) {
        const ry = row * 8;
        x.beginPath(); x.moveTo(0, ry); x.lineTo(32, ry); x.stroke();
        const off = (row % 2) * 16;
        x.beginPath(); x.moveTo(off, ry); x.lineTo(off, ry+8); x.stroke();
        x.beginPath(); x.moveTo(off+16, ry); x.lineTo(off+16, ry+8); x.stroke();
      }
    } else if (id === 8) { // door
      x.fillStyle = '#6b4422';
      x.fillRect(6, 2, 20, 28);
      x.fillStyle = '#c8a84f';
      x.fillRect(20, 14, 4, 4);
    } else if (id === 25) { // jail bars
      x.fillStyle = '#464b55';
      x.fillRect(0,0,32,32);
      x.fillStyle = '#8a8f9a';
      for (let bx = 4; bx < 32; bx += 7) x.fillRect(bx, 0, 2, 32);
    } else if (id === 26) { // jail door
      x.fillStyle = '#5a5f69';
      x.fillRect(0,0,32,32);
      x.fillStyle = '#8a8f9a';
      for (let bx = 6; bx < 26; bx += 6) x.fillRect(bx, 4, 2, 24);
      x.fillStyle = '#c89632';
      x.fillRect(22, 14, 6, 4);
    }
  }
  tileCanvasCache[key] = c;
  return c;
}

// Roof colors
const ROOF_COLORS = {
  'roof': '#5a3c37',
  'roof_police': '#283778',
  'roof_hospital': '#b4b9be',
  'roof_mayor': '#642628',
  'roof_bank': '#234b2d',
};

let ws = null;
let myId = null;
let world = { w: 2560, h: 1920, tile: 32 };
let jobs = [];
let players = {};
let buildings = [];
let droppedItems = [];
let projectiles = [];
let you = {
  health: 100,
  hunger: 100,
  thirst: 100,
  money: 5000,
  job: 0,
  inventory: [],
  hotbar: [],
  selected_hotbar: 0,
  detained: false,
  in_jail: false,
  arrest_remaining: 0,
  cuffs_sentence: 60,
};
let keys = { up: false, down: false, left: false, right: false };
let mouse = { x: 0, y: 0 };
let currentJob = 0;
let invOpen = false;

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    statusEl.textContent = 'Connected';
    send({ type: 'join', name: nameEl.value.trim() || undefined });
  };

  ws.onclose = () => {
    statusEl.textContent = 'Disconnected (retrying...)';
    setTimeout(connect, 1200);
  };

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === 'welcome') {
      myId = msg.id;
      return;
    }
    if (msg.type === 'map') {
      const gStr = msg.ground;
      const wStr = msg.walls;
      const mw = msg.w, mh = msg.h;
      const ga = new Uint8Array(mw * mh);
      const wa = new Uint8Array(mw * mh);
      for (let i = 0; i < ga.length; i++) { ga[i] = gStr.charCodeAt(i) - 48; wa[i] = wStr.charCodeAt(i) - 48; }
      tileMap = { w: mw, h: mh, ground: ga, walls: wa };
      return;
    }
    if (msg.type === 'state') {
      world = msg.world || world;
      players = msg.players || {};
      buildings = msg.buildings || [];
      droppedItems = msg.dropped_items || [];
      projectiles = msg.projectiles || [];
      you = msg.you || you;
      currentJob = Number(you.job || 0);
      renderHud();
      if (Array.isArray(msg.jobs) && msg.jobs.length > 0) {
        if (jobs.length === 0) {
          jobs = msg.jobs;
          jobs.forEach((j, i) => {
            const o = document.createElement('option');
            o.value = String(i);
            o.textContent = j.name;
            jobEl.appendChild(o);
          });
          jobEl.value = String(currentJob);
        }
      }
    }
  };
}

function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
  }
}

function sendAction(action) {
  send({ type: 'action', action });
}

function formatTime(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function renderHud() {
  const jailPart = you.in_jail ? ` | Jail ${formatTime(you.arrest_remaining || 0)}` : '';
  const detainPart = you.detained ? ' | DETAINED' : '';
  statsEl.textContent = `HP ${Math.round(you.health || 0)} | H ${Math.round(you.hunger || 0)} | T ${Math.round(you.thirst || 0)} | $${Math.round(you.money || 0)}${jailPart}${detainPart}`;

  hotbarEl.innerHTML = '';
  const hotbar = Array.isArray(you.hotbar) ? you.hotbar : [];
  for (let i = 0; i < 5; i += 1) {
    const st = hotbar[i];
    const div = document.createElement('div');
    div.className = `slot${i === Number(you.selected_hotbar || 0) ? ' selected' : ''}`;
    if (st) {
      div.textContent = `${i + 1}: ${st.name} x${st.count}`;
    } else {
      div.textContent = `${i + 1}: Empty`;
    }
    hotbarEl.appendChild(div);
  }

  invEl.className = invOpen ? 'open' : '';
  if (invOpen) {
    const lines = [];
    lines.push('Inventory');
    (you.inventory || []).forEach((st, idx) => {
      if (st) {
        lines.push(`${idx + 1}. ${st.name} x${st.count}`);
      }
    });
    if (lines.length === 1) {
      lines.push('Empty');
    }
    lines.push(`Cuff Sentence: ${formatTime(you.cuffs_sentence || 0)}`);
    invEl.textContent = lines.join('\n');
  }
}

nameEl.addEventListener('change', () => {
  send({ type: 'join', name: nameEl.value.trim() || undefined });
});

jobEl.addEventListener('change', () => {
  currentJob = Number(jobEl.value) || 0;
});

window.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    e.preventDefault();
    invOpen = !invOpen;
    renderHud();
    return;
  }
  if (e.key === 'w' || e.key === 'ArrowUp') keys.up = true;
  if (e.key === 's' || e.key === 'ArrowDown') keys.down = true;
  if (e.key === 'a' || e.key === 'ArrowLeft') keys.left = true;
  if (e.key === 'd' || e.key === 'ArrowRight') keys.right = true;

  if (e.key >= '1' && e.key <= '5') {
    you.selected_hotbar = Number(e.key) - 1;
    renderHud();
  }
  if (e.key === 'u' || e.key === 'U') sendAction('use');
  if (e.key === 'q' || e.key === 'Q') sendAction('drop');
  if (e.key === 'g' || e.key === 'G') sendAction('pickup');
  if (e.key === 'y' || e.key === 'Y') sendAction('detain');
  if (e.key === '[') sendAction('sentence_down');
  if (e.key === ']') sendAction('sentence_up');
  if (e.key === 'e' || e.key === 'E') sendAction('buy');
  if (e.key === 'f' || e.key === 'F') sendAction('sell');
  if (e.key === 'l' || e.key === 'L') sendAction('lock');
});

window.addEventListener('keyup', (e) => {
  if (e.key === 'w' || e.key === 'ArrowUp') keys.up = false;
  if (e.key === 's' || e.key === 'ArrowDown') keys.down = false;
  if (e.key === 'a' || e.key === 'ArrowLeft') keys.left = false;
  if (e.key === 'd' || e.key === 'ArrowRight') keys.right = false;
});

window.addEventListener('mousemove', (e) => {
  mouse.x = e.clientX;
  mouse.y = e.clientY;
});

function updateNetworkInput() {
  const me = players[myId];
  let angle = 0;
  if (me) {
    const camX = me.x - canvas.width / 2;
    const camY = me.y - canvas.height / 2;
    const wx = mouse.x + camX;
    const wy = mouse.y + camY;
    angle = Math.atan2(wy - me.y, wx - me.x) * 180 / Math.PI + 90;
  }
  send({ type: 'input', keys, angle, job: currentJob, selected_hotbar: Number(you.selected_hotbar || 0) });
}
setInterval(updateNetworkInput, 50);

function drawWorld(camX, camY) {
  if (!tileMap) return;
  const tile = world.tile || 32;
  const startTX = Math.max(0, Math.floor(camX / tile));
  const startTY = Math.max(0, Math.floor(camY / tile));
  const endTX = Math.min(tileMap.w, Math.ceil((camX + canvas.width) / tile) + 1);
  const endTY = Math.min(tileMap.h, Math.ceil((camY + canvas.height) / tile) + 1);

  // Ground layer
  for (let ty = startTY; ty < endTY; ty++) {
    for (let tx = startTX; tx < endTX; tx++) {
      const gid = tileMap.ground[ty * tileMap.w + tx];
      const sx = tx * tile - camX;
      const sy = ty * tile - camY;
      ctx.drawImage(getTileCanvas(gid, false), sx, sy, tile, tile);
    }
  }

  // Wall layer
  for (let ty = startTY; ty < endTY; ty++) {
    for (let tx = startTX; tx < endTX; tx++) {
      const wid = tileMap.walls[ty * tileMap.w + tx];
      if (wid === 0) continue;
      const sx = tx * tile - camX;
      const sy = ty * tile - camY;
      ctx.drawImage(getTileCanvas(wid, true), sx, sy, tile, tile);
    }
  }
}

function drawRoofs(camX, camY) {
  if (!tileMap) return;
  const tile = world.tile || 32;
  const me = players[myId];
  // Find which building the player is inside (hide its roof)
  let insideId = null;
  if (me) {
    for (const b of buildings) {
      const bx = b.x * tile, by = b.y * tile;
      const bw = b.w * tile, bh = b.h * tile;
      if (me.x >= bx && me.x < bx + bw && me.y >= by && me.y < by + bh) {
        insideId = b.id;
        break;
      }
    }
  }

  for (const b of buildings) {
    if (b.id === insideId) continue;
    const bx = b.x * tile - camX;
    const by = b.y * tile - camY;
    const bw = b.w * tile;
    const bh = b.h * tile;
    // Pick roof color
    let rc = ROOF_COLORS['roof'];
    if (b.id === 'police') rc = ROOF_COLORS['roof_police'];
    else if (b.id === 'hospital') rc = ROOF_COLORS['roof_hospital'];
    else if (b.id === 'mayor') rc = ROOF_COLORS['roof_mayor'];
    else if (b.id === 'bank') rc = ROOF_COLORS['roof_bank'];
    ctx.fillStyle = rc;
    ctx.fillRect(bx, by, bw, bh);
    // Roof strip detail
    ctx.strokeStyle = 'rgba(0,0,0,0.12)';
    ctx.lineWidth = 1;
    for (let ry = by + 6; ry < by + bh; ry += 8) {
      ctx.beginPath(); ctx.moveTo(bx, ry); ctx.lineTo(bx + bw, ry); ctx.stroke();
    }
  }
}

function drawPlayer(p, isMe, camX, camY) {
  const sx = p.x - camX;
  const sy = p.y - camY;
  const job = jobs[p.job] || jobs[0] || { color: '#b4b4b4', name: 'Citizen' };

  ctx.fillStyle = job.color || '#b4b4b4';
  ctx.beginPath();
  ctx.arc(sx, sy, 12, 0, Math.PI * 2);
  ctx.fill();

  const a = ((p.angle || 0) - 90) * Math.PI / 180;
  const hx = sx + Math.cos(a) * 8;
  const hy = sy + Math.sin(a) * 8;
  ctx.fillStyle = '#f2efe7';
  ctx.beginPath();
  ctx.arc(hx, hy, 5, 0, Math.PI * 2);
  ctx.fill();

  ctx.font = '12px Segoe UI';
  ctx.textAlign = 'center';
  ctx.fillStyle = isMe ? '#7ed2ff' : '#ffffff';
  ctx.fillText(p.name || p.id, sx, sy - 18);

  ctx.fillStyle = 'rgba(0,0,0,0.55)';
  ctx.fillRect(sx - 14, sy + 15, 28, 4);
  ctx.fillStyle = '#57df7d';
  ctx.fillRect(sx - 14, sy + 15, Math.max(0, Math.min(28, (p.health || 0) * 0.28)), 4);

  if (p.detained || p.in_jail) {
    ctx.strokeStyle = '#f2bf5b';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(sx, sy, 16, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawBuildings(camX, camY) {
  const tile = world.tile || 32;
  buildings.forEach((b) => {
    const x = b.x * tile - camX;
    const y = b.y * tile - camY;
    const w = b.w * tile;

    // Building name label
    ctx.font = 'bold 13px Segoe UI';
    ctx.textAlign = 'left';
    ctx.fillStyle = '#eaf0ff';
    ctx.strokeStyle = 'rgba(0,0,0,0.5)';
    ctx.lineWidth = 3;
    const owner = b.owner ? ` (${b.owner})` : '';
    const label = `${b.name}${owner}`;
    ctx.strokeText(label, x + 6, y - 6);
    ctx.fillText(label, x + 6, y - 6);

    // Door indicator
    const doorX = b.door[0] * tile - camX;
    const doorY = b.door[1] * tile - camY;
    if (b.locked) {
      ctx.fillStyle = 'rgba(255,80,80,0.4)';
      ctx.fillRect(doorX + 2, doorY + 2, tile - 4, tile - 4);
    }
  });
}

function drawDropped(camX, camY) {
  droppedItems.forEach((d) => {
    const x = d.x - camX;
    const y = d.y - camY;
    ctx.fillStyle = '#f4d36e';
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  });
}

function drawProjectiles(camX, camY) {
  projectiles.forEach((p) => {
    const x = p.x - camX;
    const y = p.y - camY;
    ctx.fillStyle = '#ffec9f';
    ctx.beginPath();
    ctx.arc(x, y, 2, 0, Math.PI * 2);
    ctx.fill();
  });
}

function loop() {
  requestAnimationFrame(loop);

  ctx.fillStyle = '#3a7832';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const me = players[myId];
  const camX = me ? (me.x - canvas.width / 2) : (world.w / 2 - canvas.width / 2);
  const camY = me ? (me.y - canvas.height / 2) : (world.h / 2 - canvas.height / 2);

  drawWorld(camX, camY);
  drawDropped(camX, camY);
  drawProjectiles(camX, camY);

  Object.values(players).forEach((p) => drawPlayer(p, p.id === myId, camX, camY));

  drawRoofs(camX, camY);
  drawBuildings(camX, camY);

  // World border
  ctx.strokeStyle = 'rgba(255,255,255,0.15)';
  ctx.lineWidth = 2;
  ctx.strokeRect(-camX, -camY, world.w, world.h);
}

// ---- Lobby ----
async function fetchStatus() {
  try {
    const r = await fetch('/api/status');
    const d = await r.json();
    playerCountEl.textContent = `${d.players}/${d.max_players}`;
    playBtn.disabled = d.players >= d.max_players;
  } catch {
    playerCountEl.textContent = '-/20';
  }
}

function startLobbyPolling() {
  fetchStatus();
  return setInterval(fetchStatus, 3000);
}

let lobbyInterval = startLobbyPolling();

playBtn.addEventListener('click', () => {
  const chosen = lobbyNameEl.value.trim();
  if (!chosen) { lobbyNameEl.focus(); return; }
  nameEl.value = chosen;
  lobbyEl.classList.add('hidden');
  inLobby = false;
  clearInterval(lobbyInterval);
  connect();
  renderHud();
});

lobbyNameEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') playBtn.click();
});

loop();
