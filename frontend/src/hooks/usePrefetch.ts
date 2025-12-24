import { useCallback, useRef } from 'react';

interface PrefetchOptions {
  priority?: 'low' | 'auto' | 'high';
  cancelOnUnmount?: boolean;
}

// Cache of prefetched routes to avoid duplicate prefetches
const prefetchedRoutes = new Set<string>();
const prefetchPromises = new Map<string, Promise<void>>();

/**
 * Hook for prefetching routes and data
 */
export function usePrefetch() {
  const abortControllerRef = useRef<AbortController | null>(null);

  const prefetchRoute = useCallback((routePath: string, options: PrefetchOptions = {}) => {
    const { priority = 'low', cancelOnUnmount = true } = options;

    // Skip if already prefetched or currently prefetching
    if (prefetchedRoutes.has(routePath) || prefetchPromises.has(routePath)) {
      return;
    }

    // Check if user has data saver enabled
    const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection;
    if (connection && connection.saveData) {
      return; // Skip prefetching if data saver is enabled
    }

    // Cancel previous prefetch if cancelOnUnmount is true
    if (cancelOnUnmount && abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    if (cancelOnUnmount) {
      abortControllerRef.current = abortController;
    }

    // Create link element for prefetching
    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.as = 'document';
    link.href = routePath;
    if (priority === 'high') {
      (link as any).fetchPriority = 'high';
    }
    document.head.appendChild(link);

    prefetchedRoutes.add(routePath);
    
    // Clean up link element after a short delay
    setTimeout(() => {
      if (document.head.contains(link)) {
        document.head.removeChild(link);
      }
    }, 1000);
  }, []);

  const prefetchData = useCallback(async (url: string, options: PrefetchOptions = {}) => {
    const { priority = 'low', cancelOnUnmount = true } = options;

    // Skip if already prefetched or currently prefetching
    if (prefetchedRoutes.has(url) || prefetchPromises.has(url)) {
      return;
    }

    // Check if user has data saver enabled
    const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection;
    if (connection && connection.saveData) {
      return;
    }

    // Cancel previous prefetch if cancelOnUnmount is true
    if (cancelOnUnmount && abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    if (cancelOnUnmount) {
      abortControllerRef.current = abortController;
    }

    const fetchOptions: RequestInit = {
      method: 'GET',
      signal: abortController.signal,
      priority: priority,
    };

    const prefetchPromise = fetch(url, fetchOptions)
      .then(() => {
        prefetchedRoutes.add(url);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          console.warn(`[Prefetch] Failed to prefetch ${url}:`, err);
        }
      })
      .finally(() => {
        prefetchPromises.delete(url);
      });

    prefetchPromises.set(url, prefetchPromise);
    return prefetchPromise;
  }, []);

  return {
    prefetchRoute,
    prefetchData,
  };
}
