import React from 'react';
import '../styles/components.css';

const AsciiArt = ({ art, size = 'medium', className = '' }) => {
  const sizeClasses = {
    'small': 'ascii-art-small',
    'medium': 'ascii-art-medium',
    'large': 'ascii-art-large'
  };

  return (
    <pre className={`terminal-code ascii-art ${sizeClasses[size]} ${className}`}>
      {art}
    </pre>
  );
};

export default AsciiArt;

