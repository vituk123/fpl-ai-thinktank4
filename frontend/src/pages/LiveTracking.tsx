import React, { useEffect, useState } from 'react';
import DesktopWindow from '../components/retroui/DesktopWindow';
import { useAppContext } from '../context/AppContext';
import { liveApi, imagesApi, entryApi } from '../services/api';
import LoadingLogo from '../components/common/LoadingLogo';

const LiveTracking: React.FC = () => {
  const { entryId } = useAppContext();
  const [liveData, setLiveData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [currentGameweek, setCurrentGameweek] = useState<number>(1);

  // Fetch live data - optimize by fetching gameweek and live data in parallel
  useEffect(() => {
    if (!entryId) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        // Fetch gameweek and live data in parallel for faster loading
        // Use a reasonable default gameweek (16-20 range) to start, backend will handle if wrong
        const defaultGameweek = 16; // Common gameweek range, will be corrected by backend
        
        const [gameweekResult, liveDataResult] = await Promise.allSettled([
          entryApi.getCurrentGameweek(),
          liveApi.getLiveGameweek(defaultGameweek, entryId)
        ]);

        // Get the actual gameweek
        let gameweek = defaultGameweek;
        if (gameweekResult.status === 'fulfilled') {
          gameweek = gameweekResult.value;
          setCurrentGameweek(gameweek);
          console.log('LiveTracking: Fetched current gameweek from backend:', gameweek);
        }

        // Handle live data result
        if (liveDataResult.status === 'fulfilled' && liveDataResult.value) {
          let data = liveDataResult.value;
          const playerBreakdown = data?.data?.player_breakdown || data?.player_breakdown || [];
          
          // If data is empty and we have the correct gameweek, try fetching with that
          if (playerBreakdown.length === 0 && gameweek !== defaultGameweek && gameweek > 1) {
            console.log("LiveTracking: No players found, trying fetched gameweek:", gameweek);
            try {
              data = await liveApi.getLiveGameweek(gameweek, entryId);
            } catch (e) {
              console.error("LiveTracking: Failed to fetch with gameweek:", e);
            }
          }
          
          // Update gameweek from data if available
          if (data?.data?.gameweek) {
            setCurrentGameweek(data.data.gameweek);
          }
          
          setLiveData(data);
          setLastUpdated(new Date());
        } else if (gameweekResult.status === 'fulfilled' && gameweek > 1) {
          // If live data fetch failed but we have gameweek, try fetching with correct gameweek
          try {
            const data = await liveApi.getLiveGameweek(gameweek, entryId);
            setLiveData(data);
            setLastUpdated(new Date());
          } catch (e: any) {
            console.error("LiveTracking: Fetch error:", e);
            setLiveData(null);
          }
        } else {
          setLiveData(null);
        }
      } catch (e: any) {
        console.error("LiveTracking: Error fetching data:", e);
        setLiveData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // 60s auto refresh
    return () => clearInterval(interval);
  }, [entryId]);

  if (!entryId) {
    return (
      <div className="p-4 md:p-8 pb-24">
        <DesktopWindow title={`Live GW${currentGameweek} Tracking`} className="min-h-[600px]">
          <div className="p-6 text-center">
            <p className="text-retro-error font-bold mb-2">No Entry ID</p>
            <p className="text-sm opacity-60">Please enter your FPL entry ID on the landing page.</p>
          </div>
        </DesktopWindow>
      </div>
    );
  }

  if (loading) {
    const livePhases = [
      { message: "Syncing with FPL API...", duration: 2000 },
      { message: "Calculating live points...", duration: 1500 },
      { message: "Processing player data...", duration: 2000 },
      { message: "Updating rankings...", duration: 1000 },
    ];
    return <LoadingLogo phases={livePhases} />;
  }

  if (!liveData) {
    return (
      <div className="p-4 md:p-8 pb-24">
        <DesktopWindow title={`Live GW${currentGameweek} Tracking`} className="min-h-[600px]">
          <div className="p-6 text-center">
            <p className="text-retro-error font-bold mb-2">No live data available</p>
            <p className="text-sm opacity-60">Unable to fetch live gameweek data. Please try again.</p>
            <p className="text-xs opacity-40 mt-2">Entry ID: {entryId} | Gameweek: {currentGameweek}</p>
          </div>
        </DesktopWindow>
      </div>
    );
  }

  // Both Render backend and Edge Function return: { data: { live_points, player_breakdown, team_summary }, meta }
  const data = liveData?.data || liveData;
  console.log("LiveTracking: Extracted data:", {
    data,
    livePoints: data?.live_points,
    playerBreakdown: data?.player_breakdown,
    teamSummary: data?.team_summary
  });
  
  const livePoints = data?.live_points || {};
  const teamSummaryRaw = data?.team_summary || {};
  const playerBreakdown = data?.player_breakdown || [];
  const autoSubstitutions = data?.auto_substitutions || [];
  
  console.log("LiveTracking: Player breakdown count:", playerBreakdown.length);
  if (playerBreakdown.length > 0) {
    console.log("LiveTracking: First player sample:", playerBreakdown[0]);
  }
  
  // Normalize team_summary format (Render uses gw_rank/live_rank, Edge Function uses gameweek_rank/overall_rank)
  // Handle both formats and ensure we don't treat 0 as falsy (0 is a valid rank)
  const gameweekRank = teamSummaryRaw.gameweek_rank ?? teamSummaryRaw.gw_rank ?? null;
  const overallRank = teamSummaryRaw.overall_rank ?? teamSummaryRaw.live_rank ?? null;
  
  const teamSummary = {
    gameweek_rank: gameweekRank !== null && gameweekRank !== undefined ? gameweekRank : null,
    overall_rank: overallRank !== null && overallRank !== undefined ? overallRank : null,
    ...teamSummaryRaw
  };
  
  console.log("LiveTracking: Team summary ranks:", {
    raw: teamSummaryRaw,
    normalized: { gameweek_rank: teamSummary.gameweek_rank, overall_rank: teamSummary.overall_rank }
  });
  
  // Helper function to format status with local timezone conversion
  const formatStatus = (status: string, kickoffTimeUtc: string | null | undefined): string => {
    if (!status || !status.startsWith('Playing ')) {
      return status;
    }
    
    // If we have UTC kickoff time, convert it to local timezone
    if (kickoffTimeUtc) {
      try {
        const kickoffDate = new Date(kickoffTimeUtc);
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const day = dayNames[kickoffDate.getDay()];
        const hours = kickoffDate.getHours().toString().padStart(2, '0');
        const minutes = kickoffDate.getMinutes().toString().padStart(2, '0');
        return `Playing ${day} ${hours}:${minutes}`;
      } catch (e) {
        console.error('Error formatting kickoff time:', e);
        return status; // Fallback to original status
      }
    }
    
    return status;
  };

  // Transform player_breakdown to match component expectations
  // Handle both Render backend format (has 'name', 'minutes', 'status', 'photo') and Edge Function format (has 'player_name', 'player_id')
  const elements = playerBreakdown.map((player: any, index: number) => {
    // Detect which format we have
    const isRenderFormat = player.name !== undefined || player.minutes !== undefined;
    
    if (isRenderFormat) {
      // Render backend format: { id, name, team, opponent, position, points, base_points, minutes, status, is_captain, is_vice_captain, element_type, photo }
      const webName = player.name || 'Unknown';
      if (webName === 'Unknown' && index === 0) {
        console.warn("LiveTracking: Player name is Unknown for first player:", player);
      }
      return {
        id: player.id,
        element: player.id,
        web_name: webName,
        player_name: player.name,
        position: player.position,
        points: player.points || 0,
        base_points: player.base_points || player.points || 0,
        is_captain: player.is_captain,
        is_vice_captain: player.is_vice_captain || player.is_vice,
        is_starting: player.position <= 11,
        multiplier: player.is_captain ? 2 : 1,
        minutes_played: player.minutes || 0,
        status: formatStatus(player.status, player.kickoff_time_utc),
        opponent: player.opponent || '',
        team: player.team || '',
        photo: player.photo,
        bonus: 0, // Bonus points not in breakdown, would need separate call
      };
    } else {
      // Edge Function format: { player_id, player_name, position, points, is_captain, is_vice_captain, is_starting }
      const playerName = player.player_name;
      const webName = playerName?.split(' ').pop() || playerName || 'Unknown';
      if (webName === 'Unknown' && index === 0) {
        console.warn("LiveTracking: Player name is Unknown for first player (Edge Function):", player);
      }
      return {
        id: player.player_id,
        element: player.player_id,
        web_name: webName,
        player_name: playerName,
        position: player.position,
        points: player.points || 0,
        base_points: player.points || 0,
        is_captain: player.is_captain,
        is_vice_captain: player.is_vice_captain,
        is_starting: player.is_starting,
        multiplier: player.is_captain ? 2 : 1,
        minutes_played: 0, // Not available from Edge Function
        status: '',
        opponent: '',
        team: '',
        photo: '',
        bonus: 0,
      };
    }
  });
  
  console.log("LiveTracking: Transformed elements count:", elements.length);
  if (elements.length === 0) {
    console.error("LiveTracking: No elements after transformation!");
  }
  
  return (
    <div className="p-4 md:p-8 pb-24">
      <DesktopWindow title={`Live GW${currentGameweek} Tracking`} className="min-h-[600px]">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            
            {/* Scoreboard */}
            <div className="lg:col-span-1 space-y-4">
                <div className="bg-retro-primary text-white p-4 border-2 border-black shadow-[4px_4px_0_rgba(0,0,0,0.2)]">
                    <h3 className="text-xs uppercase font-bold tracking-widest mb-1">Live Points</h3>
                    <div className="text-5xl font-mono font-bold">{livePoints?.starting_xi || livePoints?.total || 0}</div>
                    <div className="mt-2 text-xs opacity-80 font-mono">
                      GW Rank: {teamSummary.gameweek_rank !== null && teamSummary.gameweek_rank !== undefined ? teamSummary.gameweek_rank.toLocaleString() : '-'}
                    </div>
                    <div className="mt-1 text-xs opacity-60 font-mono">
                      Overall: {teamSummary.overall_rank !== null && teamSummary.overall_rank !== undefined ? teamSummary.overall_rank.toLocaleString() : '-'}
                    </div>
                </div>
                
                <div className="border-retro border-retro-primary p-4 bg-white">
                    <h3 className="text-xs uppercase font-bold mb-2 border-b-2 border-retro-primary pb-1">Captain</h3>
                    {elements.filter((p: any) => p.is_captain).map((cap: any) => (
                        <div key={cap.id} className="flex items-center space-x-2">
                             <div className="font-bold text-lg">{cap.web_name}</div>
                             <div className="bg-black text-white px-2 text-xs font-bold rounded-none">
                                {cap.multiplier}x
                             </div>
                             <div className="ml-auto font-mono text-xl">{cap.points}</div>
                        </div>
                    ))}
                </div>
                
                {autoSubstitutions.length > 0 && (
                    <div className="border-retro border-retro-primary p-4 bg-white">
                        <h3 className="text-xs uppercase font-bold mb-2 border-b-2 border-retro-primary pb-1">Auto Substitutions</h3>
                        {autoSubstitutions.map((sub: any, idx: number) => (
                            <div key={idx} className="mb-2 last:mb-0">
                                <div className="flex items-center justify-between text-sm">
                                    <div className="flex-1">
                                        <div className="font-bold text-red-600 line-through">{sub.out.name}</div>
                                        <div className="text-xs opacity-60">Pos {sub.out.position} →</div>
                                    </div>
                                    <div className="mx-2 text-lg">→</div>
                                    <div className="flex-1 text-right">
                                        <div className="font-bold text-green-600">{sub.in.name}</div>
                                        <div className="text-xs opacity-60">Pos {sub.in.position}</div>
                                    </div>
                                    <div className="ml-2 font-mono font-bold text-green-600">+{sub.points_gain}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
                
                 <div className="text-center text-xs font-mono opacity-50">
                    Last Updated: {lastUpdated.toLocaleTimeString()}
                </div>
            </div>

            {/* Pitch/List View */}
            <div className="lg:col-span-3">
                 {elements.length === 0 ? (
                   <div className="p-6 text-center">
                     <p className="text-retro-error font-bold mb-2">No players found</p>
                     <p className="text-sm opacity-60">Player breakdown is empty. Check console for details.</p>
                   </div>
                 ) : (
                   <div className="space-y-6">
                     {/* Starting XI Section */}
                     <div>
                       <h3 className="text-sm font-bold uppercase tracking-wider mb-3 text-retro-primary border-b-2 border-retro-primary pb-1">
                         Starting XI
                       </h3>
                       <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                         {elements.filter((pick: any) => pick.is_starting).map((pick: any) => (
                             <div key={pick.id} className={`
                            flex items-center p-2 border-2 border-retro-primary bg-white shadow-[2px_2px_0_rgba(0,0,0,0.1)]
                                ${pick.multiplier > 1 ? 'bg-retro-background' : ''}
                         `}>
                             <img 
                                    src={imagesApi.getPlayerImageUrl(pick.element)} 
                                    alt={pick.web_name}
                                    className="w-10 h-10 object-cover object-top mr-3"
                                    onLoad={(e) => {
                                      const img = e.target as HTMLImageElement;
                                      console.log(`[Image Load Success] Player ${pick.element} (${pick.web_name}): ${img.src}`);
                                    }}
                                      onError={(e) => {
                                        const img = e.target as HTMLImageElement;
                                      const currentSrc = img.src;
                                      const errorDetails = {
                                        failedUrl: currentSrc,
                                        playerId: pick.element,
                                        playerName: pick.web_name,
                                        isSupabaseUrl: currentSrc.includes('supabase.co'),
                                        isFPLUrl: currentSrc.includes('resources.fantasy.premierleague.com'),
                                        timestamp: new Date().toISOString()
                                      };
                                      console.error(`[Image Load Error] Player ${pick.element} (${pick.web_name}):`, errorDetails);
                                      
                                      // Try FPL API as fallback (backend provides this in pick.photo)
                                      if (!currentSrc.includes('resources.fantasy.premierleague.com')) {
                                        const fplUrl = pick.photo || imagesApi.getPlayerImageUrlFPL(pick.element);
                                        console.log(`[Image Fallback] Trying FPL URL for player ${pick.element}:`, fplUrl);
                                        // Set a flag to prevent infinite loop
                                        if (!img.dataset.fallbackAttempted) {
                                          img.dataset.fallbackAttempted = 'true';
                                          img.src = fplUrl;
                                        } else {
                                          // Both URLs failed, use a placeholder
                                          console.error(`[Image Final Failure] Both Supabase and FPL URLs failed for player ${pick.element} (${pick.web_name})`);
                                          // Use a data URI placeholder (transparent 1x1 pixel)
                                          img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTA%2BIHk9IjUwJSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk5PPC90ZXh0Pjwvc3ZnPg==';
                                          img.style.opacity = '0.5';
                                        }
                                      } else {
                                        // FPL API also failed, use placeholder
                                        console.error(`[Image Final Failure] Both Supabase and FPL URLs failed for player ${pick.element} (${pick.web_name})`);
                                        img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTA%2BIHk9IjUwJSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk5PPC90ZXh0Pjwvc3ZnPg==';
                                        img.style.opacity = '0.5';
                                        }
                                      }}
                             />
                             <div className="flex-1">
                                 <div className="flex justify-between items-center">
                                         <div className="flex items-center gap-1">
                                           <span className="font-bold text-sm">{pick.web_name}</span>
                                           {pick.is_captain && (
                                             <span className="bg-retro-primary text-white border border-black text-[10px] w-5 h-5 flex items-center justify-center font-bold rounded-none">
                                               C
                                             </span>
                                           )}
                                           {pick.is_vice_captain && !pick.is_captain && (
                                             <span className="bg-gray-600 text-white border border-black text-[10px] w-5 h-5 flex items-center justify-center font-bold rounded-none">
                                               V
                                             </span>
                                           )}
                                         </div>
                                         <span className="font-mono font-bold text-lg">{pick.points}</span>
                                           </div>
                                     <div className="text-xs opacity-60 flex justify-between">
                                         <span>{pick.status || `Pos ${pick.position}`}</span>
                                         {pick.minutes_played > 0 && <span>{pick.minutes_played}'</span>}
                                       </div>
                                     {pick.opponent && pick.opponent !== 'N/A' && (
                                       <div className="text-[10px] opacity-50 mt-0.5">
                                         vs {pick.opponent}
                                       </div>
                                   )}
                                 </div>
                                 {pick.bonus > 0 && (
                                     <div className="ml-2 bg-yellow-400 text-black border border-black text-[10px] w-5 h-5 flex items-center justify-center font-bold">
                                         {pick.bonus}
                                 </div>
                             )}
                         </div>
                         ))}
                       </div>
                     </div>

                     {/* Divider */}
                     <div className="border-t-2 border-dashed border-retro-primary my-4"></div>

                     {/* Bench Section */}
                     <div className="border-2 border-dashed border-retro-primary p-4 bg-white">
                       <h3 className="text-sm font-bold uppercase tracking-wider mb-3 text-retro-primary border-b-2 border-dashed border-retro-primary pb-1">
                         Bench
                       </h3>
                       <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                         {elements.filter((pick: any) => !pick.is_starting).map((pick: any) => (
                             <div key={pick.id} className={`
                                flex items-center p-2 border-2 border-dashed border-retro-primary bg-white
                                ${pick.multiplier > 1 ? 'bg-retro-background' : ''}
                               `}>
                                   <img 
                                    src={imagesApi.getPlayerImageUrl(pick.element)} 
                                    alt={pick.web_name}
                                    className="w-10 h-10 object-cover object-top mr-3"
                                    onLoad={(e) => {
                                      const img = e.target as HTMLImageElement;
                                      console.log(`[Image Load Success] Player ${pick.element} (${pick.web_name}): ${img.src}`);
                                    }}
                                      onError={(e) => {
                                        const img = e.target as HTMLImageElement;
                                      const currentSrc = img.src;
                                      const errorDetails = {
                                        failedUrl: currentSrc,
                                        playerId: pick.element,
                                        playerName: pick.web_name,
                                        isSupabaseUrl: currentSrc.includes('supabase.co'),
                                        isFPLUrl: currentSrc.includes('resources.fantasy.premierleague.com'),
                                        timestamp: new Date().toISOString()
                                      };
                                      console.error(`[Image Load Error] Player ${pick.element} (${pick.web_name}):`, errorDetails);
                                      
                                      // Try FPL API as fallback (backend provides this in pick.photo)
                                      if (!currentSrc.includes('resources.fantasy.premierleague.com')) {
                                        const fplUrl = pick.photo || imagesApi.getPlayerImageUrlFPL(pick.element);
                                        console.log(`[Image Fallback] Trying FPL URL for player ${pick.element}:`, fplUrl);
                                        // Set a flag to prevent infinite loop
                                        if (!img.dataset.fallbackAttempted) {
                                          img.dataset.fallbackAttempted = 'true';
                                          img.src = fplUrl;
                                        } else {
                                          // Both URLs failed, use a placeholder
                                          console.error(`[Image Final Failure] Both Supabase and FPL URLs failed for player ${pick.element} (${pick.web_name})`);
                                          // Use a data URI placeholder (transparent 1x1 pixel)
                                          img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTA%2BIHk9IjUwJSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk5PPC90ZXh0Pjwvc3ZnPg==';
                                          img.style.opacity = '0.5';
                                        }
                                      } else {
                                        // FPL API also failed, use placeholder
                                        console.error(`[Image Final Failure] Both Supabase and FPL URLs failed for player ${pick.element} (${pick.web_name})`);
                                        img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTA%2BIHk9IjUwJSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk5PPC90ZXh0Pjwvc3ZnPg==';
                                        img.style.opacity = '0.5';
                                        }
                                      }}
                                   />
                                   <div className="flex-1">
                                       <div className="flex justify-between items-center">
                                         <div className="flex items-center gap-1">
                                           <span className="font-bold text-sm">{pick.web_name}</span>
                                           {pick.is_captain && (
                                             <span className="bg-retro-primary text-white border border-black text-[10px] w-5 h-5 flex items-center justify-center font-bold rounded-none">
                                               C
                                             </span>
                                           )}
                                           {pick.is_vice_captain && !pick.is_captain && (
                                             <span className="bg-gray-600 text-white border border-black text-[10px] w-5 h-5 flex items-center justify-center font-bold rounded-none">
                                               V
                                             </span>
                                           )}
                                         </div>
                                         <span className="font-mono font-bold text-lg">{pick.points}</span>
                                     </div>
                                     <div className="text-xs opacity-60 flex justify-between">
                                         <span>{pick.status || `Bench ${pick.position - 11}`}</span>
                                         {pick.minutes_played > 0 && <span>{pick.minutes_played}'</span>}
                                           </div>
                                     {pick.opponent && pick.opponent !== 'N/A' && (
                                       <div className="text-[10px] opacity-50 mt-0.5">
                                         vs {pick.opponent}
                                       </div>
                                     )}
                                           </div>
                                 {pick.bonus > 0 && (
                                     <div className="ml-2 bg-yellow-400 text-black border border-black text-[10px] w-5 h-5 flex items-center justify-center font-bold">
                                         {pick.bonus}
                                       </div>
                                 )}
                                   </div>
                         ))}
                       </div>
                     </div>
                 </div>
                 )}
            </div>

        </div>
      </DesktopWindow>
    </div>
  );
};

export default LiveTracking;