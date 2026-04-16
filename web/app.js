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
let chatActive = false;
let chatText = '';

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
  // Chat mode intercepts all keys
  if (chatActive) {
    e.preventDefault();
    if (e.key === 'Enter') {
      if (chatText.trim()) {
        send({ type: 'action', action: 'chat', text: chatText.trim() });
      }
      chatActive = false;
      chatText = '';
    } else if (e.key === 'Escape') {
      chatActive = false;
      chatText = '';
    } else if (e.key === 'Backspace') {
      chatText = chatText.slice(0, -1);
    } else if (e.key.length === 1 && chatText.length < 80) {
      chatText += e.key;
    }
    return;
  }

  if (e.key === 't' || e.key === 'T') {
    e.preventDefault();
    chatActive = true;
    chatText = '';
    return;
  }

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

// ── Job outfit definitions (matching desktop JOB_OUTFITS) ──
const JOB_OUTFITS = [
  { clothes: '#ebebeb', hat: null },
  { clothes: '#4678d2', hat: { type: 'police', color: '#233c78' } },
  { clothes: '#d24646', hat: { type: 'cap', color: '#dcdcdc', accent: '#c83232' } },
  { clothes: '#af8c41', hat: { type: 'top', color: '#282828' } },
  { clothes: '#a55f37', hat: { type: 'beanie', color: '#3c3c41' } },
  { clothes: '#ebebeb', hat: { type: 'chef', color: '#f5f5f5' } },
  { clothes: '#783737', hat: { type: 'beanie', color: '#2d2d32' } },
  { clothes: '#379669', hat: { type: 'fedora', color: '#323c46' } },
];

// Item icon colors for dropped items & hotbar
const ITEM_COLORS = {
  food: '#c88c46', water: '#4696dc', medkit: '#d24646', toolkit: '#8c8c96',
  metal: '#aaaab4', soda: '#eb785a', bandage: '#dcdccd', battery: '#78d25a',
  lockpick: '#b4b4b9', cuffs: '#9696a0', pistol: '#464650', shotgun: '#5f503c',
  pistol_ammo: '#e6be5a', shells: '#dc3c3c',
};

// Pre-render player body sprites per job
const bodyCache = {};
function getBodySprite(jobIdx) {
  if (bodyCache[jobIdx]) return bodyCache[jobIdx];
  const c = document.createElement('canvas');
  c.width = 32; c.height = 32;
  const x = c.getContext('2d');
  const outfit = JOB_OUTFITS[jobIdx] || JOB_OUTFITS[0];
  const col = outfit.clothes;
  // Torso ellipse
  x.fillStyle = col;
  x.beginPath(); x.ellipse(16, 16, 9, 6, 0, 0, Math.PI * 2); x.fill();
  // Darker lower body
  x.globalAlpha = 0.85;
  x.beginPath(); x.ellipse(16, 21, 8, 6, 0, 0, Math.PI * 2); x.fill();
  x.globalAlpha = 1;
  // Arms
  x.beginPath(); x.arc(9, 16, 3, 0, Math.PI * 2); x.fill();
  x.beginPath(); x.arc(23, 16, 3, 0, Math.PI * 2); x.fill();
  bodyCache[jobIdx] = c;
  return c;
}

// Pre-render player head sprites per job
const headCache = {};
function getHeadSprite(jobIdx) {
  if (headCache[jobIdx]) return headCache[jobIdx];
  const c = document.createElement('canvas');
  c.width = 32; c.height = 32;
  const x = c.getContext('2d');
  const outfit = JOB_OUTFITS[jobIdx] || JOB_OUTFITS[0];
  // Skin head
  x.fillStyle = '#dcb99b';
  x.beginPath(); x.arc(16, 10, 6, 0, Math.PI * 2); x.fill();
  x.strokeStyle = '#b4916c';
  x.lineWidth = 1;
  x.beginPath(); x.arc(16, 10, 6, 0, Math.PI * 2); x.stroke();
  // Face direction triangle
  x.fillStyle = '#fafafa';
  x.beginPath(); x.moveTo(16, 2); x.lineTo(13, 6); x.lineTo(19, 6); x.closePath(); x.fill();
  // Hat
  const hat = outfit.hat;
  if (hat) {
    x.fillStyle = hat.color;
    if (hat.type === 'police') {
      x.fillRect(10, 2, 12, 4);
      x.fillStyle = '#ebb750';
      x.fillRect(15, 3, 2, 2);
    } else if (hat.type === 'chef') {
      x.beginPath(); x.ellipse(16, 3, 7, 4, 0, 0, Math.PI * 2); x.fill();
    } else if (hat.type === 'top') {
      x.fillRect(12, 1, 8, 6);
    } else if (hat.type === 'beanie') {
      x.beginPath(); x.ellipse(16, 5, 6, 3, 0, 0, Math.PI * 2); x.fill();
    } else if (hat.type === 'fedora') {
      x.beginPath(); x.ellipse(16, 6, 7, 2, 0, 0, Math.PI * 2); x.fill();
      x.fillRect(11, 1, 10, 5);
    } else { // cap
      x.beginPath(); x.ellipse(16, 4, 6, 3, 0, 0, Math.PI * 2); x.fill();
    }
  }
  headCache[jobIdx] = c;
  return c;
}

