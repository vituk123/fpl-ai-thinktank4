import React, { useState, useEffect } from 'react';
import { Chip } from '@mui/material';
import '../styles/animations.css';

const AnimatedBadge = ({ 
  label,
  color = 'default',
  size = 'medium',
  sx = {},
  ...props 
}) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  const colorMap = {
    default: {
      backgroundColor: '#C1C1BF',
      color: '#1D1D1B',
    },
    primary: {
      backgroundColor: '#1D1D1B',
      color: '#DADAD3',
    },
    success: {
      backgroundColor: '#1D1D1B',
      color: '#DADAD3',
    },
  };

  return (
    <Chip
      label={label}
      size={size}
      className={`animated-badge ${isVisible ? 'animated-badge--visible' : ''}`}
      sx={{
        ...colorMap[color],
        border: '2px solid #1D1D1B',
        borderRadius: 0,
        fontFamily: "'Roboto', sans-serif",
        fontWeight: 500,
        ...sx,
      }}
      {...props}
    />
  );
};

export default AnimatedBadge;

