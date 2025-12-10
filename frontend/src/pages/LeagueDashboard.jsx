import React from 'react';
import { Container, Typography, Grid, Box } from '@mui/material';
import { 
  People, 
  Group, 
  TrendingUp, 
  PieChart, 
  CalendarToday, 
  Event, 
  AttachMoney 
} from '@mui/icons-material';
import DesktopWindow from '../components/DesktopWindow';
import LeagueAnalyticsModule from '../components/Dashboard/LeagueAnalyticsModule';
import { useAppContext } from '../context/AppContext';
import ProtectedRoute from '../components/common/ProtectedRoute';
import '../styles/retro.css';
import '../styles/animations.css';

const LeagueDashboard = () => {
  const { currentGameweek } = useAppContext();
  const [windowPosition, setWindowPosition] = React.useState({ x: 100, y: 100 });

  React.useEffect(() => {
    const centerX = Math.max(50, (window.innerWidth / 2) - 560);
    const centerY = Math.max(50, window.innerHeight * 0.1);
    setWindowPosition({ x: centerX, y: centerY });
  }, []);

  const leagueModules = [
    {
      id: 'ownership-correlation',
      title: 'Ownership Correlation',
      description: 'Ownership vs points scatter analysis',
      icon: <People />,
      endpoint: 'ownership-correlation',
    },
    {
      id: 'template-team',
      title: 'Template Team',
      description: 'Most owned players and template',
      icon: <Group />,
      endpoint: 'template-team',
    },
    {
      id: 'price-predictors',
      title: 'Price Predictors',
      description: 'Price change prediction models',
      icon: <TrendingUp />,
      endpoint: 'price-predictors',
    },
    {
      id: 'position-distribution',
      title: 'Position Distribution',
      description: 'Points distribution by position',
      icon: <PieChart />,
      endpoint: 'position-distribution',
    },
    {
      id: 'fixture-swing',
      title: 'Fixture Swing',
      description: 'Fixture difficulty changes',
      icon: <CalendarToday />,
      endpoint: 'fixture-swing',
    },
    {
      id: 'dgw-probability',
      title: 'DGW Probability',
      description: 'Double gameweek probability engine',
      icon: <Event />,
      endpoint: 'dgw-probability',
    },
    {
      id: 'price-brackets',
      title: 'Price Brackets',
      description: 'Top performers by price range',
      icon: <AttachMoney />,
      endpoint: 'price-brackets',
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
          title="League Dashboard"
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
              League Dashboard
            </Typography>
          </Box>

          {/* League Analytics Modules Grid - Display side by side */}
          <Box className="fade-in-delay-1">
                <Grid container spacing={3}>
                  {leagueModules.map((module, index) => (
                    <Grid 
                      item 
                      xs={12} 
                      md={6} 
                      key={module.id}
                      className="staggered-item"
                      sx={{
                        animationDelay: `${index * 100}ms`,
                      }}
                    >
                  <LeagueAnalyticsModule
                    module={module}
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

export default LeagueDashboard;

