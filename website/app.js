const canvas = document.querySelector("#agentCanvas");
const context = canvas.getContext("2d");
const agentInput = document.querySelector("#agentCount");
const agentOutput = document.querySelector("#agentOutput");
const resourceInput = document.querySelector("#resourceId");
const runButton = document.querySelector("#runSimulation");
const resetButton = document.querySelector("#resetSimulation");
const runStatus = document.querySelector("#runStatus");
const apiMode = document.querySelector("#apiMode");
const lastResponse = document.querySelector("#lastResponse");
const locksSecured = document.querySelector("#locksSecured");
const conflicts = document.querySelector("#conflicts");
const latency = document.querySelector("#latency");
const latencyLabel = document.querySelector("#latencyLabel");

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8080";

// Allow a hosted backend via ?api=https://host (http/https only); default to local.
function resolveApiBaseUrl() {
  try {
    const requested = new URLSearchParams(window.location.search).get("api");
    if (requested) {
      const url = new URL(requested);
      if (url.protocol === "http:" || url.protocol === "https:") {
        return url.origin;
      }
    }
  } catch (error) {
    // Fall through to the default on a malformed value.
  }
  // Optional site-wide default set in config.js (used when the site is hosted).
  try {
    const configured = window.LOOM_CONFIG && window.LOOM_CONFIG.apiUrl;
    if (configured) {
      const url = new URL(configured);
      if (url.protocol === "http:" || url.protocol === "https:") {
        return url.origin;
      }
    }
  } catch (error) {
    // Fall through to the default on a malformed value.
  }
  return DEFAULT_API_BASE_URL;
}

const API_BASE_URL = resolveApiBaseUrl();
const apiEndpoint = document.querySelector("#apiEndpoint");
if (apiEndpoint) {
  apiEndpoint.textContent = API_BASE_URL.replace(/^https?:\/\//, "");
}

const colors = {
  background: "#111a18",
  grid: "rgba(255, 250, 242, 0.08)",
  waiting: "rgba(120, 208, 199, 0.22)",
  lock: "#d89a2b",
  conflict: "#c84f38",
  error: "#8a8f8d",
  text: "#fffaf2",
  muted: "rgba(255, 250, 242, 0.62)"
};

const FLASH_MS = 450;
// Run motion (decorative), 3 seconds in total:
//   0.00-0.40s  a black hole forms at the centre of the grid area
//   0.35-2.35s  it releases the cubes, each spiralling out into its own block
//   2.00-2.70s  the black hole collapses
//   2.40-3.00s  the winner pulses and the result line appears
const MOTION_TOTAL_MS = 3000;
const HOLE_GROW_MS = 400;
const HOLE_FADE_START_MS = 2000;
const HOLE_FADE_MS = 700;
const RELEASE_START_MS = 350;
const RELEASE_SPREAD_MS = 600;
const RELEASE_MS = 1400;
const SWIRL_RADIANS = Math.PI * 1.5; // how far each cube orbits before it lands
const RESULT_AT_MS = 2400;
const POP_MS = 260; // size pop when a response arrives
const RING_MS = 600; // pulse ring around the winning agent
const reduceMotion =
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const clamp01 = (value) => Math.max(0, Math.min(1, value));
const lerp = (from, to, amount) => from + (to - from) * amount;
const easeOutCubic = (amount) => 1 - Math.pow(1 - amount, 3);
const easeInCubic = (amount) => amount * amount * amount;

// One run = one cell per agent. In live mode each cell is filled when that
// agent's real HTTP response arrives; nothing is decided ahead of time.
let run = null;
let animationFrame = null;
let backendAvailable = false;

function newRun(count, source) {
  return {
    source,
    count,
    cells: Array.from({ length: count }, () => ({ status: null, at: 0 })),
    timeline: [],
    startedAt: 0,
    running: false,
    firstLockMs: null,
    lockAt: 0,
    winnerIndex: -1,
    lastArrival: 0,
    locks: 0,
    conflictCount: 0,
    errors: 0,
    simulated: source !== "api"
  };
}

function fitCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  draw();
}

