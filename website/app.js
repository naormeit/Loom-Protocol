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
  agent: "#78d0c7",
  winner: "#d89a2b",
  conflict: "#c84f38",
  lock: "#fffaf2",
  text: "#fffaf2",
  muted: "rgba(255, 250, 242, 0.62)"
};

let agents = [];
let animationFrame = null;
let startTime = 0;
let phase = "ready";
let backendAvailable = false;
let lastRunSource = "visual";

function fitCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  draw();
}

function createAgents(count) {
  const rect = canvas.getBoundingClientRect();
  const centerX = rect.width * 0.68;
  const centerY = rect.height * 0.5;
  const winnerIndex = Math.floor(count * 0.37);

  return Array.from({ length: count }, (_, index) => {
    const angle = (index / count) * Math.PI * 2;
    const ring = 0.32 + ((index % 11) / 11) * 0.58;
    const radiusX = rect.width * ring * 0.5;
    const radiusY = rect.height * ring * 0.42;
    return {
      x: centerX + Math.cos(angle) * radiusX - rect.width * 0.18,
      y: centerY + Math.sin(angle) * radiusY,
      originX: centerX + Math.cos(angle) * radiusX - rect.width * 0.18,
      originY: centerY + Math.sin(angle) * radiusY,
      targetX: centerX,
      targetY: centerY,
      delay: (index % 24) * 10,
      size: index === winnerIndex ? 5 : 3,
      winner: index === winnerIndex,
      settled: false
    };
  });
}

function drawGrid(width, height) {
  context.strokeStyle = colors.grid;
  context.lineWidth = 1;

  for (let x = 0; x < width; x += 46) {
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, height);
    context.stroke();
  }

  for (let y = 0; y < height; y += 46) {
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(width, y);
    context.stroke();
  }
}

function drawLock(width, height, progress) {
  const centerX = width * 0.68;
  const centerY = height * 0.5;
  const pulse = 1 + Math.sin(progress * Math.PI * 6) * 0.04;

  context.save();
  context.translate(centerX, centerY);
  context.scale(pulse, pulse);

  context.fillStyle = "rgba(255, 250, 242, 0.08)";
  context.beginPath();
  context.arc(0, 0, 96, 0, Math.PI * 2);
  context.fill();

  context.strokeStyle = colors.lock;
  context.lineWidth = 3;
  context.beginPath();
  context.roundRect(-44, -12, 88, 62, 8);
  context.stroke();

  context.beginPath();
  context.arc(0, -13, 28, Math.PI, 0);
  context.stroke();

  context.fillStyle = colors.lock;
  context.beginPath();
  context.arc(0, 18, 5, 0, Math.PI * 2);
  context.fill();

  context.restore();
}

function drawLabels(width, height) {
  context.fillStyle = colors.text;
  context.font = "700 18px Inter, system-ui, sans-serif";
  context.fillText(resourceInput.options[resourceInput.selectedIndex].text, 24, 34);

  context.fillStyle = colors.muted;
  context.font = "600 13px Inter, system-ui, sans-serif";
  const modeLabel = lastRunSource === "api"
    ? "Live API requests: intent -> safety -> atomic ledger -> lock or negotiation"
    : "Visual fallback: intent -> safety -> atomic ledger -> lock or negotiation";
  context.fillText(modeLabel, 24, 58);

  context.fillStyle = "rgba(216, 154, 43, 0.92)";
  context.fillText("Winner receives 201 Atomic Lock Secured", width * 0.54, height - 36);

  context.fillStyle = "rgba(200, 79, 56, 0.92)";
  context.fillText("Others receive 409 Conflict + retry guidance", 24, height - 36);
}

function drawAgents(progress) {
  const rect = canvas.getBoundingClientRect();
  const centerX = rect.width * 0.68;
  const centerY = rect.height * 0.5;

  for (const agent of agents) {
    const delayed = Math.max(0, Math.min(1, (progress * 1200 - agent.delay) / 820));
    const ease = 1 - Math.pow(1 - delayed, 3);
    const scatter = phase === "settled" && !agent.winner ? 1 : 0;
    const awayX = agent.originX + (agent.originX - centerX) * 0.08;
    const awayY = agent.originY + (agent.originY - centerY) * 0.08;

    const targetX = agent.winner ? centerX : awayX;
    const targetY = agent.winner ? centerY : awayY;
    const activeTargetX = delayed < 0.75 ? centerX : targetX;
    const activeTargetY = delayed < 0.75 ? centerY : targetY;

    agent.x = agent.originX + (activeTargetX - agent.originX) * ease + scatter * 0;
    agent.y = agent.originY + (activeTargetY - agent.originY) * ease + scatter * 0;

    context.strokeStyle = agent.winner ? "rgba(216, 154, 43, 0.28)" : "rgba(120, 208, 199, 0.11)";
    context.lineWidth = agent.winner ? 2 : 1;
    context.beginPath();
    context.moveTo(agent.originX, agent.originY);
    context.lineTo(agent.x, agent.y);
    context.stroke();

    context.fillStyle = agent.winner ? colors.winner : delayed > 0.75 ? colors.conflict : colors.agent;
    context.beginPath();
    context.arc(agent.x, agent.y, agent.size, 0, Math.PI * 2);
    context.fill();
  }
}

