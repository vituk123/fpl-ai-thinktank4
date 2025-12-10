import React, { useState } from 'react';
import TerminalLayout from '../components/TerminalLayout';
import TerminalText from '../components/TerminalText';
import DashboardCard from '../components/Dashboard/DashboardCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorDisplay from '../components/ErrorDisplay';
import TerminalButton from '../components/TerminalButton';
import TerminalInput from '../components/TerminalInput';
import { liveApi } from '../services/api';
import useApi from '../hooks/useApi';
import { formatPoints, formatGameweek } from '../utils/formatters';
import '../styles/components.css';
import '../styles/animations.css';

const LiveTracking = () => {
  const [entryId, setEntryId] = useState('');
  const [gameweek, setGameweek] = useState('');
  const [shouldFetch, setShouldFetch] = useState(false);

  const { data, loading, error, execute } = useApi(
    () => {
      if (!entryId || !gameweek) return Promise.resolve(null);
      return liveApi.getGameweek(parseInt(gameweek), parseInt(entryId));
    },
    [],
    false
  );

  const handleFetch = () => {
    if (entryId && gameweek) {
      execute();
      setShouldFetch(true);
    }
  };

  const liveData = data?.data;
  const playerBreakdown = liveData?.player_breakdown || [];

  return (
    <TerminalLayout>
      <section className="section fade-in">
        <TerminalText variant="large">
          Live Gameweek Tracking
        </TerminalText>
        <TerminalText variant="small" style={{ marginTop: '0.5rem', color: 'var(--text-secondary)' }}>
          Track your team's live performance
        </TerminalText>
      </section>

      <div className="terminal-divider" />

      <section className="section fade-in-delay-1">
        <div style={{ 
          display: 'flex', 
          gap: '1rem', 
          justifyContent: 'center',
          flexWrap: 'wrap',
          marginBottom: '2rem'
        }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
              Entry ID:
            </label>
            <input
              type="number"
              className="terminal-input"
              value={entryId}
              onChange={(e) => setEntryId(e.target.value)}
              placeholder="2568103"
              style={{ width: '200px' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
              Gameweek:
            </label>
            <input
              type="number"
              className="terminal-input"
              value={gameweek}
              onChange={(e) => setGameweek(e.target.value)}
              placeholder="16"
              style={{ width: '200px' }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <TerminalButton onClick={handleFetch} disabled={!entryId || !gameweek}>
              Fetch
            </TerminalButton>
          </div>
        </div>
      </section>

      {loading && <LoadingSpinner message="Loading live data..." />}

      {error && (
        <ErrorDisplay error={error} onRetry={handleFetch} />
      )}

      {!loading && !error && liveData && (
        <>
          <section className="section fade-in-delay-2">
            <DashboardCard title={`${formatGameweek(gameweek)} Summary`}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                    Total Points
                  </div>
                  <div style={{ fontSize: '2rem', color: 'var(--text-accent)', fontWeight: 'bold' }}>
                    {formatPoints(liveData.live_points?.total_points || 0)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                    Starting XI
                  </div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                    {formatPoints(liveData.live_points?.starting_xi || 0)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                    Bench
                  </div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                    {formatPoints(liveData.live_points?.bench || 0)}
                  </div>
                </div>
              </div>
            </DashboardCard>
          </section>

          {playerBreakdown.length > 0 && (
            <section className="section fade-in-delay-3">
              <TerminalText variant="default" style={{ marginBottom: '1rem' }}>
                Player Breakdown
              </TerminalText>
              <div className="terminal-grid">
                {playerBreakdown.map((player, idx) => (
                  <DashboardCard key={idx}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>
                          {player.name}
                        </div>
                        <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                          {player.team} | {player.position}
                        </div>
                        <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                          {player.status}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '1.5rem', color: 'var(--text-accent)', fontWeight: 'bold' }}>
                          {formatPoints(player.points || 0)}
                        </div>
                        {player.minutes !== undefined && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            {player.minutes}' mins
                          </div>
                        )}
                      </div>
                    </div>
                  </DashboardCard>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {!loading && !error && !liveData && shouldFetch && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
          <TerminalText variant="default">
            No data
          </TerminalText>
        </div>
      )}
    </TerminalLayout>
  );
};

export default LiveTracking;

