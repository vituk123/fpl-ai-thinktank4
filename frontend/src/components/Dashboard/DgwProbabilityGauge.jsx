import React from 'react';
import { Box, Typography, CircularProgress } from '@mui/material';
import { CardContent } from '@mui/material';
import AnimatedCard from '../AnimatedCard';
import { formatGameweek } from '../../utils/formatters';
import '../../styles/retro.css';

/**
 * Double Gameweek Probability Gauge Component
 * Shows probability of DGW for upcoming gameweeks
 */
const DgwProbabilityGauge = ({ data }) => {
  if (!data || !data.probabilities || data.probabilities.length === 0) {
    return (
      <AnimatedCard sx={{ backgroundColor: '#DADAD3' }}>
        <CardContent sx={{ backgroundColor: '#DADAD3' }}>
          <Typography sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>No data</Typography>
        </CardContent>
      </AnimatedCard>
    );
  }

  const probabilities = data.probabilities || [];

  const getProbabilityColor = (prob) => {
    if (prob >= 70) return '#00ff00'; // Green - High
    if (prob >= 40) return '#ffaa00'; // Orange - Medium
    return '#ff0000'; // Red - Low
  };

  return (
    <Card className="glass-card" sx={{ backgroundColor: '#DADAD3' }}>
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
          Double Gameweek Probability
        </Typography>

        <Box sx={{ mt: 3 }}>
          {probabilities.map((item, idx) => (
            <Box key={idx} sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography 
                  variant="body2"
                  sx={{
                    fontFamily: "'Roboto', sans-serif",
                    color: '#1D1D1B',
                  }}
                >
                  {formatGameweek(item.gameweek)}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    color: getProbabilityColor(item.probability),
                    fontFamily: "'Roboto', sans-serif",
                    fontWeight: 'bold',
                  }}
                >
                  {item.probability.toFixed(0)}%
                </Typography>
              </Box>
              <Box sx={{ position: 'relative', display: 'inline-flex', width: '100%' }}>
                <CircularProgress
                  variant="determinate"
                  value={item.probability}
                  size={60}
                  thickness={6}
                  sx={{
                    color: getProbabilityColor(item.probability),
                    '& .MuiCircularProgress-circle': {
                      strokeLinecap: 'round',
                    },
                  }}
                />
                <Box
                  sx={{
                    top: 0,
                    left: 0,
                    bottom: 0,
                    right: 0,
                    position: 'absolute',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Typography
                    variant="caption"
                    component="div"
                    sx={{
                      color: getProbabilityColor(item.probability),
                      fontFamily: "'Roboto', sans-serif",
                      fontWeight: 'bold',
                    }}
                  >
                    {item.probability.toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
              {item.teams && item.teams.length > 0 && (
                <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)' }} sx={{ mt: 0.5, display: 'block' }}>
                  Potential teams: {item.teams.join(', ')}
                </Typography>
              )}
            </Box>
          ))}
        </Box>
      </CardContent>
    </AnimatedCard>
  );
};

export default DgwProbabilityGauge;

