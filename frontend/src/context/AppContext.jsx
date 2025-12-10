import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { liveApi, utilityApi } from '../services/api';

const AppContext = createContext(null);

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
};

/**
 * Extract team ID from URL hash
 * Supports formats:
 * - /#/25/team/2568103/league/1096128
 * - /#/team/2568103
 * - /#/25/team/2568103
 */
const extractTeamIdFromHash = () => {
  if (typeof window === 'undefined') return null;
  
  const hash = window.location.hash;
  if (!hash) return null;
  
  // Match patterns like /team/2568103 or /25/team/2568103
  const teamMatch = hash.match(/\/team\/(\d+)/);
  if (teamMatch && teamMatch[1]) {
    const teamId = parseInt(teamMatch[1], 10);
    if (!isNaN(teamId) && teamId > 0) {
      return teamId;
    }
  }
  
  return null;
};

/**
 * Extract gameweek from URL hash
 */
const extractGameweekFromHash = () => {
  if (typeof window === 'undefined') return null;
  
  const hash = window.location.hash;
  if (!hash) return null;
  
  // Match pattern like /25/team/2568103 (gameweek before /team/)
  const gameweekMatch = hash.match(/^\/(\d+)\/team\//);
  if (gameweekMatch && gameweekMatch[1]) {
    const gameweek = parseInt(gameweekMatch[1], 10);
    if (!isNaN(gameweek) && gameweek > 0) {
      return gameweek;
    }
  }
  
  return null;
};

/**
 * Extract league ID from URL hash
 */
const extractLeagueIdFromHash = () => {
  if (typeof window === 'undefined') return null;
  
  const hash = window.location.hash;
  if (!hash) return null;
  
  // Match pattern like /league/1096128
  const leagueMatch = hash.match(/\/league\/(\d+)/);
  if (leagueMatch && leagueMatch[1]) {
    const leagueId = parseInt(leagueMatch[1], 10);
    if (!isNaN(leagueId) && leagueId > 0) {
      return leagueId;
    }
  }
  
  return null;
};

export const AppProvider = ({ children }) => {
  // Check URL hash first, then localStorage
  const [entryId, setEntryIdState] = useState(() => {
    // Try to get from URL hash first
    const hashTeamId = extractTeamIdFromHash();
    if (hashTeamId) {
      return hashTeamId;
    }
    
    // Fallback to localStorage
    try {
      const stored = localStorage.getItem('fpl_entry_id');
      return stored ? parseInt(stored, 10) : null;
    } catch (error) {
      console.warn('localStorage not available:', error);
      return null;
    }
  });
  
  const [currentGameweek, setCurrentGameweek] = useState(() => {
    // Try to get from URL hash first
    const hashGameweek = extractGameweekFromHash();
    if (hashGameweek) {
      return hashGameweek;
    }
    return null;
  });
  
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    // Check URL hash first
    if (extractTeamIdFromHash()) {
      return true;
    }
    
    // Fallback to localStorage
    try {
      return !!localStorage.getItem('fpl_entry_id');
    } catch (error) {
      console.warn('localStorage not available:', error);
      return false;
    }
  });
  const [isLoadingGameweek, setIsLoadingGameweek] = useState(false);

  // Listen for hash changes to update entry ID and gameweek
  useEffect(() => {
    const handleHashChange = () => {
      const hashTeamId = extractTeamIdFromHash();
      const hashGameweek = extractGameweekFromHash();
      const hashLeagueId = extractLeagueIdFromHash();
      
      if (hashTeamId && hashTeamId !== entryId) {
        setEntryIdState(hashTeamId);
        setIsAuthenticated(true);
        try {
          localStorage.setItem('fpl_entry_id', hashTeamId.toString());
        } catch (e) {
          console.warn('Failed to save entry ID:', e);
        }
      }
      
      if (hashGameweek && hashGameweek !== currentGameweek) {
        setCurrentGameweek(hashGameweek);
      }
      
      if (hashLeagueId) {
        try {
          localStorage.setItem('fpl_league_id', hashLeagueId.toString());
        } catch (e) {
          console.warn('Failed to save league ID:', e);
        }
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    // Check on mount
    handleHashChange();

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, [entryId, currentGameweek]);

  // Load current gameweek from API
  const loadCurrentGameweek = useCallback(async () => {
    if (!entryId) return;
    
    setIsLoadingGameweek(true);
    try {
      // Use backend API to get current gameweek (avoids CORS issues)
      const response = await fetch('http://localhost:8000/api/v1/gameweek/current');
      if (response.ok) {
        const data = await response.json();
        const gameweekData = data?.data || data;
        const gameweek = gameweekData.gameweek || 1;
        setCurrentGameweek(gameweek);
      } else {
        // Fallback to gameweek 1 if API fails
        setCurrentGameweek(1);
      }
    } catch (error) {
      console.error('Failed to load current gameweek:', error);
      // Fallback to gameweek 1 if API fails
      setCurrentGameweek(1);
    } finally {
      setIsLoadingGameweek(false);
    }
  }, [entryId]);

  // Set entry ID and persist to localStorage
  const setEntryId = useCallback((id) => {
    if (id) {
      const numId = typeof id === 'string' ? parseInt(id, 10) : id;
      if (!isNaN(numId) && numId > 0) {
        setEntryIdState(numId);
        try {
          localStorage.setItem('fpl_entry_id', numId.toString());
        } catch (error) {
          console.warn('Failed to save to localStorage:', error);
        }
        setIsAuthenticated(true);
        loadCurrentGameweek();
      }
    } else {
      setEntryIdState(null);
      try {
        localStorage.removeItem('fpl_entry_id');
      } catch (error) {
        console.warn('Failed to remove from localStorage:', error);
      }
      setIsAuthenticated(false);
      setCurrentGameweek(null);
    }
  }, [loadCurrentGameweek]);

  // Load gameweek when entryId changes
  useEffect(() => {
    if (entryId) {
      loadCurrentGameweek();
    }
  }, [entryId, loadCurrentGameweek]);

  const value = {
    entryId,
    setEntryId,
    currentGameweek,
    setCurrentGameweek,
    isAuthenticated,
    isLoadingGameweek,
    loadCurrentGameweek,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export default AppContext;

