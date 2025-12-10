import React, { useState, useEffect } from 'react';
import DesktopWindow from '../retroui/DesktopWindow';
import { dashboardApi } from '../../services/api';
import { useAppContext } from '../../context/AppContext';
import LoadingSpinner from '../common/LoadingSpinner';

interface League {
  id: number;
  name: string;
  rank: number;
  total_teams: number;
}

interface Standing {
  rank: number;
  entry_name: string;
  player_name: string;
  total: number;
  event_total: number;
  entry_id: number;
}

const MiniLeagueTable: React.FC = () => {
  const { entryId } = useAppContext();
  const [leagues, setLeagues] = useState<League[]>([]);
  const [selectedLeagueId, setSelectedLeagueId] = useState<number | null>(null);
  const [standings, setStandings] = useState<Standing[]>([]);
  const [leagueName, setLeagueName] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [loadingLeagues, setLoadingLeagues] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch leagues on mount
  useEffect(() => {
    const fetchLeagues = async () => {
      if (!entryId) return;
      
      try {
        setLoadingLeagues(true);
        const data = await dashboardApi.getLeagues(entryId);
        // Sort leagues by rank (best rank = lowest number first)
        const sortedLeagues = (data || []).sort((a: League, b: League) => {
          const rankA = a.rank || 999999;
          const rankB = b.rank || 999999;
          return rankA - rankB;
        });
        setLeagues(sortedLeagues);
        
        // Auto-select first league (best rank) if available
        if (sortedLeagues.length > 0) {
          setSelectedLeagueId(sortedLeagues[0].id);
        }
      } catch (err: any) {
        console.error('Error fetching leagues:', err);
        setError(err.message || 'Failed to load leagues');
        // If endpoint not found, show helpful message
        if (err.message?.includes('not found') || err.message?.includes('404')) {
          setError('Leagues endpoint not available. Please ensure backend is updated.');
        }
      } finally {
        setLoadingLeagues(false);
      }
    };

    fetchLeagues();
  }, [entryId]);

  // Fetch standings when league is selected
  useEffect(() => {
    const fetchStandings = async () => {
      if (!entryId || !selectedLeagueId) return;

      try {
        setLoading(true);
        setError(null);
        const data = await dashboardApi.getLeagueStandings(entryId, selectedLeagueId);
        // Ensure standings are sorted by rank
        const sortedStandings = (data.standings || []).sort((a: Standing, b: Standing) => {
          return (a.rank || 999999) - (b.rank || 999999);
        });
        setStandings(sortedStandings);
        setLeagueName(data.league_name || 'Unknown League');
      } catch (err: any) {
        console.error('Error fetching standings:', err);
        // If endpoint not found, show helpful message
        if (err.message?.includes('not found') || err.message?.includes('404')) {
          setError('League standings endpoint not available. Please ensure backend is updated.');
        } else {
          setError(err.message || 'Failed to load standings');
        }
        setStandings([]);
      } finally {
        setLoading(false);
      }
    };

    fetchStandings();
  }, [entryId, selectedLeagueId]);

  const selectedLeague = leagues.find(l => l.id === selectedLeagueId);

  return (
    <DesktopWindow title="Mini-League Standings" className="col-span-1 md:col-span-2 lg:col-span-3">
      <div className="space-y-4">
        {/* League Selector */}
        <div className="flex items-center gap-4">
          <label className="text-xs font-bold uppercase">Select League:</label>
          {loadingLeagues ? (
            <span className="text-xs font-mono opacity-60">Loading leagues...</span>
          ) : leagues.length === 0 ? (
            <span className="text-xs font-mono opacity-60">No leagues found</span>
          ) : (
            <select
              value={selectedLeagueId || ''}
              onChange={(e) => setSelectedLeagueId(Number(e.target.value))}
              className="flex-1 max-w-md p-2 border-retro border-retro-primary bg-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-retro-primary shadow-[2px_2px_0_rgba(0,0,0,0.1)]"
              style={{
                appearance: 'none',
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%231D1D1B' d='M6 9L1 4h10z'/%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 8px center',
                paddingRight: '32px'
              }}
            >
              {leagues.map((league) => (
                <option 
                  key={league.id} 
                  value={league.id}
                  className="bg-white text-retro-primary font-mono"
                >
                  {league.name} (Rank: #{league.rank})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-retro-error text-white p-2 text-xs font-bold border-2 border-black">
            <p className="mb-1">ERROR: {error}</p>
            {error.includes('not found') || error.includes('404') ? (
              <p className="text-[10px] opacity-90 mt-1">
                The backend endpoints may still be deploying. Please wait a few minutes and refresh.
              </p>
            ) : null}
          </div>
        )}

        {/* Standings Table */}
        {loading ? (
          <LoadingSpinner text="Loading standings..." />
        ) : standings.length > 0 ? (() => {
          // Ensure standings are sorted by rank (they should already be, but just in case)
          const sortedStandings = [...standings].sort((a, b) => (a.rank || 999999) - (b.rank || 999999));
          
          // Get top 10
          const top10 = sortedStandings.slice(0, 10);
          
          // Check if current user is in top 10 (compare as numbers to handle type mismatches)
          const userInTop10 = top10.some(s => Number(s.entry_id) === Number(entryId));
          
          // If user not in top 10, find their entry
          const userEntry = userInTop10 ? null : sortedStandings.find(s => Number(s.entry_id) === Number(entryId));
          
          // Debug logging
          console.log('Mini-League Table Debug:', {
            entryId,
            entryIdType: typeof entryId,
            totalStandings: sortedStandings.length,
            userInTop10,
            userEntry: userEntry ? { rank: userEntry.rank, name: userEntry.entry_name, entry_id: userEntry.entry_id } : null,
            top10EntryIds: top10.map(s => ({ id: s.entry_id, type: typeof s.entry_id, rank: s.rank }))
          });
          
          return (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border-retro border-retro-primary">
                <thead>
                  <tr className="bg-retro-primary text-white">
                    <th className="border-retro border-retro-primary p-2 text-left text-xs font-bold uppercase">Rank</th>
                    <th className="border-retro border-retro-primary p-2 text-left text-xs font-bold uppercase">Team Name</th>
                    <th className="border-retro border-retro-primary p-2 text-left text-xs font-bold uppercase">Manager</th>
                    <th className="border-retro border-retro-primary p-2 text-right text-xs font-bold uppercase">Total Points</th>
                    <th className="border-retro border-retro-primary p-2 text-right text-xs font-bold uppercase">GW Points</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Top 10 */}
                  {top10.map((standing, idx) => {
                    const isCurrentUser = Number(standing.entry_id) === Number(entryId);
                    return (
                      <tr
                        key={standing.entry_id || idx}
                        className={`
                          ${isCurrentUser ? 'bg-retro-secondary font-bold' : idx % 2 === 0 ? 'bg-white' : 'bg-retro-background'}
                          hover:bg-retro-secondary/50
                        `}
                      >
                        <td className="border-retro border-retro-primary p-2 text-sm font-mono font-bold">
                          {standing.rank}
                        </td>
                        <td className="border-retro border-retro-primary p-2 text-sm">
                          {standing.entry_name}
                        </td>
                        <td className="border-retro border-retro-primary p-2 text-sm">
                          {standing.player_name}
                        </td>
                        <td className="border-retro border-retro-primary p-2 text-sm font-mono text-right">
                          {standing.total.toLocaleString()}
                        </td>
                        <td className="border-retro border-retro-primary p-2 text-sm font-mono text-right">
                          {standing.event_total || 0}
                        </td>
                      </tr>
                    );
                  })}
                  
                  {/* Separator and User's entry if outside top 10 */}
                  {!userInTop10 && userEntry ? (
                    <>
                      <tr key="separator">
                        <td colSpan={5} className="border-retro border-retro-primary p-1 bg-retro-background">
                          <div className="text-center text-[10px] font-bold uppercase opacity-60">...</div>
                        </td>
                      </tr>
                      {/* User's entry */}
                      <tr key={`user-${userEntry.entry_id}`} className="bg-retro-secondary font-bold border-t-2 border-retro-primary">
                        <td className="border-retro border-retro-primary p-2 text-sm font-mono font-bold">
                          {userEntry.rank}
                        </td>
                        <td className="border-retro border-retro-primary p-2 text-sm">
                          {userEntry.entry_name}
                        </td>
                        <td className="border-retro border-retro-primary p-2 text-sm">
                          {userEntry.player_name}
                        </td>
                        <td className="border-retro border-retro-primary p-2 text-sm font-mono text-right">
                          {userEntry.total.toLocaleString()}
                        </td>
                        <td className="border-retro border-retro-primary p-2 text-sm font-mono text-right">
                          {userEntry.event_total || 0}
                        </td>
                      </tr>
                    </>
                  ) : null}
                </tbody>
              </table>
            </div>
          );
        })() : selectedLeagueId && !loading && !error ? (
          <div className="p-8 text-center border-2 border-dashed border-retro-primary">
            <p className="font-bold text-sm">NO STANDINGS AVAILABLE</p>
            <p className="text-xs mt-2 opacity-60">Unable to load standings for this league.</p>
          </div>
        ) : null}
      </div>
    </DesktopWindow>
  );
};

export default MiniLeagueTable;

