import axios from 'axios';
import { EntryInfo, NewsArticle, Prediction, Recommendation, MLReport } from '../types';

// Production Fallback Configuration
// These values are used if import.meta.env is not available (e.g. in browser preview)
const FALLBACK_ENV = {
  VITE_API_BASE_URL: 'https://fpl-api-backend.onrender.com/api/v1',
  VITE_SUPABASE_FUNCTIONS_URL: 'https://sdezcbesdubplacfxibc.supabase.co/functions/v1',
  VITE_SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkZXpjYmVzZHVicGxhY2Z4aWJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQwODAyNTYsImV4cCI6MjA3OTY1NjI1Nn0.hT-2UDR0HbIwAWQHmw6T-QO5jFwWBuyMI2qgPwJRZAE'
};

// Helper to safely get environment variables
const getEnv = (key: keyof typeof FALLBACK_ENV): string => {
  try {
    // @ts-ignore
    const meta = import.meta;
    // @ts-ignore
    if (meta && meta.env && meta.env[key]) {
      // @ts-ignore
      return meta.env[key];
    }
  } catch (e) {
    // Ignore errors accessing import.meta
  }
  return FALLBACK_ENV[key];
};

// Environment Variables
const API_BASE_URL = getEnv('VITE_API_BASE_URL');
const SUPABASE_FUNCTIONS_URL = getEnv('VITE_SUPABASE_FUNCTIONS_URL');
const SUPABASE_ANON_KEY = getEnv('VITE_SUPABASE_ANON_KEY');

// Get Supabase URL for storage (extract from functions URL or use separate env var)
const getSupabaseUrl = (): string => {
  try {
    // Try to get from env var first
    const meta = import.meta;
    // @ts-ignore
    if (meta && meta.env && meta.env.VITE_SUPABASE_URL) {
      // @ts-ignore
      const url = meta.env.VITE_SUPABASE_URL;
      // Remove trailing slash if present
      return url.replace(/\/$/, '');
    }
  } catch (e) {
    // Ignore
  }
  // Extract from functions URL: https://xxx.supabase.co/functions/v1 -> https://xxx.supabase.co
  const functionsUrl = SUPABASE_FUNCTIONS_URL;
  if (functionsUrl) {
    // Match: https://xxx.supabase.co or https://xxx.supabase.co/functions/v1
    const match = functionsUrl.match(/^(https?:\/\/[^\/]+)/);
    if (match) {
      return match[1];
    }
  }
  // Fallback - use the actual Supabase project URL
  return 'https://sdezcbesdubplacfxibc.supabase.co';
};

const SUPABASE_URL = getSupabaseUrl();
// Log for debugging
if (typeof window !== 'undefined') {
  console.log('[Supabase Config] Base URL:', SUPABASE_URL);
  console.log('[Supabase Config] Functions URL:', SUPABASE_FUNCTIONS_URL);
  console.log('[Supabase Config] Example image URL:', `${SUPABASE_URL}/storage/v1/object/public/fpl-images/players/1.png`);
}

// Clients
const renderClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

const supabaseClient = axios.create({
  baseURL: SUPABASE_FUNCTIONS_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
  },
});