function drawPlayer(p, isMe, camX, camY) {
  const sx = p.x - camX;
  const sy = p.y - camY;
  const jobIdx = p.job || 0;

  // Body (fixed orientation)
  const body = getBodySprite(jobIdx);
  ctx.drawImage(body, sx - 16, sy - 14);

  // Head (rotates with aim)
  const head = getHeadSprite(jobIdx);
  const a = -((p.angle || 0)) * Math.PI / 180;
  ctx.save();
  ctx.translate(sx, sy - 4);
  ctx.rotate(a);
  ctx.drawImage(head, -16, -16);
  ctx.restore();

  // Name label
  ctx.font = 'bold 12px Segoe UI';
  ctx.textAlign = 'center';
  ctx.strokeStyle = 'rgba(0,0,0,0.6)';
  ctx.lineWidth = 3;
  ctx.strokeText(p.name || p.id, sx, sy - 22);
  ctx.fillStyle = isMe ? '#7ed2ff' : '#ffffff';
  ctx.fillText(p.name || p.id, sx, sy - 22);

  // Health bar
  const hbw = 28, hbh = 4;
  ctx.fillStyle = 'rgba(0,0,0,0.55)';
  ctx.fillRect(sx - hbw/2, sy + 16, hbw, hbh);
  const hpFill = Math.max(0, Math.min(1, (p.health || 0) / 100));
  const r = Math.round(210 * (0.4 + 0.6 * hpFill));
  const g = Math.round(70 * (0.4 + 0.6 * hpFill));
  const b = Math.round(70 * (0.4 + 0.6 * hpFill));
  ctx.fillStyle = `rgb(${r},${g},${b})`;
  ctx.fillRect(sx - hbw/2, sy + 16, hbw * hpFill, hbh);

  // Detained/jail indicator
  if (p.detained || p.in_jail) {
    ctx.strokeStyle = '#f2bf5b';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(sx, sy, 18, 0, Math.PI * 2);
    ctx.stroke();
  }

  // Chat bubbles above player
  const bubbles = p.chat_bubbles || [];
  if (bubbles.length > 0) {
    let yOff = -32;
    for (let i = bubbles.length - 1; i >= 0; i--) {
      const [text, timer] = bubbles[i];
      const alpha = Math.min(1, timer / 1.0);
      ctx.globalAlpha = alpha;
      ctx.font = '13px Consolas';
      const tw = ctx.measureText(text).width;
      const pad = 8;
      const bw = tw + pad * 2;
      const bh = 20;
      const bx = sx - bw / 2;
      const by = sy + yOff - bh;
      // Bubble bg
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.roundRect(bx, by, bw, bh, 6);
      ctx.fill();
      ctx.strokeStyle = '#b4b4be';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(bx, by, bw, bh, 6);
      ctx.stroke();
      // Triangle pointer
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.moveTo(sx - 4, by + bh);
      ctx.lineTo(sx + 4, by + bh);
      ctx.lineTo(sx, by + bh + 5);
      ctx.closePath();
      ctx.fill();
      // Text
      ctx.fillStyle = '#141420';
      ctx.textAlign = 'center';
      ctx.fillText(text, sx, by + 14);
      yOff -= bh + 4;
    }
    ctx.globalAlpha = 1;
  }
}

function drawBuildings(camX, camY) {
  const tile = world.tile || 32;
  buildings.forEach((b) => {
    const x = b.x * tile - camX;
    const y = b.y * tile - camY;

    // Building name label above roof
    ctx.font = 'bold 13px Segoe UI';
    ctx.textAlign = 'left';
    ctx.strokeStyle = 'rgba(0,0,0,0.5)';
    ctx.lineWidth = 3;
    const owner = b.owner ? ` (${b.owner})` : '';
    const label = `${b.name}${owner}`;
    ctx.strokeText(label, x + 6, y - 6);
    ctx.fillStyle = '#eaf0ff';
    ctx.fillText(label, x + 6, y - 6);

    // Locked door overlay
    if (b.locked) {
      const doorX = b.door[0] * tile - camX;
      const doorY = b.door[1] * tile - camY;
      ctx.fillStyle = 'rgba(255,80,80,0.4)';
      ctx.fillRect(doorX + 2, doorY + 2, tile - 4, tile - 4);
    }
  });
}

