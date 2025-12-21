import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import DesktopWindow from '../components/retroui/DesktopWindow';
import { entryApi, teamSearchApi } from '../services/api';
import { useAppContext } from '../context/AppContext';
import LoadingLogo from '../components/common/LoadingLogo';
import Tooltip from '../components/common/Tooltip';
import LetterGlitch from '../components/common/LetterGlitch';
import { TeamSearchResult } from '../types';

const Landing: React.FC = () => {
  const [inputMode, setInputMode] = useState<'id' | 'search'>('id');
  const [inputId, setInputId] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<TeamSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { setEntryId, setEntryInfo } = useAppContext();
  const navigate = useNavigate();
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Debounced search effect
  useEffect(() => {
    if (inputMode !== 'search' || !searchQuery.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    setSearchLoading(true);
    setShowResults(false);

    // Debounce search by 300ms
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const results = await teamSearchApi.searchTeams(searchQuery.trim());
        setSearchResults(results);
        setShowResults(true);
      } catch (err) {
        // Silently handle errors - searchTeams returns empty array on error
        setSearchResults([]);
        setShowResults(false);
      } finally {
        setSearchLoading(false);
      }
    }, 300);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchQuery, inputMode]);

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (resultsRef.current && !resultsRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };

    if (showResults) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showResults]);

  const handleTeamSelect = async (teamId: number) => {
    setLoading(true);
    setError('');
    setShowResults(false);

    try {
      const data = await entryApi.getEntry(teamId);
      setEntryId(teamId);
      setEntryInfo(data);
      navigate('/dashboard');
    } catch (err: any) {
      const errorMessage = err?.message || 'Could not validate Entry ID. Please try again.';
      setError(errorMessage);
      console.error('Entry validation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inputMode === 'search') {
      // In search mode, don't submit form - user must select from results
      return;
    }

    if (!inputId) return;

    setLoading(true);
    setError('');

    try {
      const id = parseInt(inputId, 10);
      if (isNaN(id)) throw new Error("Invalid ID");

      const data = await entryApi.getEntry(id);
      setEntryId(id);
      setEntryInfo(data);
      navigate('/dashboard');
    } catch (err: any) {
      const errorMessage = err?.message || 'Could not validate Entry ID. Please try again.';
      setError(errorMessage);
      console.error('Entry validation error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen pt-16 pb-24 px-4 flex flex-col items-center justify-center relative overflow-visible">
        {/* LetterGlitch Background */}
        <LetterGlitch
          glitchSpeed={50}
          centerVignette={true}
          outerVignette={false}
          smooth={true}
          glitchColors={['#000000', '#808080', '#000000', '#FF0000']}
        />

      <DesktopWindow title="System Access" className="w-full max-w-md md:max-w-md max-w-[90%] z-20 relative scale-90 md:scale-100">
        <div className="p-4 md:p-6 flex flex-col items-center">
            <div className="mb-4 md:mb-6 border-retro border-retro-primary p-3 md:p-4 bg-retro-background w-full text-center">
                <img src="/logo3.png" alt="FPL OPTIMIZER" className="mx-auto mb-2 md:mb-3 h-64 md:h-96 object-contain" />
            </div>
          
          <p className="mb-4 md:mb-6 text-center text-xs md:text-sm px-2">
            {inputMode === 'id' 
              ? 'Enter your Fantasy Premier League Entry ID to access analytics and AI recommendations.'
              : 'Search for your team by team name or manager name.'}
          </p>

          {/* Mode Toggle */}
          <div className="mb-3 md:mb-4 flex gap-2 w-full">
            <button
              type="button"
              onClick={() => {
                setInputMode('id');
                setSearchQuery('');
                setSearchResults([]);
                setShowResults(false);
              }}
              className={`flex-1 py-2 px-3 text-[10px] md:text-xs font-bold uppercase border-retro border-black transition-all ${
                inputMode === 'id'
                  ? 'bg-retro-primary text-white shadow-retro'
                  : 'bg-white text-black shadow-[2px_2px_0_rgba(0,0,0,0.1)] hover:shadow-retro'
              }`}
            >
              Entry ID
            </button>
            <button
              type="button"
              onClick={() => {
                setInputMode('search');
                setInputId('');
                setError('');
              }}
              className={`flex-1 py-2 px-3 text-[10px] md:text-xs font-bold uppercase border-retro border-black transition-all ${
                inputMode === 'search'
                  ? 'bg-retro-primary text-white shadow-retro'
                  : 'bg-white text-black shadow-[2px_2px_0_rgba(0,0,0,0.1)] hover:shadow-retro'
              }`}
            >
              Search
            </button>
          </div>

          <form onSubmit={handleSubmit} className="w-full space-y-3 md:space-y-4">
            {inputMode === 'id' ? (
              <div>
                <label htmlFor="entryId" className="block text-[10px] md:text-xs font-bold uppercase mb-1">
                  <Tooltip text="Your FPL Entry ID is found in your team URL: https://fantasy.premierleague.com/entry/YOUR_ENTRY_ID/event/X. You can also find it in your browser's address bar when viewing your team page. It's a 6-7 digit number unique to your FPL team.">
                    Entry ID
                  </Tooltip>
                </label>
                <input
                  id="entryId"
                  type="text"
                  value={inputId}
                  onChange={(e) => setInputId(e.target.value)}
                  className="w-full p-2 md:p-3 border-retro border-retro-primary bg-white focus:outline-none focus:ring-2 focus:ring-retro-primary shadow-[4px_4px_0_rgba(0,0,0,0.1)] font-mono text-base md:text-lg"
                  placeholder="e.g. 123456"
                  disabled={loading}
                />
              </div>
            ) : (
              <div className="relative" ref={resultsRef}>
                <label htmlFor="searchQuery" className="block text-[10px] md:text-xs font-bold uppercase mb-1">
                  <Tooltip text="Search by your team name or manager name. Results will appear as you type. Select your team from the list.">
                    Team Name or Manager Name
                  </Tooltip>
                </label>
                <input
                  id="searchQuery"
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full p-2 md:p-3 border-retro border-retro-primary bg-white focus:outline-none focus:ring-2 focus:ring-retro-primary shadow-[4px_4px_0_rgba(0,0,0,0.1)] text-base md:text-lg"
                  placeholder="e.g. Supa Strikers or John Smith"
                  disabled={loading}
                />
                {searchLoading && (
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-retro-primary">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-retro-primary"></div>
                  </div>
                )}
                
                {/* Search Results Dropdown */}
                {showResults && searchResults.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-white border-retro border-retro-primary shadow-[4px_4px_0_rgba(0,0,0,0.1)] max-h-60 overflow-y-auto">
                    {searchResults.map((result) => (
                      <button
                        key={result.team_id}
                        type="button"
                        onClick={() => handleTeamSelect(result.team_id)}
                        className="w-full text-left p-3 hover:bg-retro-primary hover:text-white transition-colors border-b border-gray-200 last:border-b-0"
                      >
                        <div className="font-semibold text-sm">{result.team_name}</div>
                        <div className="text-xs opacity-75">{result.manager_name}</div>
                        <div className="text-[10px] opacity-50 mt-1">Match: {Math.round(result.similarity * 100)}%</div>
                      </button>
                    ))}
                  </div>
                )}
                
                {showResults && searchResults.length === 0 && searchQuery.trim() && !searchLoading && (
                  <div className="absolute z-50 w-full mt-1 bg-white border-retro border-retro-primary shadow-[4px_4px_0_rgba(0,0,0,0.1)] p-3 text-center text-xs">
                    <p className="text-retro-error font-bold">No matches found</p>
                    <p className="text-[10px] mt-1 opacity-75">Try refining your search or use Entry ID mode</p>
                  </div>
                )}
              </div>
            )}

            {error && (
              <div className="bg-retro-error text-white p-2 text-[10px] md:text-xs font-bold border-2 border-black">
                ERROR: {error}
              </div>
            )}

            {inputMode === 'id' && (
              <button
                type="submit"
                disabled={loading || !inputId}
                className="w-full bg-retro-primary text-white font-bold py-2 md:py-3 border-retro border-black shadow-retro hover:shadow-retro-hover active:shadow-retro-active active:translate-x-1 active:translate-y-1 transition-all disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-sm md:text-base"
              >
                {loading ? 'Authenticating...' : 'Connect'}
              </button>
            )}
            
            {inputMode === 'search' && (
              <div className="text-[10px] md:text-xs text-center opacity-60">
                <p>Type to search, then select your team from the results</p>
              </div>
            )}
          </form>
          
          <div className="mt-6 md:mt-8 text-[10px] md:text-xs text-center opacity-60">
             <p>Made by Vitu K</p>
          </div>
        </div>
      </DesktopWindow>
      
       {/* Loading Overlay if loading */}
       {loading && (
           <div className="absolute inset-0 bg-white z-50 flex items-center justify-center">
               <LoadingLogo phases={[
                 { message: "Validating Entry ID...", duration: 1000 },
                 { message: "Connecting to Mainframe...", duration: 1500 },
                 { message: "Authenticating...", duration: 1000 },
               ]} />
           </div>
       )}
    </div>
  );
};

export default Landing;