export const entryApi = {
  getEntry: async (entryId: number): Promise<EntryInfo> => {
    // ByteHosty server as primary backend
    const bytehostyUrl = 'http://198.23.185.233:8080';
    
    try {
      // Try ByteHosty server first (primary backend)
      const response = await axios.get(`${bytehostyUrl}/api/v1/entry/${entryId}/info`, {
        timeout: 10000
      });
      // Handle both direct data and StandardResponse format
      return response.data?.data || response.data;
    } catch (bytehostyError: any) {
      console.warn(`Entry API: ByteHosty failed for entry ${entryId}, trying Render fallback:`, bytehostyError.message);
      
      // Fallback to Render
      try {
        const response = await renderClient.get(`/entry/${entryId}/info`);
        // Handle both direct data and StandardResponse format
        return response.data?.data || response.data;
      } catch (error: any) {
        console.error("Error fetching entry from both backends:", error);
        
        // Provide more helpful error messages
        if (error.code === 'ERR_NETWORK' || error.message?.includes('ERR_CONNECTION_RESET') || 
            bytehostyError.code === 'ERR_NETWORK' || bytehostyError.message?.includes('ERR_CONNECTION_RESET')) {
          throw new Error('Cannot connect to backend server. The API may be down or unreachable.');
        }
        if (error.response?.status === 404) {
          throw new Error(`Entry ID ${entryId} not found. Please check your entry ID.`);
        }
        if (error.response?.status === 500) {
          throw new Error('Backend server error. Please try again later.');
        }
        
        const message = error.response?.data?.detail || error.response?.data?.error || error.message || 'Failed to fetch entry information';
        throw new Error(message);
      }
    }
  },
  getCurrentGameweek: async (): Promise<number> => {
    // ByteHosty server as primary backend
    const bytehostyUrl = 'http://198.23.185.233:8080';
    try {
      const response = await axios.get(`${bytehostyUrl}/api/v1/gameweek/current`, {
        timeout: 10000
      });
      if (response.data?.data?.gameweek) {
        return response.data.data.gameweek;
      }
      return response.data?.gameweek || 1;
    } catch (error) {
      // Fallback to Render
      try {
        const response = await renderClient.get('/gameweek/current');
        if (response.data?.data?.gameweek) {
          return response.data.data.gameweek;
        }
        return response.data?.gameweek || 1;
      } catch {
        return 1;
      }
    }
  },
};

// Helper function to call dashboard endpoints with ByteHosty primary and Render fallback
const callDashboardEndpoint = async (endpoint: string, params?: Record<string, any>) => {
  const bytehostyUrl = 'http://198.23.185.233:8080';
  const queryString = params ? '?' + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString() : '';
  
  try {
    // Try ByteHosty server first (primary backend)
    const response = await axios.get(`${bytehostyUrl}/api/v1${endpoint}${queryString}`, {
      timeout: 30000 // 30 second timeout (increased for slow database queries)
    });
    return response.data;
  } catch (bytehostyError: any) {
    console.warn(`Dashboard API: ByteHosty failed for ${endpoint}, trying Render fallback:`, bytehostyError.message);
    // Fallback to Render
    try {
      const response = await renderClient.get(`${endpoint}${queryString}`, {
        timeout: 30000 // 30 second timeout
      });
      return response.data;
    } catch (renderError: any) {
      console.error(`Dashboard API: Both ByteHosty and Render failed for ${endpoint}:`, {
        bytehostyError: bytehostyError.message,
        renderError: renderError.message,
        renderStatus: renderError.response?.status
      });
      // Return empty data structure instead of throwing to prevent UI breakage
      // This allows components to render with "NO DATA AVAILABLE" messages
      if (endpoint.includes('ownership-correlation')) {
        return { data: { players: [], correlation_coefficient: null } };
      } else if (endpoint.includes('captain-performance')) {
        return { data: { captains: [] } };
      } else if (endpoint.includes('transfer-analysis')) {
        return { data: { transfers: [] } };
      } else if (endpoint.includes('rank-progression')) {
        return { data: { gameweeks: [], overall_rank: [] } };
      }
      // Generic fallback
      return { data: {} };
    }
  }
};

export const dashboardApi = {
  getTeamHistory: async (entryId: number) => {
    return callDashboardEndpoint('/dashboard/team/rank-progression', { entry_id: entryId });
  },
  getValueTracker: async (entryId: number) => {
    return callDashboardEndpoint('/dashboard/team/value-tracker', { entry_id: entryId });
  },
  getLeagues: async (entryId: number) => {
      const response = await renderClient.get(`/entry/${entryId}/leagues`);
      // Handle StandardResponse format
    return response.data?.data || response.data || [];
  },
  getLeagueStandings: async (entryId: number, leagueId: number) => {
      const response = await renderClient.get(`/entry/${entryId}/league/${leagueId}/standings`);
      // Handle StandardResponse format
    return response.data?.data || response.data || { standings: [], league_name: 'Unknown' };
  },
  getCaptainPerformance: async (entryId: number) => {
    return callDashboardEndpoint('/dashboard/team/captain-performance', { entry_id: entryId });
  },
  getTransferAnalysis: async (entryId: number) => {
    return callDashboardEndpoint('/dashboard/team/transfer-analysis', { entry_id: entryId });
  },
  getOwnershipCorrelation: async (gameweek?: number) => {
    const params = gameweek ? { gameweek } : {};
    return callDashboardEndpoint('/dashboard/ownership-correlation', params);
  }
};

