import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Typography, TextField, Box, Alert, Card, CardContent, Divider } from '@mui/material';
import DesktopWindow from '../components/DesktopWindow';
import AnimatedButton from '../components/AnimatedButton';
import MacSpinner from '../components/MacSpinner';
import { useAppContext } from '../context/AppContext';
import { validateEntryId } from '../utils/validators';
import { entryApi } from '../services/api';
import '../styles/retro.css';
import '../styles/animations.css';

const Landing = () => {
  const [entryIdInput, setEntryIdInput] = useState('');
  const [error, setError] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [entryInfo, setEntryInfo] = useState(null);
  const [isAccepted, setIsAccepted] = useState(false);
  const [windowPosition, setWindowPosition] = useState({ x: 100, y: 100 });
  const { setEntryId, isAuthenticated, entryId, currentGameweek } = useAppContext();
  const navigate = useNavigate();

  useEffect(() => {
    // Center window on mount
    const centerX = Math.max(50, (window.innerWidth / 2) - 416);
    const centerY = Math.max(50, window.innerHeight * 0.15);
    setWindowPosition({ x: centerX, y: centerY });
  }, []);

  // Redirect if already authenticated - use hash URL format
  useEffect(() => {
    if (isAuthenticated && entryId) {
      // Build hash URL with team ID
      const gameweek = currentGameweek || '';
      let leagueId = null;
      try {
        leagueId = localStorage.getItem('fpl_league_id');
      } catch (e) {
        // Ignore
      }
      const leaguePart = leagueId ? `/league/${leagueId}` : '';
      const hashUrl = `/${gameweek ? gameweek + '/' : ''}team/${entryId}${leaguePart}`;
      navigate(hashUrl, { replace: true });
    }
  }, [isAuthenticated, entryId, navigate, currentGameweek]);

  const handleValidate = async (e) => {
    e.preventDefault();
    setError(null);
    setEntryInfo(null);
    setIsAccepted(false);

    const validation = validateEntryId(entryIdInput);
    if (!validation.valid) {
      setError(validation.error);
      return;
    }

    setIsValidating(true);
    
    try {
      const numEntryId = parseInt(entryIdInput, 10);
      
      // Validate entry ID by fetching entry info
      const response = await entryApi.getEntryInfo(numEntryId);
      const info = response?.data || response;
      
      if (info && info.manager_name) {
        setEntryInfo(info);
      } else {
        setError('Invalid entry ID. Please check and try again.');
      }
    } catch (err) {
      setError(err.message || 'Invalid entry ID. Please check and try again.');
      console.error('Error validating entry ID:', err);
    } finally {
      setIsValidating(false);
    }
  };

  const handleAccept = () => {
    if (entryInfo && entryInfo.entry_id) {
      setIsAccepted(true);
      // Store entry ID (this will trigger gameweek loading in context)
      setEntryId(entryInfo.entry_id);
      
      // Build hash URL with team ID
      const gameweek = currentGameweek || '';
      let leagueId = null;
      try {
        leagueId = localStorage.getItem('fpl_league_id');
      } catch (e) {
        // Ignore
      }
      const leaguePart = leagueId ? `/league/${leagueId}` : '';
      const hashUrl = `/${gameweek ? gameweek + '/' : ''}team/${entryInfo.entry_id}${leaguePart}`;
      
      // Small delay to ensure state is updated
      setTimeout(() => {
        navigate(hashUrl, { replace: true });
      }, 100);
    }
  };

  const handleReset = () => {
    setEntryIdInput('');
    setEntryInfo(null);
    setError(null);
    setIsAccepted(false);
  };

  return (
    <Box
      sx={{
        width: '100vw',
        height: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        position: 'relative',
        paddingTop: '2.5rem',
      }}
    >
      <DesktopWindow
        title="FPL Analytics"
        size="medium"
        initialPosition={windowPosition}
        draggable={true}
        className="fade-in"
      >
        <Box className="fade-in" sx={{ width: '100%', textAlign: 'center', mb: 4 }}>
          <Typography 
            variant="h1" 
            component="h1" 
            gutterBottom
            sx={{
              fontFamily: "'Roboto', sans-serif",
              fontWeight: 400,
              fontSize: '2.5rem',
              mb: 2,
              color: '#1D1D1B',
            }}
          >
            FPL Analytics
          </Typography>
          <Typography 
            variant="body1" 
            sx={{ mb: 1, color: 'rgba(29, 29, 27, 0.7)' }}
          >
            Enter your FPL Entry ID
          </Typography>
        </Box>

        {!entryInfo ? (
          <Box 
            component="form" 
            onSubmit={handleValidate}
            className="fade-in-delay-1"
            sx={{ 
              width: '100%',
              maxWidth: 400,
            }}
          >
            {error && (
              <Alert 
                severity="error" 
                sx={{ mb: 3 }}
                onClose={() => setError(null)}
              >
                {typeof error === 'string' ? error : error?.message || String(error)}
              </Alert>
            )}

            <TextField
              fullWidth
              type="number"
              label="Entry ID"
              value={entryIdInput}
              onChange={(e) => {
                setEntryIdInput(e.target.value);
                setError(null);
              }}
              placeholder="e.g., 2568103"
              variant="outlined"
              required
              autoFocus
              disabled={isValidating}
              sx={{ mb: 3 }}
              inputProps={{
                min: 1,
                style: { 
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '1.25rem',
                },
              }}
            />

            <AnimatedButton
              type="submit"
              fullWidth
              variant="outlined"
              size="large"
              disabled={isValidating || !entryIdInput}
              sx={{
                py: 1.5,
                fontFamily: "'Roboto', sans-serif",
                fontSize: '0.875rem',
                fontWeight: 500,
                border: '2px solid #1D1D1B',
                backgroundColor: '#C1C1BF',
                color: '#1D1D1B',
                '&:hover': {
                  backgroundColor: '#A0A09E',
                  borderColor: '#1D1D1B',
                },
                '&:disabled': {
                  backgroundColor: '#C1C1BF',
                  opacity: 0.6,
                },
              }}
            >
              {isValidating ? (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <MacSpinner size={16} />
                  <span>Validating...</span>
                </Box>
              ) : (
                'Validate Entry ID'
              )}
            </AnimatedButton>
          </Box>
        ) : (
          <Box className="fade-in-delay-1" sx={{ width: '100%', maxWidth: 400 }}>
            <Card 
              sx={{ 
                backgroundColor: '#DADAD3',
                border: '2px solid #1D1D1B',
                borderRadius: 0,
                mb: 3,
              }}
            >
              <CardContent sx={{ backgroundColor: '#DADAD3' }}>
                <Typography 
                  variant="h6" 
                  sx={{ 
                    fontFamily: "'Roboto', sans-serif",
                    fontWeight: 600,
                    color: '#1D1D1B',
                    mb: 2,
                  }}
                >
                  Entry Verified
                </Typography>
                
                <Divider sx={{ mb: 2, borderColor: '#1D1D1B' }} />
                
                <Box sx={{ mb: 2 }}>
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: 'rgba(29, 29, 27, 0.7)',
                      display: 'block',
                      mb: 0.5,
                    }}
                  >
                    Manager Name
                  </Typography>
                  <Typography 
                    variant="body1" 
                    sx={{ 
                      fontFamily: "'Roboto', sans-serif",
                      fontWeight: 500,
                      color: '#1D1D1B',
                    }}
                  >
                    {entryInfo.manager_name}
                  </Typography>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: 'rgba(29, 29, 27, 0.7)',
                      display: 'block',
                      mb: 0.5,
                    }}
                  >
                    Team Name
                  </Typography>
                  <Typography 
                    variant="body1" 
                    sx={{ 
                      fontFamily: "'Roboto', sans-serif",
                      fontWeight: 500,
                      color: '#1D1D1B',
                    }}
                  >
                    {entryInfo.team_name}
                  </Typography>
                </Box>

                <Box>
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: 'rgba(29, 29, 27, 0.7)',
                      display: 'block',
                      mb: 0.5,
                    }}
                  >
                    Entry ID
                  </Typography>
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontFamily: "'JetBrains Mono', monospace",
                      color: '#1D1D1B',
                    }}
                  >
                    {entryInfo.entry_id}
                  </Typography>
                </Box>
              </CardContent>
            </Card>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <AnimatedButton
                fullWidth
                variant="outlined"
                onClick={handleReset}
                disabled={isAccepted}
                sx={{
                  py: 1.5,
                  fontFamily: "'Roboto', sans-serif",
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  border: '2px solid #1D1D1B',
                  backgroundColor: '#C1C1BF',
                  color: '#1D1D1B',
                  '&:hover': {
                    backgroundColor: '#A0A09E',
                    borderColor: '#1D1D1B',
                  },
                }}
              >
                Change Entry ID
              </AnimatedButton>

              <AnimatedButton
                fullWidth
                variant="outlined"
                onClick={handleAccept}
                disabled={isAccepted}
                sx={{
                  py: 1.5,
                  fontFamily: "'Roboto', sans-serif",
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  border: '2px solid #1D1D1B',
                  backgroundColor: isAccepted ? '#1CB59F' : '#1D1D1B',
                  color: isAccepted ? '#DADAD3' : '#DADAD3',
                  '&:hover': {
                    backgroundColor: isAccepted ? '#1CB59F' : '#A0A09E',
                    borderColor: '#1D1D1B',
                  },
                }}
              >
                {isAccepted ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <MacSpinner size={16} />
                    <span>Entering...</span>
                  </Box>
                ) : (
                  'Accept & Enter Dashboard'
                )}
              </AnimatedButton>
            </Box>
          </Box>
        )}

      </DesktopWindow>
    </Box>
  );
};

export default Landing;

