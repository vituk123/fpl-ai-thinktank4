import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate, useLocation, Link, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Container, Button, Typography, useTheme, useMediaQuery, Box } from '@mui/material';
import { Home as HomeIcon, Dashboard as DashboardIcon, Article, LiveTv, Recommend, Info } from '@mui/icons-material';
import { AppProvider, useAppContext } from './context/AppContext';
import MacMenuBar from './components/MacMenuBar';
import DesktopWindow from './components/DesktopWindow';
import RouteTransition from './components/RouteTransition';
import TerminalLayout from './components/TerminalLayout';
import ProtectedRoute from './components/common/ProtectedRoute';
import Landing from './pages/Landing';
import Home from './pages/Home';
import TeamDashboard from './pages/TeamDashboard';
import LeagueDashboard from './pages/LeagueDashboard';
import Dashboard from './pages/Dashboard';
import News from './pages/News';
import LiveTracking from './pages/LiveTracking';
import Recommendations from './pages/Recommendations';
import About from './pages/About';
import TeamRoute from './pages/TeamRoute';
import './styles/terminal.css';
import './styles/animations.css';
import './styles/components.css';
import './styles/retro.css';

const Navigation = () => {
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { entryId, currentGameweek } = useAppContext();

  // Generate hash-based URLs with team ID
  const getHashUrl = (path) => {
    if (!entryId) {
      // If no entry ID, use regular path (will redirect to landing)
      return path;
    }
    
    // Extract league ID from localStorage if available
    let leagueId = null;
    try {
      leagueId = localStorage.getItem('fpl_league_id');
    } catch (e) {
      // Ignore
    }
    
    // Build hash URL: /#/{gameweek}/team/{teamId}/league/{leagueId}
    const gameweek = currentGameweek || '';
    const leaguePart = leagueId ? `/league/${leagueId}` : '';
    
    // Map paths to hash URLs
    if (path === '/team-dashboard') {
      return `/${gameweek ? gameweek + '/' : ''}team/${entryId}${leaguePart}`;
    } else if (path === '/league-dashboard') {
      return `/${gameweek ? gameweek + '/' : ''}team/${entryId}${leaguePart ? leaguePart : '/league/0'}`;
    } else if (path === '/news') {
      return `/${gameweek ? gameweek + '/' : ''}team/${entryId}${leaguePart}/news`;
    } else if (path === '/recommendations') {
      return `/${gameweek ? gameweek + '/' : ''}team/${entryId}${leaguePart}/recommendations`;
    } else if (path === '/about') {
      return `/${gameweek ? gameweek + '/' : ''}team/${entryId}${leaguePart}/about`;
    }
    return path;
  };

  const navItems = [
    { path: '/team-dashboard', label: 'Team', icon: <DashboardIcon fontSize="small" /> },
    { path: '/league-dashboard', label: 'League', icon: <DashboardIcon fontSize="small" /> },
    { path: '/news', label: 'News', icon: <Article fontSize="small" /> },
    { path: '/recommendations', label: 'Transfers', icon: <Recommend fontSize="small" /> },
    { path: '/about', label: 'About', icon: <Info fontSize="small" /> },
  ];

  return (
    <Box
      sx={{
        backgroundColor: '#DADAD3',
        borderBottom: '2px solid #1D1D1B',
        padding: { xs: 1, md: 2 },
        display: 'flex',
        justifyContent: { xs: 'center', md: 'flex-end' },
        gap: { xs: 1, md: 2 },
        flexWrap: 'wrap',
      }}
    >
      {navItems.map((item) => {
        const isActive = location.pathname === item.path || location.hash.includes(item.path.replace('/', ''));
        const hashUrl = getHashUrl(item.path);
        return (
          <Button
            key={item.path}
            component={Link}
            to={hashUrl}
            startIcon={item.icon}
            variant={isActive ? 'outlined' : 'outlined'}
            sx={{
              color: '#1D1D1B',
              borderColor: '#1D1D1B',
              backgroundColor: isActive ? '#C1C1BF' : 'transparent',
              fontWeight: isActive ? 600 : 500,
              fontSize: { xs: '0.75rem', md: 'clamp(12px, calc(12px + 0.4vw), 14px)' },
              minWidth: { xs: 'auto', md: 'auto' },
              px: { xs: 1.5, md: 2 },
              borderRadius: 0,
              '&:hover': {
                backgroundColor: 'rgba(29, 29, 27, 0.1)',
                borderColor: '#1D1D1B',
              },
            }}
          >
            {item.label}
          </Button>
        );
      })}
    </Box>
  );
};

