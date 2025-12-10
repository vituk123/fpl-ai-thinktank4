import React from 'react';
import { Box } from '@mui/material';
import '../styles/animations.css';

const MacSpinner = ({ 
  size = 40,
  sx = {},
  ...props 
}) => {
  return (
    <Box
      className="mac-spinner"
      sx={{
        width: `${size}px`,
        height: `${size}px`,
        position: 'relative',
        display: 'inline-block',
        ...sx,
      }}
      {...props}
    >
      <Box
        sx={{
          width: '100%',
          height: '100%',
          border: '3px solid #C1C1BF',
          borderTop: '3px solid #1D1D1B',
          borderRight: '3px solid #1D1D1B',
          transform: 'rotate(45deg)',
          animation: 'macSpinnerRotate 0.8s linear infinite',
        }}
      />
    </Box>
  );
};

export default MacSpinner;

