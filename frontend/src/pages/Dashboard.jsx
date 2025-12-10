import React, { useState } from 'react';
import { 
  Container, 
  Typography, 
  TextField, 
  Card, 
  CardContent, 
  Grid, 
  Box, 
  CircularProgress, 
  Alert, 
  AlertTitle,
  Divider,
  Stack
} from '@mui/material';
import TerminalLayout from '../components/TerminalLayout';
import { dashboardApi } from '../services/api';
import '../styles/components.css';
import '../styles/animations.css';

const Dashboard = () => {
  const [entryId, setEntryId] = useState('2568103');
  const [selectedView, setSelectedView] = useState(null);
  const [viewData, setViewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const views = [
    { id: 'heatmap', name: 'Performance Heatmap', api: dashboardApi.getHeatmap },
    { id: 'value-tracker', name: 'Value Tracker', api: dashboardApi.getValueTracker },
    { id: 'transfers', name: 'Transfer Analysis', api: dashboardApi.getTransfers },
    { id: 'position-balance', name: 'Position Balance', api: dashboardApi.getPositionBalance },
    { id: 'chips', name: 'Chip Usage', api: dashboardApi.getChips },
    { id: 'captain', name: 'Captain Performance', api: dashboardApi.getCaptain },
    { id: 'rank-progression', name: 'Rank Progression', api: dashboardApi.getRankProgression },
    { id: 'value-efficiency', name: 'Value Efficiency', api: dashboardApi.getValueEfficiency },
  ];

  const leagueViews = [
    { id: 'ownership-correlation', name: 'Ownership Correlation', api: dashboardApi.getOwnershipCorrelation },
    { id: 'template-team', name: 'Template Team', api: dashboardApi.getTemplateTeam },
    { id: 'price-predictors', name: 'Price Predictors', api: dashboardApi.getPricePredictors },
    { id: 'position-distribution', name: 'Position Distribution', api: dashboardApi.getPositionDistribution },
    { id: 'fixture-swing', name: 'Fixture Swing', api: dashboardApi.getFixtureSwing },
    { id: 'dgw-probability', name: 'DGW Probability', api: dashboardApi.getDgwProbability },
    { id: 'price-brackets', name: 'Price Brackets', api: dashboardApi.getPriceBrackets },
  ];

  const fetchView = async (view) => {
    if (!entryId) {
      setError('Please enter an Entry ID');
      return;
    }

    setLoading(true);
    setError(null);
    setSelectedView(view.id);
    
    try {
      const result = await view.api(parseInt(entryId));
      setViewData(result);
    } catch (err) {
      setError(err.message || 'Failed to fetch data');
      setViewData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <TerminalLayout>
      <Container maxWidth="xl" sx={{ py: { xs: 4, md: 8 } }}>
        <Box className="fade-in" sx={{ mb: 6 }}>
          <Typography variant="h1" component="h1" gutterBottom>
            Analytics Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Comprehensive FPL analytics and insights
          </Typography>
        </Box>

        <Divider sx={{ my: 4, opacity: 0.16 }} />

        <Box className="fade-in-delay-1" sx={{ mb: 6, display: 'flex', justifyContent: 'center' }}>
          <TextField
            type="number"
            label="Enter your Entry ID"
            value={entryId}
            onChange={(e) => setEntryId(e.target.value)}
            placeholder="2568103"
            variant="outlined"
            fullWidth
            sx={{ maxWidth: 400 }}
          />
        </Box>

        <Box className="fade-in-delay-2" sx={{ mb: 6 }}>
          <Typography variant="h2" component="h2" gutterBottom sx={{ mb: 3 }}>
            Team Analytics
          </Typography>
          <Grid container spacing={3}>
            {views.map((view) => (
              <Grid item xs={12} sm={6} md={4} key={view.id}>
                <Card 
                  sx={{ 
                    cursor: 'pointer',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column'
                  }}
                  onClick={() => fetchView(view)}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Typography variant="h3" component="h3" gutterBottom>
                      {view.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Click to load
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>

        <Divider sx={{ my: 4, opacity: 0.16 }} />

        <Box className="fade-in-delay-3" sx={{ mb: 6 }}>
          <Typography variant="h2" component="h2" gutterBottom sx={{ mb: 3 }}>
            League Analytics
          </Typography>
          <Grid container spacing={3}>
            {leagueViews.map((view) => (
              <Grid item xs={12} sm={6} md={4} key={view.id}>
                <Card 
                  sx={{ 
                    cursor: 'pointer',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column'
                  }}
                  onClick={() => fetchView(view)}
                >
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Typography variant="h3" component="h3" gutterBottom>
                      {view.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Click to load
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
            <Stack spacing={2} alignItems="center">
              <CircularProgress />
              <Typography variant="body2" color="text.secondary">
                Loading analytics...
              </Typography>
            </Stack>
          </Box>
        )}

        {error && (
          <Alert 
            severity="error" 
            sx={{ mb: 4 }}
            action={
              <Box
                component="button"
                onClick={() => selectedView && fetchView(views.find(v => v.id === selectedView) || leagueViews.find(v => v.id === selectedView))}
                sx={{
                  background: 'transparent',
                  border: '1px solid rgba(235, 78, 61, 0.5)',
                  borderRadius: 1,
                  color: '#eb4e3d',
                  px: 2,
                  py: 1,
                  cursor: 'pointer',
                  '&:hover': {
                    backgroundColor: 'rgba(235, 78, 61, 0.1)',
                  },
                }}
              >
                Retry
              </Box>
            }
          >
            <AlertTitle>Error</AlertTitle>
            {typeof error === 'string' ? error : error?.message || String(error)}
          </Alert>
        )}

        {!loading && !error && viewData && selectedView && (
          <Box className="fade-in" sx={{ mt: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="h3" component="h3" gutterBottom>
                  {views.find(v => v.id === selectedView)?.name || leagueViews.find(v => v.id === selectedView)?.name}
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    overflow: 'auto',
                    maxHeight: '500px',
                    fontSize: '0.875rem',
                    color: 'text.secondary',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontFamily: 'monospace',
                    mt: 2,
                  }}
                >
                  {JSON.stringify(viewData, null, 2)}
                </Box>
              </CardContent>
            </Card>
          </Box>
        )}
      </Container>
    </TerminalLayout>
  );
};

export default Dashboard;

