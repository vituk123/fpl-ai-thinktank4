import React, { useState } from 'react';
import { Box, Tooltip } from '@mui/material';
import '../styles/animations.css';

const AnimatedTooltip = ({ 
  title,
  children,
  placement = 'top',
  ...props 
}) => {
  return (
    <Tooltip
      title={title}
      placement={placement}
      arrow
      componentsProps={{
        tooltip: {
          sx: {
            backgroundColor: '#DADAD3',
            color: '#1D1D1B',
            border: '2px solid #1D1D1B',
            borderRadius: 0,
            padding: '0.5rem 0.75rem',
            fontSize: '0.875rem',
            fontFamily: "'Roboto', sans-serif",
            animation: 'tooltipFadeIn 200ms cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: '-0.3rem 0.3rem 0 rgba(29, 30, 28, 0.2)',
          },
        },
        arrow: {
          sx: {
            color: '#1D1D1B',
          },
        },
      }}
      TransitionProps={{
        timeout: 200,
      }}
      {...props}
    >
      {children}
    </Tooltip>
  );
};

export default AnimatedTooltip;

