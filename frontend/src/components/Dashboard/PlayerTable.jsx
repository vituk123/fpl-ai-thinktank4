import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Box,
  Typography,
  Avatar,
  LinearProgress,
  Chip,
} from '@mui/material';
import { imagesApi } from '../../services/api';
import '../../styles/retro.css';

const PlayerTable = ({ players = [] }) => {
  const [imageUrls, setImageUrls] = React.useState({});

  React.useEffect(() => {
    const loadImages = async () => {
      const imageMap = {};
      for (const player of players) {
        if (player.id && !imageUrls[player.id]) {
          try {
            const response = await imagesApi.getPlayerImage(player.id);
            if (response?.data?.image_url) {
              imageMap[player.id] = response.data.image_url;
            } else if (player.photo) {
              imageMap[player.id] = player.photo;
            }
          } catch (error) {
            // Fallback to photo URL if available
            if (player.photo) {
              imageMap[player.id] = player.photo;
            }
          }
        } else if (player.photo) {
          imageMap[player.id] = player.photo;
        }
      }
      setImageUrls(prev => ({ ...prev, ...imageMap }));
    };

    if (players.length > 0) {
      loadImages();
    }
  }, [players]);

  if (players.length === 0) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body2" sx={{ color: 'rgba(29, 29, 27, 0.7)' }}>
          No players available
        </Typography>
      </Box>
    );
  }

  const getStatusColor = (status) => {
    if (status?.includes('Done')) return '#1CB59F'; // Green
    if (status?.includes('Did not play') || status?.includes('!')) return '#EB3E49'; // Red
    if (status?.includes('Playing')) return '#FFA500'; // Orange/Yellow
    return 'rgba(29, 29, 27, 0.7)'; // Default gray
  };

  return (
    <TableContainer
      sx={{
        backgroundColor: '#DADAD3',
        border: '2px solid #1D1D1B',
        borderRadius: 0,
      }}
    >
      <Table sx={{ minWidth: 650 }}>
        <TableHead>
          <TableRow sx={{ backgroundColor: '#C1C1BF' }}>
            <TableCell
              sx={{
                borderBottom: '2px solid #1D1D1B',
                color: '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 600,
                fontSize: '0.875rem',
              }}
            >
              Player
            </TableCell>
            <TableCell
              sx={{
                borderBottom: '2px solid #1D1D1B',
                color: '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 600,
                fontSize: '0.875rem',
              }}
            >
              Opp
            </TableCell>
            <TableCell
              sx={{
                borderBottom: '2px solid #1D1D1B',
                color: '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 600,
                fontSize: '0.875rem',
              }}
            >
              Status
            </TableCell>
            <TableCell
              align="center"
              sx={{
                borderBottom: '2px solid #1D1D1B',
                color: '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 600,
                fontSize: '0.875rem',
              }}
            >
              Pts
            </TableCell>
            <TableCell
              sx={{
                borderBottom: '2px solid #1D1D1B',
                color: '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 600,
                fontSize: '0.875rem',
                minWidth: 120,
              }}
            >
              Imp
            </TableCell>
            <TableCell
              align="center"
              sx={{
                borderBottom: '2px solid #1D1D1B',
                color: '#1D1D1B',
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 600,
                fontSize: '0.875rem',
              }}
            >
              Min
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {players.map((player, idx) => {
            const imageUrl = imageUrls[player.id] || player.photo;
            const ownership = parseFloat(player.ownership || 0);
            const statusColor = getStatusColor(player.status);
            const isCaptain = player.is_captain || player.isCaptain;
            const isVice = player.is_vice || player.is_vice_captain || player.isViceCaptain;

            return (
              <TableRow
                key={player.id || idx}
                sx={{
                  '&:nth-of-type(odd)': {
                    backgroundColor: '#DADAD3',
                  },
                  '&:nth-of-type(even)': {
                    backgroundColor: '#C1C1BF',
                  },
                  '&:hover': {
                    backgroundColor: '#A0A09E',
                  },
                }}
              >
                <TableCell
                  sx={{
                    borderBottom: '1px solid rgba(29, 29, 27, 0.2)',
                    color: '#1D1D1B',
                    fontFamily: "'Roboto', sans-serif",
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Avatar
                      src={imageUrl}
                      alt={player.name}
                      sx={{
                        width: 40,
                        height: 40,
                        border: '2px solid #1D1D1B',
                        bgcolor: '#C1C1BF',
                      }}
                    >
                      {player.name?.[0] || '?'}
                    </Avatar>
                    <Box>
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: "'Roboto', sans-serif",
                          fontWeight: 500,
                          color: '#1D1D1B',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.5,
                        }}
                      >
                        {player.name || 'Unknown'}
                        {isCaptain && (
                          <Chip
                            label="C"
                            size="small"
                            sx={{
                              height: 18,
                              minWidth: 18,
                              fontSize: '0.7rem',
                              fontWeight: 'bold',
                              bgcolor: '#1D1D1B',
                              color: '#DADAD3',
                              fontFamily: "'JetBrains Mono', monospace",
                            }}
                          />
                        )}
                        {isVice && !isCaptain && (
                          <Chip
                            label="V"
                            size="small"
                            sx={{
                              height: 18,
                              minWidth: 18,
                              fontSize: '0.7rem',
                              fontWeight: 'bold',
                              bgcolor: '#C1C1BF',
                              color: '#1D1D1B',
                              border: '1px solid #1D1D1B',
                              fontFamily: "'JetBrains Mono', monospace",
                            }}
                          />
                        )}
                      </Typography>
                    </Box>
                  </Box>
                </TableCell>
                <TableCell
                  sx={{
                    borderBottom: '1px solid rgba(29, 29, 27, 0.2)',
                    color: '#1D1D1B',
                    fontFamily: "'Roboto', sans-serif",
                    fontSize: '0.875rem',
                  }}
                >
                  {player.opponent || 'N/A'}
                </TableCell>
                <TableCell
                  sx={{
                    borderBottom: '1px solid rgba(29, 29, 27, 0.2)',
                    color: statusColor,
                    fontFamily: "'Roboto', sans-serif",
                    fontSize: '0.875rem',
                    fontWeight: 500,
                  }}
                >
                  {player.status || 'Unknown'}
                </TableCell>
                <TableCell
                  align="center"
                  sx={{
                    borderBottom: '1px solid rgba(29, 29, 27, 0.2)',
                    color: '#1D1D1B',
                    fontFamily: "'Roboto', sans-serif",
                    fontSize: '0.875rem',
                    fontWeight: 600,
                  }}
                >
                  {player.points || 0}
                </TableCell>
                <TableCell
                  sx={{
                    borderBottom: '1px solid rgba(29, 29, 27, 0.2)',
                    minWidth: 120,
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box sx={{ flex: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={Math.max(0, Math.min(100, ownership))}
                        sx={{
                          height: 8,
                          borderRadius: 0,
                          backgroundColor: '#C1C1BF',
                          '& .MuiLinearProgress-bar': {
                            backgroundColor: ownership > 50 ? '#1CB59F' : ownership > 20 ? '#FFA500' : '#EB3E49',
                          },
                        }}
                      />
                    </Box>
                    <Typography
                      variant="caption"
                      sx={{
                        color: '#1D1D1B',
                        fontFamily: "'Roboto', sans-serif",
                        fontSize: '0.75rem',
                        minWidth: 40,
                        textAlign: 'right',
                      }}
                    >
                      {ownership.toFixed(0)}%
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell
                  align="center"
                  sx={{
                    borderBottom: '1px solid rgba(29, 29, 27, 0.2)',
                    color: '#1D1D1B',
                    fontFamily: "'Roboto', sans-serif",
                    fontSize: '0.875rem',
                  }}
                >
                  {player.minutes || 0}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default PlayerTable;