const NotFound = () => {
  const navigate = useNavigate();
  const [windowPosition, setWindowPosition] = React.useState({ x: 100, y: 100 });

  React.useEffect(() => {
    const centerX = Math.max(50, (window.innerWidth / 2) - 232);
    const centerY = Math.max(50, (window.innerHeight / 2) - 232);
    setWindowPosition({ x: centerX, y: centerY });
  }, []);

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
        title="404 - Page Not Found"
        size="small"
        initialPosition={windowPosition}
        draggable={true}
      >
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography 
            variant="h1" 
            component="h1" 
            gutterBottom
            sx={{
              fontFamily: "'Roboto', sans-serif",
              fontWeight: 400,
              fontSize: '3rem',
              color: '#1D1D1B',
              mb: 2,
            }}
          >
            404
          </Typography>
          <Typography 
            variant="body1" 
            sx={{ mb: 4, color: 'rgba(29, 29, 27, 0.7)' }}
          >
            Page not found
          </Typography>
          <Button
            variant="outlined"
            startIcon={<HomeIcon />}
            onClick={() => navigate('/')}
            sx={{
              border: '2px solid #1D1D1B',
              backgroundColor: '#C1C1BF',
              color: '#1D1D1B',
              '&:hover': {
                backgroundColor: '#A0A09E',
              },
            }}
          >
            Back to Home
          </Button>
        </Box>
      </DesktopWindow>
    </Box>
  );
};

function App() {
  return (
    <AppProvider>
      <Router>
        <Box 
          className="App body-wrap"
          sx={{
            width: '100vw',
            height: '100vh',
            backgroundColor: '#DADAD3',
            backgroundImage: 'url(/pattern-grid.png)',
            backgroundSize: '105rem',
            paddingTop: '2.5rem', // Space for Mac menu bar
            overflow: 'auto',
          }}
        >
          <MacMenuBar />
          <RouteTransition>
            <Routes>
            {/* Landing page - entry gate */}
            <Route path="/" element={<Landing />} />
            
            {/* Hash-based URL routes for team authentication */}
            <Route path="/:gameweek?/team/:teamId/league/:leagueId?" element={<TeamRoute />} />
            <Route path="/:gameweek?/team/:teamId" element={<TeamRoute />} />
            <Route path="/team/:teamId/league/:leagueId?" element={<TeamRoute />} />
            <Route path="/team/:teamId" element={<TeamRoute />} />
            
            {/* Hash-based routes for specific pages with team ID */}
            <Route path="/:gameweek?/team/:teamId/league/:leagueId?/news" element={
              <>
                <Navigation />
                <ProtectedRoute>
                  <News />
                </ProtectedRoute>
              </>
            } />
            <Route path="/:gameweek?/team/:teamId/league/:leagueId?/recommendations" element={
              <>
                <Navigation />
                <ProtectedRoute>
                  <Recommendations />
                </ProtectedRoute>
              </>
            } />
            <Route path="/:gameweek?/team/:teamId/league/:leagueId?/about" element={
              <>
                <Navigation />
                <About />
              </>
            } />
            
            {/* Protected routes - require entry_id */}
            <Route path="/team-dashboard" element={
              <ProtectedRoute>
                <>
                  <Navigation />
                  <TeamDashboard />
                </>
              </ProtectedRoute>
            } />
            <Route path="/league-dashboard" element={
              <ProtectedRoute>
                <>
                  <Navigation />
                  <LeagueDashboard />
                </>
              </ProtectedRoute>
            } />
            
            {/* Legacy routes - keep for backward compatibility */}
            <Route path="/home" element={<Home />} />
            <Route path="/dashboard" element={
              <>
                <Navigation />
                <Dashboard />
              </>
            } />
            <Route path="/news" element={
              <>
                <Navigation />
                <ProtectedRoute>
                  <News />
                </ProtectedRoute>
              </>
            } />
            <Route path="/live" element={
              <>
                <Navigation />
                <ProtectedRoute>
                  <LiveTracking />
                </ProtectedRoute>
              </>
            } />
            <Route path="/recommendations" element={
              <>
                <Navigation />
                <ProtectedRoute>
                  <Recommendations />
                </ProtectedRoute>
              </>
            } />
            <Route path="/about" element={
              <>
                <Navigation />
                <About />
              </>
            } />
            <Route path="/404" element={<NotFound />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
            </Routes>
          </RouteTransition>
        </Box>
      </Router>
    </AppProvider>
  );
}

export default App;
