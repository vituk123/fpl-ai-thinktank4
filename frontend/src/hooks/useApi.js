import { useState, useEffect } from 'react';

const useApi = (apiFunction, dependencies = [], immediate = true) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);

  const execute = async (...args) => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiFunction(...args);
      setData(result);
      return result;
    } catch (err) {
      // Normalize error to always be a string or object with message
      const normalizedError = err instanceof Error 
        ? err.message || err.toString()
        : typeof err === 'string' 
        ? err 
        : err?.message || String(err);
      setError(normalizedError);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (immediate) {
      execute();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  const refetch = () => {
    return execute();
  };

  return { data, loading, error, execute, refetch };
};

export default useApi;