function recordResponse(index, status) {
  if (!run || run.cells[index].status !== null) {
    return;
  }
  const now = performance.now();
  const cell = run.cells[index];
  cell.status = status;
  cell.at = now;
  run.lastArrival = now;
  run.timeline.push({ t: now - run.startedAt, n: run.timeline.length + 1 });

  if (status === 201) {
    run.locks += 1;
    if (run.firstLockMs === null) {
      run.lockAt = now;
      run.firstLockMs = now - run.startedAt;
      run.winnerIndex = index;
    }
  } else if (status === 409) {
    run.conflictCount += 1;
  } else {
    run.errors += 1;
  }

  locksSecured.textContent = String(run.locks);
  conflicts.textContent = String(run.conflictCount);
  requestFrame();
}

function requestFrame() {
  if (animationFrame === null) {
    animationFrame = requestAnimationFrame(() => {
      animationFrame = null;
      draw();
    });
  }
}

function gridLayout(width, top, bottom, count) {
  const gap = 2;
  const availableHeight = Math.max(20, bottom - top);
  let size = Math.floor(Math.sqrt((width * availableHeight) / count));
  size = Math.max(4, Math.min(28, size));
  let columns = Math.max(1, Math.floor((width + gap) / (size + gap)));
  let rows = Math.ceil(count / columns);
  while (rows * (size + gap) > availableHeight && size > 3) {
    size -= 1;
    columns = Math.max(1, Math.floor((width + gap) / (size + gap)));
    rows = Math.ceil(count / columns);
  }
  return { size, gap, columns, rows };
}

function cellColor(status) {
  if (status === 201) {
    return colors.lock;
  }
  if (status === 409) {
    return colors.conflict;
  }
  if (status === null) {
    return colors.waiting;
  }
  return colors.error;
}

function drawHeader(width) {
  const label = resourceInput.options[resourceInput.selectedIndex].text;
  context.fillStyle = colors.text;
  context.font = "700 18px Inter, system-ui, sans-serif";
  context.fillText(label, 24, 34);

  context.fillStyle = colors.muted;
  context.font = "600 13px Inter, system-ui, sans-serif";
  const responded = run.timeline.length;
  const resultVisible =
    reduceMotion || !run.startedAt || performance.now() - run.startedAt >= RESULT_AT_MS;
  let line;
  if (run.simulated) {
    line = "SIMULATED - API not running. Start it with: python -m core.api.server";
  } else if (run.running || (responded > 0 && !resultVisible)) {
    line = `Live API: ${responded} of ${run.count} agents have a response`;
  } else if (responded === 0) {
    line = `Live API connected - press Run to send ${run.count} real requests`;
  } else if (run.winnerIndex >= 0) {
    line = `Live API: agent #${run.winnerIndex + 1} got the lock at ${Math.round(run.firstLockMs)}ms; ${run.conflictCount} others were told to renegotiate`;
  } else {
    line = `Live API: no lock was granted (${run.conflictCount} conflicts, ${run.errors} errors)`;
  }
  context.fillText(line, 24, 58, width - 48);
}

function drawBlackHole(centerX, centerY, elapsed, extent) {
  const grow = easeOutCubic(clamp01(elapsed / HOLE_GROW_MS));
  const fade = 1 - easeInCubic(clamp01((elapsed - HOLE_FADE_START_MS) / HOLE_FADE_MS));
  const scale = grow * fade;
  if (scale <= 0.01) {
    return;
  }

  const radius = Math.min(extent * 0.16, 56) * scale;

  // Soft glow around the hole.
  const glow = context.createRadialGradient(centerX, centerY, radius * 0.4, centerX, centerY, radius * 3);
  glow.addColorStop(0, `rgba(122, 108, 255, ${0.55 * scale})`);
  glow.addColorStop(0.5, `rgba(31, 75, 255, ${0.2 * scale})`);
  glow.addColorStop(1, "rgba(31, 75, 255, 0)");
  context.fillStyle = glow;
  context.beginPath();
  context.arc(centerX, centerY, radius * 3, 0, Math.PI * 2);
  context.fill();

  // Swirling accretion rings.
  const rings = [
    ["rgba(169, 146, 240, 0.85)", 1.35, 0.0052],
    ["rgba(31, 75, 255, 0.8)", 1.7, -0.0038],
    ["rgba(166, 230, 0, 0.7)", 2.05, 0.0029]
  ];
  rings.forEach(([color, factor, speed], index) => {
    context.save();
    context.translate(centerX, centerY);
    context.rotate(elapsed * speed + index);
    context.scale(1, 0.38);
    context.strokeStyle = color;
    context.lineWidth = 2.5 * scale + 0.5;
    context.beginPath();
    context.arc(0, 0, radius * factor, 0, Math.PI * 1.35);
    context.stroke();
    context.restore();
  });

  // The black core with a thin bright rim.
  context.fillStyle = "#000000";
  context.beginPath();
  context.arc(centerX, centerY, radius, 0, Math.PI * 2);
  context.fill();
  context.strokeStyle = `rgba(255, 250, 242, ${0.7 * scale})`;
  context.lineWidth = 1.5;
  context.stroke();
}

