# Loom Protocol Main Website

This is the static main website for the Imagine Cup 2027 submission story.

There are two pages: `index.html` is the landing page (story, how it works, honest status, calls to action, and the particle intro) and `demo.html` is the live simulator.

Open `index.html` directly in a browser, or serve the folder over HTTP (`python -m http.server 5500 --directory website`) so the intro can sample the logo. No build step or package install is required.
When Live Server is started from the repository root, the root `index.html` redirects to `website/`.

## Live Backend Demo (`demo.html`)

Start the Loom API before using the simulator as technical proof:

```powershell
python -m core.api.server
```

The website checks `http://127.0.0.1:8080/health` by default. To point it at a hosted backend, open the page with `?api=https://<your-host>` (http/https origins only); the endpoint shown in the page updates to match. If the API is available, the Run button sends real `POST /v1/handshake` packets and displays actual `201` lock and `409` conflict counts. On Run, a black hole forms at the centre, releases the cubes (one per agent) along spiral paths into their blocks and collapses, over 3 seconds in total; each cell pops when its response arrives and the winner sends out a pulse ring (decorative; disabled for `prefers-reduced-motion`). Each agent is one cell in the grid and is coloured by the status code of its own real response as it arrives, with a chart of responses over time. If the API is offline, the simulator labels itself SIMULATED and its outcomes are generated locally, not measured.

## Landing Intro (`index.html` only)

`hero-intro.js` plays a short decorative intro: particles (electric blue, soft lavender, acid green; see `PALETTE` in `hero-intro.js`) form a sphere, morph into the Loom logo (sampled from `assets/loom-logo.png`), then the page content fades in. As the particles land, a clean cut-out of the real logo is cross-faded in over them so the finished mark has no gaps. It lasts about 3.8 seconds in total; adjust `TIMING` at the top of `hero-intro.js` to change that. It does not represent any request or protocol data. It plays once per browser session, is skipped for visitors who prefer reduced motion, and can be skipped with a click or any key. Use `?intro=1` to force it or `?intro=0` to disable it. Opened directly from `file://`, the logo cannot be sampled and the particles settle into a ring instead; serve the folder over HTTP for the full effect.

## Landing Animation (`index.html`)

Decorative only, plain CSS and JavaScript. `landing.js` fades and raises sections into view as you scroll (content stays visible without JavaScript). The illustration in the hero loops for 5 seconds with CSS keyframes: agents send along flowing lines, Loom pulses, the winner pops with its "201 lock" label, then the retry agents light up. Buttons and cards have hover states and links have a visible focus outline. With `prefers-reduced-motion` all of it is switched off.

## Current Direction

- Lead with the limited-inventory agent commerce wedge.
- Keep the landing page short and honest, with the live demo one click away; the simulator and its live API status live on `demo.html`.
- The "Tell us what breaks for you" links open a pre-filled GitHub issue; swap the `href` in `index.html` for a form if you prefer.
- Keep claims aligned with the repository: local proof exists, Azure deployment and live service validation still need to be completed.
- Use the website as the public-facing path for judges, validation conversations, and future demo packaging.
