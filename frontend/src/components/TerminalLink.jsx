import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import '../styles/components.css';

const TerminalLink = ({ 
  to, 
  children, 
  external = false,
  showIcon = false,
  className = '',
  onClick
}) => {
  const location = useLocation();
  const isActive = !external && location.pathname === to;
  const linkClasses = `terminal-link ${isActive ? 'active' : ''} ${className}`;

  const iconSvg = (
    <svg xmlns="http://www.w3.org/2000/svg" xmlSpace="preserve" viewBox="0 0 8 8" className="terminal-link-icon">
      <path d="M7.9.1c-.2-.1-.6-.1-.8 0L1 6.3V3.5C1 3.2.8 3 .5 3s-.5.2-.5.5V8h4.5c.3 0 .5-.2.5-.5S4.8 7 4.5 7H1.7L7.8.9c.2-.2.2-.6.1-.8" fill="currentColor"/>
    </svg>
  );

  if (external) {
    return (
      <a
        href={to}
        target="_blank"
        rel="noopener noreferrer"
        className={linkClasses}
        onClick={onClick}
      >
        <span className="label-02">{children}</span>
        {showIcon && iconSvg}
      </a>
    );
  }

  return (
    <Link to={to} className={linkClasses} onClick={onClick}>
      <span className="label-02">{children}</span>
      {showIcon && iconSvg}
    </Link>
  );
};

export default TerminalLink;

