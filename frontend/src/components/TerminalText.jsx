import React from 'react';
import '../styles/terminal.css';
import '../styles/animations.css';

const TerminalText = ({ 
  children, 
  variant = 'default', 
  animate = false,
  className = '',
  style = {}
}) => {
  const variantClasses = {
    'default': '',
    'large': 'terminal-text-large',
    'small': 'terminal-text-small',
    'accent': 'terminal-text-accent',
    'secondary': 'terminal-text-secondary'
  };

  const classes = [
    'terminal-text',
    variantClasses[variant] || '',
    animate ? 'animate-typing' : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={classes} style={style}>
      {children}
    </div>
  );
};

export default TerminalText;

