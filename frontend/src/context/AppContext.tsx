import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { EntryInfo } from '../types';
import { entryApi } from '../services/api';

interface AppContextType {
  entryId: number | null;
  setEntryId: (id: number) => void;
  entryInfo: EntryInfo | null;
  setEntryInfo: (info: EntryInfo) => void;
  currentGameweek: number;
  isAuthenticated: boolean;
  logout: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [entryId, setEntryIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem('fpl_entry_id');
    return stored ? parseInt(stored, 10) : null;
  });
  
  const [entryInfo, setEntryInfo] = useState<EntryInfo | null>(() => {
    const stored = localStorage.getItem('fpl_entry_info');
    return stored ? JSON.parse(stored) : null;
  });

  const [currentGameweek, setCurrentGameweek] = useState<number>(1); // Default, update via API if possible

  useEffect(() => {
    if (entryId) {
      localStorage.setItem('fpl_entry_id', entryId.toString());
    } else {
      localStorage.removeItem('fpl_entry_id');
    }
  }, [entryId]);

  useEffect(() => {
    if (entryInfo) {
      localStorage.setItem('fpl_entry_info', JSON.stringify(entryInfo));
      if (entryInfo.current_event) {
        setCurrentGameweek(entryInfo.current_event);
      }
    } else {
      localStorage.removeItem('fpl_entry_info');
    }
  }, [entryInfo]);

  // Note: We don't fetch gameweek from /api/v1/gameweek/current anymore
  // because it returns the "next" gameweek (GW17), not the "latest played" gameweek (GW16).
  // The ML system correctly uses api_client.get_current_gameweek() which finds the latest
  // played gameweek based on data availability. We'll use the gameweek from the ML report
  // response instead, which is the actual gameweek that was analyzed.

  const setEntryId = (id: number) => {
    setEntryIdState(id);
  };

  const logout = () => {
    setEntryIdState(null);
    setEntryInfo(null);
    localStorage.clear();
  };

  return (
    <AppContext.Provider value={{ 
      entryId, 
      setEntryId, 
      entryInfo, 
      setEntryInfo, 
      currentGameweek, 
      isAuthenticated: !!entryId,
      logout 
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
