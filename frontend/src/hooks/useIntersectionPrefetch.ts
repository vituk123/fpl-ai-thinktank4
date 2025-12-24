import { useEffect, useRef } from 'react';
import { usePrefetch } from './usePrefetch';

interface UseIntersectionPrefetchOptions {
  root?: Element | null;
  rootMargin?: string;
  threshold?: number;
  enabled?: boolean;
}

/**
 * Hook to prefetch routes when links enter viewport using Intersection Observer
 */
export function useIntersectionPrefetch(
  elementRef: React.RefObject<Element>,
  routePath: string,
  options: UseIntersectionPrefetchOptions = {}
) {
  const { root = null, rootMargin = '200px', threshold = 0, enabled = true } = options;
  const { prefetchRoute } = usePrefetch();
  const observerRef = useRef<IntersectionObserver | null>(null);
  const hasPrefetchedRef = useRef(false);

  useEffect(() => {
    if (!enabled || !elementRef.current || hasPrefetchedRef.current) {
      return;
    }

    // Check if user has data saver enabled
    const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection;
    if (connection && connection.saveData) {
      return;
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasPrefetchedRef.current) {
            hasPrefetchedRef.current = true;
            prefetchRoute(routePath, { priority: 'low' });
            // Disconnect after prefetching
            if (observerRef.current) {
              observerRef.current.disconnect();
            }
          }
        });
      },
      {
        root,
        rootMargin,
        threshold,
      }
    );

    observerRef.current.observe(elementRef.current);

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [elementRef, routePath, root, rootMargin, threshold, enabled, prefetchRoute]);
}
