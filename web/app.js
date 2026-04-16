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

function drawGrid(camX, camY) {
  const tile = world.tile || 32;
  const startX = -((camX % tile) + tile) % tile;
  const startY = -((camY % tile) + tile) % tile;
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  for (let x = startX; x < canvas.width; x += tile) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  for (let y = startY; y < canvas.height; y += tile) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
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
  buildings.forEach((b) => {
    const x = b.x * world.tile - camX;
    const y = b.y * world.tile - camY;
    const w = b.w * world.tile;
    const h = b.h * world.tile;
    ctx.fillStyle = 'rgba(220,225,235,0.07)';
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = b.locked ? '#ff6b6b' : 'rgba(255,255,255,0.25)';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);

    const doorX = b.door[0] * world.tile - camX;
    const doorY = b.door[1] * world.tile - camY;
    ctx.fillStyle = b.locked ? '#ff6868' : '#a3b4cf';
    ctx.fillRect(doorX + 6, doorY + 6, world.tile - 12, world.tile - 12);

    ctx.font = '12px Segoe UI';
    ctx.textAlign = 'left';
    ctx.fillStyle = '#d6deec';
    const owner = b.owner ? ` (${b.owner})` : '';
    ctx.fillText(`${b.name}${owner}`, x + 6, y + 16);
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

  ctx.fillStyle = '#1a2230';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const me = players[myId];
  const camX = me ? (me.x - canvas.width / 2) : (world.w / 2 - canvas.width / 2);
  const camY = me ? (me.y - canvas.height / 2) : (world.h / 2 - canvas.height / 2);

  drawGrid(camX, camY);
  drawBuildings(camX, camY);
  drawDropped(camX, camY);
  drawProjectiles(camX, camY);

  Object.values(players).forEach((p) => drawPlayer(p, p.id === myId, camX, camY));

  ctx.fillStyle = 'rgba(255,255,255,0.08)';
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
