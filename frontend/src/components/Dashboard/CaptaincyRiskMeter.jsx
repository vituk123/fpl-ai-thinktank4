import React from 'react';
import { Box, Typography } from '@mui/material';
import { CardContent } from '@mui/material';
import AnimatedCard from '../AnimatedCard';
import MacProgress from '../MacProgress';
import AnimatedNumber from '../AnimatedNumber';
import '../../styles/retro.css';

/**
 * Captaincy Risk Meter Component
 * Visual indicator of captaincy decision risk
 */
const CaptaincyRiskMeter = ({ riskLevel, playerName, expectedPoints }) => {
  // Risk level: 0-100 (0 = low risk, 100 = high risk)
  const riskPercentage = Math.min(100, Math.max(0, riskLevel || 0));
  
  const getRiskColor = (level) => {
    if (level < 30) return '#00ff00'; // Green - Low risk
    if (level < 60) return '#ffaa00'; // Orange - Medium risk
    return '#ff0000'; // Red - High risk
  };

  const getRiskLabel = (level) => {
    if (level < 30) return 'LOW RISK';
    if (level < 60) return 'MEDIUM RISK';
    return 'HIGH RISK';
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
          Captaincy Risk Meter
        </Typography>
        
        {playerName && (
          <Typography variant="body2" sx={{ mb: 2, color: 'rgba(29, 29, 27, 0.7)' }}>
            {playerName}
          </Typography>
        )}

        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="caption" className="retro-text">
              {getRiskLabel(riskPercentage)}
            </Typography>
            <Typography 
              variant="caption" 
              sx={{ 
                color: getRiskColor(riskPercentage),
                fontFamily: "'JetBrains Mono', monospace",
                fontWeight: 'bold',
              }}
            >
              {riskPercentage}%
            </Typography>
          </Box>
          <MacProgress
            value={riskPercentage}
            fillSx={{
              backgroundColor: getRiskColor(riskPercentage),
            }}
          />
        </Box>

        {expectedPoints !== undefined && (
          <Box className="data-terminal" sx={{ p: 1.5, mt: 2 }}>
            <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 0.5 }}>
              Expected Points
            </Typography>
            <Typography 
              variant="h5" 
              sx={{ 
                color: '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 700,
              }}
            >
              <AnimatedNumber value={expectedPoints} duration={600} decimals={1} />
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default CaptaincyRiskMeter;

