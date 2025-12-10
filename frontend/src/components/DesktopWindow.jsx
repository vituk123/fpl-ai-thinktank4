import React, { useState, useRef, useEffect } from 'react';
import { Box, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import '../styles/desktop-window.css';

const DesktopWindow = ({ 
  title, 
  children, 
  onClose, 
  size = 'medium',
  initialPosition = null,
  draggable = true,
  className = '',
}) => {
  const [position, setPosition] = useState(initialPosition || { x: 100, y: 100 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const windowRef = useRef(null);
  const titleBarRef = useRef(null);

  const sizeClasses = {
    small: 'desktop-window_small',
    medium: 'desktop-window_medium',
    large: 'desktop-window_large',
    narrow: 'desktop-window_narrow',
    xsmall: 'desktop-window_xsmall',
  };

  useEffect(() => {
    if (!draggable) return;

    const handleMouseMove = (e) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y,
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset, draggable]);

  const handleTitleBarMouseDown = (e) => {
    if (!draggable) return;
    const rect = titleBarRef.current?.getBoundingClientRect();
    if (rect) {
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
      setIsDragging(true);
    }
  };

  return (
    <Box
      ref={windowRef}
      className={`desktop-window ${sizeClasses[size]} ${className}`}
      sx={{
        position: 'absolute',
        left: `${position.x}px`,
        top: `${position.y}px`,
        backgroundColor: '#DADAD3',
        border: '2px solid #1D1D1B',
        boxShadow: '-0.6rem 0.6rem 0 rgba(29, 30, 28, 0.26)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 1000,
        minWidth: size === 'small' ? '29rem' : size === 'large' ? '70rem' : size === 'narrow' ? '37rem' : size === 'xsmall' ? '17rem' : '52rem',
        minHeight: size === 'small' ? '29rem' : size === 'large' ? '40.6rem' : size === 'narrow' ? '49rem' : size === 'xsmall' ? '28rem' : '40.4rem',
        transition: isDragging ? 'none' : 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      {/* Title Bar */}
      <Box
        ref={titleBarRef}
        className="desktop-window__title-bar"
        onMouseDown={handleTitleBarMouseDown}
        sx={{
          position: 'relative',
          padding: '0.5rem 5rem 1.5rem 6rem',
          backgroundColor: '#DADAD3',
          borderBottom: '2px solid #1D1D1B',
          cursor: draggable ? 'move' : 'default',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '4rem',
          backgroundImage: 'url(/window-tres-lineas.svg)',
          backgroundPosition: '50% 0.4rem',
          backgroundSize: '67rem 1.3rem',
          backgroundRepeat: 'no-repeat',
        }}
      >
        <Box
          sx={{
            position: 'relative',
            zIndex: 1,
            backgroundColor: '#DADAD3',
            padding: '0 0.5rem',
            fontSize: '0.9rem',
            fontWeight: 'normal',
            letterSpacing: '1px',
            textAlign: 'center',
            color: '#1D1D1B',
            fontFamily: "'Roboto', sans-serif",
          }}
        >
          {title}
        </Box>
        {onClose && (
          <IconButton
            onClick={onClose}
            sx={{
              position: 'absolute',
              right: '0.3rem',
              top: '0.3rem',
              width: '2rem',
              height: '2.2rem',
              padding: '0.3rem',
              border: '2px solid #1D1D1B',
              backgroundColor: '#C1C1BF',
              borderRadius: 0,
              cursor: 'pointer',
              '&:hover': {
                backgroundColor: '#A0A09E',
              },
              zIndex: 2,
            }}
          >
            <img 
              src="/x.svg" 
              alt="Close" 
              style={{ width: '100%', height: '100%', pointerEvents: 'none' }}
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.parentElement.innerHTML = '×';
              }}
            />
          </IconButton>
        )}
      </Box>

      {/* Content Area */}
      <Box
        className="desktop-window__content"
        sx={{
          flex: 1,
          overflow: 'auto',
          backgroundColor: '#DADAD3',
          padding: '1rem',
          '&::-webkit-scrollbar': {
            width: '1rem',
            backgroundColor: '#DADAD3',
          },
          '&::-webkit-scrollbar-track': {
            border: '2px solid #1D1D1B',
            borderTop: 'none',
            borderRight: 'none',
          },
          '&::-webkit-scrollbar-thumb': {
            border: '2px solid #1D1D1B',
            borderRight: 'none',
            backgroundColor: '#C1C1BF',
          },
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

export default DesktopWindow;

