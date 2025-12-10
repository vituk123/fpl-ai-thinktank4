import React from 'react';
import '../styles/components.css';

const TerminalButton = ({ 
  children, 
  onClick, 
  disabled = false,
  variant = 'default',
  className = '',
  type = 'button'
}) => {
  return (
    <button
      type={type}
      className={`terminal-button ${variant} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
};

export default TerminalButton;

