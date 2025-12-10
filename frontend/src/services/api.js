import axios from 'axios';

// API URLs - can be configured via environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const SUPABASE_FUNCTIONS_URL = import.meta.env.VITE_SUPABASE_FUNCTIONS_URL || 'http://localhost:54321/functions/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // Increased to 60 seconds for ML predictions
});

// Edge Functions API client (for lightweight endpoints)
const edgeApi = axios.create({
  baseURL: SUPABASE_FUNCTIONS_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds for lightweight endpoints
});

// Edge API response interceptor
edgeApi.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response) {
      const errorMessage = error.response.data?.error || error.response.data?.detail || 'An error occurred';
      return Promise.reject(new Error(errorMessage));
    } else if (error.request) {
      const errorMsg = error.code === 'ECONNABORTED' 
        ? 'Request timed out. The server is taking too long to respond.'
        : 'Network error. Please check your connection.';
      return Promise.reject(new Error(errorMsg));
    } else {
      return Promise.reject(new Error(error.message || 'An unexpected error occurred'));
    }
  }
);

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response) {
      // Server responded with error
      const errorMessage = error.response.data?.error || error.response.data?.detail || 'An error occurred';
      return Promise.reject(new Error(errorMessage));
    } else if (error.request) {
      // Request made but no response
      const errorMsg = error.code === 'ECONNABORTED' 
        ? 'Request timed out. The server is taking too long to respond.'
        : error.code === 'ECONNREFUSED'
        ? 'Cannot connect to server. Please ensure the backend is running on port 8000.'
        : 'Network error. Please check your connection and ensure the backend server is running.';
      return Promise.reject(new Error(errorMsg));
    } else {
      // Error in request setup
      return Promise.reject(new Error(error.message || 'An unexpected error occurred'));
    }
  }
);

// Dashboard Analytics - Team Endpoints
export const dashboardApi = {
  // Team-specific analytics
  getHeatmap: (entryId, season = null) => {
    const params = { entry_id: entryId };
    if (season) params.season = season;
    return api.get('/dashboard/team/heatmap', { params });
  },

  getValueTracker: (entryId, season = null) => {
    const params = { entry_id: entryId };
    if (season) params.season = season;
    return api.get('/dashboard/team/value-tracker', { params });
  },

  getTransfers: (entryId, season = null) => {
    const params = { entry_id: entryId };
    if (season) params.season = season;
    return api.get('/dashboard/team/transfers', { params });
  },

  getPositionBalance: (entryId, gameweek = null) => {
    const params = { entry_id: entryId };
    if (gameweek) params.gameweek = gameweek;
    return api.get('/dashboard/team/position-balance', { params });
  },

  getChips: (entryId, season = null) => {
    const params = { entry_id: entryId };
    if (season) params.season = season;
    return api.get('/dashboard/team/chips', { params });
  },

  getCaptain: (entryId, season = null) => {
    const params = { entry_id: entryId };
    if (season) params.season = season;
    return api.get('/dashboard/team/captain', { params });
  },

  getRankProgression: (entryId, season = null) => {
    const params = { entry_id: entryId };
    if (season) params.season = season;
    return api.get('/dashboard/team/rank-progression', { params });
  },

  getValueEfficiency: (entryId, season = null) => {
    const params = { entry_id: entryId };
    if (season) params.season = season;
    return api.get('/dashboard/team/value-efficiency', { params });
  },

  // League-wide analytics
  getOwnershipCorrelation: (season = null, gameweek = null) => {
    const params = {};
    if (season) params.season = season;
    if (gameweek) params.gameweek = gameweek;
    return api.get('/dashboard/league/ownership-correlation', { params });
  },

  getTemplateTeam: (season = null, gameweek = null) => {
    const params = {};
    if (season) params.season = season;
    if (gameweek) params.gameweek = gameweek;
    return api.get('/dashboard/league/template-team', { params });
  },

  getPricePredictors: (season = null, gameweek = null) => {
    const params = {};
    if (season) params.season = season;
    if (gameweek) params.gameweek = gameweek;
    return api.get('/dashboard/league/price-predictors', { params });
  },

  getPositionDistribution: (season = null, gameweek = null) => {
    const params = {};
    if (season) params.season = season;
    if (gameweek) params.gameweek = gameweek;
    return api.get('/dashboard/league/position-distribution', { params });
  },

  getFixtureSwing: (season = null, gameweek = null, lookahead = 5) => {
    const params = { lookahead };
    if (season) params.season = season;
    if (gameweek) params.gameweek = gameweek;
    return api.get('/dashboard/league/fixture-swing', { params });
  },

  getDgwProbability: (season = null, gameweek = null, lookahead = 10) => {
    const params = { lookahead };
    if (season) params.season = season;
    if (gameweek) params.gameweek = gameweek;
    return api.get('/dashboard/league/dgw-probability', { params });
  },

  getPriceBrackets: (season = null, gameweek = null) => {
    const params = {};
    if (season) params.season = season;
    if (gameweek) params.gameweek = gameweek;
    return api.get('/dashboard/league/price-brackets', { params });
  },
};

