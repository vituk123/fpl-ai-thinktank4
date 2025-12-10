import React from 'react';
import { Card } from '@mui/material';
import '../styles/animations.css';

const AnimatedCard = ({ 
  children,
  className = '',
  sx = {},
  ...props 
}) => {
  return (
    <Card
      className={`glass-card animated-card ${className}`}
      sx={{
        transition: 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1), border-width 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1)',
        transform: 'translateY(0)',
        border: '2px solid #1D1D1B',
        '&:hover': {
          transform: 'translateY(-2px)',
          borderWidth: '3px',
          boxShadow: '-0.8rem 0.8rem 0 rgba(29, 30, 28, 0.3)',
        },
        ...sx,
      }}
      {...props}
    >
      {children}
    </Card>
  );
};

export default AnimatedCard;

