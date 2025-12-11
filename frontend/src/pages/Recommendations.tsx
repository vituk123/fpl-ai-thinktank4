import React, { useEffect, useState } from 'react';
import DesktopWindow from '../components/retroui/DesktopWindow';
import { useAppContext } from '../context/AppContext';
import { mlApi } from '../services/api';
import LoadingSpinner from '../components/common/LoadingSpinner';

const Recommendations: React.FC = () => {
  const { entryId, currentGameweek } = useAppContext();
  const [mlPlayers, setMLPlayers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<string>('EV');
  const [filterPosition, setFilterPosition] = useState<string>('all');

  useEffect(() => {
    const fetchMLData = async () => {
      if (!entryId) {
        setLoading(false);
        return;
      }
      try {
        console.log('ML Page: Fetching ML-enhanced players for entryId:', entryId, 'gameweek:', currentGameweek);
        const data = await mlApi.getMLPlayers(currentGameweek, entryId);
        console.log('ML Page: Received data:', data);
        console.log('ML Page: Players count:', data?.players?.length);
        setMLPlayers(data?.players || []);
      } catch (e: any) {
        console.error('ML Page: Error fetching:', e);
        console.error('ML Page: Error details:', {
          message: e.message,
          response: e.response?.data,
          status: e.response?.status
        });
        setMLPlayers([]);
      } finally {
        setLoading(false);
      }
    };
    fetchMLData();
  }, [entryId, currentGameweek]);

  if (!entryId) {
    return (
      <div className="p-4 md:p-8 pb-24">
        <DesktopWindow title="ML Engine Output" className="max-w-7xl mx-auto">
          <div className="p-6 text-center">
            <p className="text-retro-error font-bold mb-2">No Entry ID</p>
            <p className="text-sm opacity-60">Please enter your FPL entry ID on the landing page to view ML predictions.</p>
          </div>
        </DesktopWindow>
      </div>
    );
  }

  if (loading) {
      return (
          <div className="h-[80vh] flex flex-col items-center justify-center">
              <LoadingSpinner text="Running ML Algorithms..." />
              <p className="mt-4 font-mono text-xs opacity-60">Generating ML predictions for your team. This may take up to 60s.</p>
          </div>
      );
  }

  const positionNames: { [key: number]: string } = { 1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD' };
  
  const filteredPlayers = mlPlayers.filter((p: any) => 
    filterPosition === 'all' || p.element_type === parseInt(filterPosition)
  );
  
  const sortedPlayers = [...filteredPlayers].sort((a: any, b: any) => {
    const aVal = a[sortBy] || 0;
    const bVal = b[sortBy] || 0;
    return sortBy === 'EV' || sortBy === 'predicted_ev' ? bVal - aVal : aVal - bVal;
  });

  return (
    <div className="p-4 md:p-8 pb-24">
      <DesktopWindow title="ML Engine Output" className="max-w-7xl mx-auto">
        <div className="space-y-6">
            <div className="border-b-retro border-retro-primary pb-4">
                <h2 className="text-lg font-bold uppercase mb-2">ML-Enhanced Player Data for GW{currentGameweek}</h2>
                <p className="text-sm">Full ML engine output for your team (Entry ID: {entryId}) - Same as main.py</p>
            </div>

            {/* Filters */}
            <div className="flex gap-4 items-center">
              <div>
                <label className="text-xs font-bold uppercase mr-2">Sort By:</label>
                <select 
                  value={sortBy} 
                  onChange={(e) => setSortBy(e.target.value)}
                  className="border-2 border-retro-primary px-2 py-1 text-sm"
                >
                  <option value="EV">EV (Expected Value)</option>
                  <option value="predicted_ev">Predicted EV</option>
                  <option value="total_points">Total Points</option>
                  <option value="now_cost">Price</option>
                  <option value="selected_by_percent">Ownership %</option>
                  <option value="form">Form</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-bold uppercase mr-2">Position:</label>
                <select 
                  value={filterPosition} 
                  onChange={(e) => setFilterPosition(e.target.value)}
                  className="border-2 border-retro-primary px-2 py-1 text-sm"
                >
                  <option value="all">All</option>
                  <option value="1">GK</option>
                  <option value="2">DEF</option>
                  <option value="3">MID</option>
                  <option value="4">FWD</option>
                </select>
              </div>
              <div className="ml-auto text-xs font-mono opacity-60">
                Showing {sortedPlayers.length} players
              </div>
            </div>

            {sortedPlayers.length === 0 ? (
                <div className="p-8 text-center border-2 border-dashed border-retro-primary">
                    <p className="font-bold">NO ML DATA AVAILABLE</p>
                    <p className="text-sm">ML engine output not found.</p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-2 border-retro-primary">
                    <thead className="bg-retro-primary text-white">
                      <tr>
                        <th className="px-2 py-2 text-left text-xs font-bold">Player</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">Pos</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">Team</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">Price</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">EV</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">Pred EV</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">xP</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">Points</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">Form</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">Own %</th>
                        <th className="px-2 py-2 text-center text-xs font-bold">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedPlayers.map((player: any, idx: number) => (
                        <tr 
                          key={player.id || idx} 
                          className="border-b border-retro-primary hover:bg-retro-background"
                        >
                          <td className="px-2 py-2 text-sm font-bold">{player.web_name}</td>
                          <td className="px-2 py-2 text-center text-xs font-mono">{positionNames[player.element_type] || '-'}</td>
                          <td className="px-2 py-2 text-center text-xs">{player.team_name || '-'}</td>
                          <td className="px-2 py-2 text-center text-xs font-mono">£{(player.now_cost/10).toFixed(1)}m</td>
                          <td className="px-2 py-2 text-center text-xs font-mono font-bold">{player.EV?.toFixed(2) || '-'}</td>
                          <td className="px-2 py-2 text-center text-xs font-mono">{player.predicted_ev?.toFixed(2) || '-'}</td>
                          <td className="px-2 py-2 text-center text-xs font-mono">{player.xP_raw?.toFixed(2) || player.ep_next?.toFixed(2) || '-'}</td>
                          <td className="px-2 py-2 text-center text-xs font-mono">{player.total_points || 0}</td>
                          <td className="px-2 py-2 text-center text-xs font-mono">{player.form || '-'}</td>
                          <td className="px-2 py-2 text-center text-xs font-mono">{player.selected_by_percent || '0'}%</td>
                          <td className="px-2 py-2 text-center text-xs">
                            {player.status === 'a' ? '✅' : player.status === 'i' ? '❌' : player.status === 'd' ? '⚠️' : '❓'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
            )}
        </div>
      </DesktopWindow>
    </div>
  );
};

export default Recommendations;