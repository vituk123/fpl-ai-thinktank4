import React from 'react';
import { Box, Typography, Grid } from '@mui/material';
import { CardContent } from '@mui/material';
import AnimatedCard from '../AnimatedCard';
import { formatGameweek } from '../../utils/formatters';
import '../../styles/retro.css';

/**
 * Fixture Difficulty Heatmap Component
 * Visual representation of fixture difficulty
 */
const FixtureDifficultyHeatmap = ({ data }) => {
  if (!data || !data.fixtures || data.fixtures.length === 0) {
    return (
      <AnimatedCard sx={{ backgroundColor: '#DADAD3' }}>
        <CardContent sx={{ backgroundColor: '#DADAD3' }}>
          <Typography sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>No data</Typography>
        </CardContent>
      </AnimatedCard>
    );
  }

  const getDifficultyColor = (difficulty) => {
    // FPL difficulty: 1-5 (1 = easiest, 5 = hardest)
    const colors = {
      1: '#00ff00', // Green - Easy
      2: '#80ff80', // Light Green
      3: '#ffff00', // Yellow - Medium
      4: '#ff8000', // Orange - Hard
      5: '#ff0000', // Red - Very Hard
    };
    return colors[difficulty] || '#666666';
  };

  const getDifficultyLabel = (difficulty) => {
    const labels = {
      1: 'EASY',
      2: 'MED',
      3: 'MED',
      4: 'HARD',
      5: 'VHARD',
    };
    return labels[difficulty] || 'N/A';
  };

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
          Fixture Difficulty Heatmap
        </Typography>

        <Grid container spacing={1} sx={{ mt: 2 }}>
          {data.fixtures.map((fixture, idx) => (
            <Grid item xs={6} sm={4} md={3} key={idx}>
              <Box
                className="data-terminal"
                sx={{
                  p: 1.5,
                  textAlign: 'center',
                  bgcolor: getDifficultyColor(fixture.difficulty),
                  color: '#000',
                  border: '1px solid rgba(0,0,0,0.2)',
                  '&:hover': {
                    transform: 'scale(1.05)',
                    zIndex: 1,
                  },
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontWeight: 'bold',
                    mb: 0.5,
                  }}
                >
                  {formatGameweek(fixture.gameweek)}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '0.7rem',
                  }}
                >
                  {fixture.opponent || 'TBD'}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '0.65rem',
                    mt: 0.5,
                  }}
                >
                  {getDifficultyLabel(fixture.difficulty)}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </AnimatedCard>
  );
};

export default FixtureDifficultyHeatmap;

