import React from 'react';
import '../styles/components.css';

const LoadingSpinner = ({ message = 'Loading...', className = '' }) => {
  return (
    <div className={`loading-container ${className}`} style={{ textAlign: 'center', padding: '2rem' }}>
      <div className="terminal-spinner"></div>
      {message && (
        <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>
          {message}
        </p>
      )}
    </div>
  );
};

export default LoadingSpinner;

