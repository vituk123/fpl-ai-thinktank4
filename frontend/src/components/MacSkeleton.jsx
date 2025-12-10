import React from 'react';
import { Box } from '@mui/material';
import '../styles/animations.css';

const MacSkeleton = ({ 
  variant = 'rectangular',
  width,
  height,
  animation = 'pulse',
  sx = {},
  ...props 
}) => {
  const baseStyles = {
    backgroundColor: '#C1C1BF',
    border: '2px solid #1D1D1B',
    borderRadius: 0,
    ...sx,
  };

  const variantStyles = {
    rectangular: {
      width: width || '100%',
      height: height || '1rem',
    },
    circular: {
      width: width || '3rem',
      height: height || '3rem',
      borderRadius: '50%',
    },
    text: {
      width: width || '100%',
      height: height || '1rem',
      marginBottom: '0.5rem',
    },
  };

  return (
    <Box
      className={`mac-skeleton mac-skeleton--${animation}`}
      sx={{
        ...baseStyles,
        ...variantStyles[variant],
        animation: animation === 'pulse' 
          ? 'skeletonPulse 1.5s ease-in-out infinite' 
          : animation === 'wave'
          ? 'skeletonWave 1.6s ease-in-out infinite'
          : 'none',
      }}
      {...props}
    />
  );
};

export default MacSkeleton;

