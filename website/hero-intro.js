// Landing-page intro: particles gather into a sphere, then morph into the Loom
// mark, then the page content fades in. Decorative only: it does not represent
// any request, response, or protocol data. Skipped for reduced-motion users,
// after the first play in a session, and when the visitor clicks or presses a key.
//
// Query overrides: ?intro=1 always plays it, ?intro=0 never plays it.
(function () {
  "use strict";

  const STORAGE_KEY = "loomIntroSeen";
  const LOGO_URL = "assets/loom-logo.png";
  const TIMING = { gather: 700, sphere: 650, morph: 900, hold: 350, fade: 400 };
  const SPREAD = 250; // per-particle start offset in ms, for an organic feel
  const FAILSAFE_MS = 7000;

  function readParam() {
    try {
      return new URLSearchParams(window.location.search).get("intro");
    } catch (error) {
      return null;
    }
  }

  function alreadySeen() {
    try {
      return window.sessionStorage.getItem(STORAGE_KEY) === "1";
    } catch (error) {
      return false;
    }
  }

  function markSeen() {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, "1");
    } catch (error) {
      // Storage can be blocked; the intro then simply plays again next visit.
    }
  }

  const param = readParam();
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (param === "0" || reduced || (param !== "1" && alreadySeen())) {
    return;
  }
  if (typeof Element.prototype.animate !== "function") {
    return;
  }

  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const easeOut = (t) => 1 - Math.pow(1 - t, 3);
  const clamp01 = (v) => Math.max(0, Math.min(1, v));
  const lerp = (a, b, t) => a + (b - a) * t;

  const overlay = document.createElement("div");
  overlay.className = "intro-overlay";
  overlay.setAttribute("aria-hidden", "true");
  const canvas = document.createElement("canvas");
  const skip = document.createElement("span");
  skip.className = "intro-skip";
  skip.textContent = "Click or press any key to skip";
  overlay.append(canvas, skip);
  document.body.appendChild(overlay);

  const root = document.documentElement;
  const previousOverflow = root.style.overflow;
  root.style.overflow = "hidden";

  const context = canvas.getContext("2d");
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  let width = 0;
  let height = 0;

  function fit() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
  }
  fit();

  const compact = width < 700;
  const COUNT = compact ? 1800 : 3600;

  // Sphere points (Fibonacci lattice) and random start positions.
  const golden = Math.PI * (3 - Math.sqrt(5));
  const particles = Array.from({ length: COUNT }, (_, i) => {
    const y = 1 - (i / (COUNT - 1)) * 2;
    const radius = Math.sqrt(1 - y * y);
    const theta = golden * i;
    const amber = Math.random() < 0.12;
    return {
      ux: Math.cos(theta) * radius,
      uy: y,
      uz: Math.sin(theta) * radius,
      sx: Math.random() * width,
      sy: Math.random() * height,
      delay: Math.random() * SPREAD,
      base: amber ? [216, 154, 43] : [11, 118, 111],
      target: null,
      color: null
    };
  });

  // Sample the logo into normalised target points (largest dimension = 1).
  function sampleLogo(image) {
    const sampleWidth = 480;
    const sampleHeight = Math.round(sampleWidth * (image.naturalHeight / image.naturalWidth));
    const offscreen = document.createElement("canvas");
    offscreen.width = sampleWidth;
    offscreen.height = sampleHeight;
    const offContext = offscreen.getContext("2d", { willReadFrequently: true });
    offContext.drawImage(image, 0, 0, sampleWidth, sampleHeight);
    // Throws on a tainted canvas (e.g. opened via file://); the caller falls back.
    const data = offContext.getImageData(0, 0, sampleWidth, sampleHeight).data;

    const points = [];
    const xMin = sampleWidth * 0.2;
    const xMax = sampleWidth * 0.8;
    const yMin = sampleHeight * 0.05;
    const yMax = sampleHeight * 0.95;
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    for (let y = Math.floor(yMin); y < yMax; y += 1) {
      for (let x = Math.floor(xMin); x < xMax; x += 1) {
        const index = (y * sampleWidth + x) * 4;
        const alpha = data[index + 3];
        const red = data[index];
        const green = data[index + 1];
        const blue = data[index + 2];
        if (alpha > 128 && Math.min(red, green, blue) < 215) {
          points.push([x, y, red, green, blue]);
          minX = Math.min(minX, x);
          maxX = Math.max(maxX, x);
          minY = Math.min(minY, y);
          maxY = Math.max(maxY, y);
        }
      }
    }

    if (points.length < 200) {
      return null;
    }

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const span = Math.max(maxX - minX, maxY - minY) || 1;
    return points.map(([x, y, r, g, b]) => ({
      x: (x - centerX) / span,
      y: (y - centerY) / span,
      color: [r, g, b]
    }));
  }

  function assignTargets(samples) {
    for (const particle of particles) {
      if (samples) {
        const sample = samples[Math.floor(Math.random() * samples.length)];
        particle.target = [sample.x, sample.y];
        particle.color = sample.color;
      } else {
        // Fallback when the logo cannot be sampled: settle into a ring.
        const angle = Math.random() * Math.PI * 2;
        particle.target = [Math.cos(angle) * 0.5, Math.sin(angle) * 0.5];
        particle.color = particle.base;
      }
    }
  }

  let ready = false;
  const image = new Image();
  image.onload = () => {
    let samples = null;
    try {
      samples = sampleLogo(image);
    } catch (error) {
      samples = null;
    }
    assignTargets(samples);
    ready = true;
  };
  image.onerror = () => {
    assignTargets(null);
    ready = true;
  };
  image.src = LOGO_URL;

  const gatherEnd = TIMING.gather;
  const sphereEnd = gatherEnd + TIMING.sphere;
  const morphEnd = sphereEnd + TIMING.morph;
  const totalMs = morphEnd + TIMING.hold;

  let startedAt = null;
  let frame = null;
  let finished = false;

  function render(now) {
    if (finished) {
      return;
    }
    if (startedAt === null) {
      startedAt = now;
    }
    const t = now - startedAt;
    const centerX = width / 2;
    const centerY = height / 2;
    const sphereRadius = Math.min(width, height) * 0.28;
    const logoSize = Math.min(width, height) * (compact ? 0.5 : 0.42);
    const angle = t * 0.0013;
    const cosA = Math.cos(angle);
    const sinA = Math.sin(angle);

    context.fillStyle = "#f7f3ec";
    context.fillRect(0, 0, width, height);

    const readyForMorph = ready;
    for (const p of particles) {
      const rotatedX = p.ux * cosA + p.uz * sinA;
      const depth = (-p.ux * sinA + p.uz * cosA + 1) / 2;
      const sphereX = centerX + rotatedX * sphereRadius;
      const sphereY = centerY + p.uy * sphereRadius;

      const gather = easeOut(clamp01((t - p.delay) / (TIMING.gather - SPREAD * 0.4)));
      let x = lerp(p.sx, sphereX, gather);
      let y = lerp(p.sy, sphereY, gather);
      let size = 1.8 + depth * 1.8;
      let alpha = (0.4 + depth * 0.6) * gather;
      let red = p.base[0];
      let green = p.base[1];
      let blue = p.base[2];

      if (readyForMorph && p.target) {
        const morph = ease(clamp01((t - sphereEnd - p.delay) / (TIMING.morph - SPREAD * 0.4)));
        if (morph > 0) {
          x = lerp(x, centerX + p.target[0] * logoSize, morph);
          y = lerp(y, centerY + p.target[1] * logoSize, morph);
          size = lerp(size, 2.6, morph);
          alpha = lerp(alpha, 1, morph);
          red = lerp(red, p.color[0], morph);
          green = lerp(green, p.color[1], morph);
          blue = lerp(blue, p.color[2], morph);
        }
      }

      context.globalAlpha = alpha;
      context.fillStyle = `rgb(${red | 0}, ${green | 0}, ${blue | 0})`;
      context.fillRect(x - size / 2, y - size / 2, size, size);
    }
    context.globalAlpha = 1;

    if (t >= totalMs && ready) {
      finish();
      return;
    }
    frame = requestAnimationFrame(render);
  }

  function revealContent() {
    const targets = document.querySelectorAll(".hero-copy > *, .sim-panel");
    targets.forEach((element, index) => {
      element.animate(
        [
          { opacity: 0, transform: "translateY(14px)" },
          { opacity: 1, transform: "none" }
        ],
        {
          duration: 600,
          delay: index * 70,
          easing: "cubic-bezier(0.2, 0.7, 0.2, 1)",
          fill: "backwards"
        }
      );
    });
  }

  function finish(quick) {
    if (finished) {
      return;
    }
    finished = true;
    cancelAnimationFrame(frame);
    markSeen();
    window.clearTimeout(failsafe);
    window.removeEventListener("keydown", onSkip);
    window.removeEventListener("resize", fit);
    overlay.removeEventListener("click", onSkip);
    root.style.overflow = previousOverflow;

    revealContent();
    const fade = overlay.animate([{ opacity: 1 }, { opacity: 0 }], {
      duration: quick === true ? 200 : TIMING.fade,
      easing: "ease-out",
      fill: "forwards"
    });
    fade.finished.then(() => overlay.remove(), () => overlay.remove());
  }

  const onSkip = () => finish(true);
  const failsafe = window.setTimeout(onSkip, FAILSAFE_MS);
  overlay.addEventListener("click", onSkip);
  window.addEventListener("keydown", onSkip);
  window.addEventListener("resize", fit);

  frame = requestAnimationFrame(render);
})();
