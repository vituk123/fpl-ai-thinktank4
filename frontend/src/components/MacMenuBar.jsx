import React, { useState } from 'react';
import { Box, Typography, Menu, MenuItem, ListItemIcon, ListItemText } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home as HomeIcon, Folder, Settings, Mail, Info } from '@mui/icons-material';
import '../styles/mac-menu-bar.css';

const MacMenuBar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [fileAnchor, setFileAnchor] = useState(null);
  const [contactAnchor, setContactAnchor] = useState(null);

  const handleFileClick = (event) => {
    setFileAnchor(event.currentTarget);
  };

  const handleContactClick = (event) => {
    setContactAnchor(event.currentTarget);
  };

  const handleClose = () => {
    setFileAnchor(null);
    setContactAnchor(null);
  };

  const handleNavigation = (path) => {
    navigate(path);
    handleClose();
  };

  const currentTime = new Date().toLocaleTimeString('en-US', { 
    weekday: 'short', 
    hour: '2-digit', 
    minute: '2-digit' 
  });

  return (
    <Box className="mac-bar" sx={{ 
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      zIndex: 10000,
      backgroundColor: '#DADAD3',
      borderBottom: '2px solid #1D1D1B',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.5rem 1rem',
      height: '2.5rem',
    }}>
      {/* Left Section */}
      <Box className="mac-bar_left" sx={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Box 
          sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            cursor: 'pointer',
            '&:hover': { opacity: 0.7 }
          }}
          onClick={() => navigate('/')}
        >
          <img 
            src="/icons/icon-home.svg" 
            alt="Home" 
            style={{ width: '1.2rem', height: '1.2rem', marginRight: '0.5rem' }}
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        </Box>
        <Typography 
          variant="body2" 
          sx={{ 
            fontWeight: 700,
            fontSize: '0.9rem',
            color: '#1D1D1B',
            cursor: 'default',
          }}
        >
          FPL Optimizer
        </Typography>
        <Box
          component="button"
          onClick={handleFileClick}
          className="mac-bar__item"
          sx={{
            background: 'none',
            border: 'none',
            color: '#1D1D1B',
            cursor: 'pointer',
            fontSize: '0.9rem',
            padding: '0.25rem 0.5rem',
            '&:hover': {
              backgroundColor: 'rgba(29, 29, 27, 0.1)',
            },
          }}
        >
          File
        </Box>
        <Menu
          anchorEl={fileAnchor}
          open={Boolean(fileAnchor)}
          onClose={handleClose}
          TransitionProps={{
            timeout: 300,
          }}
          PaperProps={{
            className: 'menu-animated',
            sx: {
              backgroundColor: '#DADAD3',
              border: '2px solid #1D1D1B',
              borderRadius: 0,
              mt: 0.5,
            },
          }}
        >
          <MenuItem 
            onClick={() => handleNavigation('/about')}
            sx={{
              '&:hover': { backgroundColor: 'rgba(29, 29, 27, 0.1)' },
              color: '#1D1D1B',
            }}
          >
            <ListItemIcon>
              <Info sx={{ color: '#1D1D1B', fontSize: '1.2rem' }} />
            </ListItemIcon>
            <ListItemText>About</ListItemText>
          </MenuItem>
          <MenuItem 
            onClick={() => handleNavigation('/team-dashboard')}
            sx={{
              '&:hover': { backgroundColor: 'rgba(29, 29, 27, 0.1)' },
              color: '#1D1D1B',
            }}
          >
            <ListItemIcon>
              <Folder sx={{ color: '#1D1D1B', fontSize: '1.2rem' }} />
            </ListItemIcon>
            <ListItemText>Team Dashboard</ListItemText>
          </MenuItem>
          <MenuItem 
            onClick={() => handleNavigation('/league-dashboard')}
            sx={{
              '&:hover': { backgroundColor: 'rgba(29, 29, 27, 0.1)' },
              color: '#1D1D1B',
            }}
          >
            <ListItemIcon>
              <Folder sx={{ color: '#1D1D1B', fontSize: '1.2rem' }} />
            </ListItemIcon>
            <ListItemText>League Dashboard</ListItemText>
          </MenuItem>
        </Menu>
        <Box
          component="button"
          onClick={handleContactClick}
          className="mac-bar__item"
          sx={{
            background: 'none',
            border: 'none',
            color: '#1D1D1B',
            cursor: 'pointer',
            fontSize: '0.9rem',
            padding: '0.25rem 0.5rem',
            '&:hover': {
              backgroundColor: 'rgba(29, 29, 27, 0.1)',
            },
          }}
        >
          Contact
        </Box>
        <Menu
          anchorEl={contactAnchor}
          open={Boolean(contactAnchor)}
          onClose={handleClose}
          TransitionProps={{
            timeout: 300,
          }}
          PaperProps={{
            className: 'menu-animated',
            sx: {
              backgroundColor: '#DADAD3',
              border: '2px solid #1D1D1B',
              borderRadius: 0,
              mt: 0.5,
            },
          }}
        >
          <MenuItem 
            component="a"
            href="mailto:support@fpl-optimizer.com"
            sx={{
              '&:hover': { backgroundColor: 'rgba(29, 29, 27, 0.1)' },
              color: '#1D1D1B',
              textDecoration: 'none',
            }}
          >
            <ListItemIcon>
              <Mail sx={{ color: '#1D1D1B', fontSize: '1.2rem' }} />
            </ListItemIcon>
            <ListItemText>Email</ListItemText>
          </MenuItem>
        </Menu>
        <Box
          component="button"
          onClick={() => navigate('/about')}
          className="mac-bar__item"
          sx={{
            background: 'none',
            border: 'none',
            color: '#1D1D1B',
            cursor: 'pointer',
            fontSize: '0.9rem',
            padding: '0.25rem 0.5rem',
            '&:hover': {
              backgroundColor: 'rgba(29, 29, 27, 0.1)',
            },
          }}
        >
          Settings
        </Box>
      </Box>

      {/* Right Section */}
      <Box className="mac-bar_right" sx={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Typography 
          variant="body2" 
          sx={{ 
            fontSize: '0.85rem',
            color: '#1D1D1B',
            cursor: 'default',
          }}
        >
          {currentTime}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <img 
            src="/icons/icon-small-battery.svg" 
            alt="Battery" 
            style={{ width: '1rem', height: '1rem' }}
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default MacMenuBar;

