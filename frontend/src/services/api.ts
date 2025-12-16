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
    try {
      const response = await renderClient.get(`/entry/${entryId}/info`);
      // Handle both direct data and StandardResponse format
      return response.data?.data || response.data;
    } catch (error: any) {
      console.error("Error fetching entry:", error);
      
      // Provide more helpful error messages
      if (error.code === 'ERR_NETWORK' || error.message?.includes('ERR_CONNECTION_RESET')) {
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
  },
  getCurrentGameweek: async (): Promise<number> => {
    try {
      // Try GCE VM first
      const gceVmUrl = 'http://35.192.15.52';
      const response = await axios.get(`${gceVmUrl}/api/v1/gameweek/current`, {
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

// Helper function to call dashboard endpoints with GCE VM fallback
const callDashboardEndpoint = async (endpoint: string, params?: Record<string, any>) => {
  const gceVmUrl = 'http://35.192.15.52';
  const queryString = params ? '?' + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString() : '';
  
  try {
    // Try GCE VM first (where new endpoints are deployed)
    const response = await axios.get(`${gceVmUrl}/api/v1${endpoint}${queryString}`, {
      timeout: 30000 // 30 second timeout (increased for slow database queries)
    });
    return response.data;
  } catch (gceError: any) {
    console.warn(`Dashboard API: GCE VM failed for ${endpoint}, trying Render fallback:`, gceError.message);
    // Fallback to Render
    try {
      const response = await renderClient.get(`${endpoint}${queryString}`, {
        timeout: 30000 // 30 second timeout
      });
      return response.data;
    } catch (renderError: any) {
      console.error(`Dashboard API: Both GCE VM and Render failed for ${endpoint}:`, {
        gceError: gceError.message,
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
    // Try GCP directly first for full mode (bypasses Supabase 60s timeout)
    // For fast mode, use Supabase edge function (faster, stays under timeout)
    const useDirectGCP = !fastMode; // Use direct GCP for full mode
    
    if (useDirectGCP) {
      // Call GCE VM directly to avoid Supabase timeout for full ML analysis
      const gceVmUrl = 'http://35.192.15.52';
      console.log('mlApi.getMLReport: Calling GCE VM directly for full ML report');
      const params: any = {
        entry_id: entryId,
        model_version: 'v4.6',
        fast_mode: fastMode
      };
      // Only include gameweek if it's provided (backend will use current gameweek if not provided)
      if (gameweek !== undefined && gameweek !== null) {
        params.gameweek = gameweek;
      }
      const response = await axios.get(`${gceVmUrl}/api/v1/ml/report`, {
        params: params,
        timeout: 300000 // 5 minute timeout for full ML report
      });
      const responseData = response.data;
      if (responseData?.data) {
        return responseData.data;
      }
      return responseData;
    } else {
      // Use Supabase edge function for fast mode (stays under 60s timeout)
      const params = new URLSearchParams({
        entry_id: String(entryId),
        model_version: 'v4.6',
        fast_mode: String(fastMode)
      });
      // Only include gameweek if it's provided
      if (gameweek !== undefined && gameweek !== null) {
        params.append('gameweek', String(gameweek));
      }
      const response = await supabaseClient.get(`/ml-report?${params.toString()}`, {
        timeout: 60000 // 1 minute timeout for fast mode
      });
      // Backend returns StandardResponse format: { data: {...}, meta: {...} }
      const responseData = response.data;
      if (responseData?.data) {
        return responseData.data;
      }
      // Fallback: if it's already the data object
      return responseData;
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
  getPlayerImageUrl: (playerId: number) => {
    // Supabase get_public_url adds a query parameter, but it's optional for public buckets
    // We'll use the base URL without query params first
    const url = `${SUPABASE_URL}/storage/v1/object/public/fpl-images/players/${playerId}.png`;
    return url;
  },
  // Fallback: FPL API photo URL (same format as backend uses)
  getPlayerImageUrlFPL: (playerId: number) => {
    const url = `https://resources.fantasy.premierleague.com/drf/element_photos/${playerId}.png`;
    if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
      console.log(`[imagesApi] Generated FPL URL for player ${playerId}:`, url);
    }
    return url;
  },
  getTeamImageUrl: (teamId: number) => `${API_BASE_URL}/images/teams/${teamId}`,
};