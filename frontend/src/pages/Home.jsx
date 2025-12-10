import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Container, Typography, Button, Box, Divider, Stack } from '@mui/material';
import { Dashboard as DashboardIcon, Article, LiveTv, Recommend, Info } from '@mui/icons-material';
import TerminalLayout from '../components/TerminalLayout';
import '../styles/animations.css';

const Home = () => {
  const [showContent, setShowContent] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowContent(true);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  if (!showContent) {
    return (
      <TerminalLayout>
        <Container maxWidth="md" sx={{ minHeight: '60vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 8 }}>
          <Typography variant="h2" component="h2" className="fade-in">
            Once upon a time, we pressed
          </Typography>
          <Typography variant="body1" sx={{ mt: 4 }} className="fade-in-delay-1">
            Enter to Continue
          </Typography>
        </Container>
      </TerminalLayout>
    );
  }

  return (
    <TerminalLayout>
      <Container maxWidth="lg" sx={{ py: { xs: 4, md: 8 } }}>
        <Box className="fade-in" sx={{ mb: 6 }}>
          <Typography variant="h1" component="h1" gutterBottom>
            FPL Optimizer
          </Typography>
          <Typography variant="caption" display="block" sx={{ mt: 2 }}>
            Computer, Inc.
          </Typography>
          <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 1 }}>
            Copyright 2025 | All Rights Reserved
          </Typography>
        </Box>

        <Divider sx={{ my: 4, opacity: 0.16 }} />

        <Box className="fade-in-delay-1" sx={{ mb: 6 }}>
          <Typography 
            variant="h2" 
            component="h2" 
            sx={{ 
              fontFamily: 'JetBrains Mono, Consolas, monospace',
              textTransform: 'uppercase',
              letterSpacing: '-0.01em',
            }}
          >
            cd, rm, ping: commands we memorized
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
            to translate our desires into actions...
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
            If we chose to learn them.
          </Typography>
        </Box>

        <Box className="fade-in-delay-2" sx={{ mb: 6 }}>
          <Typography variant="h2" component="h2" gutterBottom>
            Now, we believe it's time for
          </Typography>
          <Typography variant="h1" component="h1" sx={{ mt: 3 }}>
            Interfaces for the future.
          </Typography>
        </Box>

        <Box className="fade-in-delay-3" sx={{ display: 'flex', flexDirection: 'column', gap: 3, alignItems: 'center' }}>
          <Button
            variant="outlined"
            size="large"
            startIcon={<DashboardIcon />}
            onClick={() => navigate('/dashboard')}
            sx={{ minWidth: 200 }}
          >
            Enter Dashboard
          </Button>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ flexWrap: 'wrap', justifyContent: 'center' }}>
            <Button variant="text" component={Link} to="/news" startIcon={<Article />}>
              News
            </Button>
            <Button variant="text" component={Link} to="/live" startIcon={<LiveTv />}>
              Live Tracking
            </Button>
            <Button variant="text" component={Link} to="/recommendations" startIcon={<Recommend />}>
              Recommendations
            </Button>
            <Button variant="text" component={Link} to="/about" startIcon={<Info />}>
              About
            </Button>
          </Stack>
        </Box>
      </Container>
    </TerminalLayout>
  );
};

export default Home;

