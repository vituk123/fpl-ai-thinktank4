import React from 'react';
import { Container, Typography, Grid, Box } from '@mui/material';
import { ShowChart } from '@mui/icons-material';
import DesktopWindow from '../components/DesktopWindow';
import LiveGameweekTracker from '../components/dashboard/LiveGameweekTracker';
import AnalyticsModule from '../components/dashboard/AnalyticsModule';
import { useAppContext } from '../context/AppContext';
import ProtectedRoute from '../components/common/ProtectedRoute';
import '../styles/retro.css';
import '../styles/animations.css';

const TeamDashboard = () => {
  const { entryId, currentGameweek } = useAppContext();
  const [windowPosition, setWindowPosition] = React.useState({ x: 100, y: 100 });

  React.useEffect(() => {
    const centerX = Math.max(50, (window.innerWidth / 2) - 560);
    const centerY = Math.max(50, window.innerHeight * 0.1);
    setWindowPosition({ x: centerX, y: centerY });
  }, []);

  const analyticsModules = [
    {
      id: 'rank-progression',
      title: 'Rank Progression',
      description: 'Overall rank over time',
      icon: <ShowChart />,
      endpoint: 'getRankProgression',
    },
  ];

  return (
    <ProtectedRoute>
      <Box
        sx={{
          width: '100vw',
          minHeight: 'calc(100vh - 2.5rem)',
          padding: { xs: 2, md: 4 },
          position: 'relative',
        }}
      >
        <DesktopWindow
          title="Team Dashboard"
          size="large"
          initialPosition={windowPosition}
          draggable={true}
          className="fade-in"
        >
          <Container maxWidth={false} sx={{ py: { xs: 2, md: 4 } }}>
          <Box className="fade-in" sx={{ mb: 6 }}>
            <Typography 
              variant="h1" 
              component="h1" 
              gutterBottom
              sx={{
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 400,
                fontSize: '2.5rem',
                color: '#1D1D1B',
                mb: 2,
              }}
            >
              Team Dashboard
            </Typography>
          </Box>

          {/* Live Gameweek Tracker */}
          <Box className="fade-in-delay-1" sx={{ mb: 6, display: 'flex', justifyContent: 'center' }}>
            <Box sx={{ maxWidth: '800px', width: '100%' }}>
              <LiveGameweekTracker gameweek={currentGameweek} />
            </Box>
          </Box>

          {/* Analytics Modules Grid - Centered */}
          <Box className="fade-in-delay-2" sx={{ display: 'flex', justifyContent: 'center' }}>
                <Grid container spacing={3} sx={{ maxWidth: '800px', width: '100%' }}>
                  {analyticsModules.map((module, index) => (
                    <Grid 
                      item 
                      xs={12} 
                      key={module.id}
                      className="staggered-item"
                      sx={{
                        animationDelay: `${index * 100}ms`,
                      }}
                    >
                  <AnalyticsModule
                    module={module}
                    entryId={entryId}
                    currentGameweek={currentGameweek}
                  />
                </Grid>
              ))}
            </Grid>
          </Box>
          </Container>
        </DesktopWindow>
      </Box>
    </ProtectedRoute>
  );
};

export default TeamDashboard;

