// Service Worker for FPL Optimizer
// Cache version - increment on each deployment
const CACHE_VERSION = 'v1';
const STATIC_CACHE = `static-assets-${CACHE_VERSION}`;
const API_CACHE = `api-cache-${CACHE_VERSION}`;
const RUNTIME_CACHE = `runtime-cache-${CACHE_VERSION}`;

// Cache strategies
const CACHE_STRATEGIES = {
  // Static assets: cache-first (long cache)
  STATIC_ASSETS: [
    '/',
    /\.js$/,
    /\.css$/,
    /\.png$/,
    /\.jpg$/,
    /\.jpeg$/,
    /\.svg$/,
    /\.webp$/,
    /\.woff2?$/,
    /\.ttf$/,
    /\.eot$/,
  ],
  // API responses: stale-while-revalidate (short TTL)
  API_RESPONSES: [
    /\/api\/v1\//,
  ],
};

// API response TTL (in milliseconds)
const API_TTL = {
  'entry': 5 * 60 * 1000, // 5 minutes
  'ml/report': 10 * 60 * 1000, // 10 minutes
  'live': 1 * 60 * 1000, // 1 minute
  'bootstrap': 60 * 60 * 1000, // 1 hour
  'default': 5 * 60 * 1000, // 5 minutes default
};

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log('[Service Worker] Caching static assets');
      // Don't pre-cache everything, use runtime caching
      return cache.addAll([
        '/',
        '/logo1.png',
        '/logo2.png',
        '/logo3.png',
      ]).catch((err) => {
        console.warn('[Service Worker] Error caching static assets:', err);
      });
    })
  );
  // Activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => {
            // Delete old cache versions
            return name.startsWith('static-assets-') ||
                   name.startsWith('api-cache-') ||
                   name.startsWith('runtime-cache-') &&
                   name !== STATIC_CACHE &&
                   name !== API_CACHE &&
                   name !== RUNTIME_CACHE;
          })
          .map((name) => {
            console.log('[Service Worker] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  // Take control immediately
  self.clients.claim();
});

// Helper: Check if URL matches pattern
function matchesPattern(url, patterns) {
  const urlString = url.toString();
  return patterns.some((pattern) => {
    if (pattern instanceof RegExp) {
      return pattern.test(urlString);
    }
    if (typeof pattern === 'string') {
      return urlString.includes(pattern);
    }
    return false;
  });
}

// Helper: Get API TTL for a URL
function getApiTTL(url) {
  const urlString = url.toString();
  for (const [key, ttl] of Object.entries(API_TTL)) {
    if (urlString.includes(key)) {
      return ttl;
    }
  }
  return API_TTL.default;
}

// Helper: Check if cached response is still valid
function isCacheValid(cachedResponse, ttl) {
  if (!cachedResponse) return false;
  const cacheDate = cachedResponse.headers.get('sw-cache-date');
  if (!cacheDate) return false;
  const age = Date.now() - parseInt(cacheDate, 10);
  return age < ttl;
}

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other protocols
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Static assets: cache-first strategy
  if (matchesPattern(url, CACHE_STRATEGIES.STATIC_ASSETS)) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(request).then((response) => {
          // Don't cache if not ok
          if (!response.ok) {
            return response;
          }
          const responseToCache = response.clone();
          caches.open(STATIC_CACHE).then((cache) => {
            cache.put(request, responseToCache);
          });
          return response;
        }).catch(() => {
          // Return offline fallback if available
          if (request.destination === 'document') {
            return caches.match('/');
          }
        });
      })
    );
    return;
  }

  // API responses: stale-while-revalidate strategy
  if (matchesPattern(url, CACHE_STRATEGIES.API_RESPONSES)) {
    event.respondWith(
      caches.open(API_CACHE).then((cache) => {
        return cache.match(request).then((cachedResponse) => {
          const ttl = getApiTTL(url);
          const isValid = isCacheValid(cachedResponse, ttl);

          // Fetch fresh data in background
          const fetchPromise = fetch(request).then((response) => {
            if (response.ok) {
              // Add cache date header
              const headers = new Headers(response.headers);
              headers.set('sw-cache-date', Date.now().toString());
              const responseToCache = new Response(response.body, {
                status: response.status,
                statusText: response.statusText,
                headers: headers,
              });
              cache.put(request, responseToCache.clone());
              return response;
            }
            return response;
          }).catch((err) => {
            console.warn('[Service Worker] Fetch error:', err);
            // Return cached response if fetch fails
            return cachedResponse || new Response(JSON.stringify({ error: 'Offline' }), {
              status: 503,
              headers: { 'Content-Type': 'application/json' },
            });
          });

          // Return cached response immediately if valid, otherwise wait for fetch
          if (isValid && cachedResponse) {
            // Return cached, update in background
            fetchPromise.catch(() => {}); // Ignore errors in background update
            return cachedResponse;
          }

          // Cache expired or no cache, wait for fresh response
          return fetchPromise;
        });
      })
    );
    return;
  }

  // Runtime cache: network-first with cache fallback
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache successful responses
        if (response.ok) {
          const responseToCache = response.clone();
          caches.open(RUNTIME_CACHE).then((cache) => {
            cache.put(request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        // Return from cache if network fails
        return caches.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Return offline response
          return new Response('Offline', {
            status: 503,
            headers: { 'Content-Type': 'text/plain' },
          });
        });
      })
  );
});

// Handle messages from clients (for cache invalidation, etc.)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (event.data && event.data.type === 'CACHE_CLEAR') {
    caches.delete(API_CACHE).then(() => {
      event.ports[0].postMessage({ success: true });
    });
  }
});
