# Loom Protocol Main Website

This is the static main website for the Imagine Cup 2027 submission story.

Open `index.html` directly in a browser. No build step or package install is required.
When Live Server is started from the repository root, the root `index.html` redirects to `website/`.

## Live Backend Demo

Start the Loom API before using the simulator as technical proof:

```powershell
python -m core.api.server
```

The website checks `http://127.0.0.1:8080/health` by default. To point it at a hosted backend, open the page with `?api=https://<your-host>` (http/https origins only); the endpoint shown in the page updates to match. If the API is available, the Run button sends real `POST /v1/handshake` packets and displays actual `201` lock and `409` conflict counts. If the API is offline, the simulator labels itself as visual fallback mode.

## Current Direction

- Lead with the limited-inventory agent commerce wedge.
- Make the first viewport useful with the collision simulator and live API status.
- Keep claims aligned with the repository: local proof exists, Azure deployment and live service validation still need to be completed.
- Use the website as the public-facing path for judges, validation conversations, and future demo packaging.
