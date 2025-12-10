import React from 'react';
import { Box } from '@mui/material';
import '../styles/animations.css';

const MacProgress = ({ 
  value = 0,
  variant = 'determinate',
  sx = {},
  fillSx = {},
  ...props 
}) => {
  return (
    <Box
      sx={{
        width: '100%',
        position: 'relative',
        border: '2px solid #1D1D1B',
        backgroundColor: '#DADAD3',
        height: '1.5rem',
        overflow: 'hidden',
        ...sx,
      }}
      {...props}
    >
      <Box
        className="mac-progress__fill"
        sx={{
          height: '100%',
          backgroundColor: '#C1C1BF',
          width: `${value}%`,
          transition: 'width 400ms cubic-bezier(0.4, 0, 0.2, 1)',
          borderRight: '2px solid #1D1D1B',
          position: 'relative',
          ...fillSx,
          '&::after': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'linear-gradient(90deg, transparent, rgba(29, 29, 27, 0.1), transparent)',
            animation: 'progressShine 2s ease-in-out infinite',
          },
        }}
      />
    </Box>
  );
};

export default MacProgress;

