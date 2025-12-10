import React, { useState, useEffect } from 'react';
import { Box, Typography, Chip, Avatar } from '@mui/material';
import { CardContent } from '@mui/material';
import AnimatedCard from '../AnimatedCard';
import { imagesApi } from '../../services/api';
import { formatPrice, formatPoints, formatPosition } from '../../utils/formatters';
import '../../styles/retro.css';
import '../../styles/components.css';

const PlayerCard = ({ 
  player, 
  imageUrl: propImageUrl = null, 
  onClick,
  isCaptain = false,
  isViceCaptain = false,
  showLiveStatus = true,
}) => {
  const [imageUrl, setImageUrl] = useState(propImageUrl);
  const [imageLoading, setImageLoading] = useState(true);

  useEffect(() => {
    const loadImage = async () => {
      if (propImageUrl) {
        setImageUrl(propImageUrl);
        return;
      }

      if (player?.id) {
        try {
          const response = await imagesApi.getPlayerImage(player.id);
          if (response?.data?.image_url) {
            setImageUrl(response.data.image_url);
          }
        } catch (error) {
          console.error('Failed to load player image:', error);
        }
      }
    };

    loadImage();
  }, [player?.id, propImageUrl]);

  if (!player) return null;

  const position = formatPosition(player.element_type || player.position);
  const points = player.points !== undefined ? player.points : player.total_points;
  const status = player.status || player.injury_status || 'Available';
  const minutes = player.minutes !== undefined ? player.minutes : null;

  return (
    <AnimatedCard
      className="motion-blur"
      onClick={onClick}
      sx={{ 
        cursor: onClick ? 'pointer' : 'default',
        height: '100%',
        position: 'relative',
        overflow: 'visible',
        backgroundColor: '#DADAD3',
      }}
    >
      {(isCaptain || isViceCaptain) && (
        <Chip
          label={isCaptain ? 'C' : 'VC'}
          size="small"
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 1,
            bgcolor: isCaptain ? 'primary.main' : 'secondary.main',
            color: 'background.default',
            fontWeight: 'bold',
            fontFamily: "'JetBrains Mono', monospace",
            }}
          />
        )}
      
      <CardContent sx={{ backgroundColor: '#DADAD3' }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          {imageUrl ? (
            <Avatar
              src={imageUrl}
              alt={player.name || player.web_name}
              sx={{
                width: 64,
                height: 64,
                border: '2px solid #1D1D1B',
              }}
              onError={() => setImageLoading(false)}
            />
          ) : (
            <Avatar
              sx={{
                width: 64,
                height: 64,
                bgcolor: '#C1C1BF',
                border: '2px solid #1D1D1B',
              }}
            >
              {player.name?.[0] || player.web_name?.[0] || '?'}
            </Avatar>
          )}
          
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography 
              variant="h6" 
              component="h4" 
              sx={{ 
                mb: 0.5,
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 600,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {player.name || player.web_name}
            </Typography>
            
            <Typography 
              variant="caption" 
              sx={{ color: 'rgba(29, 29, 27, 0.7)', display: 'block', mb: 0.5 }}
            >
              {position}
              {player.team && ` • ${player.team}`}
            </Typography>

            {showLiveStatus && (
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 1 }}>
                <Chip
                  label={status}
                  size="small"
                  sx={{
                    fontSize: '0.7rem',
                    height: 20,
                    fontFamily: "'Roboto', sans-serif",
                  }}
                  color={
                    status === 'Playing' || status === 'Available' 
                      ? 'success' 
                      : status === 'Doubtful' 
                      ? 'warning' 
                      : 'default'
                  }
                />
                {minutes !== null && (
                  <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>
                    {minutes}'
                  </Typography>
                )}
              </Box>
            )}
          </Box>

          <Box sx={{ textAlign: 'right' }}>
            <Typography 
              variant="h5" 
              className="retro-text"
                sx={{ 
                color: '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 'bold',
              }}
            >
              {formatPoints(points || 0)}
            </Typography>
            {player.now_cost && (
              <Typography variant="caption" sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>
                {formatPrice(player.now_cost)}
              </Typography>
            )}
          </Box>
        </Box>
      </CardContent>
    </AnimatedCard>
  );
};

export default PlayerCard;

