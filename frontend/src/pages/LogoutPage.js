import React, { useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from '../components/LoadingSpinner';

/**
 * LogoutPage component
 * Handles the logout process and redirects to home page
 */
const LogoutPage = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const logoutPerformed = useRef(false);

  // Use callback to avoid recreating the function on each render
  const handleLogout = useCallback(async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      // Always navigate to home page
      navigate('/', { replace: true });
    }
  }, [logout, navigate]);

  useEffect(() => {
    // Only attempt logout once
    if (!logoutPerformed.current) {
      logoutPerformed.current = true;
      handleLogout();
    }
  }, [handleLogout]); // handleLogout is stable due to useCallback

  // Show loading spinner while the component is mounted
  return <LoadingSpinner message="Logging out..." />;
};

export default LogoutPage; 