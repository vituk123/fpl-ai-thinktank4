import React, { useState, useEffect } from 'react';
import { Box } from '@mui/material';
import DesktopWindow from './DesktopWindow';
import '../styles/animations.css';

const AnimatedWindow = ({ 
  isOpen = true,
  onClose,
  children,
  ...windowProps 
}) => {
  const [isAnimating, setIsAnimating] = useState(false);
  const [shouldRender, setShouldRender] = useState(isOpen);

  useEffect(() => {
    if (isOpen) {
      setShouldRender(true);
      // Small delay to ensure DOM is ready
      setTimeout(() => setIsAnimating(true), 10);
    } else {
      setIsAnimating(false);
      // Wait for animation to complete before unmounting
      const timer = setTimeout(() => setShouldRender(false), 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  if (!shouldRender) return null;

  const handleClose = () => {
    if (onClose) {
      setIsAnimating(false);
      setTimeout(() => {
        onClose();
      }, 300);
    }
  };

  return (
    <Box
      className={`animated-window ${isAnimating ? 'animated-window--open' : 'animated-window--closing'}`}
      sx={{
        '&.animated-window--open': {
          animation: 'windowOpen 400ms cubic-bezier(0.4, 0, 0.2, 1) forwards',
        },
        '&.animated-window--closing': {
          animation: 'windowClose 300ms cubic-bezier(0.4, 0, 0.2, 1) forwards',
        },
      }}
    >
      <DesktopWindow
        {...windowProps}
        onClose={handleClose}
        className={`${windowProps.className || ''} ${isAnimating ? 'fade-in' : ''}`}
      >
        {children}
      </DesktopWindow>
    </Box>
  );
};

export default AnimatedWindow;

