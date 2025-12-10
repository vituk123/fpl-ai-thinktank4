import React from 'react';
import { Box, Typography, Chip, CardContent } from '@mui/material';
import AnimatedCard from '../AnimatedCard';
import AnimatedBadge from '../AnimatedBadge';
import { Timeline, TimelineItem, TimelineContent, TimelineDot } from '@mui/lab';
import { formatGameweek, formatDate } from '../../utils/formatters';
import '../../styles/retro.css';

/**
 * Chip Activation Panel Component
 * Displays chip usage timeline
 */
const ChipActivationPanel = ({ chipData }) => {
  if (!chipData || !chipData.chips || chipData.chips.length === 0) {
    return (
      <AnimatedCard sx={{ backgroundColor: '#DADAD3' }}>
        <CardContent sx={{ backgroundColor: '#DADAD3' }}>
              <Typography sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>No data</Typography>
        </CardContent>
      </AnimatedCard>
    );
  }

  const chips = chipData.chips || [];
  const chipColors = {
    wildcard: '#50C1EC',
    freehit: '#FEE242',
    benchboost: '#1CB59F',
    triplecaptain: '#EB3E49',
  };

  const getChipLabel = (chipName) => {
    const labels = {
      wildcard: 'Wildcard',
      freehit: 'Free Hit',
      benchboost: 'Bench Boost',
      triplecaptain: 'Triple Captain',
    };
    return labels[chipName] || chipName;
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
          Chip Usage Timeline
        </Typography>

        <Timeline sx={{ mt: 2 }}>
          {chips.map((chip, idx) => (
            <TimelineItem key={idx}>
              <TimelineDot
                sx={{
                  bgcolor: chipColors[chip.name] || 'primary.main',
                  boxShadow: `0 0 10px ${chipColors[chip.name] || '#e2deda'}`,
                }}
              />
              <TimelineContent>
                <Box sx={{ mb: 1 }}>
                  <AnimatedBadge
                    label={getChipLabel(chip.name)}
                    size="small"
                    sx={{
                      bgcolor: chipColors[chip.name] || '#C1C1BF',
                      color: '#1D1D1B',
                      fontFamily: "'Roboto', sans-serif",
                      fontWeight: 'bold',
                      mb: 1,
                    }}
                  />
                </Box>
                <Typography 
                  variant="body2"
                  sx={{
                    fontFamily: "'Roboto', sans-serif",
                    color: '#1D1D1B',
                  }}
                >
                  {formatGameweek(chip.event || chip.gameweek)}
                </Typography>
                {chip.time && (
                  <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>
                    {formatDate(chip.time)}
                  </Typography>
                )}
              </TimelineContent>
            </TimelineItem>
          ))}
        </Timeline>

        {/* Summary */}
        <Box className="data-terminal" sx={{ p: 2, mt: 3 }}>
          <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 1 }}>
            Chips Used: {chips.length} / 4
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>
            Remaining: {4 - chips.length}
          </Typography>
        </Box>
      </CardContent>
    </AnimatedCard>
  );
};

export default ChipActivationPanel;