function draw() {
  const rect = canvas.getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;
  const elapsed = startTime ? performance.now() - startTime : 0;
  const progress = phase === "ready" ? 0.18 : Math.min(1, elapsed / 1300);

  context.clearRect(0, 0, width, height);
  context.fillStyle = colors.background;
  context.fillRect(0, 0, width, height);
  drawGrid(width, height);
  drawLock(width, height, progress);
  drawAgents(progress);
  drawLabels(width, height);

  if (phase === "running" && progress < 1) {
    animationFrame = requestAnimationFrame(draw);
    return;
  }

  if (phase === "running") {
    phase = "settled";
    runStatus.textContent = "Resolved";
    draw();
  }
}

function updateMetrics() {
  const count = Number(agentInput.value);
  const estimatedLatency = Math.round(42 + Math.log2(count) * 12);
  agentOutput.value = count;
  locksSecured.textContent = "1";
  conflicts.textContent = String(Math.max(0, count - 1));
  latency.textContent = `${estimatedLatency}ms`;
  latencyLabel.textContent = "visual estimate";
}

function reset() {
  cancelAnimationFrame(animationFrame);
  phase = "ready";
  startTime = 0;
  runStatus.textContent = "Ready";
  lastRunSource = backendAvailable ? "api" : "visual";
  agents = createAgents(Number(agentInput.value));
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
  lastRunSource = backendAvailable ? "api" : "visual";
  draw();
}

async function runLiveHandshake(count) {
  const selectedResource = resourceInput.value;
  const resourceLabel = resourceInput.options[resourceInput.selectedIndex].text;
  const runResourceId = `${selectedResource}-${Date.now()}`;
  const startedAt = performance.now();
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
      .catch((error) => ({ status: 0, message: error.message }));
  });

  const responses = await Promise.all(requests);
  const elapsedMs = Math.round(performance.now() - startedAt);
  const lockCount = responses.filter((response) => response.status === 201).length;
  const conflictCount = responses.filter((response) => response.status === 409).length;
  const errorCount = responses.length - lockCount - conflictCount;

  locksSecured.textContent = String(lockCount);
  conflicts.textContent = String(conflictCount);
  latency.textContent = `${elapsedMs}ms`;
  latencyLabel.textContent = "live API round trip";
  lastResponse.textContent = errorCount
    ? `${errorCount} request errors`
    : `${lockCount} locked, ${conflictCount} negotiated`;
}

function runVisualFallback(count) {
  const estimatedLatency = Math.round(42 + Math.log2(count) * 12);
  locksSecured.textContent = "1";
  conflicts.textContent = String(Math.max(0, count - 1));
  latency.textContent = `${estimatedLatency}ms`;
  latencyLabel.textContent = "visual estimate";
  lastResponse.textContent = "API not running";
}

async function runSimulation() {
  cancelAnimationFrame(animationFrame);
  await checkBackend();
  phase = "running";
  startTime = performance.now();
  runStatus.textContent = "Running";
  const count = Number(agentInput.value);
  agents = createAgents(count);
  agentOutput.value = count;
  lastRunSource = backendAvailable ? "api" : "visual";
  draw();

  if (backendAvailable) {
    try {
      await runLiveHandshake(count);
      runStatus.textContent = "Resolved";
      return;
    } catch (error) {
      backendAvailable = false;
      apiMode.textContent = "Visual fallback";
      lastRunSource = "visual";
    }
  }

  runVisualFallback(count);
}

agentInput.addEventListener("input", reset);
resourceInput.addEventListener("change", reset);
runButton.addEventListener("click", runSimulation);
resetButton.addEventListener("click", reset);
window.addEventListener("resize", fitCanvas);

if (!CanvasRenderingContext2D.prototype.roundRect) {
  CanvasRenderingContext2D.prototype.roundRect = function roundRect(x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    this.moveTo(x + r, y);
    this.arcTo(x + width, y, x + width, y + height, r);
    this.arcTo(x + width, y + height, x, y + height, r);
    this.arcTo(x, y + height, x, y, r);
    this.arcTo(x, y, x + width, y, r);
    return this;
  };
}

fitCanvas();
reset();
checkBackend();
