/**
 * Order-to-Audit App Shell Service Worker
 * - Pre-caches only /static/ static assets and generic /offline/ fallback page.
 * - NEVER caches authenticated HTML responses.
 * - Navigation requests fall back to /offline/ when network fails.
 * - Clears all caches on user logout via postMessage({ action: 'CLEAR_CACHES' }).
 */

const CACHE_NAME = 'ota-static-v1.1.0';

const STATIC_PRECACHE = [
  '/offline/',
  '/static/manifest.webmanifest',
  '/static/dist/app.min.css',
  '/static/js/app.js',
  '/static/js/motion/tokens.js',
  '/static/js/motion/registry.js',
  '/static/vendor/htmx.min.js',
  '/static/vendor/alpine.min.js',
  '/static/fonts/inter-latin-400-normal.woff2',
  '/static/fonts/inter-latin-600-normal.woff2',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png',
  '/static/img/icon-maskable-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return Promise.allSettled(
        STATIC_PRECACHE.map((url) =>
          cache.add(url).catch((err) => {
            console.debug(`[SW] Pre-cache skipped for: ${url}`, err.message);
          })
        )
      );
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Ignore cross-origin and non-GET requests
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // Navigation requests: Network-ONLY for authenticated security.
  // Falls back to generic /offline/ if disconnected.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => {
        return caches.match('/offline/').then((cached) => {
          return cached || new Response('Network offline. Please reconnect.', {
            status: 503,
            headers: { 'Content-Type': 'text/plain' }
          });
        });
      })
    );
    return;
  }

  // Static assets (/static/): Stale-While-Revalidate
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        const fetchPromise = fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          }
          return networkResponse;
        }).catch(() => cachedResponse);

        return cachedResponse || fetchPromise;
      })
    );
  }
});

// Logout Cache Clearance Handler
self.addEventListener('message', (event) => {
  if (event.data && event.data.action === 'CLEAR_CACHES') {
    event.waitUntil(
      caches.keys().then((keys) => {
        return Promise.all(keys.map((key) => caches.delete(key)));
      }).then(() => {
        console.debug('[SW] All authenticated cache stores purged upon logout.');
        if (event.ports && event.ports[0]) {
          event.ports[0].postMessage({ status: 'cleared' });
        }
      })
    );
  }
});
