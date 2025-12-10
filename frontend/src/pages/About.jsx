import React from 'react';
import TerminalLayout from '../components/TerminalLayout';
import TerminalText from '../components/TerminalText';
import TerminalLink from '../components/TerminalLink';
import '../styles/animations.css';

const About = () => {
  return (
    <TerminalLayout>
      <section className="section fade-in">
        <TerminalText variant="large">
          About FPL Optimizer
        </TerminalText>
      </section>

      <div className="terminal-divider" />

      <section className="section fade-in-delay-1" style={{ textAlign: 'left', maxWidth: '800px', margin: '0 auto' }}>
        <TerminalText variant="default" style={{ marginBottom: '1.5rem' }}>
          Features:
        </TerminalText>

        <ul style={{ 
          listStyle: 'none', 
          padding: 0,
          marginLeft: '2rem',
          color: 'var(--text-secondary)'
        }}>
          <li style={{ marginBottom: '0.75rem' }}>• Multi-Model Projections</li>
          <li style={{ marginBottom: '0.75rem' }}>• Transfer Optimization</li>
          <li style={{ marginBottom: '0.75rem' }}>• Chip Evaluation</li>
          <li style={{ marginBottom: '0.75rem' }}>• Live Gameweek Tracking</li>
          <li style={{ marginBottom: '0.75rem' }}>• News Aggregation</li>
          <li style={{ marginBottom: '0.75rem' }}>• Advanced Analytics Dashboard</li>
        </ul>

        <div style={{ marginTop: '3rem', textAlign: 'center' }}>
          <TerminalLink to="/">← Back to Home</TerminalLink>
        </div>
      </section>
    </TerminalLayout>
  );
};

export default About;

