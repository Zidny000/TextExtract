import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from './LoadingSpinner';

/**
 * Component to protect routes that require authentication
 * If user is not authenticated, redirects to login page with return URL
 */
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  // If still loading auth state, show loading spinner
  if (loading) {
    return <LoadingSpinner message="Checking authentication..." />;
  }

  // If not authenticated, redirect to login with the return URL
  if (!isAuthenticated()) {
    return (
      <Navigate 
        to="/login" 
        state={{ from: location.pathname }}
        replace 
      />
    );
  }

  // If authenticated, render the children components
  return children;
};

export default ProtectedRoute; 