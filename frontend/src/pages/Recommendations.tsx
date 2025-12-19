import React, { useEffect, useState } from 'react';
import DesktopWindow from '../components/retroui/DesktopWindow';
import { useAppContext } from '../context/AppContext';
import { mlApi, imagesApi } from '../services/api';
import { MLReport } from '../types';
import LoadingLogo from '../components/common/LoadingLogo';
import Tooltip from '../components/common/Tooltip';

const Recommendations: React.FC = () => {
  const { entryId, currentGameweek } = useAppContext();
  const [report, setReport] = useState<MLReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      if (!entryId) {
        setLoading(false);
        return;
      }
      try {
        console.log('ML Report: Fetching for entryId:', entryId, 'gameweek:', currentGameweek);
        // Always pass undefined so backend uses its own current gameweek logic (latest played gameweek)
        // The ML system correctly determines the latest played gameweek based on data availability
        // Use fast_mode=false to get full ML analysis on GCE VM (32GB RAM, 8 CPUs)
        const data = await mlApi.getMLReport(entryId, undefined, false);
        console.log('ML Report: Received data:', data);
        console.log('ML Report: Header gameweek from API:', data?.header?.gameweek);
        console.log('ML Report: Full header:', data?.header);
        // Debug: Log transfer recommendations data
        if (data?.transfer_recommendations?.top_suggestion) {
          const topSug = data.transfer_recommendations.top_suggestion;
          console.log('ML Report: Top suggestion players_out:', topSug.players_out);
          console.log('ML Report: Top suggestion players_in:', topSug.players_in);
          if (topSug.players_out && topSug.players_out.length > 0) {
            console.log('ML Report: First player OUT:', {
              name: topSug.players_out[0].name,
              element_type: topSug.players_out[0].element_type,
              fdr: topSug.players_out[0].fdr,
              allFields: topSug.players_out[0]
            });
          }
        }
        setReport(data);
        setError(null);
        
        // Update currentGameweek from the ML report response (this is the actual gameweek analyzed)
        if (data?.header?.gameweek) {
          console.log('ML Report: Updating currentGameweek from report:', data.header.gameweek);
          // Note: We can't directly update context here, but the report will display the correct gameweek
        }
      } catch (e: any) {
        console.error('ML Report: Error fetching:', e);
        // Check if it's a timeout error
        if (e.message?.includes('timeout') || e.response?.data?.timeout) {
          setError('ML report generation timed out. The analysis is computationally intensive. Please try again.');
        } else {
          setError(e.message || 'Failed to load ML report');
        }
        setReport(null);
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [entryId, currentGameweek]);

  if (!entryId) {
    return (
      <div className="p-4 md:p-8 pb-24">
        <DesktopWindow title="FPL Analysis Report" className="max-w-7xl mx-auto">
          <div className="p-6 text-center">
            <p className="text-retro-error font-bold mb-2">No Entry ID</p>
            <p className="text-sm opacity-60">Please enter your FPL entry ID on the landing page to view ML report.</p>
          </div>
        </DesktopWindow>
      </div>
    );
  }

  if (loading) {
    const mlPhases = [
      { message: "Initializing ML Engine...", duration: 2000 },
      { message: "Loading player data...", duration: 3000 },
      { message: "Running machine learning models...", duration: 8000 },
      { message: "Analyzing fixture difficulty...", duration: 3000 },
      { message: "Generating transfer recommendations...", duration: 4000 },
      { message: "Compiling comprehensive report...", duration: 2000 },
    ];
    return (
      <div className="h-[80vh] flex flex-col items-center justify-center">
        <LoadingLogo phases={mlPhases} />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-4 md:p-8 pb-24">
        <DesktopWindow title="FPL Analysis Report" className="max-w-7xl mx-auto">
          <div className="p-6 text-center">
            <p className="text-retro-error font-bold mb-2">Error Loading Report</p>
            <p className="text-sm opacity-60">{error || 'ML report not available'}</p>
          </div>
        </DesktopWindow>
      </div>
    );
  }

  const positionNames: { [key: number]: string } = { 1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD' };

  return (
    <div className="p-4 md:p-8 pb-24">
      <DesktopWindow title={`FPL Analysis Report - GW${report.header.gameweek}`} className="max-w-7xl mx-auto">
        <div className="space-y-8">
          {/* Header */}
          <div className="border-b-2 border-retro-primary pb-4">
            <h1 className="text-2xl font-bold uppercase mb-2">FPL Analysis Report - GW{report.header.gameweek}</h1>
            <p className="text-sm">
              <strong>Manager:</strong> {report.header.manager}
            </p>
            <p className="text-sm">
              <strong>Team:</strong> {report.header.team}
            </p>
            <p className="text-xs font-mono opacity-60 mt-1">
              Generated: {report.header.generated}
            </p>
          </div>

          {/* Current Squad Analysis */}
          <div>
            <h2 className="text-lg font-bold uppercase mb-3 border-b-2 border-retro-primary pb-1">Current Squad Analysis</h2>
            {report.current_squad.length === 0 ? (
              <p className="text-sm opacity-60">Could not retrieve current squad.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-2 border-retro-primary">
                  <thead className="bg-retro-primary text-white">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-bold">Player</th>
                      <th className="px-3 py-2 text-center text-xs font-bold">Team</th>
                      <th className="px-3 py-2 text-center text-xs font-bold">Pos</th>
                      <th className="px-3 py-2 text-center text-xs font-bold">Price</th>
                      <th className="px-3 py-2 text-center text-xs font-bold">
                        <Tooltip text="Expected Points: ML model's prediction of points the player will score in the next gameweek">
                          xP
                        </Tooltip>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.current_squad.map((player, idx) => (
                      <tr key={idx} className="border-b border-retro-primary hover:bg-retro-background">
                        <td className="px-3 py-2 text-sm font-bold">{player.player}</td>
                        <td className="px-3 py-2 text-center text-xs">{player.team}</td>
                        <td className="px-3 py-2 text-center text-xs font-mono">{positionNames[player.pos] || player.pos}</td>
                        <td className="px-3 py-2 text-center text-xs font-mono">£{player.price.toFixed(1)}m</td>
                        <td className="px-3 py-2 text-center text-xs font-mono font-bold">{player.xp.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Transfer Recommendations */}
          <div>
            <h2 className="text-lg font-bold uppercase mb-3 border-b-2 border-retro-primary pb-1">Transfer Recommendations</h2>
            {!report.transfer_recommendations.top_suggestion ? (
              <p className="text-sm">No beneficial transfers found.</p>
            ) : (
              <div className="bg-retro-background p-4 border-2 border-retro-primary">
                <p className="text-sm mb-2">
                  <strong>Top Suggestion:</strong> {report.transfer_recommendations.top_suggestion.num_transfers} transfer(s) with a net <Tooltip text="Expected Value: The predicted point gain from making this transfer">EV</Tooltip> gain of <strong>{report.transfer_recommendations.top_suggestion.net_ev_gain.toFixed(2)}</strong>.
                  {report.transfer_recommendations.top_suggestion.penalty_hits && report.transfer_recommendations.top_suggestion.penalty_hits > 0 && (
                    <span className="ml-2 text-retro-error font-bold">
                      (-{report.transfer_recommendations.top_suggestion.penalty_hits * 4} point hit)
                    </span>
                  )}
                </p>
                {report.transfer_recommendations.top_suggestion.hit_reason && (
                  <div className="mt-2 p-3 bg-yellow-50 border-2 border-yellow-300 rounded">
                    <p className="text-sm font-bold text-yellow-800 mb-1">⚠️ Hit Transfer Reason:</p>
                    <p className="text-xs text-yellow-700">{report.transfer_recommendations.top_suggestion.hit_reason}</p>
                  </div>
                )}
                <div className="mt-2 space-y-1 text-sm">
                  <p>
                    <strong>Out:</strong> {report.transfer_recommendations.top_suggestion.players_out.map(p => `${p.name} (${p.team})`).join(', ')}
                  </p>
                  <p>
                    <strong>In:</strong> {report.transfer_recommendations.top_suggestion.players_in.map(p => `${p.name} (${p.team})`).join(', ')}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Hit vs No-Hit Comparison - Only show when hit transfer is recommended */}
          {report.transfer_recommendations.hit_vs_no_hit_comparison && 
           report.transfer_recommendations.top_suggestion && 
           report.transfer_recommendations.top_suggestion.penalty_hits && 
           report.transfer_recommendations.top_suggestion.penalty_hits > 0 && (
            <div>
              <h2 className="text-lg font-bold uppercase mb-3 border-b-2 border-retro-primary pb-1">Hit vs No-Hit Comparison</h2>
              <div className={`p-4 border-2 rounded ${
                report.transfer_recommendations.hit_vs_no_hit_comparison.better_option === 'hit' 
                  ? 'bg-green-50 border-green-300' 
                  : 'bg-blue-50 border-blue-300'
              }`}>
                <div className="flex items-start gap-3 mb-3">
                  <span className="text-2xl">
                    {report.transfer_recommendations.hit_vs_no_hit_comparison.better_option === 'hit' ? '✅' : '💡'}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-bold mb-1">
                      {report.transfer_recommendations.hit_vs_no_hit_comparison.better_option === 'hit' 
                        ? 'Hit Transfer is Better' 
                        : 'No-Hit Transfer is Better'}
                    </p>
                    <p className="text-xs opacity-80">
                      {report.transfer_recommendations.hit_vs_no_hit_comparison.reason}
                    </p>
                  </div>
                </div>
                
                {report.transfer_recommendations.hit_vs_no_hit_comparison.hit_net_gain !== null && 
                 report.transfer_recommendations.hit_vs_no_hit_comparison.no_hit_net_gain !== null && (
                  <div className="grid grid-cols-2 gap-4 mt-3 text-xs">
                    <div className="bg-white p-2 border border-gray-300 rounded">
                      <p className="font-bold mb-1">Best No-Hit Option:</p>
                      <p className="text-green-600 font-mono">{report.transfer_recommendations.hit_vs_no_hit_comparison.no_hit_net_gain.toFixed(2)} points</p>
                      {report.transfer_recommendations.best_no_hit && (
                        <p className="mt-1 opacity-70">
                          {report.transfer_recommendations.best_no_hit.num_transfers} transfer(s)
                        </p>
                      )}
                    </div>
                    <div className="bg-white p-2 border border-gray-300 rounded">
                      <p className="font-bold mb-1">Best Hit Option:</p>
                      <p className="text-orange-600 font-mono">{report.transfer_recommendations.hit_vs_no_hit_comparison.hit_net_gain.toFixed(2)} points</p>
                      {report.transfer_recommendations.best_hit && (
                        <p className="mt-1 opacity-70">
                          {report.transfer_recommendations.best_hit.num_transfers} transfer(s) (-{report.transfer_recommendations.best_hit.penalty_hits * 4} pts)
                        </p>
                      )}
                    </div>
                  </div>
                )}
                
                {report.transfer_recommendations.hit_vs_no_hit_comparison.difference !== null && 
                 report.transfer_recommendations.hit_vs_no_hit_comparison.difference !== 0 && (
                  <div className="mt-3 p-2 bg-white border border-gray-300 rounded">
                    <p className="text-xs font-bold">
                      Difference: <span className={`font-mono ${report.transfer_recommendations.hit_vs_no_hit_comparison.difference > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {report.transfer_recommendations.hit_vs_no_hit_comparison.difference > 0 ? '+' : ''}{report.transfer_recommendations.hit_vs_no_hit_comparison.difference.toFixed(2)} points
                      </span> in favor of {report.transfer_recommendations.hit_vs_no_hit_comparison.better_option === 'hit' ? 'hit transfer' : 'no-hit transfer'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Transfer In vs Transfer Out Comparison */}
          {report.transfer_recommendations.top_suggestion && 
           report.transfer_recommendations.top_suggestion.players_out.length > 0 &&
           report.transfer_recommendations.top_suggestion.players_in.length > 0 && (
            <div>
              <h2 className="text-lg font-bold uppercase mb-3 border-b-2 border-retro-primary pb-1">Transfer Comparison</h2>
              <div className="space-y-4">
                {report.transfer_recommendations.top_suggestion.players_out.map((playerOut, idx) => {
                  const playerIn = report.transfer_recommendations.top_suggestion!.players_in[idx] || report.transfer_recommendations.top_suggestion!.players_in[0];
                  
                  // Helper function to format stat value
                  const formatStat = (value: number | null, type: 'form' | 'ev' | 'ownership' | 'ppg' | 'fdr') => {
                    if (value === null || value === undefined) return 'N/A';
                    switch (type) {
                      case 'form':
                      case 'ppg':
                        return value.toFixed(1);
                      case 'ev':
                        return value.toFixed(2);
                      case 'ownership':
                        return `${value.toFixed(1)}%`;
                      case 'fdr':
                        return value.toFixed(1);
                      default:
                        return String(value);
                    }
                  };
                  
                  // Helper function to determine if transfer in is better
                  const isBetter = (outVal: number | null, inVal: number | null, higherIsBetter: boolean = true) => {
                    if (outVal === null || inVal === null) return false;
                    return higherIsBetter ? inVal > outVal : inVal < outVal;
                  };
                  
                  return (
                    <div key={idx} className="bg-retro-background p-4 border-2 border-retro-primary">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Transfer Out */}
                        <div className="flex items-start gap-3">
                          <img
                            src={playerOut.id ? imagesApi.getPlayerImageUrl(playerOut.id) : imagesApi.getPlayerImageUrlFPL(0)}
                            alt={playerOut.name}
                            className="w-14 h-14 object-cover object-top border-2 border-retro-primary flex-shrink-0"
                            onError={(e) => {
                              const img = e.target as HTMLImageElement;
                              console.warn('[Recommendations] Image load error for player OUT:', {
                                playerId: playerOut.id,
                                playerName: playerOut.name,
                                failedUrl: img.src,
                                playerData: playerOut
                              });
                              if (playerOut.id) {
                                const fallbackUrl = imagesApi.getPlayerImageUrlFPL(playerOut.id);
                                console.log('[Recommendations] Trying FPL fallback URL:', fallbackUrl);
                                img.src = fallbackUrl;
                              }
                            }}
                            onLoad={() => {
                              console.log('[Recommendations] Image loaded successfully for player OUT:', playerOut.id, playerOut.name);
                            }}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="mb-2">
                              <h3 className="font-bold text-base">{playerOut.name}</h3>
                              <p className="text-xs opacity-80">{playerOut.team} • {positionNames[playerOut.element_type] || '?'}</p>
                              <p className="text-xs font-bold bg-red-100 text-red-700 border border-red-300 px-2 py-0.5 mt-0.5 inline-block">OUT</p>
                            </div>
                            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
                              <div>
                                <Tooltip text="Form: Average points scored in the last 3-5 gameweeks">
                                  <span className="opacity-70">Form:</span>
                                </Tooltip>
                                <span className="ml-1 font-mono font-bold">{formatStat(playerOut.form, 'form')}</span>
                              </div>
                              <div>
                                <Tooltip text="Expected Value: ML model's prediction of points the player will score in the next gameweek">
                                  <span className="opacity-70">EV:</span>
                                </Tooltip>
                                <span className="ml-1 font-mono font-bold">{formatStat(playerOut.ev, 'ev')}</span>
                              </div>
                              <div>
                                <span className="opacity-70">Ownership:</span>
                                <span className="ml-1 font-mono font-bold">{formatStat(playerOut.ownership, 'ownership')}</span>
                              </div>
                              <div>
                                <Tooltip text="Points Per Game: Average points scored per 90 minutes played">
                                  <span className="opacity-70">Points/G:</span>
                                </Tooltip>
                                <span className="ml-1 font-mono font-bold">{formatStat(playerOut.points_per_game, 'ppg')}</span>
                              </div>
                              <div className="col-span-2">
                                <Tooltip text="Fixture Difficulty Rating: Difficulty of upcoming fixtures (1-5, lower is easier)">
                                  <span className="opacity-70">FDR:</span>
                                </Tooltip>
                                <span className="ml-1 font-mono font-bold">{formatStat(playerOut.fdr ?? (playerOut as any).fixture_difficulty, 'fdr')}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {/* Transfer In */}
                        <div className="flex items-start gap-3">
                          <img
                            src={playerIn.id ? imagesApi.getPlayerImageUrl(playerIn.id) : imagesApi.getPlayerImageUrlFPL(0)}
                            alt={playerIn.name}
                            className="w-14 h-14 object-cover object-top border-2 border-retro-primary flex-shrink-0"
                            onError={(e) => {
                              const img = e.target as HTMLImageElement;
                              console.warn('[Recommendations] Image load error for player IN:', {
                                playerId: playerIn.id,
                                playerName: playerIn.name,
                                failedUrl: img.src,
                                playerData: playerIn
                              });
                              if (playerIn.id) {
                                const fallbackUrl = imagesApi.getPlayerImageUrlFPL(playerIn.id);
                                console.log('[Recommendations] Trying FPL fallback URL:', fallbackUrl);
                                img.src = fallbackUrl;
                              }
                            }}
                            onLoad={() => {
                              console.log('[Recommendations] Image loaded successfully for player IN:', playerIn.id, playerIn.name);
                            }}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="mb-2">
                              <h3 className="font-bold text-base">{playerIn.name}</h3>
                              <p className="text-xs opacity-80">{playerIn.team} • {positionNames[playerIn.element_type] || '?'}</p>
                              <p className="text-xs font-bold bg-green-100 text-green-700 border border-green-300 px-2 py-0.5 mt-0.5 inline-block">IN</p>
                            </div>
                            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
                              <div>
                                <Tooltip text="Form: Average points scored in the last 3-5 gameweeks">
                                  <span className="opacity-70">Form:</span>
                                </Tooltip>
                                <span className="ml-1 font-mono font-bold">
                                  {formatStat(playerIn.form, 'form')}
                                  {isBetter(playerOut.form, playerIn.form) && (
                                    <span className="ml-1 text-green-600">↑</span>
                                  )}
                                </span>
                              </div>
                              <div>
                                <Tooltip text="Expected Value: ML model's prediction of points the player will score in the next gameweek">
                                  <span className="opacity-70">EV:</span>
                                </Tooltip>
                                <span className="ml-1 font-mono font-bold">
                                  {formatStat(playerIn.ev, 'ev')}
                                  {isBetter(playerOut.ev, playerIn.ev) && (
                                    <span className="ml-1 text-green-600">↑</span>
                                  )}
                                </span>
                              </div>
                              <div>
                                <span className="opacity-70">Ownership:</span>
                                <span className="ml-1 font-mono font-bold">
                                  {formatStat(playerIn.ownership, 'ownership')}
                                  {isBetter(playerOut.ownership, playerIn.ownership) && (
                                    <span className="ml-1 text-green-600">↑</span>
                                  )}
                                </span>
                              </div>
                              <div>
                                <Tooltip text="Points Per Game: Average points scored per 90 minutes played">
                                  <span className="opacity-70">Points/G:</span>
                                </Tooltip>
                                <span className="ml-1 font-mono font-bold">
                                  {formatStat(playerIn.points_per_game, 'ppg')}
                                  {isBetter(playerOut.points_per_game, playerIn.points_per_game) && (
                                    <span className="ml-1 text-green-600">↑</span>
                                  )}
                                </span>
                              </div>
                              <div className="col-span-2">
                                <Tooltip text="Fixture Difficulty Rating: Difficulty of upcoming fixtures (1-5, lower is easier)">
                                  <span className="opacity-70">FDR:</span>
                                </Tooltip>
                                <span className="ml-1 font-mono font-bold">
                                  {formatStat(playerIn.fdr ?? (playerIn as any).fixture_difficulty, 'fdr')}
                                  {isBetter(playerOut.fdr ?? (playerOut as any).fixture_difficulty, playerIn.fdr ?? (playerIn as any).fixture_difficulty, false) && (
                                    <span className="ml-1 text-green-600">↑</span>
                                  )}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Updated Squad After Transfers */}
          {report.transfer_recommendations.top_suggestion && 
           (report.updated_squad.starting_xi.length > 0 || report.updated_squad.bench.length > 0) && (
            <div>
              <h2 className="text-lg font-bold uppercase mb-3 border-b-2 border-retro-primary pb-1">Updated Squad After Transfers</h2>
              
              {report.updated_squad.starting_xi.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-bold uppercase mb-2">Starting XI</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full border-2 border-retro-primary">
                      <thead className="bg-retro-primary text-white">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-bold">Player</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">Team</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">Pos</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">Price</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">
                            <Tooltip text="Expected Points: ML model's prediction of points the player will score in the next gameweek">
                              xP
                            </Tooltip>
                          </th>
                          <th className="px-3 py-2 text-center text-xs font-bold">Fixture</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.updated_squad.starting_xi.map((player, idx) => (
                          <tr key={idx} className="border-b border-retro-primary hover:bg-retro-background">
                            <td className="px-3 py-2 text-sm font-bold">{player.player}</td>
                            <td className="px-3 py-2 text-center text-xs">{player.team}</td>
                            <td className="px-3 py-2 text-center text-xs font-mono">{positionNames[player.pos] || player.pos}</td>
                            <td className="px-3 py-2 text-center text-xs font-mono">£{player.price.toFixed(1)}m</td>
                            <td className="px-3 py-2 text-center text-xs font-mono font-bold">{player.xp.toFixed(2)}</td>
                            <td className="px-3 py-2 text-center text-xs">{player.fixture}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {report.updated_squad.bench.length > 0 && (
                <div>
                  <h3 className="text-sm font-bold uppercase mb-2">Bench</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full border-2 border-retro-primary">
                      <thead className="bg-retro-primary text-white">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-bold">Player</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">Team</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">Pos</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">Price</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">
                            <Tooltip text="Expected Points: ML model's prediction of points the player will score in the next gameweek">
                              xP
                            </Tooltip>
                          </th>
                          <th className="px-3 py-2 text-center text-xs font-bold">Fixture</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.updated_squad.bench.map((player, idx) => (
                          <tr key={idx} className="border-b border-retro-primary hover:bg-retro-background">
                            <td className="px-3 py-2 text-sm font-bold">{player.player}</td>
                            <td className="px-3 py-2 text-center text-xs">{player.team}</td>
                            <td className="px-3 py-2 text-center text-xs font-mono">{positionNames[player.pos] || player.pos}</td>
                            <td className="px-3 py-2 text-center text-xs font-mono">£{player.price.toFixed(1)}m</td>
                            <td className="px-3 py-2 text-center text-xs font-mono font-bold">{player.xp.toFixed(2)}</td>
                            <td className="px-3 py-2 text-center text-xs">{player.fixture}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Captain and Vice-Captain Recommendations */}
              {(report.updated_squad.captain || report.updated_squad.vice_captain) && (
                <div className="mt-6">
                  <h3 className="text-sm font-bold uppercase mb-3">Captain & Vice-Captain Recommendations</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {report.updated_squad.captain && (
                      <div className="bg-retro-background p-4 border-2 border-retro-primary rounded">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-lg font-bold">C</span>
                          <h4 className="text-sm font-bold uppercase">Captain</h4>
                        </div>
                        <div className="space-y-1 text-xs">
                          <p className="font-bold text-base">{report.updated_squad.captain.player}</p>
                          <p className="opacity-80">{report.updated_squad.captain.team} • {positionNames[report.updated_squad.captain.pos] || report.updated_squad.captain.pos}</p>
                          <div className="grid grid-cols-2 gap-2 mt-2">
                            <div>
                              <span className="opacity-70">xP:</span> <span className="font-bold">{report.updated_squad.captain.xp.toFixed(2)}</span>
                            </div>
                            <div>
                              <span className="opacity-70">Form:</span> <span className="font-bold">{report.updated_squad.captain.form.toFixed(1)}</span>
                            </div>
                            <div>
                              <span className="opacity-70">FDR:</span> <span className="font-bold">{report.updated_squad.captain.fdr.toFixed(1)}</span>
                            </div>
                            <div>
                              <span className="opacity-70">Fixture:</span> <span className="font-bold">{report.updated_squad.captain.fixture}</span>
                            </div>
                          </div>
                          <p className="mt-2 text-xs opacity-80 italic">{report.updated_squad.captain.reason}</p>
                        </div>
                      </div>
                    )}
                    {report.updated_squad.vice_captain && (
                      <div className="bg-retro-background p-4 border-2 border-retro-primary rounded">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-lg font-bold">V</span>
                          <h4 className="text-sm font-bold uppercase">Vice-Captain</h4>
                        </div>
                        <div className="space-y-1 text-xs">
                          <p className="font-bold text-base">{report.updated_squad.vice_captain.player}</p>
                          <p className="opacity-80">{report.updated_squad.vice_captain.team} • {positionNames[report.updated_squad.vice_captain.pos] || report.updated_squad.vice_captain.pos}</p>
                          <div className="grid grid-cols-2 gap-2 mt-2">
                            <div>
                              <span className="opacity-70">xP:</span> <span className="font-bold">{report.updated_squad.vice_captain.xp.toFixed(2)}</span>
                            </div>
                            <div>
                              <span className="opacity-70">Form:</span> <span className="font-bold">{report.updated_squad.vice_captain.form.toFixed(1)}</span>
                            </div>
                            <div>
                              <span className="opacity-70">FDR:</span> <span className="font-bold">{report.updated_squad.vice_captain.fdr.toFixed(1)}</span>
                            </div>
                            <div>
                              <span className="opacity-70">Fixture:</span> <span className="font-bold">{report.updated_squad.vice_captain.fixture}</span>
                            </div>
                          </div>
                          <p className="mt-2 text-xs opacity-80 italic">{report.updated_squad.vice_captain.reason}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Chip Recommendation */}
          <div>
            <h2 className="text-lg font-bold uppercase mb-3 border-b-2 border-retro-primary pb-1">Chip Recommendation</h2>
            <div className="bg-retro-background p-4 border-2 border-retro-primary">
              <p className="text-sm mb-2">
                <strong>Suggestion:</strong> Play <strong>{report.chip_recommendation.best_chip}</strong>.
              </p>
              {Object.entries(report.chip_recommendation.evaluations).length > 0 && (
                <ul className="list-disc list-inside space-y-1 text-sm mt-2">
                  {Object.entries(report.chip_recommendation.evaluations).map(([chipName, evaluation]) => (
                    <li key={chipName}>
                      <strong>{chipName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong> {(evaluation as { reason: string }).reason}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Fixture Analysis Insights */}
          {(report.fixture_insights.best_fixture_runs.length > 0 || 
            report.fixture_insights.bgw_alerts.length > 0) && (
            <div>
              <h2 className="text-lg font-bold uppercase mb-3 border-b-2 border-retro-primary pb-1">Fixture Analysis Insights</h2>
              
              {report.fixture_insights.best_fixture_runs.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-bold uppercase mb-2">Best Fixture Runs (Next 3 GWs)</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full border-2 border-retro-primary">
                      <thead className="bg-retro-background">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-bold">Player</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">Team</th>
                          <th className="px-3 py-2 text-center text-xs font-bold">
                            <Tooltip text="Average Fixture Difficulty Rating: Average difficulty of next 3 fixtures (1-5, lower is easier)">
                              Avg FDR
                            </Tooltip>
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.fixture_insights.best_fixture_runs.map((run, idx) => (
                          <tr key={idx} className="border-b border-retro-primary">
                            <td className="px-3 py-2 text-sm">{run.player}</td>
                            <td className="px-3 py-2 text-center text-xs">{run.team}</td>
                            <td className="px-3 py-2 text-center text-xs font-mono">{run.avg_fdr.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {report.fixture_insights.bgw_alerts.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-bold uppercase mb-2">Blank Gameweek Alerts</h3>
                  <p className="text-sm mb-2">Teams likely to blank:</p>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    {report.fixture_insights.bgw_alerts.map((alert, idx) => (
                      <li key={idx}><strong>{alert.team}</strong></li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </DesktopWindow>
    </div>
  );
};

export default Recommendations;