export const liveApi = {
  getLiveGameweek: async (gameweek: number, entryId: number) => {
    console.log(`liveApi.getLiveGameweek: gameweek=${gameweek}, entryId=${entryId}`);
    
    // Try Render backend first (more comprehensive data with minutes, status, opponent, etc.)
    try {
      const url = `/live/gameweek/${gameweek}?entry_id=${entryId}`;
      console.log(`liveApi: Trying Render backend: ${url}`);
      const response = await renderClient.get(url);
      console.log("liveApi: Render backend response:", {
        status: response.status,
        hasData: !!response.data,
        dataKeys: response.data ? Object.keys(response.data) : [],
        dataStructure: response.data
      });
      // Render backend returns: { data: {...}, meta: {...} } in StandardResponse format
      return response.data;
    } catch (renderError: any) {
      console.warn("liveApi: Render backend failed:", {
        message: renderError.message,
        status: renderError.response?.status,
        data: renderError.response?.data
      });
      console.warn("liveApi: Trying Supabase Edge Function as fallback");
      
      // Fallback to Supabase Edge Function
      try {
        const url = `/live-gameweek?gameweek=${gameweek}&entry_id=${entryId}`;
        console.log(`liveApi: Trying Supabase Edge Function: ${url}`);
        const response = await supabaseClient.get(url);
        console.log("liveApi: Supabase Edge Function response:", {
          status: response.status,
          hasData: !!response.data,
          dataKeys: response.data ? Object.keys(response.data) : [],
          dataStructure: response.data
        });
        // Edge Function returns: { data: {...}, meta: {...} }
        return response.data;
      } catch (edgeError: any) {
        console.error("liveApi: Both endpoints failed:", {
          renderError: renderError.message,
          edgeError: edgeError.message,
          edgeStatus: edgeError.response?.status,
          edgeData: edgeError.response?.data
        });
        const message = edgeError.response?.data?.error || edgeError.response?.data?.message || edgeError.message || 'Failed to fetch live data';
      throw new Error(message);
      }
    }
  }
};

