import React, { useState, useEffect, useRef } from 'react';
import { Box } from '@mui/material';
import '../styles/animations.css';

const AnimatedNumber = ({ 
  value,
  duration = 1000,
  decimals = 0,
  prefix = '',
  suffix = '',
  sx = {},
  ...props 
}) => {
  const [displayValue, setDisplayValue] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const startTimeRef = useRef(null);
  const animationFrameRef = useRef(null);

  useEffect(() => {
    if (value === displayValue && !isAnimating) return;

    setIsAnimating(true);
    const startValue = displayValue;
    const endValue = value;
    const startTime = performance.now();
    startTimeRef.current = startTime;

    const animate = (currentTime) => {
      if (!startTimeRef.current) return;

      const elapsed = currentTime - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function: ease-out
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const currentValue = startValue + (endValue - startValue) * easeOut;

      setDisplayValue(currentValue);

      if (progress < 1) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        setDisplayValue(endValue);
        setIsAnimating(false);
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [value, duration]);

  const formattedValue = displayValue.toFixed(decimals);

  return (
    <Box
      className="animated-number"
      sx={{
        display: 'inline-block',
        fontFamily: "'Roboto', sans-serif",
        ...sx,
      }}
      {...props}
    >
      {prefix}{formattedValue}{suffix}
    </Box>
  );
};

export default AnimatedNumber;

