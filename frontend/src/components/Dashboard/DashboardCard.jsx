import React from 'react';
import '../../styles/components.css';

const DashboardCard = ({ title, children, className = '', onClick }) => {
  return (
    <div 
      className={`terminal-card ${onClick ? 'clickable' : ''} ${className}`}
      onClick={onClick}
    >
      {title && (
        <h3 className="heading-02" style={{ marginBottom: 'var(--spacing-md)', color: 'var(--text-primary)' }}>
          {title}
        </h3>
      )}
      {children}
    </div>
  );
};

export default DashboardCard;

