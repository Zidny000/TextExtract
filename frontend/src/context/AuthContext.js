import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import axios from 'axios';
import { jwtDecode } from "jwt-decode";

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const TOKEN_KEY = 'textextract_token';
const REFRESH_TOKEN_KEY = 'textextract_refresh_token';
const USER_KEY = 'textextract_user';
const CSRF_TOKEN_KEY = 'textextract_csrf_token';

// Create a new axios instance to handle auth interceptors
const axiosAuth = axios.create({
  baseURL: API_URL,
});

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [csrfToken, setCsrfToken] = useState(null);
  const [refreshingToken, setRefreshingToken] = useState(false);
  
  // Generate a CSRF token
  const generateCsrfToken = () => {
    const token = Math.random().toString(36).substring(2, 15) + 
                  Math.random().toString(36).substring(2, 15);
    localStorage.setItem(CSRF_TOKEN_KEY, token);
    setCsrfToken(token);
    
    // Add CSRF token to all non-GET requests
    axiosAuth.defaults.headers.common['X-CSRF-TOKEN'] = token;
    return token;
  };

  // Setup axios interceptor to handle token expiration
  const setupInterceptors = useCallback(() => {
    axiosAuth.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        
        // If error is 401 and we haven't already tried to refresh
        if (error.response?.status === 401 && !originalRequest._retry && refreshToken) {
          originalRequest._retry = true;
          
          // Try to refresh the token
          const refreshSuccess = await refreshAccessToken();
          
          if (refreshSuccess) {
            // Update the authorization header with the new token
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            // Retry the original request
            return axiosAuth(originalRequest);
          }
        }
        
        return Promise.reject(error);
      }
    );
  }, [token, refreshToken]);

  // Check if token is expired
  const isTokenExpired = (token) => {
    if (!token) return true;
    
    try {
      const decoded = jwtDecode(token);
      const currentTime = Date.now() / 1000;
      
      return decoded.exp < currentTime;
    } catch (error) {
      console.error('Error decoding token:', error);
      return true;
    }
  };

  // Refresh access token
  const refreshAccessToken = async () => {
    if (refreshingToken) return false;
    
    setRefreshingToken(true);
    
    try {
      if (!refreshToken) {
        return false;
      }
      
      const response = await axios.post(
        `${API_URL}/auth/refresh`,
        { refresh_token: refreshToken }
      );
      
      const newToken = response.data.token;
      
      // Update state
      setToken(newToken);
      
      // Update localStorage
      localStorage.setItem(TOKEN_KEY, newToken);
      
      // Update axios default headers
      axiosAuth.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      
      setRefreshingToken(false);
      return true;
    } catch (error) {
      console.error('Token refresh error:', error);
      
      // If refresh fails, log out
      logout();
      setRefreshingToken(false);
      return false;
    }
  };

  // Initialize auth state from local storage on component mount
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);
    const storedCsrfToken = localStorage.getItem(CSRF_TOKEN_KEY);

    if (storedToken && storedUser) {
      if (isTokenExpired(storedToken) && storedRefreshToken) {
        // Will attempt to refresh in setupInterceptors
        setRefreshToken(storedRefreshToken);
      } else {
        setToken(storedToken);
        // Set default Authorization header for all requests
        axiosAuth.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
      }
      
      setUser(JSON.parse(storedUser));
    }
    
    // Set CSRF token or generate a new one
    if (storedCsrfToken) {
      setCsrfToken(storedCsrfToken);
      axiosAuth.defaults.headers.common['X-CSRF-TOKEN'] = storedCsrfToken;
    } else {
      generateCsrfToken();
    }

    setLoading(false);
    
    // Return cleanup function
    return () => {
      axiosAuth.interceptors.response.eject();
    };
  }, []);

  // Setup interceptors when token or refreshToken changes
  useEffect(() => {
    setupInterceptors();
  }, [token, refreshToken, setupInterceptors]);


  const signup = async (email, password, fullName) => {
    try {
      const response = await axios.post(`${API_URL}/auth/register`, {
        email,
        password,
        full_name: fullName,
      });
      const { token, refresh_token, user } = response.data;
      // Save to state
      setToken(token);
      setRefreshToken(refresh_token);
      setUser(user);

      // Save to local storage
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.error || 'Signup failed' };
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axiosAuth.post(`${API_URL}/auth/login`, {
        email,
        password,
      });

      const { token, refresh_token, user } = response.data;

      // Save to state
      setToken(token);
      setRefreshToken(refresh_token);
      setUser(user);

      // Save to local storage
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      // Set default Authorization header for future requests
      axiosAuth.defaults.headers.common['Authorization'] = `Bearer ${token}`;

      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return { 
        success: false, 
        error: error.response?.data?.error || 'Login failed' 
      };
    }
  };

  const logout = async () => {
    try {
      // First, try server-side logout if we have valid tokens
      if (token && refreshToken && !isTokenExpired(token)) {
        try {
          await axiosAuth.post(`${API_URL}/auth/logout`, {
            refresh_token: refreshToken
          });
          console.log("Server-side logout successful");
        } catch (error) {
          // Log but continue with client-side logout
          console.error('Server-side logout failed:', error);
        }
      }
      
      // Proceed with client-side cleanup regardless of server response
      // Clear state
      setToken(null);
      setRefreshToken(null);
      setUser(null);

      // Clear localStorage
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);

      // Remove Authorization header
      delete axiosAuth.defaults.headers.common['Authorization'];
      
      // Generate a new CSRF token for security
      generateCsrfToken();

      return true;
    } catch (error) {
      console.error('Logout error:', error);
      return false;
    }
  };

  const isAuthenticated = () => {
    return !!token && !isTokenExpired(token);
  };

  // Create a value object with all the auth context
  const value = {
    user,
    token,
    loading,
    signup,
    login,
    logout,
    refreshAccessToken,
    isAuthenticated,
    axiosAuth,  // Provide the axios instance with interceptors
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