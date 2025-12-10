import React from 'react';
import { Box } from '@mui/material';
import '../styles/components.css';

const TerminalLayout = ({ children, className = '' }) => {
  return (
    <Box 
      className={`terminal-layout ${className}`}
      sx={{
        width: '100%',
        height: '100%',
        backgroundColor: 'transparent',
      }}
    >
      <Box className="terminal-container" sx={{ width: '100%', height: '100%' }}>
        {children}
      </Box>
    </Box>
  );
};

export default TerminalLayout;

