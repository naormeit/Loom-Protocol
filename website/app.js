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
  let line;
  if (run.simulated) {
    line = "SIMULATED - API not running. Start it with: python -m core.api.server";
  } else if (run.running) {
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

function drawCells(left, top, width, bottom) {
  const layout = gridLayout(width, top, bottom, run.count);
  const now = performance.now();

  run.cells.forEach((cell, index) => {
    const column = index % layout.columns;
    const row = Math.floor(index / layout.columns);
    const x = left + column * (layout.size + layout.gap);
    const y = top + row * (layout.size + layout.gap);

    context.fillStyle = cellColor(cell.status);
    context.fillRect(x, y, layout.size, layout.size);

    if (cell.status !== null) {
      const age = now - cell.at;
      if (age < FLASH_MS) {
        context.strokeStyle = `rgba(255, 250, 242, ${1 - age / FLASH_MS})`;
        context.lineWidth = 2;
        context.strokeRect(x - 1, y - 1, layout.size + 2, layout.size + 2);
      }
    }

    if (index === run.winnerIndex) {
      context.strokeStyle = colors.text;
      context.lineWidth = 2;
      context.strokeRect(x - 2, y - 2, layout.size + 4, layout.size + 4);
    }
  });
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

  const showTimeline = height >= 300;
  const timelineHeight = showTimeline ? 70 : 0;
  const gridTop = 76;
  const gridBottom = height - 28 - (showTimeline ? timelineHeight + 12 : 0);

  drawHeader(width);
  drawCells(24, gridTop, width - 48, gridBottom);
  if (showTimeline) {
    drawTimeline(24, gridBottom + 12, width - 48, timelineHeight);
  }
  drawLegend(width, height);

  const stillFlashing = run.lastArrival && performance.now() - run.lastArrival < FLASH_MS;
  if (run.running || stillFlashing) {
    requestFrame();
  }
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
