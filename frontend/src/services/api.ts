import axios from 'axios';
import { EntryInfo, NewsArticle, Prediction, Recommendation } from '../types';

// Production Fallback Configuration
// These values are used if import.meta.env is not available (e.g. in browser preview)
const FALLBACK_ENV = {
  VITE_API_BASE_URL: 'https://fpl-api-backend.onrender.com/api/v1',
  VITE_SUPABASE_FUNCTIONS_URL: 'https://sdezcbesdubplacfxibc.supabase.co/functions/v1',
  VITE_SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNkZXpjYmVzZHVicGxhY2Z4aWJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQwODAyNTYsImV4cCI6MjA3OTY1NjI1Nn0.hT-2UDR0HbIwAWQHmw6T-QO5jFwWBuyMI2qgPwJRZAE',
  VITE_SUPABASE_URL: 'https://sdezcbesdubplacfxibc.supabase.co'
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
  // Return fallback value
  return FALLBACK_ENV[key] || '';
};

// Environment Variables
const API_BASE_URL = getEnv('VITE_API_BASE_URL');
const SUPABASE_FUNCTIONS_URL = getEnv('VITE_SUPABASE_FUNCTIONS_URL');
const SUPABASE_ANON_KEY = getEnv('VITE_SUPABASE_ANON_KEY');
const SUPABASE_URL = getEnv('VITE_SUPABASE_URL') || 'https://sdezcbesdubplacfxibc.supabase.co';

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
      // Backend returns StandardResponse with data field containing full entry info
      const responseData = response.data?.data || response.data;
      
      // Map backend response to EntryInfo interface
      const entryInfo: EntryInfo = {
        id: responseData.id || responseData.entry_id || entryId,
        player_first_name: responseData.player_first_name || '',
        player_last_name: responseData.player_last_name || '',
        player_region_name: responseData.player_region_name || '',
        player_region_iso_code_short: responseData.player_region_iso_code_short || '',
        player_region_iso_code_long: responseData.player_region_iso_code_long || '',
        summary_overall_points: responseData.summary_overall_points || 0,
        summary_overall_rank: responseData.summary_overall_rank || 0,
        summary_event_points: responseData.summary_event_points || 0,
        summary_event_rank: responseData.summary_event_rank || 0,
        current_event: responseData.current_event || 1,
        name: responseData.name || responseData.team_name || 'Unknown Team',
        kit: responseData.kit,
      };
      
      return entryInfo;
    } catch (error: any) {
      console.error("Error fetching entry:", error);
      const message = error.response?.status === 404 
        ? `Entry ID ${entryId} not found. Please check your entry ID.`
        : error.response?.data?.detail || error.message || 'Failed to fetch entry information';
      throw new Error(message);
    }
  },
};

export const dashboardApi = {
  getTeamHistory: async (entryId: number) => {
    try {
    const response = await renderClient.get(`/dashboard/team/rank-progression?entry_id=${entryId}`);
      // Handle both direct data and nested data structure
      return response.data?.data || response.data || response;
    } catch (error: any) {
      console.error("Error fetching team history:", error);
      const message = error.response?.status === 404
        ? 'Rank progression endpoint not found. The backend may need to be updated.'
        : error.response?.data?.detail || error.message || 'Failed to fetch team history';
      throw new Error(message);
    }
  },
  getValueTracker: async (entryId: number) => {
    // This endpoint may not exist in all backend versions
    try {
    const response = await renderClient.get(`/dashboard/team/value-tracker?entry_id=${entryId}`);
      // Handle both direct data and nested data structure
      return response.data?.data || response.data || response;
    } catch (error: any) {
      // If 404, return null to indicate endpoint doesn't exist
      if (error.response?.status === 404) {
        console.warn('Value tracker endpoint not available');
        return null;
      }
      console.error("Error fetching value tracker:", error);
      throw error;
    }
  },
  getCurrentGameweek: async () => {
    try {
      const response = await renderClient.get(`/api/v1/gameweek/current`);
      return response.data?.data || response.data || null;
    } catch (error: any) {
      console.error("Error fetching current gameweek:", error);
      const message = error.response?.data?.detail || error.message || 'Failed to fetch current gameweek';
      throw new Error(message);
    }
  },
  getLeagues: async (entryId: number) => {
    try {
      const response = await renderClient.get(`/api/v1/entry/${entryId}/leagues`);
      // Handle StandardResponse format
      if (response.data?.data) {
        return Array.isArray(response.data.data) ? response.data.data : [];
      }
      return Array.isArray(response.data) ? response.data : [];
    } catch (error: any) {
      console.error("Error fetching leagues:", error);
      if (error.response?.status === 404) {
        throw new Error('Leagues endpoint not found. Backend may need to be updated.');
      }
      const message = error.response?.data?.detail || error.response?.data?.error || error.message || 'Failed to fetch leagues';
      throw new Error(message);
    }
  },
  getLeagueStandings: async (entryId: number, leagueId: number) => {
    try {
      const response = await renderClient.get(`/api/v1/entry/${entryId}/league/${leagueId}/standings`);
      // Handle StandardResponse format
      if (response.data?.data) {
        return response.data.data;
      }
      return response.data || { standings: [], league_name: 'Unknown' };
    } catch (error: any) {
      console.error("Error fetching league standings:", error);
      if (error.response?.status === 404) {
        throw new Error('League standings endpoint not found. Backend may need to be updated.');
      }
      const message = error.response?.data?.detail || error.response?.data?.error || error.message || 'Failed to fetch league standings';
      throw new Error(message);
    }
  }
};

