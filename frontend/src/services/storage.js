/**
 * LocalStorage utilities for FPL app
 */

const STORAGE_KEYS = {
  ENTRY_ID: 'fpl_entry_id',
  LAST_GAMEWEEK: 'fpl_last_gameweek',
  PREFERENCES: 'fpl_preferences',
};

export const storage = {
  getEntryId: () => {
    const stored = localStorage.getItem(STORAGE_KEYS.ENTRY_ID);
    return stored ? parseInt(stored, 10) : null;
  },

  setEntryId: (entryId) => {
    if (entryId) {
      localStorage.setItem(STORAGE_KEYS.ENTRY_ID, entryId.toString());
    } else {
      localStorage.removeItem(STORAGE_KEYS.ENTRY_ID);
    }
  },

  getLastGameweek: () => {
    const stored = localStorage.getItem(STORAGE_KEYS.LAST_GAMEWEEK);
    return stored ? parseInt(stored, 10) : null;
  },

  setLastGameweek: (gameweek) => {
    if (gameweek) {
      localStorage.setItem(STORAGE_KEYS.LAST_GAMEWEEK, gameweek.toString());
    } else {
      localStorage.removeItem(STORAGE_KEYS.LAST_GAMEWEEK);
    }
  },

  getPreferences: () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEYS.PREFERENCES);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  },

  setPreferences: (prefs) => {
    try {
      localStorage.setItem(STORAGE_KEYS.PREFERENCES, JSON.stringify(prefs));
    } catch (error) {
      console.error('Failed to save preferences:', error);
    }
  },

  clear: () => {
    Object.values(STORAGE_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
  },
};

export default storage;

