import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Box } from '@mui/material';
import '../styles/animations.css';

const RouteTransition = ({ children }) => {
  const location = useLocation();
  const [shouldAnimate, setShouldAnimate] = useState(true);

  useEffect(() => {
    // Check if reduced motion is preferred
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setShouldAnimate(!mediaQuery.matches);

    const handleChange = (e) => {
      setShouldAnimate(!e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return (
    <Box
      key={location.pathname}
      className={shouldAnimate ? 'route-transition' : ''}
      sx={{
        animation: shouldAnimate ? 'routeSlide 500ms cubic-bezier(0.4, 0, 0.2, 1)' : 'none',
        width: '100%',
        height: '100%',
      }}
    >
      {children}
    </Box>
  );
};

export default RouteTransition;

