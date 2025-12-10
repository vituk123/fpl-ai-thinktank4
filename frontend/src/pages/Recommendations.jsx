import React, { useState, useEffect } from 'react';
import { Container, Typography, Box, Grid, Card, CardContent, TextField, Button, Slider } from '@mui/material';
import TerminalLayout from '../components/TerminalLayout';
import RecommendationCard from '../components/Dashboard/RecommendationCard';
import DashboardCard from '../components/Dashboard/DashboardCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorDisplay from '../components/ErrorDisplay';
import { recommendationsApi } from '../services/api';
import useApi from '../hooks/useApi';
import { useAppContext } from '../context/AppContext';
import ProtectedRoute from '../components/common/ProtectedRoute';
import '../styles/components.css';
import '../styles/animations.css';
import '../styles/retro.css';

const Recommendations = () => {
  const { entryId, currentGameweek } = useAppContext();
  const [gameweek, setGameweek] = useState('');
  const [maxTransfers, setMaxTransfers] = useState(4);
  const [forcedOutIds, setForcedOutIds] = useState('');
  const [autoFetch, setAutoFetch] = useState(true);

  useEffect(() => {
    if (currentGameweek) {
      setGameweek(currentGameweek.toString());
    }
  }, [currentGameweek]);

  const { data, loading, error, execute, refetch } = useApi(
    () => {
      if (!entryId) return Promise.resolve(null);
      const forcedOut = forcedOutIds
        ? forcedOutIds.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id))
        : null;
      return recommendationsApi.getRecommendations(
        entryId,
        gameweek ? parseInt(gameweek) : null,
        maxTransfers,
        forcedOut
      );
    },
    [entryId, gameweek, maxTransfers, forcedOutIds],
    autoFetch && !!entryId
  );

  const recommendations = data?.data?.recommendations || [];
  const summary = data?.data?.summary || {};

  return (
    <ProtectedRoute>
    <TerminalLayout>
        <div className="crt-overlay" />
        <div className="scanlines" />
        
        <Container maxWidth="xl" sx={{ py: { xs: 4, md: 8 }, position: 'relative', zIndex: 1 }}>
          <Box className="fade-in" sx={{ mb: 6 }}>
            <Typography variant="h1" component="h1" gutterBottom className="retro-glow">
          Transfer Recommendations
            </Typography>
          </Box>

          {/* Controls */}
          <Card className="glass-card fade-in-delay-1" sx={{ mb: 4 }}>
            <CardContent>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    label="Gameweek"
              type="number"
              value={gameweek}
              onChange={(e) => setGameweek(e.target.value)}
                    placeholder={currentGameweek?.toString() || 'Auto'}
                    sx={{ fontFamily: "'JetBrains Mono', monospace" }}
            />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                    Max Transfers: {maxTransfers}
                  </Typography>
                  <Slider
              value={maxTransfers}
                    onChange={(e, val) => setMaxTransfers(val)}
                    min={1}
                    max={15}
                    marks
                    step={1}
                    sx={{ fontFamily: "'JetBrains Mono', monospace" }}
            />
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Force Out Player IDs (comma-separated)"
                    value={forcedOutIds}
                    onChange={(e) => setForcedOutIds(e.target.value)}
                    placeholder="123, 456, 789"
                    sx={{ fontFamily: "'JetBrains Mono', monospace" }}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={() => {
                      setAutoFetch(false);
                      execute();
                    }}
                    disabled={loading || !entryId}
                    sx={{
                      mt: { xs: 0, md: 3 },
                      fontFamily: "'JetBrains Mono', monospace",
                      textTransform: 'uppercase',
                    }}
                  >
                    {loading ? 'Loading...' : 'Generate'}
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

      {loading && <LoadingSpinner message="Loading..." />}

      {error && (
            <ErrorDisplay error={error} onRetry={refetch} />
      )}

      {!loading && !error && recommendations.length > 0 && (
        <>
          {/* ML Status Banner */}
          {data?.meta?.ml_enabled && (
            <Card className="glass-card fade-in-delay-2" sx={{ mb: 4, bgcolor: '#DADAD3', border: '2px solid #1D1D1B' }}>
              <CardContent sx={{ bgcolor: '#DADAD3' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Box sx={{ 
                    width: 40, 
                    height: 40, 
                    borderRadius: 0, 
                    bgcolor: '#1D1D1B', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                  }}>
                    <Typography sx={{ color: '#DADAD3', fontSize: '1.5rem' }}>🤖</Typography>
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" sx={{ fontFamily: "'Roboto', sans-serif", color: '#1D1D1B', fontWeight: 600 }}>
                      ML-Enhanced
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: "'Roboto', sans-serif", color: 'rgba(29, 29, 27, 0.7)' }}>
                      Model: {data.meta.ml_model_version || 'v4.6'}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          )}

          {summary && Object.keys(summary).length > 0 && (
                <Card className="glass-card fade-in-delay-2" sx={{ mb: 4, bgcolor: '#DADAD3', border: '2px solid #1D1D1B' }}>
                  <CardContent sx={{ bgcolor: '#DADAD3' }}>
                    <Typography variant="h4" gutterBottom sx={{ fontFamily: "'Roboto', sans-serif", color: '#1D1D1B', fontWeight: 500 }}>
                      Summary
                    </Typography>
                    <Box className="data-terminal" sx={{ p: 2, mt: 2, bgcolor: '#C1C1BF', border: '2px solid #1D1D1B' }}>
                  {Object.entries(summary).map(([key, value]) => (
                        <Typography key={key} variant="body2" sx={{ mb: 1, fontFamily: "'JetBrains Mono', monospace", color: '#1D1D1B' }}>
                          <strong>{key.replace(/_/g, ' ').toUpperCase()}:</strong> {String(value)}
                        </Typography>
                  ))}
                    </Box>
                  </CardContent>
                </Card>
          )}

              <Box className="fade-in-delay-3">
                <Grid container spacing={3}>
              {recommendations.map((rec, idx) => (
                    <Grid item xs={12} md={6} key={idx}>
                      <RecommendationCard recommendation={rec} />
                    </Grid>
              ))}
                </Grid>
              </Box>
        </>
      )}

          {!loading && !error && recommendations.length === 0 && entryId && (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Typography color="text.secondary">
                No recommendations
              </Typography>
            </Box>
      )}
        </Container>
    </TerminalLayout>
    </ProtectedRoute>
  );
};

export default Recommendations;
