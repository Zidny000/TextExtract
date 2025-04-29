import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const TOKEN_KEY = 'textextract_token';
const USER_KEY = 'textextract_user';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth state from local storage on component mount
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);

    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      
      // Set default Authorization header for all requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
    }

    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API_URL}/auth/login`, {
        email,
        password,
      });

      const { token, user } = response.data;

      // Save to state
      setToken(token);
      setUser(user);

      // Save to local storage
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      // Set default Authorization header for future requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return { 
        success: false, 
        error: error.response?.data?.error || 'Login failed' 
      };
    }
  };

  const logout = () => {
    // Clear state
    setToken(null);
    setUser(null);

    // Clear localStorage
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);

    // Remove Authorization header
    delete axios.defaults.headers.common['Authorization'];
  };

  const refreshToken = async () => {
    if (!token) return false;

    try {
      const response = await axios.post(
        `${API_URL}/auth/refresh`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const newToken = response.data.token;

      // Update state
      setToken(newToken);

      // Update localStorage
      localStorage.setItem(TOKEN_KEY, newToken);

      // Update default headers
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;

      return true;
    } catch (error) {
      console.error('Token refresh error:', error);
      
      // If refresh fails, log out
      logout();
      return false;
    }
  };

  const isAuthenticated = () => {
    return !!token;
  };

  // Create a value object with all the auth context
  const value = {
    user,
    token,
    loading,
    login,
    logout,
    refreshToken,
    isAuthenticated,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use the auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext; 