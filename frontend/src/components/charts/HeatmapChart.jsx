import React from 'react';
import { Box, Typography } from '@mui/material';

/**
 * Performance Heatmap Chart Component
 * Displays player performance across gameweeks as a heatmap
 */
const HeatmapChart = ({ data }) => {
  if (!data || !data.players || data.players.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">No data</Typography>
      </Box>
    );
  }

  // Transform data for heatmap visualization
  const heatmapData = [];
  const gameweeks = data.gameweeks || [];
  
  data.players.forEach((player) => {
    player.points_by_gw?.forEach((gwData) => {
      heatmapData.push({
        player: player.name || player.web_name,
        gameweek: `GW${gwData.gw}`,
        points: gwData.points || 0,
      });
    });
  });

  // Get unique players and gameweeks
  const players = [...new Set(heatmapData.map(d => d.player))];
  const gwLabels = [...new Set(heatmapData.map(d => d.gameweek))].sort();

  // Create matrix for heatmap
  const matrix = players.map(player => {
    const row = { player };
    gwLabels.forEach(gw => {
      const point = heatmapData.find(d => d.player === player && d.gameweek === gw);
      row[gw] = point ? point.points : 0;
    });
    return row;
  });

  // Color scale based on points
  const getColor = (value) => {
    if (value === 0) return '#1f1f1f';
    if (value < 3) return '#2d4a2d';
    if (value < 6) return '#4a7c4a';
    if (value < 9) return '#6ba86b';
    if (value < 12) return '#8dc88d';
    return '#b0e5b0';
  };

  return (
    <Box sx={{ width: '100%', p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Performance Heatmap
      </Typography>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: `auto repeat(${gwLabels.length}, 1fr)`,
          gap: 1,
          fontSize: '0.75rem',
          fontFamily: "'JetBrains Mono', monospace",
          overflowX: 'auto',
        }}
      >
        {/* Header */}
        <Box sx={{ p: 1 }}></Box>
        {gwLabels.map(gw => (
          <Box key={gw} sx={{ p: 1, textAlign: 'center', color: 'text.secondary', minWidth: '60px' }}>
            {gw}
          </Box>
        ))}
        
        {/* Rows */}
        {matrix.map((row, idx) => (
          <React.Fragment key={idx}>
            <Box sx={{ p: 1, color: 'text.primary', fontWeight: 500, minWidth: '120px' }}>
              {row.player}
            </Box>
            {gwLabels.map(gw => (
              <Box
                key={gw}
                sx={{
                  p: 1,
                  bgcolor: getColor(row[gw]),
                  border: '1px solid rgba(226, 222, 218, 0.1)',
                  textAlign: 'center',
                  color: row[gw] > 0 ? 'text.primary' : 'text.secondary',
                  cursor: 'pointer',
                  minWidth: '60px',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    borderColor: 'primary.main',
                    transform: 'scale(1.05)',
                    zIndex: 1,
                    boxShadow: '0 0 10px rgba(226, 222, 218, 0.3)',
                  },
                }}
                title={`${row.player} - ${gw}: ${row[gw]} points`}
              >
                {row[gw] > 0 ? row[gw] : '-'}
              </Box>
            ))}
          </React.Fragment>
        ))}
      </Box>
    </Box>
  );
};

export default HeatmapChart;

