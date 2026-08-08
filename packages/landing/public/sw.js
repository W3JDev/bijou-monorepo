// Bijou AI PWA Service Worker
const CACHE_NAME = "bijou-ai-v2.0.0";
const OFFLINE_URL = "/offline.html";

// Assets to cache on install
const CORE_ASSETS = [
  "/",
  "/index.html",
  "/offline.html",
  "/manifest.json",
  "/icons/icon-base.svg",
];

// API endpoints that should be cached
const API_CACHE_PATTERNS = ["/api/leads", "/api/slide-deck", "/api/send"];

// Install event - cache core assets
self.addEventListener("install", (event) => {
  console.log("[ServiceWorker] Install");

  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        console.log("[ServiceWorker] Caching core assets");
        return cache.addAll(CORE_ASSETS);
      })
      .then(() => {
        console.log("[ServiceWorker] Core assets cached successfully");
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error("[ServiceWorker] Failed to cache core assets:", error);
      }),
  );
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
  console.log("[ServiceWorker] Activate");

  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log("[ServiceWorker] Removing old cache:", cacheName);
              return caches.delete(cacheName);
            }
          }),
        );
      })
      .then(() => {
        console.log("[ServiceWorker] Cache cleanup complete");
        return self.clients.claim();
      }),
  );
});

// Fetch event - serve cached content when offline
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Handle navigation requests (page loads)
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => {
        // If network fails, serve offline page
        return caches.match(OFFLINE_URL);
      }),
    );
    return;
  }

  // Handle API requests with network-first strategy
  if (isApiRequest(url.pathname)) {
    event.respondWith(networkFirstStrategy(request));
    return;
  }

  // Handle static assets with cache-first strategy
  event.respondWith(cacheFirstStrategy(request));
});

// Network-first strategy for API calls
async function networkFirstStrategy(request) {
  const cache = await caches.open(CACHE_NAME);

  try {
    // Try network first
    const networkResponse = await fetch(request);

    // Cache successful responses
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.log("[ServiceWorker] Network failed, trying cache:", request.url);

    // Fallback to cache
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // If no cache, return error response for API calls
    return new Response(
      JSON.stringify({
        error: "Offline - Please check your internet connection",
        offline: true,
      }),
      {
        status: 503,
        statusText: "Service Unavailable",
        headers: { "Content-Type": "application/json" },
      },
    );
  }
}

// Cache-first strategy for static assets
async function cacheFirstStrategy(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    // Serve from cache
    return cachedResponse;
  }

  try {
    // Fetch from network and cache
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log("[ServiceWorker] Failed to fetch asset:", request.url);

    // For images, return a placeholder
    if (request.destination === "image") {
      return new Response(
        '<svg width="300" height="200" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#030810"/><text x="50%" y="50%" text-anchor="middle" fill="#10b981" font-family="Arial">Offline</text></svg>',
        { headers: { "Content-Type": "image/svg+xml" } },
      );
    }

    throw error;
  }
}

// Helper function to check if request is for API
function isApiRequest(pathname) {
  return API_CACHE_PATTERNS.some((pattern) => pathname.startsWith(pattern));
}

// Handle background sync for form submissions when offline
self.addEventListener("sync", (event) => {
  console.log("[ServiceWorker] Background sync:", event.tag);

  if (event.tag === "bijou-lead-sync") {
    event.waitUntil(syncOfflineLeads());
  }
});

// Sync offline form submissions when network returns
async function syncOfflineLeads() {
  console.log("[ServiceWorker] Syncing offline leads");

  try {
    // Implementation would sync pending leads from IndexedDB
    // This is a placeholder for the sync logic
    console.log("[ServiceWorker] Lead sync completed");
  } catch (error) {
    console.error("[ServiceWorker] Lead sync failed:", error);
  }
}

// Push notification handling for Malaysian SME updates
self.addEventListener("push", (event) => {
  console.log("[ServiceWorker] Push received");

  const options = {
    body: event.data ? event.data.text() : "New update from Bijou AI!",
    icon: "/icons/icon-base.svg",
    badge: "/icons/icon-base.svg",
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: "bijou-notification",
    },
    tag: "bijou-update",
    requireInteraction: true,
    actions: [
      {
        action: "open",
        title: "Open Bijou AI",
        icon: "/icons/icon-base.svg",
      },
      {
        action: "close",
        title: "Close",
        icon: "/icons/icon-base.svg",
      },
    ],
  };

  event.waitUntil(
    self.registration.showNotification("Bijou AI Update", options),
  );
});

// Handle notification clicks
self.addEventListener("notificationclick", (event) => {
  console.log("[ServiceWorker] Notification clicked:", event.action);

  event.notification.close();

  if (event.action === "open") {
    event.waitUntil(clients.openWindow("/"));
  }
});