function drawCells(left, top, width, bottom) {
  const layout = gridLayout(width, top, bottom, run.count);
  const now = performance.now();
  const elapsed = run.startedAt ? now - run.startedAt : 0;
  const centerX = left + width / 2;
  const centerY = top + (bottom - top) / 2;
  const moving = !reduceMotion && run.startedAt > 0 && elapsed < MOTION_TOTAL_MS;
  let winnerCenter = null;
  let winnerSize = layout.size;

  if (moving) {
    drawBlackHole(centerX, centerY, elapsed, Math.min(width, bottom - top));
  }

  run.cells.forEach((cell, index) => {
    const column = index % layout.columns;
    const row = Math.floor(index / layout.columns);
    const homeX = left + column * (layout.size + layout.gap) + layout.size / 2;
    const homeY = top + row * (layout.size + layout.gap) + layout.size / 2;

    // Motion only: the black hole releases each cube along a spiral into its
    // block. Position never encodes the result; colour always comes from the
    // real response.
    let x = homeX;
    let y = homeY;
    let size = layout.size;
    if (moving) {
      const spread = ((index * 37) % 100) / 100;
      const progress = clamp01((elapsed - RELEASE_START_MS - spread * RELEASE_SPREAD_MS) / RELEASE_MS);
      const travelled = easeOutCubic(progress);
      const offsetX = homeX - centerX;
      const offsetY = homeY - centerY;
      const distance = Math.hypot(offsetX, offsetY);
      const angle = Math.atan2(offsetY, offsetX) + (1 - travelled) * SWIRL_RADIANS;
      x = centerX + Math.cos(angle) * distance * travelled;
      y = centerY + Math.sin(angle) * distance * travelled;
      size = layout.size * easeOutCubic(clamp01(progress * 1.8));
    }

    const age = now - cell.at;
    if (cell.status !== null && !reduceMotion && age < POP_MS) {
      const pop = 1 - age / POP_MS;
      size *= 1 + 0.6 * pop * pop;
    }

    if (size > 0.2) {
      context.fillStyle = cellColor(cell.status);
      context.fillRect(x - size / 2, y - size / 2, size, size);

      if (cell.status !== null && age < FLASH_MS) {
        context.strokeStyle = `rgba(255, 250, 242, ${1 - age / FLASH_MS})`;
        context.lineWidth = 2;
        context.strokeRect(x - size / 2 - 1, y - size / 2 - 1, size + 2, size + 2);
      }
    }

    if (index === run.winnerIndex) {
      winnerCenter = [x, y];
      winnerSize = Math.max(size, 4);
      if (size > 0.2) {
        context.strokeStyle = colors.text;
        context.lineWidth = 2;
        context.strokeRect(x - size / 2 - 2, y - size / 2 - 2, size + 4, size + 4);
      }
    }
  });

  if (winnerCenter && run.startedAt && !reduceMotion) {
    const ringProgress = (elapsed - RESULT_AT_MS) / RING_MS;
    if (ringProgress >= 0 && ringProgress < 1) {
      context.strokeStyle = `rgba(216, 154, 43, ${0.85 * (1 - ringProgress)})`;
      context.lineWidth = 3;
      context.beginPath();
      context.arc(
        winnerCenter[0],
        winnerCenter[1],
        winnerSize + easeOutCubic(ringProgress) * Math.min(width, bottom - top) * 0.3,
        0,
        Math.PI * 2
      );
      context.stroke();
    }
  }
}

