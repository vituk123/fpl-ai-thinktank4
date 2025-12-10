import React from 'react';
import { Box, Typography, Chip, LinearProgress } from '@mui/material';
import { Psychology, TrendingUp, CheckCircle } from '@mui/icons-material';
import AnimatedCard from '../AnimatedCard';
import { formatPoints } from '../../utils/formatters';
import '../../styles/components.css';
import '../../styles/retro.css';

const RecommendationCard = ({ recommendation, onClick }) => {
  if (!recommendation) return null;

  const mlInsights = recommendation.ml_insights || {};
  const usingML = mlInsights.using_ml || false;
  const avgConfidence = mlInsights.avg_confidence_in || 0;

  return (
    <AnimatedCard 
      onClick={onClick}
      sx={{ 
        height: '100%',
        cursor: onClick ? 'pointer' : 'default',
        backgroundColor: '#DADAD3',
        border: '2px solid #1D1D1B',
      }}
    >
      <Box sx={{ p: 2, backgroundColor: '#DADAD3' }}>
        {/* Header with ML Badge */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography 
              variant="h6" 
              sx={{ 
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 600,
                color: '#1D1D1B',
                mb: 0.5,
              }}
            >
              {recommendation.strategy || 'Transfer Recommendation'}
            </Typography>
            {recommendation.description && (
              <Typography 
                variant="body2" 
                sx={{ 
                  fontSize: '0.875rem', 
                  color: 'rgba(29, 29, 27, 0.7)',
                  fontFamily: "'Roboto', sans-serif",
                }}
              >
                {recommendation.description}
              </Typography>
            )}
          </Box>
          {usingML && (
            <Chip
              icon={<Psychology sx={{ fontSize: '1rem !important' }} />}
              label="ML Enhanced"
              size="small"
              sx={{
                bgcolor: '#1D1D1B',
                color: '#DADAD3',
                fontFamily: "'Roboto', sans-serif",
                fontSize: '0.7rem',
                height: 24,
                borderRadius: 0,
                border: '1px solid #1D1D1B',
              }}
            />
          )}
        </Box>

        {/* ML Confidence Indicator */}
        {usingML && avgConfidence > 0 && (
          <Box sx={{ mb: 2, p: 1.5, bgcolor: '#C1C1BF', border: '1px solid #1D1D1B' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography 
                variant="caption" 
                sx={{ 
                  fontFamily: "'Roboto', sans-serif",
                  color: '#1D1D1B',
                  fontWeight: 500,
                }}
              >
                ML Confidence
              </Typography>
              <Typography 
                variant="caption" 
                sx={{ 
                  fontFamily: "'Roboto', sans-serif",
                  color: '#1D1D1B',
                  fontWeight: 'bold',
                }}
              >
                {(avgConfidence * 100).toFixed(0)}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={avgConfidence * 100}
              sx={{
                height: 8,
                borderRadius: 0,
                backgroundColor: '#DADAD3',
                '& .MuiLinearProgress-bar': {
                  backgroundColor: avgConfidence > 0.7 ? '#1CB59F' : avgConfidence > 0.5 ? '#FEE242' : '#EB3E49',
                },
              }}
            />
            {mlInsights.model_version && (
              <Typography 
                variant="caption" 
                sx={{ 
                  mt: 0.5,
                  display: 'block',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.65rem',
                  color: 'rgba(29, 29, 27, 0.6)',
                }}
              >
                Model: {mlInsights.model_version}
              </Typography>
            )}
          </Box>
        )}

        {/* Players OUT */}
        {recommendation.players_out && recommendation.players_out.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography 
              variant="caption" 
              sx={{ 
                fontSize: '0.75rem', 
                color: 'rgba(29, 29, 27, 0.7)',
                fontFamily: "'Roboto', sans-serif",
                display: 'block',
                mb: 0.5,
              }}
            >
              OUT:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {recommendation.players_out.map((p, idx) => {
                const confidence = usingML ? (mlInsights.players_out_confidence?.[p.id] || 0) : null;
                return (
                  <Chip
                    key={idx}
                    label={p.web_name || p.name}
                    size="small"
                    sx={{
                      bgcolor: '#C1C1BF',
                      color: '#1D1D1B',
                      fontFamily: "'Roboto', sans-serif",
                      fontSize: '0.75rem',
                      borderRadius: 0,
                      border: '1px solid #1D1D1B',
                      opacity: confidence !== null && confidence < 0.5 ? 0.7 : 1,
                    }}
                  />
                );
              })}
            </Box>
          </Box>
        )}

        {/* Players IN */}
        {recommendation.players_in && recommendation.players_in.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography 
              variant="caption" 
              sx={{ 
                fontSize: '0.75rem', 
                color: 'rgba(29, 29, 27, 0.7)',
                fontFamily: "'Roboto', sans-serif",
                display: 'block',
                mb: 0.5,
              }}
            >
              IN:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {recommendation.players_in.map((p, idx) => {
                const confidence = usingML ? (mlInsights.players_in_confidence?.[p.id] || 0) : null;
                return (
                  <Chip
                    key={idx}
                    icon={confidence !== null && confidence > 0.7 ? <CheckCircle sx={{ fontSize: '0.9rem !important' }} /> : null}
                    label={p.web_name || p.name}
                    size="small"
                    sx={{
                      bgcolor: confidence !== null && confidence > 0.7 ? '#1CB59F' : '#C1C1BF',
                      color: confidence !== null && confidence > 0.7 ? '#DADAD3' : '#1D1D1B',
                      fontFamily: "'Roboto', sans-serif",
                      fontSize: '0.75rem',
                      fontWeight: confidence !== null && confidence > 0.7 ? 'bold' : 'normal',
                      borderRadius: 0,
                      border: '1px solid #1D1D1B',
                    }}
                  />
                );
              })}
            </Box>
          </Box>
        )}

        {/* Stats Footer */}
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between',
          mt: 2,
          pt: 2,
          borderTop: '2px solid #1D1D1B',
        }}>
          <Box>
            <Typography 
              variant="caption" 
              sx={{ 
                color: 'rgba(29, 29, 27, 0.7)',
                fontFamily: "'Roboto', sans-serif",
                display: 'block',
                mb: 0.5,
              }}
            >
              Net EV Gain:
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <TrendingUp sx={{ fontSize: '1rem', color: '#1CB59F' }} />
              <Typography 
                variant="h6" 
                sx={{ 
                  color: '#1D1D1B', 
                  fontWeight: 'bold',
                  fontFamily: "'Roboto', sans-serif",
                }}
              >
                {formatPoints(recommendation.net_ev_gain || 0)}
              </Typography>
            </Box>
          </Box>
          {recommendation.num_transfers !== undefined && (
            <Box sx={{ textAlign: 'right' }}>
              <Typography 
                variant="caption" 
                sx={{ 
                  color: 'rgba(29, 29, 27, 0.7)',
                  fontFamily: "'Roboto', sans-serif",
                  display: 'block',
                  mb: 0.5,
                }}
              >
                Transfers:
              </Typography>
              <Typography 
                variant="h6" 
                sx={{ 
                  fontFamily: "'Roboto', sans-serif",
                  color: '#1D1D1B',
                  fontWeight: 600,
                }}
              >
                {recommendation.num_transfers}
              </Typography>
            </Box>
          )}
        </Box>
      </Box>
    </AnimatedCard>
  );
};

export default RecommendationCard;

