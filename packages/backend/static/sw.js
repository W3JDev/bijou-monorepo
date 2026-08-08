// Bijou AI — Service Worker v1
// Strategy: Cache shell on install, stale-while-revalidate for API calls

const CACHE_NAME = "bijou-ai-v1";
const SHELL_ASSETS = [
  "/static/dashboard.html",
  "/static/manifest.json",
  "/static/bijou-logo.svg",
];

// CDN assets to cache on first fetch (long-lived)
const CDN_PATTERNS = [
  "cdn.tailwindcss.com",
  "unpkg.com/react",
  "unpkg.com/react-dom",
  "unpkg.com/@babel",
  "fonts.googleapis.com",
  "fonts.gstatic.com",
];

// ── Install: pre-cache shell ─────────────────────────────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL_ASSETS).catch(() => {})),
  );
  self.skipWaiting();
});

// ── Activate: clean old caches ───────────────────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)),
        ),
      ),
  );
  self.clients.claim();
});

// ── Fetch: Stale-while-revalidate ────────────────────────────────────────────
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET, chrome-extension, and cross-origin API calls we shouldn't cache
  if (request.method !== "GET") return;
  if (url.protocol === "chrome-extension:") return;

  const isAPI = url.pathname.startsWith("/api/");
  const isCDN = CDN_PATTERNS.some((p) => url.href.includes(p));
  const isShell =
    SHELL_ASSETS.some((a) => url.pathname.endsWith(a)) ||
    url.pathname === "/static/dashboard.html";

  if (isAPI) {
    // Network-first for API, fall back to cache (for offline skeleton)
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(request, clone));
          }
          return res;
        })
        .catch(() => caches.match(request)),
    );
    return;
  }

  if (isShell || isCDN) {
    // Stale-while-revalidate for shell + CDN assets
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) =>
        cache.match(request).then((cached) => {
          const fetched = fetch(request)
            .then((res) => {
              if (res.ok) cache.put(request, res.clone());
              return res;
            })
            .catch(() => cached);
          return cached || fetched;
        }),
      ),
    );
    return;
  }

  // Default: network only
});