function drawTimeline(left, top, width, height) {
  context.strokeStyle = colors.grid;
  context.lineWidth = 1;
  context.strokeRect(left, top, width, height);

  context.fillStyle = colors.muted;
  context.font = "600 11px Inter, system-ui, sans-serif";
  context.fillText("responses over time", left + 6, top + 14);

  if (run.timeline.length === 0) {
    return;
  }

  const lastT = run.timeline[run.timeline.length - 1].t;
  const spanMs = Math.max(lastT, 200);
  context.strokeStyle = colors.text;
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(left, top + height);
  for (const point of run.timeline) {
    const x = left + (point.t / spanMs) * width;
    const y = top + height - (point.n / run.count) * (height - 4);
    context.lineTo(x, y);
  }
  context.stroke();

  if (run.firstLockMs !== null) {
    const x = left + (run.firstLockMs / spanMs) * width;
    context.strokeStyle = colors.lock;
    context.setLineDash([4, 3]);
    context.beginPath();
    context.moveTo(x, top);
    context.lineTo(x, top + height);
    context.stroke();
    context.setLineDash([]);
    context.fillStyle = colors.lock;
    context.fillText("lock", Math.min(x + 4, left + width - 28), top + 28);
  }

  context.fillStyle = colors.muted;
  context.fillText(`${Math.round(spanMs)}ms`, left + width - 46, top + height - 4);
}

function drawLegend(width, height) {
  const items = [
    [colors.waiting, "waiting"],
    [colors.lock, "201 lock"],
    [colors.conflict, width < 520 ? "409 conflict" : "409 conflict + retry guidance"],
    [colors.error, "error"]
  ];
  context.font = "600 12px Inter, system-ui, sans-serif";
  let x = 24;
  const y = height - 14;
  for (const [color, text] of items) {
    context.fillStyle = color;
    context.fillRect(x, y - 9, 10, 10);
    context.fillStyle = colors.muted;
    context.fillText(text, x + 16, y);
    x += 16 + context.measureText(text).width + 18;
    if (x > width - 80) {
      break;
    }
  }
}

function draw() {
  const rect = canvas.getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;

  context.clearRect(0, 0, width, height);
  context.fillStyle = colors.background;
  context.fillRect(0, 0, width, height);

  if (!run) {
    return;
  }

  const showTimeline = height >= 230;
  const timelineHeight = showTimeline ? Math.min(70, Math.round(height * 0.22)) : 0;
  const gridTop = 76;
  const gridBottom = height - 28 - (showTimeline ? timelineHeight + 12 : 0);

  drawHeader(width);
  drawCells(24, gridTop, width - 48, gridBottom);
  if (showTimeline) {
    drawTimeline(24, gridBottom + 12, width - 48, timelineHeight);
  }
  drawLegend(width, height);

  const now = performance.now();
  const settling = run.lastArrival && now - run.lastArrival < Math.max(FLASH_MS, POP_MS);
  const moving = !reduceMotion && run.startedAt && now - run.startedAt < MOTION_TOTAL_MS + 50;
  if (run.running || settling || moving) {
    requestFrame();
  }
}

const runAnnounce = document.querySelector("#runAnnounce");

// The grid is drawn on a canvas, so say the outcome in text for screen readers.
function announceResult() {
  if (!runAnnounce || !run) {
    return;
  }
  const prefix = run.simulated ? "Simulated run, not measured. " : "";
  let sentence;
  if (run.winnerIndex >= 0) {
    sentence =
      `${run.count} agents sent requests. Agent ${run.winnerIndex + 1} got the lock after ` +
      `${Math.round(run.firstLockMs)} milliseconds. ${run.conflictCount} other agents were told to renegotiate.`;
  } else {
    sentence = `${run.count} agents sent requests. No lock was granted: ${run.conflictCount} conflicts, ${run.errors} errors.`;
  }
  if (run.errors && run.winnerIndex >= 0) {
    sentence += ` ${run.errors} requests failed.`;
  }
  runAnnounce.textContent = prefix + sentence;
}

