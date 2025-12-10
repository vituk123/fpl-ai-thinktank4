import React from 'react';
import TerminalButton from './TerminalButton';
import '../styles/components.css';

const ErrorDisplay = ({ 
  error, 
  onRetry, 
  className = '',
  showRetry = true 
}) => {
  if (!error) return null;

  const errorMessage = typeof error === 'string' ? error : error.message || 'An error occurred';

  return (
    <div className={`terminal-error ${className}`}>
      <p style={{ marginBottom: '0.5rem' }}>
        <strong>ERROR:</strong> {errorMessage}
      </p>
      {showRetry && onRetry && (
        <TerminalButton onClick={onRetry} style={{ marginTop: '1rem' }}>
          Retry
        </TerminalButton>
      )}
    </div>
  );
};

export default ErrorDisplay;

