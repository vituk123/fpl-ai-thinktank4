import React from 'react';
import '../styles/components.css';

const TerminalInput = ({ 
  type = 'text',
  value,
  onChange,
  placeholder = '',
  label = '',
  className = '',
  style = {},
  ...props
}) => {
  const inputId = `input-${Math.random().toString(36).substr(2, 9)}`;
  
  return (
    <div className={`terminal-input-wrapper ${className}`} style={style}>
      <input
        id={inputId}
        type={type}
        className="terminal-input"
        value={value}
        onChange={onChange}
        placeholder={label ? '' : placeholder}
        {...props}
      />
      {label && (
        <label htmlFor={inputId} className="terminal-input-label">
          {label}
        </label>
      )}
    </div>
  );
};

export default TerminalInput;

