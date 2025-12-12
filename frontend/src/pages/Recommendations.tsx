import React, { useEffect, useState } from 'react';
import DesktopWindow from '../components/retroui/DesktopWindow';
import { useAppContext } from '../context/AppContext';
import { mlApi } from '../services/api';
import { MLReport } from '../types';
import LoadingSpinner from '../components/common/LoadingSpinner';

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
        // Use fast_mode=false to get full ML analysis on GCE VM (32GB RAM, 8 CPUs)
        const data = await mlApi.getMLReport(entryId, currentGameweek, false);
        console.log('ML Report: Received data:', data);
        setReport(data);
        setError(null);
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
    return (
      <div className="h-[80vh] flex flex-col items-center justify-center">
        <LoadingSpinner text="Generating ML Report..." />
        <p className="mt-4 font-mono text-xs opacity-60">Running complete analysis pipeline. This may take up to 5 minutes.</p>
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
                      <th className="px-3 py-2 text-center text-xs font-bold">xP</th>
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

          {/* Fixture Analysis Insights */}
          {(report.fixture_insights.best_fixture_runs.length > 0 || 
            report.fixture_insights.dgw_alerts.length > 0 || 
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
                          <th className="px-3 py-2 text-center text-xs font-bold">Avg FDR</th>
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

              {report.fixture_insights.dgw_alerts.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-bold uppercase mb-2">Double Gameweek Alerts</h3>
                  <p className="text-sm mb-2">Teams with potential DGW:</p>
                  <ul className="list-disc list-inside space-y-1 text-sm">
                    {report.fixture_insights.dgw_alerts.map((alert, idx) => (
                      <li key={idx}>
                        <strong>{alert.team}</strong>: {Math.round(alert.probability * 100)}% probability
                      </li>
                    ))}
                  </ul>
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

          {/* Transfer Recommendations */}
          <div>
            <h2 className="text-lg font-bold uppercase mb-3 border-b-2 border-retro-primary pb-1">Transfer Recommendations</h2>
            {!report.transfer_recommendations.top_suggestion ? (
              <p className="text-sm">No beneficial transfers found.</p>
            ) : (
              <div className="bg-retro-background p-4 border-2 border-retro-primary">
                <p className="text-sm mb-2">
                  <strong>Top Suggestion:</strong> {report.transfer_recommendations.top_suggestion.num_transfers} transfer(s) with a net EV gain of <strong>{report.transfer_recommendations.top_suggestion.net_ev_gain.toFixed(2)}</strong>.
                </p>
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
                          <th className="px-3 py-2 text-center text-xs font-bold">xP</th>
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
                          <th className="px-3 py-2 text-center text-xs font-bold">xP</th>
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
                      <strong>{chipName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong> {evaluation.reason}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </DesktopWindow>
    </div>
  );
};

export default Recommendations;
