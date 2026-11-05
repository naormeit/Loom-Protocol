# Loom Protocol Main Website

This is the static main website for the Imagine Cup 2027 submission story.

Open `index.html` directly in a browser. No build step or package install is required.
When Live Server is started from the repository root, the root `index.html` redirects to `website/`.

## Live Backend Demo

Start the Loom API before using the simulator as technical proof:

```powershell
python -m core.api.server
```

The website checks `http://127.0.0.1:8080/health` by default. To point it at a hosted backend, open the page with `?api=https://<your-host>` (http/https origins only); the endpoint shown in the page updates to match. If the API is available, the Run button sends real `POST /v1/handshake` packets and displays actual `201` lock and `409` conflict counts. Each agent is one cell in the grid and is coloured by the status code of its own real response as it arrives, with a chart of responses over time. If the API is offline, the simulator labels itself SIMULATED and its outcomes are generated locally, not measured.

## Landing Intro

`hero-intro.js` plays a short decorative intro: particles form a sphere, morph into the Loom logo (sampled from `assets/loom-logo.png`), then the page content fades in. It lasts about 3.8 seconds in total; adjust `TIMING` at the top of `hero-intro.js` to change that. It does not represent any request or protocol data. It plays once per browser session, is skipped for visitors who prefer reduced motion, and can be skipped with a click or any key. Use `?intro=1` to force it or `?intro=0` to disable it. Opened directly from `file://`, the logo cannot be sampled and the particles settle into a ring instead; serve the folder over HTTP for the full effect.

## Current Direction

- Lead with the limited-inventory agent commerce wedge.
- Make the first viewport useful with the collision simulator and live API status.
- Keep claims aligned with the repository: local proof exists, Azure deployment and live service validation still need to be completed.
- Use the website as the public-facing path for judges, validation conversations, and future demo packaging.
