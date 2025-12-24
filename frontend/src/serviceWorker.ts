// Service Worker registration and update handling

const isLocalhost = Boolean(
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1' ||
  window.location.hostname === '[::1]' ||
  window.location.hostname.includes('192.168.') ||
  window.location.hostname.includes('10.0.')
);

export function register(): void {
  if ('serviceWorker' in navigator) {
    // Check if user has data saver enabled
    const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection;
    if (connection && connection.saveData) {
      console.log('[Service Worker] Data saver enabled, skipping registration');
      return;
    }

    const publicUrl = new URL(import.meta.env.PUBLIC_URL || '/', window.location.href);
    if (publicUrl.origin !== window.location.origin) {
      return;
    }

    window.addEventListener('load', () => {
      const swUrl = `${import.meta.env.PUBLIC_URL || ''}/sw.js`;

      if (isLocalhost) {
        // Check if service worker exists locally
        checkValidServiceWorker(swUrl);
      } else {
        // Register service worker for production
        registerValidSW(swUrl);
      }
    });
  }
}

function registerValidSW(swUrl: string): void {
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      console.log('[Service Worker] Registered:', registration);

      registration.onupdatefound = () => {
        const installingWorker = registration.installing;
        if (installingWorker == null) {
          return;
        }

        installingWorker.onstatechange = () => {
          if (installingWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              // New service worker available
              console.log('[Service Worker] New content available, please refresh');
              // Optionally show update notification to user
              if (window.confirm('New version available. Reload to update?')) {
                window.location.reload();
              }
            } else {
              // Content cached for offline use
              console.log('[Service Worker] Content cached for offline use');
            }
          }
        };
      };
    })
    .catch((error) => {
      console.error('[Service Worker] Registration failed:', error);
    });

  // Listen for updates
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    window.location.reload();
  });
}

function checkValidServiceWorker(swUrl: string): void {
  fetch(swUrl, {
    headers: { 'Service-Worker': 'script' },
  })
    .then((response) => {
      const contentType = response.headers.get('content-type');
      if (
        response.status === 404 ||
        (contentType != null && !contentType.includes('javascript'))
      ) {
        // No service worker found
        navigator.serviceWorker.ready.then((registration) => {
          registration.unregister().then(() => {
            window.location.reload();
          });
        });
      } else {
        // Service worker found, proceed with registration
        registerValidSW(swUrl);
      }
    })
    .catch(() => {
      console.log('[Service Worker] No internet connection found. App is running in offline mode.');
    });
}

export function unregister(): void {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister();
      })
      .catch((error) => {
        console.error(error.message);
      });
  }
}