// News Endpoints
export const newsApi = {
  getArticles: (limit = 50, offset = 0, daysBack = null) => {
    const params = { limit, offset };
    if (daysBack) params.days_back = daysBack;
    return api.get('/news/articles', { params });
  },

  getArticle: (articleId) => {
    return api.get(`/news/articles/${articleId}`);
  },

  getSummaries: (limit = 50, minRelevance = 0.3) => {
    return api.get('/news/summaries', {
      params: { limit, min_relevance: minRelevance },
    });
  },
};

// Images Endpoints
export const imagesApi = {
  getPlayerImage: (playerId) => {
    return api.get(`/images/players/${playerId}`);
  },

  getPlayerImages: (playerIds) => {
    const idsString = Array.isArray(playerIds) ? playerIds.join(',') : playerIds;
    return api.get('/images/players', { params: { player_ids: idsString } });
  },

  getTeamLogo: (teamId) => {
    return api.get(`/images/teams/${teamId}`);
  },

  getAllTeamLogos: () => {
    return api.get('/images/teams');
  },
};

// Live Tracking Endpoints
// Entry Info Endpoints
export const entryApi = {
  getEntryInfo: (entryId) => {
    return api.get(`/entry/${entryId}/info`);
  },
};

export const liveApi = {
  // Use Edge Function for lightweight live tracking
  getGameweek: (gameweek, entryId) => {
    return edgeApi.get(`/live-gameweek`, {
      params: { gameweek, entry_id: entryId },
    });
  },

  getPoints: (gameweek, entryId) => {
    return edgeApi.get(`/live-gameweek`, {
      params: { gameweek, entry_id: entryId },
    });
  },

  getBreakdown: (gameweek, entryId) => {
    return edgeApi.get(`/live-gameweek`, {
      params: { gameweek, entry_id: entryId },
    });
  },
};

// Transfer Recommendations Endpoints
export const recommendationsApi = {
  // Use Edge Function proxy (which forwards to Render FastAPI) for ML recommendations
  getRecommendations: (entryId, gameweek = null, maxTransfers = 4, forcedOutIds = null) => {
    const params = { entry_id: entryId, max_transfers: maxTransfers };
    if (gameweek) params.gameweek = gameweek;
    if (forcedOutIds) {
      const idsString = Array.isArray(forcedOutIds) ? forcedOutIds.join(',') : forcedOutIds;
      params.forced_out_ids = idsString;
    }
    // Route through Edge Function proxy for ML recommendations
    return edgeApi.get('/ml-recommendations', { params });
  },

  generateRecommendations: (requestData) => {
    // Route through Edge Function proxy
    return edgeApi.post('/ml-recommendations', requestData);
  },
};

// ML Predictions Endpoints (direct to FastAPI, not Edge Function)
export const mlApi = {
  // Get predictions from database
  getPredictions: (gameweek = null, entryId = null, modelVersion = 'v4.6') => {
    const params = { model_version: modelVersion };
    if (gameweek) params.gameweek = gameweek;
    if (entryId) params.entry_id = entryId;
    return api.get('/ml/predictions', { params });
  },
  // Generate new ML predictions (triggers training + prediction)
  generatePredictions: (gameweek = 999, modelVersion = 'v4.6') => {
    return api.post('/ml/predictions/generate', null, {
      params: {
        gameweek: gameweek,
        model_version: modelVersion
      }
    });
  },
};

// Utility Endpoints
export const utilityApi = {
  getHealth: () => {
    return api.get('/health');
  },

  getInfo: () => {
    return api.get('/info');
  },
};

export default api;

