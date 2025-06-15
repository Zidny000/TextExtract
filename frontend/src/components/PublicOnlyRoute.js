import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from './LoadingSpinner';

/**
 * Component to protect routes that should only be accessible to non-authenticated users
 * If user is authenticated, redirects to profile or the previous intended destination
 */
const PublicOnlyRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  // Get intended destination from state or default to profile
  const from = location.state?.from || '/profile';

  // If still loading auth state, show loading spinner
  if (loading) {
    return <LoadingSpinner message="Checking authentication..." />;
  }

  // If already authenticated, redirect to profile or intended destination
  if (isAuthenticated()) {
    return <Navigate to={from} replace />;
  }

  // If not authenticated, render the children components (login/signup forms)
  return children;
};

export default PublicOnlyRoute; 