export const mlApi = {
  getPredictions: async (gameweek: number, entryId: number): Promise<Prediction[]> => {
    const response = await renderClient.get(`/ml/predictions?gameweek=${gameweek}&entry_id=${entryId}&model_version=v4.6`);
    return response.data;
  },
  getMLPlayers: async (gameweek: number, entryId?: number): Promise<any> => {
    if (!entryId) {
      throw new Error('entry_id is required for ML players');
    }
    // Use Supabase edge function proxy (consistent with other ML endpoints)
    const response = await supabaseClient.get(`/ml-players?entry_id=${entryId}&gameweek=${gameweek}&model_version=v4.6&limit=500`, {
      timeout: 120000 // 2 minute timeout for ML processing
    });
    // Backend returns StandardResponse format: { data: { players: [...] }, meta: {...} }
    const responseData = response.data;
    if (responseData?.data?.players) {
      return responseData.data;
    }
    // Fallback: if it's already the data object
    if (responseData?.players) {
      return responseData;
    }
    console.warn('ML players: Unexpected response format', responseData);
    return { players: [] };
  },
  getMLReport: async (entryId: number, gameweek: number | undefined, fastMode: boolean = true): Promise<MLReport> => {
    // #region agent log
    const logEndpoint = 'http://127.0.0.1:7242/ingest/cbe61e98-98ca-4046-830f-3dbf90ee4a82';
    const runId = `api_${Date.now()}`;
    const logData = (location: string, message: string, data: any, hypothesisId: string) => {
      fetch(logEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: 'debug-session', runId, hypothesisId, location, message, data, timestamp: Date.now() })
      }).catch(() => {});
    };
    logData('api.ts:getMLReport:entry', 'getMLReport called', { entryId, gameweek, fastMode }, 'H');
    // #endregion
    
    // ML page ONLY uses ByteHosty server - no fallbacks
    const bytehostyUrl = 'http://198.23.185.233:8080';
    console.log('mlApi.getMLReport: Calling ByteHosty server (no fallbacks)');
    const params: any = {
      entry_id: entryId,
      model_version: 'v4.6',
      fast_mode: fastMode
    };
    // Only include gameweek if it's provided (backend will use current gameweek if not provided)
    if (gameweek !== undefined && gameweek !== null) {
      params.gameweek = gameweek;
    }
    
    // #region agent log
    logData('api.ts:getMLReport:before_bytehosty', 'Before ByteHosty API call', {
      url: `${bytehostyUrl}/api/v1/ml/report`,
      params
    }, 'I');
    // #endregion
    
    try {
      // Add timestamp to prevent caching
      const response = await axios.get(`${bytehostyUrl}/api/v1/ml/report`, {
        params: {
          ...params,
          _t: Date.now() // Cache buster timestamp
        },
        timeout: 300000, // 5 minute timeout for full ML report
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        }
      });
      
      // #region agent log
      logData('api.ts:getMLReport:after_bytehosty', 'After ByteHosty API call', {
        status: response.status,
        response_gameweek: response.data?.data?.header?.gameweek || response.data?.header?.gameweek,
        has_data: !!response.data?.data,
        response_keys: response.data ? Object.keys(response.data) : []
      }, 'J');
      // #endregion
      
      const responseData = response.data;
      console.log('mlApi.getMLReport: ByteHosty response structure:', {
        has_data_key: !!responseData?.data,
        has_header: !!responseData?.header,
        has_data_header: !!responseData?.data?.header,
        gameweek_in_data: responseData?.data?.header?.gameweek,
        gameweek_in_root: responseData?.header?.gameweek,
        response_keys: responseData ? Object.keys(responseData) : []
      });
      
      // Handle both response formats: { data: {...} } and direct {...}
      if (responseData?.data) {
        console.log('mlApi.getMLReport: Returning nested data, gameweek:', responseData.data?.header?.gameweek);
        return responseData.data;
      }
      console.log('mlApi.getMLReport: Returning root data, gameweek:', responseData?.header?.gameweek);
      return responseData;
    } catch (error: any) {
      // #region agent log
      logData('api.ts:getMLReport:bytehosty_error', 'ByteHosty error - no fallback', {
        error_message: error.message,
        error_status: error.response?.status,
        error_code: error.code
      }, 'K');
      // #endregion
      
      console.error('mlApi.getMLReport: ByteHosty server error:', error.message);
      
      // Provide helpful error messages
      if (error.code === 'ERR_NETWORK' || error.message?.includes('ERR_CONNECTION_RESET') || error.message?.includes('ECONNREFUSED')) {
        throw new Error('Cannot connect to ML server. The ByteHosty server may be down or unreachable.');
      }
      if (error.response?.status === 404) {
        throw new Error(`Entry ID ${entryId} not found on ML server.`);
      }
      if (error.response?.status === 500) {
        throw new Error('ML server error. Please try again later.');
      }
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        throw new Error('ML report generation timed out. The analysis is computationally intensive. Please try again.');
      }
      
      const message = error.response?.data?.detail || error.response?.data?.error || error.message || 'Failed to fetch ML report from ByteHosty server';
      throw new Error(message);
    }
  },
  getRecommendations: async (entryId: number, gameweek: number): Promise<Recommendation[]> => {
    // This is a potentially long-running request (30-60s)
    console.log('mlApi.getRecommendations: Calling Supabase edge function');
    const response = await supabaseClient.get(`/ml-recommendations?entry_id=${entryId}&gameweek=${gameweek}&max_transfers=4`, {
      timeout: 60000 // Extended timeout
    });
    console.log('mlApi.getRecommendations: Response status:', response.status);
    console.log('mlApi.getRecommendations: Response data:', response.data);
    
    // Backend returns StandardResponse format: { data: { recommendations: [...] }, meta: {...} }
    // Supabase edge function passes it through, so response.data is the StandardResponse
    const responseData = response.data;
    console.log('mlApi.getRecommendations: responseData:', responseData);
    console.log('mlApi.getRecommendations: responseData.data:', responseData?.data);
    console.log('mlApi.getRecommendations: responseData.data?.recommendations:', responseData?.data?.recommendations);
    
    // Extract recommendations from the nested structure
    if (responseData?.data?.recommendations) {
      const recs = responseData.data.recommendations;
      console.log('mlApi.getRecommendations: Found recommendations in data.data.recommendations:', recs?.length, recs);
      return recs;
    }
    // Fallback: if it's already an array (legacy format)
    if (Array.isArray(responseData)) {
      console.log('mlApi.getRecommendations: Response is already an array:', responseData.length);
      return responseData;
    }
    // Fallback: if recommendations is at top level
    if (responseData?.recommendations) {
      console.log('mlApi.getRecommendations: Found recommendations at top level:', responseData.recommendations?.length);
      return responseData.recommendations;
    }
    // No recommendations found
    console.warn('ML recommendations: Unexpected response format', responseData);
    return [];
  }
};

