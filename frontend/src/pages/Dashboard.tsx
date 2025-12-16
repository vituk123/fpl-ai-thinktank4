import React, { useEffect, useState } from 'react';
import DesktopWindow from '../components/retroui/DesktopWindow';
import { useAppContext } from '../context/AppContext';
import { dashboardApi } from '../services/api';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import LoadingLogo from '../components/common/LoadingLogo';
import MiniLeagueTable from '../components/dashboard/MiniLeagueTable';

const Dashboard: React.FC = () => {
  const { entryId, entryInfo } = useAppContext();
  const [history, setHistory] = useState<any>(null);
  const [captainData, setCaptainData] = useState<any>(null);
  const [transferData, setTransferData] = useState<any>(null);
  const [ownershipData, setOwnershipData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      if (!entryId) return;
      try {
        // Fetch all data in parallel
        const [historyResult, captainResult, transferResult, ownershipResult] = await Promise.allSettled([
          dashboardApi.getTeamHistory(entryId),
          dashboardApi.getCaptainPerformance(entryId),
          dashboardApi.getTransferAnalysis(entryId),
          dashboardApi.getOwnershipCorrelation()
        ]);

        if (historyResult.status === 'fulfilled') {
          console.log('Dashboard: Team history response:', historyResult.value);
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/cbe61e98-98ca-4046-830f-3dbf90ee4a82',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Dashboard.tsx:30',message:'Team history response received',data:{hasData:!!historyResult.value,dataKeys:historyResult.value?Object.keys(historyResult.value):[],dataStructure:JSON.stringify(historyResult.value).substring(0,500)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
          // #endregion
          setHistory(historyResult.value);
        } else {
          console.error('Dashboard: Error fetching team history:', historyResult.reason);
        }

        if (captainResult.status === 'fulfilled') {
          console.log('Dashboard: Captain performance response:', captainResult.value);
          // #region agent log
          const captainData = captainResult.value?.data || captainResult.value;
          const captains = captainData?.captains || [];
          const sampleCaptain = captains[0] || null;
          fetch('http://127.0.0.1:7242/ingest/cbe61e98-98ca-4046-830f-3dbf90ee4a82',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Dashboard.tsx:37',message:'Captain performance response received',data:{captainsCount:captains.length,sampleCaptain:sampleCaptain,allPointsZero:captains.every((c:any)=>!c.points),allDoubledZero:captains.every((c:any)=>!c.doubled_points)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
          // #endregion
          setCaptainData(captainResult.value);
        } else {
          console.error('Dashboard: Error fetching captain performance:', captainResult.reason);
        }

        if (transferResult.status === 'fulfilled') {
          console.log('Dashboard: Transfer analysis response:', transferResult.value);
          console.log('Dashboard: Transfer analysis data structure:', {
            hasData: !!transferResult.value?.data,
            hasTransfers: !!transferResult.value?.data?.transfers,
            transfersLength: transferResult.value?.data?.transfers?.length,
            transfersType: typeof transferResult.value?.data?.transfers,
            isArray: Array.isArray(transferResult.value?.data?.transfers)
          });
          // #region agent log
          const transferData = transferResult.value?.data || transferResult.value;
          const transfers = transferData?.transfers || [];
          const sampleTransfer = transfers[0] || null;
          fetch('http://127.0.0.1:7242/ingest/cbe61e98-98ca-4046-830f-3dbf90ee4a82',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Dashboard.tsx:44',message:'Transfer analysis response received',data:{transfersCount:transfers.length,sampleTransfer:sampleTransfer,allPredictedZero:transfers.every((t:any)=>!t.predicted_gain),allActualZero:transfers.every((t:any)=>!t.actual_gain)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
          // #endregion
          setTransferData(transferResult.value);
        } else {
          console.error('Dashboard: Error fetching transfer analysis:', transferResult.reason);
        }

        if (ownershipResult.status === 'fulfilled') {
          console.log('Dashboard: Ownership correlation response:', ownershipResult.value);
          // #region agent log
          const ownershipData = ownershipResult.value?.data || ownershipResult.value;
          const players = ownershipData?.players || [];
          const samplePlayer = players[0] || null;
          fetch('http://127.0.0.1:7242/ingest/cbe61e98-98ca-4046-830f-3dbf90ee4a82',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Dashboard.tsx:51',message:'Ownership correlation response received',data:{playersCount:players.length,samplePlayer:samplePlayer,allPointsZero:players.every((p:any)=>!p.total_points),correlationCoeff:ownershipData?.correlation_coefficient},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
          // #endregion
          setOwnershipData(ownershipResult.value);
        } else {
          console.error('Dashboard: Error fetching ownership correlation:', ownershipResult.reason);
        }
      } catch (e) {
        console.error('Dashboard: Error fetching data:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [entryId]);

  if (loading) {
    const dashboardPhases = [
      { message: "Fetching team data...", duration: 1500 },
      { message: "Loading analytics...", duration: 2000 },
      { message: "Calculating statistics...", duration: 1500 },
      { message: "Preparing charts...", duration: 1000 },
    ];
    return <LoadingLogo phases={dashboardPhases} />;
  }

  // Transform data for charts - handle different response structures
  let chartData: any[] = [];
  if (history) {
    // Backend returns StandardResponse format: { data: { gameweeks: [], overall_rank: [] }, meta: {} }
    const data = history.data || history;
    
    // If backend returns separate arrays for gameweeks and overall_rank, combine them
    if (data.gameweeks && Array.isArray(data.gameweeks) && data.overall_rank && Array.isArray(data.overall_rank)) {
      chartData = data.gameweeks.map((gw: number, index: number) => ({
        event: gw,
        overall_rank: data.overall_rank[index] || 0
      }));
    } 
    // If it's already an array of objects
    else if (Array.isArray(data)) {
      chartData = data;
    } 
    // If data has a history array
    else if (data.history && Array.isArray(data.history)) {
      chartData = data.history;
    }
    // If data has rank_progression array
    else if (data.rank_progression && Array.isArray(data.rank_progression)) {
      chartData = data.rank_progression;
    }
  }
  
  console.log('Dashboard: Chart data:', chartData);

  return (
    <div className="p-4 md:p-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-24">
      
      {/* User Profile Card */}
      <DesktopWindow title="Manager Profile" className="col-span-1 h-fit">
        <div className="flex flex-col items-center text-center space-y-4">
             <div>
                 <h2 className="text-xl font-bold uppercase">{entryInfo?.name}</h2>
                 <p className="text-sm font-mono">{entryInfo?.player_first_name} {entryInfo?.player_last_name}</p>
                 <div className="mt-4 grid grid-cols-2 gap-2 text-left">
                     <div className="border border-retro-primary p-2 bg-retro-background">
                         <span className="block text-[10px] uppercase font-bold">Total Points</span>
                         <span className="text-lg font-mono">{entryInfo?.summary_overall_points}</span>
                     </div>
                     <div className="border border-retro-primary p-2 bg-retro-background">
                         <span className="block text-[10px] uppercase font-bold">Overall Rank</span>
                         <span className="text-lg font-mono">#{entryInfo?.summary_overall_rank?.toLocaleString()}</span>
                     </div>
                 </div>
             </div>
        </div>
      </DesktopWindow>

      {/* Mini-League Standings */}
      <MiniLeagueTable />

      {/* Rank History Chart */}
      <DesktopWindow title="Rank Progression" className="col-span-1 md:col-span-2 min-h-[300px]">
        <div className="h-64 w-full" style={{ minHeight: '256px', minWidth: '100%' }}>
            {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%" minHeight={256} minWidth={0}>
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ccc" />
                        <XAxis 
                            dataKey="event" 
                            stroke="#1D1D1B" 
                            style={{ fontSize: '12px', fontFamily: 'monospace' }}
                            label={{ value: 'Gameweek', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle', fontSize: '12px', fontFamily: 'monospace', fill: '#1D1D1B' } }}
                        />
                        <YAxis 
                            reversed 
                            stroke="#1D1D1B" 
                            style={{ fontSize: '12px', fontFamily: 'monospace' }}
                            tickFormatter={(value) => {
                                if (value >= 1000000) {
                                    const millions = Math.round(value / 1000000);
                                    return `Top ${millions} Mill`;
                                } else if (value >= 1000) {
                                    const thousands = Math.round(value / 1000);
                                    return `Top ${thousands}K`;
                                }
                                return `Top ${value}`;
                            }}
                            label={{ value: 'Overall Rank', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fontSize: '12px', fontFamily: 'monospace', fill: '#1D1D1B' } }}
                        />
                        <Tooltip 
                            contentStyle={{ 
                                backgroundColor: '#FFF', 
                                border: '2.5px solid #1D1D1B', 
                                boxShadow: '4px 4px 0 rgba(0,0,0,0.2)',
                                borderRadius: 0 
                            }}
                            formatter={(value: any) => {
                                const rank = Number(value);
                                if (rank >= 1000000) {
                                    const millions = Math.round(rank / 1000000);
                                    return `Top ${millions} Mill`;
                                } else if (rank >= 1000) {
                                    const thousands = Math.round(rank / 1000);
                                    return `Top ${thousands}K`;
                                }
                                return `Top ${rank}`;
                            }}
                        />
                        <Line type="step" dataKey="overall_rank" stroke="#1D1D1B" strokeWidth={2.5} dot={{ stroke: '#1D1D1B', strokeWidth: 2, r: 4, fill: '#fff' }} />
                    </LineChart>
                </ResponsiveContainer>
            ) : (
                <div className="h-full flex items-center justify-center font-mono text-sm opacity-50">NO DATA AVAILABLE</div>
            )}
         </div>
      </DesktopWindow>

      {/* Captain Performance Section */}
      <DesktopWindow title="Captain Performance" className="col-span-1">
        {(() => {
          const captains = captainData?.data?.captains;
          console.log('Captain Performance Render Check:', {
            hasCaptainData: !!captainData,
            hasData: !!captainData?.data,
            hasCaptains: !!captains,
            captainsLength: captains?.length,
            isArray: Array.isArray(captains),
            shouldRender: captains && Array.isArray(captains) && captains.length > 0
          });
          return captains && Array.isArray(captains) && captains.length > 0;
        })() ? (
          <div className="space-y-3">
            {(() => {
              const captains = captainData.data.captains;
              // Find most captained player
              const mostCaptained = captains.reduce((max: any, curr: any) => 
                curr.times_captained > max.times_captained ? curr : max, captains[0]);
              // Calculate total captain points
              const totalCaptainPoints = captains.reduce((sum: number, c: any) => sum + (c.doubled_points || 0), 0);
              // Calculate average captain points
              const avgCaptainPoints = captains.length > 0 ? totalCaptainPoints / captains.length : 0;
              
              return (
                <div className="grid grid-cols-1 gap-3">
                  <div className="border border-retro-primary p-3 bg-retro-background">
                    <span className="block text-[10px] uppercase font-bold mb-1">Most Captained</span>
                    <span className="text-base font-mono font-bold">{mostCaptained?.player_name || 'N/A'}</span>
                    <span className="block text-xs text-gray-600 mt-1">{mostCaptained?.times_captained || 0}x</span>
                  </div>
                  <div className="border border-retro-primary p-3 bg-retro-background">
                    <span className="block text-[10px] uppercase font-bold mb-1">Total Captain Points</span>
                    <span className="text-lg font-mono font-bold">{totalCaptainPoints.toFixed(0)}</span>
                  </div>
                  <div className="border border-retro-primary p-3 bg-retro-background">
                    <span className="block text-[10px] uppercase font-bold mb-1">Average Captain Points</span>
                    <span className="text-lg font-mono font-bold">{avgCaptainPoints.toFixed(1)}</span>
                  </div>
                </div>
              );
            })()}
          </div>
        ) : (
          <div className="font-mono text-xs opacity-50 text-center py-4">NO DATA AVAILABLE</div>
        )}
      </DesktopWindow>

      {/* Transfer Analysis Section */}
      <DesktopWindow title="Transfer Analysis" className="col-span-1 md:col-span-2">
        {transferData?.data?.transfers && Array.isArray(transferData.data.transfers) && transferData.data.transfers.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b-2 border-retro-primary">
                  <th className="text-left p-2 uppercase font-bold">GW</th>
                  <th className="text-left p-2 uppercase font-bold">Players In</th>
                  <th className="text-left p-2 uppercase font-bold">Players Out</th>
                  <th className="text-right p-2 uppercase font-bold">Predicted</th>
                  <th className="text-right p-2 uppercase font-bold">Actual</th>
                  <th className="text-right p-2 uppercase font-bold">Success %</th>
                </tr>
              </thead>
              <tbody>
                {transferData.data.transfers.map((transfer: any, index: number) => (
                  <tr key={index} className="border-b border-retro-primary hover:bg-retro-background">
                    <td className="p-2 font-bold">{transfer.gw}</td>
                    <td className="p-2">
                      {Array.isArray(transfer.players_in) 
                        ? transfer.players_in.join(', ') 
                        : transfer.players_in || '-'}
                    </td>
                    <td className="p-2">
                      {Array.isArray(transfer.players_out) 
                        ? transfer.players_out.join(', ') 
                        : transfer.players_out || '-'}
                    </td>
                    <td className="p-2 text-right">{transfer.predicted_gain?.toFixed(1) || '0.0'}</td>
                    <td className="p-2 text-right">{transfer.actual_gain?.toFixed(1) || '0.0'}</td>
                    <td className="p-2 text-right">{transfer.success_rate?.toFixed(1) || '0.0'}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="font-mono text-xs opacity-50 text-center py-4">NO DATA AVAILABLE</div>
        )}
      </DesktopWindow>

      {/* Ownership vs Points Correlation Section */}
      <DesktopWindow title="Ownership vs Points Correlation" className="col-span-1 md:col-span-2">
        {ownershipData?.data?.players && ownershipData.data.players.length > 0 ? (
          <div className="space-y-3">
            {ownershipData.data.correlation_coefficient != null && (
              <div className="border border-retro-primary p-2 bg-retro-background text-center">
                <span className="text-xs uppercase font-bold">Correlation: </span>
                <span className="text-sm font-mono font-bold">
                  {Number(ownershipData.data.correlation_coefficient).toFixed(3)}
                </span>
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b-2 border-retro-primary">
                    <th className="text-left p-2 uppercase font-bold">Player</th>
                    <th className="text-right p-2 uppercase font-bold">Ownership %</th>
                    <th className="text-right p-2 uppercase font-bold">Points</th>
                    <th className="text-right p-2 uppercase font-bold">Differential</th>
                  </tr>
                </thead>
                <tbody>
                  {ownershipData.data.players.slice(0, 25).map((player: any, index: number) => (
                    <tr key={index} className="border-b border-retro-primary hover:bg-retro-background">
                      <td className="p-2 font-bold">{player.name}</td>
                      <td className="p-2 text-right">{player.ownership?.toFixed(1) || '0.0'}%</td>
                      <td className="p-2 text-right">{player.total_points || 0}</td>
                      <td className="p-2 text-right font-bold">{player.differential_score?.toFixed(2) || '0.00'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="font-mono text-xs opacity-50 text-center py-4">NO DATA AVAILABLE</div>
        )}
      </DesktopWindow>

    </div>
  );
};

export default Dashboard;