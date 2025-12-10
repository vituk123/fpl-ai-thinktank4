import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAppContext } from '../../context/AppContext';

/**
 * Extract team ID from URL hash
 */
const extractTeamIdFromHash = () => {
  if (typeof window === 'undefined') return null;
  
  const hash = window.location.hash;
  if (!hash) return null;
  
  // Match patterns like /team/2568103 or /25/team/2568103
  const teamMatch = hash.match(/\/team\/(\d+)/);
  if (teamMatch && teamMatch[1]) {
    const teamId = parseInt(teamMatch[1], 10);
    if (!isNaN(teamId) && teamId > 0) {
      return teamId;
    }
  }
  
  return null;
};

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, entryId } = useAppContext();
  const location = useLocation();
  
  // Check if team ID is in URL hash
  const hashTeamId = extractTeamIdFromHash();
  
  // If no entry ID in context and no team ID in URL hash, redirect to landing
  if (!entryId && !hashTeamId) {
    return <Navigate to="/" replace />;
  }
  
  // If we have team ID in hash but not in context, let TeamRoute handle it
  // But if we're already on a protected route without auth, redirect
  if (!isAuthenticated && !hashTeamId) {
    return <Navigate to="/" replace />;
  }

  return children;
};

export default ProtectedRoute;