export const newsApi = {
  getArticles: async (): Promise<NewsArticle[]> => {
    const response = await renderClient.get('/news/articles?limit=50&offset=0');
    return response.data;
  }
};

export const imagesApi = {
  // Get player image from Supabase storage bucket 'fpl-images' at path 'players/{playerId}.png'
  // Supabase storage public URL format: https://{project}.supabase.co/storage/v1/object/public/{bucket}/{path}
  // Verified: Images are stored at: players/{playerId}.png in the 'fpl-images' bucket
  getPlayerImageUrl: (playerId: number | string | null | undefined) => {
    // Validate inputs
    if (!playerId || playerId === 0) {
      // Return a placeholder or fallback URL
      return `https://resources.fantasy.premierleague.com/drf/element_photos/0.png`;
    }
    
    // Ensure playerId is a number
    const id = typeof playerId === 'string' ? parseInt(playerId, 10) : playerId;
    if (isNaN(id) || id <= 0) {
      return `https://resources.fantasy.premierleague.com/drf/element_photos/0.png`;
    }
    
    // Ensure SUPABASE_URL is defined and valid
    const baseUrl = SUPABASE_URL?.trim();
    if (!baseUrl || baseUrl === 'undefined' || baseUrl === 'null' || !baseUrl.startsWith('http')) {
      console.warn('[imagesApi] SUPABASE_URL is invalid, using FPL fallback for player', id, 'SUPABASE_URL:', SUPABASE_URL);
      return `https://resources.fantasy.premierleague.com/drf/element_photos/${id}.png`;
    }
    
    // Supabase get_public_url adds a query parameter, but it's optional for public buckets
    // We'll use the base URL without query params first
    // Ensure the URL is absolute (starts with http:// or https://)
    const url = `${baseUrl.replace(/\/$/, '')}/storage/v1/object/public/fpl-images/players/${id}.png`;
    
    // Validate the final URL is absolute
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      console.error('[imagesApi] Generated invalid URL (not absolute):', url, 'for player', id);
      return `https://resources.fantasy.premierleague.com/drf/element_photos/${id}.png`;
    }
    
    // Debug logging in development
    if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
      console.log(`[imagesApi] Generated Supabase URL for player ${id}:`, url);
    }
    
    return url;
  },
  // Fallback: FPL API photo URL (same format as backend uses)
  getPlayerImageUrlFPL: (playerId: number | string | null | undefined) => {
    // Validate inputs
    if (!playerId || playerId === 0) {
      return `https://resources.fantasy.premierleague.com/drf/element_photos/0.png`;
    }
    
    // Ensure playerId is a number
    const id = typeof playerId === 'string' ? parseInt(playerId, 10) : playerId;
    if (isNaN(id) || id <= 0) {
      return `https://resources.fantasy.premierleague.com/drf/element_photos/0.png`;
    }
    
    const url = `https://resources.fantasy.premierleague.com/drf/element_photos/${id}.png`;
    if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
      console.log(`[imagesApi] Generated FPL URL for player ${id}:`, url);
    }
    return url;
  },
  getTeamImageUrl: (teamId: number) => `${API_BASE_URL}/images/teams/${teamId}`,
};