function drawDropped(camX, camY) {
  droppedItems.forEach((d) => {
    const x = d.x - camX;
    const y = d.y - camY;
    // Shadow
    ctx.fillStyle = 'rgba(0,0,0,0.25)';
    ctx.beginPath(); ctx.ellipse(x, y + 8, 9, 4, 0, 0, Math.PI * 2); ctx.fill();
    // Item icon circle
    const col = ITEM_COLORS[d.id] || '#f4d36e';
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.arc(x, y, 7, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = 'rgba(0,0,0,0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(x, y, 7, 0, Math.PI * 2); ctx.stroke();
    // Count
    if (d.count > 1) {
      ctx.font = 'bold 10px Consolas';
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'center';
      ctx.fillText(String(d.count), x, y - 10);
    }
  });
}

function drawProjectiles(camX, camY) {
  projectiles.forEach((p) => {
    const x = p.x - camX;
    const y = p.y - camY;
    ctx.fillStyle = '#ffe678';
    ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill();
  });
}

// ── Indoor blackout: dim everything outside the building ──
function drawIndoorBlackout(camX, camY) {
  const me = players[myId];
  if (!me) return null;
  const tile = world.tile || 32;
  let insideB = null;
  for (const b of buildings) {
    const bx = b.x * tile, by = b.y * tile;
    const bw = b.w * tile, bh = b.h * tile;
    if (me.x >= bx && me.x < bx + bw && me.y >= by && me.y < by + bh) {
      insideB = b; break;
    }
  }
  if (!insideB) return null;
  // Draw full-screen dark overlay
  ctx.fillStyle = 'rgba(0,0,0,0.85)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  // Cut out the building interior
  const bx = insideB.x * tile - camX;
  const by = insideB.y * tile - camY;
  const bw = insideB.w * tile;
  const bh = insideB.h * tile;
  ctx.clearRect(bx, by, bw, bh);
  // Redraw the building interior tiles
  if (tileMap) {
    for (let ty = insideB.y; ty < insideB.y + insideB.h; ty++) {
      for (let tx = insideB.x; tx < insideB.x + insideB.w; tx++) {
        const gid = tileMap.ground[ty * tileMap.w + tx];
        ctx.drawImage(getTileCanvas(gid, false), tx * tile - camX, ty * tile - camY, tile, tile);
        const wid = tileMap.walls[ty * tileMap.w + tx];
        if (wid) ctx.drawImage(getTileCanvas(wid, true), tx * tile - camX, ty * tile - camY, tile, tile);
      }
    }
  }
  // Redraw players inside
  Object.values(players).forEach(p => {
    const bpx = insideB.x * tile, bpy = insideB.y * tile;
    if (p.x >= bpx && p.x < bpx + insideB.w * tile && p.y >= bpy && p.y < bpy + insideB.h * tile) {
      drawPlayer(p, p.id === myId, camX, camY);
    }
  });
  return insideB;
}

// ── Canvas HUD (stat bars, position, money) drawn on canvas ──
function drawCanvasHud() {
  const me = players[myId];
  if (!me) return;

  // Position (top left)
  const tile = world.tile || 32;
  ctx.font = '13px Consolas';
  ctx.textAlign = 'left';
  ctx.fillStyle = '#fff';
  ctx.fillText(`X:${Math.floor(me.x / tile)} Y:${Math.floor(me.y / tile)}`, 10, canvas.height - 120);

  // Stat bars (bottom left, above hotbar area)
  const barW = 160, barH = 12, labelW = 50;
  const barX = 10;
  const baseY = canvas.height - 105;

  function drawBar(y, fill, color, label) {
    ctx.font = '12px Consolas';
    ctx.fillStyle = '#ddd';
    ctx.fillText(label, barX, y + 10);
    const bx = barX + labelW;
    const bw = barW - labelW;
    // Background
    ctx.fillStyle = '#1e1e1e';
    ctx.fillRect(bx, y, bw, barH);
    // Fill
    const f = Math.max(0, Math.min(1, fill));
    if (f > 0) {
      const r = Math.round(color[0] * (0.4 + 0.6 * f));
      const g = Math.round(color[1] * (0.4 + 0.6 * f));
      const b = Math.round(color[2] * (0.4 + 0.6 * f));
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(bx, y, bw * f, barH);
    }
    // Border
    ctx.strokeStyle = '#646464';
    ctx.lineWidth = 1;
    ctx.strokeRect(bx, y, bw, barH);
  }
  drawBar(baseY, (you.health || 0) / 100, [210, 70, 70], 'Health');
  drawBar(baseY + 18, (you.hunger || 0) / 100, [200, 140, 50], 'Hunger');
  drawBar(baseY + 36, (you.thirst || 0) / 100, [60, 150, 220], 'Thirst');

  // Jail timer
  if (you.in_jail) {
    ctx.font = 'bold 14px Consolas';
    ctx.fillStyle = '#e67878';
    ctx.fillText(`Jail: ${formatTime(you.arrest_remaining || 0)}`, 10, canvas.height - 130);
  }
  if (you.detained) {
    ctx.font = 'bold 14px Consolas';
    ctx.fillStyle = '#f2bf5b';
    ctx.fillText('DETAINED', 10, canvas.height - 130);
  }
}

// ── Chat input bar ──
function drawChatInput() {
  if (!chatActive) return;
  const barH = 32;
  const barY = canvas.height - barH;
  ctx.fillStyle = 'rgba(10,10,20,0.86)';
  ctx.fillRect(0, barY, canvas.width, barH);
  ctx.font = '16px Consolas';
  ctx.textAlign = 'left';
  ctx.fillStyle = '#b4b4b4';
  ctx.fillText('Say: ', 10, barY + 22);
  const cursor = (Math.floor(Date.now() / 500) % 2 === 0) ? '|' : '';
  ctx.fillStyle = '#fff';
  ctx.fillText(chatText + cursor, 54, barY + 22);
}

// ── Canvas-drawn hotbar (matching desktop) ──
function drawCanvasHotbar() {
  const HOTBAR_SIZE = 5;
  const slotW = 56, slotH = 56, gap = 8;
  const totalW = HOTBAR_SIZE * slotW + (HOTBAR_SIZE - 1) * gap;
  const startX = canvas.width / 2 - totalW / 2;
  const startY = canvas.height - 74;
  const hotbar = Array.isArray(you.hotbar) ? you.hotbar : [];
  const sel = Number(you.selected_hotbar || 0);

  for (let i = 0; i < HOTBAR_SIZE; i++) {
    const x = startX + i * (slotW + gap);
    const y = startY;
    const st = hotbar[i] || null;

    // Slot background
    ctx.fillStyle = '#1e1e28';
    ctx.beginPath();
    ctx.roundRect(x, y, slotW, slotH, 6);
    ctx.fill();

    // Border
    ctx.strokeStyle = i === sel ? '#ffdc5a' : '#5a5a6e';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(x, y, slotW, slotH, 6);
    ctx.stroke();

    if (st) {
      // Item icon (colored rect)
      const col = ITEM_COLORS[st.id] || '#969696';
      const ix = x + 6, iy = y + 6, iw = slotW - 12, ih = slotH - 24;
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.roundRect(ix, iy, iw, ih, 4);
      ctx.fill();
      ctx.strokeStyle = '#141414';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(ix, iy, iw, ih, 4);
      ctx.stroke();

      // Item name
      ctx.font = '11px Consolas';
      ctx.textAlign = 'center';
      ctx.fillStyle = '#e6e6eb';
      const short = (st.name || 'Item').substring(0, 8);
      ctx.fillText(short, x + slotW / 2, y + slotH - 5);

      // Count
      ctx.font = 'bold 12px Consolas';
      ctx.textAlign = 'right';
      ctx.fillStyle = '#fff';
      ctx.fillText(String(st.count), x + slotW - 5, y + 13);
    }

    // Slot number
    ctx.font = '10px Consolas';
    ctx.textAlign = 'left';
    ctx.fillStyle = 'rgba(255,255,255,0.35)';
    ctx.fillText(String(i + 1), x + 3, y + 12);
  }

  // Money display above hotbar
  ctx.font = 'bold 14px Consolas';
  ctx.textAlign = 'center';
  ctx.fillStyle = '#50dc50';
  ctx.fillText(`$${Math.round(you.money || 0)}`, canvas.width / 2, startY - 8);
}

// ── Main game loop ──
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

  // Indoor blackout
  drawIndoorBlackout(camX, camY);

  // HUD on canvas
  drawCanvasHud();
  drawCanvasHotbar();
  drawChatInput();

  // World border
  ctx.strokeStyle = 'rgba(255,255,255,0.15)';
  ctx.lineWidth = 2;
  ctx.strokeRect(-camX, -camY, world.w, world.h);
}
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
