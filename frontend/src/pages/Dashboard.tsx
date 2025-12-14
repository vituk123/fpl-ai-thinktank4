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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      if (!entryId) return;
      try {
        const histData = await dashboardApi.getTeamHistory(entryId);
        setHistory(histData);
      } catch (e) {
        console.error(e);
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

  // Transform data for charts (mock logic if structure varies, assuming standard API response)
  // Assuming history is array of { event: number, overall_rank: number }
  const chartData = history?.history || [];

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
        <div className="h-64 w-full">
            {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ccc" />
                        <XAxis dataKey="event" stroke="#1D1D1B" style={{ fontSize: '12px', fontFamily: 'monospace' }} />
                        <YAxis reversed stroke="#1D1D1B" style={{ fontSize: '12px', fontFamily: 'monospace' }} />
                        <Tooltip 
                            contentStyle={{ 
                                backgroundColor: '#FFF', 
                                border: '2.5px solid #1D1D1B', 
                                boxShadow: '4px 4px 0 rgba(0,0,0,0.2)',
                                borderRadius: 0 
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

      {/* Placeholders for other widgets */}
      <DesktopWindow title="System Status" className="col-span-1">
          <div className="font-mono text-xs space-y-2">
              <p>API_CONNECTION: <span className="text-green-600 font-bold">ESTABLISHED</span></p>
              <p>DATA_STREAM: <span className="text-green-600 font-bold">ACTIVE</span></p>
              <p>LAST_UPDATE: {new Date().toLocaleTimeString()}</p>
          </div>
      </DesktopWindow>

    </div>
  );
};

export default Dashboard;