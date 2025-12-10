import React from 'react';
import { Button } from '@mui/material';
import '../styles/animations.css';

const AnimatedButton = ({ 
  children,
  sx = {},
  ...props 
}) => {
  return (
    <Button
      className="animated-button"
      sx={{
        transition: 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1)',
        transform: 'translateY(0)',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: '-0.8rem 0.8rem 0 rgba(29, 30, 28, 0.3)',
        },
        '&:active': {
          transform: 'translateY(0)',
        },
        ...sx,
      }}
      {...props}
    >
      {children}
    </Button>
  );
};

export default AnimatedButton;

