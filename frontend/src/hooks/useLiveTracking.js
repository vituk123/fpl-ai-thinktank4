import { useState, useEffect, useCallback, useRef } from 'react';
import { liveApi } from '../services/api';

/**
 * Hook for live gameweek tracking with auto-polling
 */
export const useLiveTracking = (gameweek, entryId, options = {}) => {
  const {
    enabled = true,
    pollInterval = 30000, // 30 seconds
    autoStart = true,
  } = options;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isPolling, setIsPolling] = useState(autoStart);
  
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchLiveData = useCallback(async () => {
    if (!gameweek || !entryId || !enabled) {
      console.log('useLiveTracking - fetchLiveData skipped:', { gameweek, entryId, enabled });
      return;
    }

    console.log('useLiveTracking - fetchLiveData called:', { gameweek, entryId });
    setLoading(true);
    setError(null);

    try {
      const response = await liveApi.getGameweek(gameweek, entryId);
      console.log('useLiveTracking - API response:', response);
      
      if (mountedRef.current) {
        // Axios interceptor returns response.data which is the StandardResponse object
        // StandardResponse structure: { data: {...actual data...}, meta: {...}, errors: null }
        // So we need response.data to get the actual data object
        const actualData = response?.data || response;
        console.log('useLiveTracking - extracted data:', actualData);
        setData(actualData);
        setLastUpdate(new Date());
      }
    } catch (err) {
      console.error('useLiveTracking - error:', err);
      if (mountedRef.current) {
        setError(err.message || 'Failed to fetch live data');
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [gameweek, entryId, enabled]);

  // Initial fetch
  useEffect(() => {
    if (isPolling && enabled) {
      fetchLiveData();
    }
  }, [isPolling, enabled, fetchLiveData]);

  // Set up polling interval
  useEffect(() => {
    if (isPolling && enabled && pollInterval > 0) {
      intervalRef.current = setInterval(() => {
        fetchLiveData();
      }, pollInterval);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [isPolling, enabled, pollInterval, fetchLiveData]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const startPolling = useCallback(() => {
    setIsPolling(true);
  }, []);

  const stopPolling = useCallback(() => {
    setIsPolling(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  }, []);

  const refetch = useCallback(() => {
    fetchLiveData();
  }, [fetchLiveData]);

  return {
    data,
    loading,
    error,
    lastUpdate,
    isPolling,
    startPolling,
    stopPolling,
    refetch,
  };
};

export default useLiveTracking;

