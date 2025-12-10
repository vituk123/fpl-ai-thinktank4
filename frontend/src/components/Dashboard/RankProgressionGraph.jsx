import React from 'react';
import { Box, Typography } from '@mui/material';
import { CardContent } from '@mui/material';
import AnimatedCard from '../AnimatedCard';
import LineChart from '../charts/LineChart';
import { formatGameweek } from '../../utils/formatters';
import '../../styles/retro.css';

/**
 * Rank Progression Graph Component
 * Shows overall rank over time
 */
const RankProgressionGraph = ({ data }) => {
  console.log('RankProgressionGraph received data:', data);
  console.log('RankProgressionGraph data type:', typeof data);
  console.log('RankProgressionGraph data keys:', data ? Object.keys(data) : 'null');
  
  // Handle API response format: {gameweeks: [...], overall_rank: [...]}
  // or legacy format: {history: [{event, overall_rank, ...}]}
  let history = [];
  
  if (data?.history && Array.isArray(data.history) && data.history.length > 0) {
    // Legacy format with history array
    console.log('Using legacy history format, length:', data.history.length);
    history = data.history;
  } else if (data?.gameweeks && data?.overall_rank && 
             Array.isArray(data.gameweeks) && Array.isArray(data.overall_rank) &&
             data.gameweeks.length === data.overall_rank.length && data.gameweeks.length > 0) {
    // New format with parallel arrays - convert to history format
    console.log('Using new parallel arrays format, converting to history. Length:', data.gameweeks.length);
    history = data.gameweeks.map((gw, idx) => ({
      event: gw,
      gameweek: gw,
      overall_rank: data.overall_rank[idx] || 0,
      rank: data.overall_rank[idx] || 0,
    }));
  } else {
    console.warn('RankProgressionGraph: No valid data format found.');
    console.warn('Data:', data);
    console.warn('Has gameweeks?', !!data?.gameweeks, 'Type:', Array.isArray(data?.gameweeks) ? 'array' : typeof data?.gameweeks);
    console.warn('Has overall_rank?', !!data?.overall_rank, 'Type:', Array.isArray(data?.overall_rank) ? 'array' : typeof data?.overall_rank);
    console.warn('Has history?', !!data?.history, 'Type:', Array.isArray(data?.history) ? 'array' : typeof data?.history);
  }

  if (history.length === 0) {
    return (
      <AnimatedCard sx={{ backgroundColor: '#DADAD3' }}>
        <CardContent sx={{ backgroundColor: '#DADAD3' }}>
          <Typography sx={{ color: 'rgba(29, 29, 27, 0.7)', mb: 2 }}>
            No data available
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.5)', display: 'block' }}>
            Debug: data = {data ? JSON.stringify(data).substring(0, 200) : 'null'}
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.5)', display: 'block' }}>
            Has gameweeks: {data?.gameweeks ? 'yes' : 'no'}, Has overall_rank: {data?.overall_rank ? 'yes' : 'no'}
          </Typography>
        </CardContent>
      </AnimatedCard>
    );
  }

  // Transform data for chart
  const chartData = history.map((entry) => ({
    x: formatGameweek(entry.event || entry.gameweek),
    y: entry.overall_rank || entry.rank || 0,
    points: entry.total_points || 0,
  }));

  // Reverse so most recent is on right
  chartData.reverse();

  return (
    <AnimatedCard sx={{ backgroundColor: '#DADAD3' }}>
      <CardContent sx={{ backgroundColor: '#DADAD3' }}>
        <Typography 
          variant="h6" 
          gutterBottom
          sx={{
            fontFamily: "'Roboto', sans-serif",
            fontWeight: 500,
            color: '#1D1D1B',
          }}
        >
          Rank Progression
        </Typography>
        
        <Box sx={{ mt: 3 }}>
          <LineChart
            data={chartData}
            xKey="x"
            yKey="y"
            title="Overall Rank Over Time"
            color="#50C1EC"
          />
        </Box>

        {/* Current Rank Display */}
        {(data.current_rank || (history.length > 0 && history[history.length - 1]?.overall_rank)) && (
          <Box 
            className="data-terminal" 
            sx={{ 
              p: 2, 
              mt: 3,
              backgroundColor: '#C1C1BF',
              border: '2px solid #1D1D1B',
            }}
          >
            <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 1 }}>
              Current Overall Rank
            </Typography>
            <Typography 
              variant="h4" 
              sx={{ 
                color: '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 700,
              }}
            >
              #{(data.current_rank || history[history.length - 1]?.overall_rank || 0).toLocaleString()}
            </Typography>
          </Box>
        )}
      </CardContent>
    </AnimatedCard>
  );
};

export default RankProgressionGraph;