export const liveApi = {
  getLiveGameweek: async (gameweek: number, entryId: number) => {
    try {
      const response = await supabaseClient.get(`/live-gameweek?gameweek=${gameweek}&entry_id=${entryId}`);
      // Supabase Edge Function returns { data: {...}, meta: {...} }
      // Handle both direct data and nested data structure
      if (response.data) {
        return response.data; // Already has data and meta fields
      }
      return response;
    } catch (error: any) {
      console.error("Error fetching live data:", error);
      const message = error.response?.data?.error || error.response?.data?.message || error.message || 'Failed to load live data';
      throw new Error(message);
    }
  }
};

export const mlApi = {
  getPredictions: async (gameweek: number, entryId: number): Promise<Prediction[]> => {
    const response = await renderClient.get(`/ml/predictions?gameweek=${gameweek}&entry_id=${entryId}&model_version=v4.6`);
    // Handle both direct array and nested predictions structure
    return response.data?.predictions || response.data || [];
  },
  getRecommendations: async (entryId: number, gameweek: number): Promise<Recommendation[]> => {
    // This is a potentially long-running request (30-60s)
    const response = await supabaseClient.get(`/ml-recommendations?entry_id=${entryId}&gameweek=${gameweek}&max_transfers=4`, {
      timeout: 60000 // Extended timeout
    });
    // Handle both direct array and nested recommendations structure
    return response.data?.recommendations || response.data || [];
  }
};

export const newsApi = {
  getArticles: async (): Promise<NewsArticle[]> => {
    const response = await renderClient.get('/news/articles?limit=50&offset=0');
    // Handle both direct array and nested articles structure
    return response.data?.articles || response.data || [];
  }
};

export const imagesApi = {
  getPlayerImageUrl: (playerId: number) => {
    // Use Supabase storage - images are stored at players/{player_id}.png
    // Bucket name: fpl-images
    return `${SUPABASE_URL}/storage/v1/object/public/fpl-images/players/${playerId}.png`;
  },
  getTeamImageUrl: (teamId: number) => {
    // Use Supabase storage - team logos are stored at teams/{team_id}.png
    return `${SUPABASE_URL}/storage/v1/object/public/fpl-images/teams/${teamId}.png`;
  },
  // Direct FPL URLs as fallback (if Supabase image doesn't exist)
  getFPLPlayerImageUrl: (photoCode: string) => {
    // FPL direct player photo URL
    // photoCode format: "123456" (string from FPL API)
    return `https://resources.premierleague.com/premierleague/photos/players/250x250/p${photoCode}.png`;
  },
  getFPLTeamImageUrl: (teamCode: number) => {
    // FPL direct team logo URL
    return `https://resources.premierleague.com/premierleague/badges/t${teamCode}.png`;
  },
};