function updateMetrics() {
  const count = Number(agentInput.value);
  agentOutput.value = count;
  locksSecured.textContent = "-";
  conflicts.textContent = "-";
  latency.textContent = "-";
  latencyLabel.textContent = backendAvailable ? "press Run" : "API not running";
}

function reset() {
  run = newRun(Number(agentInput.value), backendAvailable ? "api" : "visual");
  runStatus.textContent = "Ready";
  updateMetrics();
  lastResponse.textContent = "Not run yet";
  draw();
}

async function checkBackend() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
    const payload = await response.json();
    backendAvailable = response.ok && payload.service === "loom-atp";
  } catch (error) {
    backendAvailable = false;
  }

  apiMode.textContent = backendAvailable ? "Live API connected" : "Visual fallback";
  if (run && !run.running && run.timeline.length === 0) {
    run = newRun(run.count, backendAvailable ? "api" : "visual");
    updateMetrics();
  }
  draw();
}

async function runLiveHandshake(count) {
  const selectedResource = resourceInput.value;
  const resourceLabel = resourceInput.options[resourceInput.selectedIndex].text;
  const runResourceId = `${selectedResource}-${Date.now()}`;
  const requests = Array.from({ length: count }, (_, index) => {
    const packet = {
      agent_id: `WEB-AGENT-${index + 1}`,
      intent: `Purchase one unit from ${resourceLabel}`,
      intent_hash: runResourceId,
      expiry: 5000
    };

    return fetch(`${API_BASE_URL}/v1/handshake`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(packet)
    })
      .then((response) => response.json())
      .then((body) => recordResponse(index, body.status))
      .catch(() => recordResponse(index, 0));
  });

  await Promise.all(requests);
  const elapsedMs = Math.round(performance.now() - run.startedAt);
  latency.textContent = `${elapsedMs}ms`;
  latencyLabel.textContent = "live API round trip";
  lastResponse.textContent = run.errors
    ? `${run.errors} request errors`
    : `${run.locks} locked, ${run.conflictCount} negotiated`;
}

// Offline demo only: outcomes are generated here and the view says SIMULATED.
function runSimulated(count) {
  const winner = Math.floor(Math.random() * count);
  const order = Array.from({ length: count }, (_, i) => i).sort(() => Math.random() - 0.5);
  order.unshift(order.splice(order.indexOf(winner), 1)[0]);
  return new Promise((resolve) => {
    order.forEach((index, position) => {
      setTimeout(() => {
        recordResponse(index, index === winner ? 201 : 409);
        if (position === count - 1) {
          resolve();
        }
      }, 30 + position * 4);
    });
  });
}

async function runSimulation() {
  await checkBackend();
  const count = Number(agentInput.value);
  run = newRun(count, backendAvailable ? "api" : "visual");
  run.startedAt = performance.now();
  run.running = true;
  runStatus.textContent = "Running";
  agentOutput.value = count;
  locksSecured.textContent = "0";
  conflicts.textContent = "0";
  latency.textContent = "...";
  latencyLabel.textContent = backendAvailable ? "waiting for responses" : "simulated";
  draw();

  if (backendAvailable) {
    try {
      await runLiveHandshake(count);
      run.running = false;
      runStatus.textContent = "Resolved";
      announceResult();
      draw();
      return;
    } catch (error) {
      backendAvailable = false;
      apiMode.textContent = "Visual fallback";
      run = newRun(count, "visual");
      run.startedAt = performance.now();
      run.running = true;
    }
  }

  await runSimulated(count);
  run.running = false;
  const elapsedMs = Math.round(performance.now() - run.startedAt);
  latency.textContent = `${elapsedMs}ms`;
  latencyLabel.textContent = "simulated, not measured";
  lastResponse.textContent = "API not running";
  runStatus.textContent = "Simulated";
  announceResult();
  draw();
}

agentInput.addEventListener("input", reset);
resourceInput.addEventListener("change", reset);
runButton.addEventListener("click", runSimulation);
resetButton.addEventListener("click", reset);
window.addEventListener("resize", fitCanvas);

fitCanvas();
reset();
checkBackend();
