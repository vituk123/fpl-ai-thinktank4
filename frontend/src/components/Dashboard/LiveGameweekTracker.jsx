import React, { useEffect } from 'react';
import { Box, Typography, Grid, CardContent, Chip, IconButton, Divider, Alert } from '@mui/material';
import AnimatedCard from '../AnimatedCard';
import MacSpinner from '../MacSpinner';
import AnimatedNumber from '../AnimatedNumber';
import AnimatedBadge from '../AnimatedBadge';
import { Refresh, Pause, PlayArrow, TrendingUp, TrendingDown, Remove } from '@mui/icons-material';
import { useLiveTracking } from '../../hooks/useLiveTracking';
import { useAppContext } from '../../context/AppContext';
import PlayerTable from './PlayerTable';
import { formatTime } from '../../utils/formatters';
import '../../styles/retro.css';

const LiveGameweekTracker = ({ gameweek: propGameweek = null }) => {
  const { entryId, currentGameweek } = useAppContext();
  const gameweek = propGameweek || currentGameweek;
  
  // Debug logging
  React.useEffect(() => {
    console.log('LiveGameweekTracker - entryId:', entryId, 'gameweek:', gameweek);
  }, [entryId, gameweek]);
  
  const {
    data,
    loading,
    error,
    lastUpdate,
    isPolling,
    startPolling,
    stopPolling,
    refetch,
  } = useLiveTracking(gameweek, entryId, {
    enabled: !!gameweek && !!entryId,
    pollInterval: 30000,
    autoStart: true,
  });

  // Debug logging for hook state
  React.useEffect(() => {
    console.log('LiveGameweekTracker - loading:', loading, 'hasData:', !!data, 'error:', error);
    if (data) {
      console.log('LiveGameweekTracker - data keys:', Object.keys(data));
      console.log('LiveGameweekTracker - live_points:', data.live_points);
      console.log('LiveGameweekTracker - player_breakdown length:', data.player_breakdown?.length);
    }
  }, [loading, data, error]);

  if (!entryId || !gameweek) {
    return (
      <AnimatedCard sx={{ backgroundColor: '#DADAD3' }}>
        <CardContent sx={{ backgroundColor: '#DADAD3' }}>
              <Typography sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>
                Entry ID: {entryId || 'Not set'} | Gameweek: {gameweek || 'Not set'}
              </Typography>
        </CardContent>
      </AnimatedCard>
    );
  }

  // Handle API response structure - data comes from StandardResponse format
  // The hook already extracts response.data, so data should be the actual data object
  const livePoints = data?.live_points || {};
  const playerBreakdown = data?.player_breakdown || [];
  const teamSummary = data?.team_summary || {};
  const autoSubstitutions = data?.auto_substitutions || [];
  const bonusPredictions = data?.bonus_predictions || {};
  const rankProjection = data?.rank_projection || {};
  const alerts = data?.alerts || [];

  return (
    <AnimatedCard className="retro-border" sx={{ backgroundColor: '#DADAD3' }}>
      <CardContent sx={{ backgroundColor: '#DADAD3' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography 
              variant="h3" 
              component="h2"
              sx={{
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 500,
                color: '#1D1D1B',
              }}
            >
              Live Gameweek {gameweek}
            </Typography>
            {lastUpdate && (
              <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', mt: 0.5, display: 'block' }}>
                Last updated: {formatTime(lastUpdate)}
              </Typography>
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <IconButton
              onClick={isPolling ? stopPolling : startPolling}
              size="small"
              sx={{ color: 'text.primary' }}
            >
              {isPolling ? <Pause /> : <PlayArrow />}
            </IconButton>
            <IconButton
              onClick={refetch}
              size="small"
              disabled={loading}
              sx={{ color: 'text.primary' }}
            >
              <Refresh />
            </IconButton>
            <AnimatedBadge
              label={isPolling ? 'Live' : 'Paused'}
              size="small"
              sx={{
                bgcolor: isPolling ? '#1D1D1B' : '#C1C1BF',
                color: isPolling ? '#DADAD3' : '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontSize: '0.75rem',
              }}
            />
          </Box>
        </Box>

        {loading && !data && (
          <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', py: 4 }}>
            <MacSpinner size={40} />
            <Typography variant="body2" sx={{ mt: 2, color: 'rgba(29, 29, 27, 0.7)' }}>
              Loading live data for Entry ID: {entryId}, Gameweek: {gameweek}
            </Typography>
          </Box>
        )}

        {error && (
          <Box sx={{ p: 2, bgcolor: '#EB3E49', borderRadius: 0, mb: 2, border: '2px solid #1D1D1B' }}>
            <Typography variant="body2" sx={{ color: '#1D1D1B', fontWeight: 'bold', mb: 1 }}>
              Error Loading Live Data
            </Typography>
            <Typography variant="body2" sx={{ color: '#1D1D1B' }}>
              {typeof error === 'string' ? error : error?.message || String(error)}
            </Typography>
            <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'rgba(29, 29, 27, 0.7)' }}>
              Entry ID: {entryId} | Gameweek: {gameweek}
            </Typography>
          </Box>
        )}

        {!loading && !error && !data && (
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>
              No data available. Entry ID: {entryId}, Gameweek: {gameweek}
            </Typography>
          </Box>
        )}

        {data && (
          <>
            {/* Team Summary Section */}
            {teamSummary && Object.keys(teamSummary).length > 0 && (
              <Box sx={{ mb: 4 }}>
                <Typography 
                  variant="h4" 
                  component="h3" 
                  gutterBottom 
                  sx={{ 
                    mb: 3,
                    fontFamily: "'Roboto', sans-serif",
                    fontWeight: 500,
                    color: '#1D1D1B',
                  }}
                >
                  Team Summary
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Box className="data-terminal" sx={{ p: 2, mb: 2 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 0.5 }}>
                        Manager
                      </Typography>
                      <Typography variant="h6" sx={{ fontFamily: "'Roboto', sans-serif", fontWeight: 600, color: '#1D1D1B' }}>
                        {teamSummary.manager_name || 'Unknown'}
                      </Typography>
                      {teamSummary.seasons_played > 0 && (
                        <Typography variant="body2" sx={{ color: 'rgba(29, 29, 27, 0.7)', mt: 0.5 }}>
                          {teamSummary.seasons_played} Season{teamSummary.seasons_played !== 1 ? 's' : ''}
                          {teamSummary.avg_rank > 0 && ` (Avg Rank: ${teamSummary.avg_rank.toLocaleString()})`}
                        </Typography>
                      )}
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Box className="data-terminal" sx={{ p: 2, mb: 2 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 0.5 }}>
                        Total Points
                      </Typography>
                      <Typography variant="h6" sx={{ fontFamily: "'Roboto', sans-serif", fontWeight: 600, color: '#1D1D1B' }}>
                        {teamSummary.total_points?.toLocaleString() || 0}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Box className="data-terminal" sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 1 }}>
                        GW Points
                      </Typography>
                      <Typography variant="h4" sx={{ fontFamily: "'Roboto', sans-serif", fontWeight: 700, color: '#1D1D1B' }}>
                        <AnimatedNumber value={livePoints.total || livePoints.total_points || teamSummary.gw_points || 0} duration={800} />
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Box className="data-terminal" sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 1 }}>
                        Starting XI
                      </Typography>
                      <Typography variant="h4" sx={{ fontFamily: "'Roboto', sans-serif", fontWeight: 700, color: '#1D1D1B' }}>
                        <AnimatedNumber value={livePoints.starting_xi || 0} duration={800} />
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Box className="data-terminal" sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 1 }}>
                        Bench
                      </Typography>
                      <Typography variant="h4" sx={{ fontFamily: "'Roboto', sans-serif", fontWeight: 700, color: '#1D1D1B' }}>
                        <AnimatedNumber value={livePoints.bench || 0} duration={800} />
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Box className="data-terminal" sx={{ textAlign: 'center', p: 2 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 1 }}>
                        Transfers
                      </Typography>
                      <Typography variant="h4" sx={{ fontFamily: "'Roboto', sans-serif", fontWeight: 700, color: '#1D1D1B' }}>
                        {teamSummary.gw_transfers || 0}
                      </Typography>
                      {teamSummary.free_transfers && (
                        <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>
                          (Saved: {teamSummary.free_transfers})
                        </Typography>
                      )}
                    </Box>
                  </Grid>
                  {teamSummary.live_rank > 0 && (
                    <Grid item xs={12} sm={6} md={4}>
                      <Box className="data-terminal" sx={{ p: 2 }}>
                        <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 0.5 }}>
                          Live Rank
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="h6" sx={{ fontFamily: "'Roboto', sans-serif", fontWeight: 600, color: '#1D1D1B' }}>
                            {teamSummary.live_rank.toLocaleString()}
                          </Typography>
                          {teamSummary.gw_rank > 0 && teamSummary.gw_rank !== teamSummary.live_rank && (
                            <>
                              {teamSummary.gw_rank < teamSummary.live_rank ? (
                                <TrendingUp sx={{ color: '#1CB59F', fontSize: 20 }} />
                              ) : (
                                <TrendingDown sx={{ color: '#EB3E49', fontSize: 20 }} />
                              )}
                              <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>
                                (GW: {teamSummary.gw_rank.toLocaleString()})
                              </Typography>
                            </>
                          )}
                        </Box>
                      </Box>
                    </Grid>
                  )}
                  <Grid item xs={12} sm={6} md={4}>
                    <Box className="data-terminal" sx={{ p: 2 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 0.5 }}>
                        Chip
                      </Typography>
                      <Typography variant="body1" sx={{ fontFamily: "'Roboto', sans-serif", fontWeight: 500, color: '#1D1D1B' }}>
                        {teamSummary.current_chip || 'None'}
                        {teamSummary.chips_used && ` (Used: ${teamSummary.chips_used})`}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Box className="data-terminal" sx={{ p: 2 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 0.5 }}>
                        Team Value
                      </Typography>
                      <Typography variant="body1" sx={{ fontFamily: "'Roboto', sans-serif", fontWeight: 500, color: '#1D1D1B' }}>
                        £{teamSummary.total_value?.toFixed(1) || '0.0'}m
                        {teamSummary.bank > 0 && ` (£${teamSummary.squad_value?.toFixed(1) || '0.0'}m + £${teamSummary.bank?.toFixed(1) || '0.0'}m bank)`}
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Box>
            )}

            <Divider sx={{ my: 4, borderColor: 'rgba(29, 29, 27, 0.2)' }} />

            {/* Player Breakdown Table */}
            {playerBreakdown.length > 0 && (
              <Box sx={{ mb: 4 }}>
                <Typography 
                  variant="h4" 
                  component="h3" 
                  gutterBottom 
                  sx={{ 
                    mb: 2,
                    fontFamily: "'Roboto', sans-serif",
                    fontWeight: 500,
                    color: '#1D1D1B',
                  }}
                >
                  Player Breakdown
                </Typography>
                <PlayerTable players={playerBreakdown} />
              </Box>
            )}

            {/* Auto-Substitutions */}
            {autoSubstitutions.length > 0 && (
              <Box sx={{ mb: 4 }}>
                <Typography 
                  variant="h5" 
                  component="h3" 
                  gutterBottom 
                  sx={{ 
                    mb: 2,
                    fontFamily: "'Roboto', sans-serif",
                    fontWeight: 500,
                    color: '#1D1D1B',
                  }}
                >
                  Auto-Substitutions ({autoSubstitutions.length})
                </Typography>
                {autoSubstitutions.map((sub, idx) => (
                  <Box key={idx} className="data-terminal" sx={{ p: 2, mb: 1 }}>
                    <Typography variant="body2" sx={{ fontFamily: "'Roboto', sans-serif", color: '#1D1D1B' }}>
                      <strong>{sub.out?.name || 'Unknown'}</strong> (0 min) → <strong>{sub.in?.name || 'Unknown'}</strong> (+{sub.points_gain || 0} pts)
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}

            {/* Bonus Predictions */}
            {Object.keys(bonusPredictions).length > 0 && (
              <Box sx={{ mb: 4 }}>
                <Typography 
                  variant="h5" 
                  component="h3" 
                  gutterBottom 
                  sx={{ 
                    mb: 2,
                    fontFamily: "'Roboto', sans-serif",
                    fontWeight: 500,
                    color: '#1D1D1B',
                  }}
                >
                  Bonus Points Prediction (Top 3)
                </Typography>
                {Object.entries(bonusPredictions)
                  .slice(0, 3)
                  .map(([playerId, data]) => (
                    <Box key={playerId} className="data-terminal" sx={{ p: 2, mb: 1 }}>
                      <Typography variant="body2" sx={{ fontFamily: "'Roboto', sans-serif", color: '#1D1D1B' }}>
                        {data.rank}. <strong>{data.name}</strong>: {data.current_bps} BPS → {data.predicted_bonus} bonus
                      </Typography>
                    </Box>
                  ))}
              </Box>
            )}

            {/* Rank Projection */}
            {rankProjection && Object.keys(rankProjection).length > 0 && (
              <Box sx={{ mb: 4 }}>
                <Typography 
                  variant="h5" 
                  component="h3" 
                  gutterBottom 
                  sx={{ 
                    mb: 2,
                    fontFamily: "'Roboto', sans-serif",
                    fontWeight: 500,
                    color: '#1D1D1B',
                  }}
                >
                  Rank Projection
                </Typography>
                <Box className="data-terminal" sx={{ p: 2 }}>
                  <Typography variant="body1" sx={{ fontFamily: "'Roboto', sans-serif", color: '#1D1D1B' }}>
                    {rankProjection.current_rank?.toLocaleString() || 'N/A'}
                    {rankProjection.rank_change !== undefined && rankProjection.rank_change !== 0 && (
                      <>
                        {' '}
                        {rankProjection.rank_change < 0 ? (
                          <TrendingUp sx={{ color: '#1CB59F', fontSize: 18, verticalAlign: 'middle', ml: 0.5 }} />
                        ) : (
                          <TrendingDown sx={{ color: '#EB3E49', fontSize: 18, verticalAlign: 'middle', ml: 0.5 }} />
                        )}
                        {' '}
                        {rankProjection.projected_rank?.toLocaleString() || 'N/A'}
                      </>
                    )}
                    {rankProjection.is_mini_league && rankProjection.league_name && (
                      <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: 'rgba(29, 29, 27, 0.7)' }}>
                        Mini-League: {rankProjection.league_name}
                      </Typography>
                    )}
                  </Typography>
                </Box>
              </Box>
            )}

            {/* Alerts */}
            {alerts.length > 0 && (
              <Box sx={{ mb: 4 }}>
                <Typography 
                  variant="h5" 
                  component="h3" 
                  gutterBottom 
                  sx={{ 
                    mb: 2,
                    fontFamily: "'Roboto', sans-serif",
                    fontWeight: 500,
                    color: '#1D1D1B',
                  }}
                >
                  Alerts ({alerts.length})
                </Typography>
                {alerts.map((alert, idx) => (
                  <Alert 
                    key={idx}
                    severity={alert.type === 'goal' || alert.type === 'assist' ? 'success' : alert.type === 'red_card' || alert.type === 'clean_sheet_lost' ? 'error' : 'warning'}
                    sx={{ 
                      mb: 1,
                      backgroundColor: '#DADAD3',
                      border: '2px solid #1D1D1B',
                      borderRadius: 0,
                      '& .MuiAlert-icon': {
                        color: '#1D1D1B',
                      },
                    }}
                  >
                    <Typography variant="body2" sx={{ fontFamily: "'Roboto', sans-serif", color: '#1D1D1B' }}>
                      {alert.message || `${alert.type}: ${alert.player || 'Unknown'}`}
                    </Typography>
                  </Alert>
                ))}
              </Box>
            )}
          </>
        )}
        </CardContent>
      </AnimatedCard>
    );
  };

export default LiveGameweekTracker;

