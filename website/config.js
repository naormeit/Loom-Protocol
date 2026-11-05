// Site-wide settings. Leave apiUrl empty for local use (the demo then talks to
// http://127.0.0.1:8080). When you publish the site, set it to your hosted Loom
// gateway, for example "https://loom-api.example.com", and add the site's origin
// to the gateway's LOOM_ALLOWED_ORIGINS. A ?api=... query parameter overrides it.
window.LOOM_CONFIG = {
  apiUrl: ""
};
