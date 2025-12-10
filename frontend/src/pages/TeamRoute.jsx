import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import MacSpinner from '../components/MacSpinner';
import { useAppContext } from '../context/AppContext';
import { entryApi } from '../services/api';
import '../styles/retro.css';

/**
 * TeamRoute - Handles URL-based team authentication
 * Supports URLs like: /#/25/team/2568103/league/1096128
 * or minimal: /#/team/2568103
 */
const TeamRoute = () => {
  const { teamId, gameweek, leagueId } = useParams();
  const navigate = useNavigate();
  const { setEntryId, setCurrentGameweek, entryId, currentGameweek } = useAppContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const authenticateFromUrl = async () => {
      if (!teamId) {
        setError('Team ID is required');
        setLoading(false);
        return;
      }

      const numTeamId = parseInt(teamId, 10);
      if (isNaN(numTeamId) || numTeamId <= 0) {
        setError('Invalid team ID');
        setLoading(false);
        return;
      }

      try {
        console.log('Validating team ID:', numTeamId);
        // Validate team ID via backend
        const response = await entryApi.getEntryInfo(numTeamId);
        console.log('API response received:', response);
        
        // Handle nested response structure: backend returns {data: {...}, meta: {...}}
        // Axios interceptor already extracts response.data, so we get {data: {...}, meta: {...}}
        // Extract the actual entry info from response.data or response.data.data
        const info = response?.data?.entry_id ? response.data : (response?.data || response);
        console.log('Extracted entry info:', info);

        if (info && info.entry_id) {
          const validatedEntryId = info.entry_id;
          console.log('Team ID validated successfully:', validatedEntryId);
          
          // Set entry ID in context
          setEntryId(validatedEntryId);

          // Set gameweek if provided in URL
          if (gameweek) {
            const numGameweek = parseInt(gameweek, 10);
            if (!isNaN(numGameweek) && numGameweek > 0) {
              setCurrentGameweek(numGameweek);
            }
          }

          // Store league ID if provided (for future use)
          if (leagueId) {
            const numLeagueId = parseInt(leagueId, 10);
            if (!isNaN(numLeagueId) && numLeagueId > 0) {
              // Store in localStorage for now (can be moved to context later)
              try {
                localStorage.setItem('fpl_league_id', numLeagueId.toString());
              } catch (e) {
                console.warn('Failed to store league ID:', e);
              }
            }
          }

          // Redirect to team dashboard with hash URL
          const targetGameweek = currentGameweek || '';
          const leaguePart = leagueId ? `/league/${leagueId}` : '';
          const hashUrl = `/${targetGameweek ? targetGameweek + '/' : ''}team/${validatedEntryId}${leaguePart}`;
          console.log('Navigating to:', hashUrl);
          
          // Use window.location.hash for hash routing
          window.location.hash = hashUrl;
          // Also navigate to ensure React Router updates
          navigate(hashUrl, { replace: true });
          setLoading(false);
        } else {
          console.error('Invalid response structure. Expected entry_id but got:', info);
          setError('Invalid team ID - response format error');
          setLoading(false);
        }
      } catch (err) {
        console.error('Error validating team ID:', err);
        const errorMessage = err?.message || err?.response?.data?.error || err?.response?.data?.detail || 'Failed to validate team ID. Please check the team ID and try again.';
        setError(errorMessage);
        setLoading(false);
      }
    };

    // Only authenticate if we don't already have this entry ID set
    if (entryId !== parseInt(teamId, 10)) {
      authenticateFromUrl();
    } else {
      // Already authenticated, build hash URL and redirect
      setLoading(false);
      const targetGameweek = currentGameweek || '';
      const leaguePart = leagueId ? `/league/${leagueId}` : '';
      const hashUrl = `/${targetGameweek ? targetGameweek + '/' : ''}team/${entryId}${leaguePart}`;
      navigate(hashUrl, { replace: true });
    }
  }, [teamId, gameweek, leagueId, setEntryId, setCurrentGameweek, navigate, entryId, currentGameweek]);

  if (loading) {
    return (
      <Box
        sx={{
          width: '100vw',
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: '#DADAD3',
        }}
      >
        <MacSpinner size={50} />
        <Typography
          variant="body1"
          sx={{
            mt: 3,
            color: 'rgba(29, 29, 27, 0.7)',
            fontFamily: "'Roboto', sans-serif",
          }}
        >
          Validating team ID...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        sx={{
          width: '100vw',
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: '#DADAD3',
          p: 4,
        }}
      >
        <Typography
          variant="h5"
          sx={{
            color: '#1D1D1B',
            fontFamily: "'Roboto', sans-serif",
            fontWeight: 600,
            mb: 2,
          }}
        >
          Authentication Error
        </Typography>
        <Typography
          variant="body1"
          sx={{
            color: 'rgba(29, 29, 27, 0.7)',
            fontFamily: "'Roboto', sans-serif",
            textAlign: 'center',
            maxWidth: 500,
          }}
        >
          {error}
        </Typography>
      </Box>
    );
  }

  return null;
};

export default TeamRoute;

