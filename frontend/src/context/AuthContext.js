import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { api, API_URL } from '../services/api';
import { jwtDecode } from "jwt-decode";

const TOKEN_KEY = 'textextract_token';
const REFRESH_TOKEN_KEY = 'textextract_refresh_token';
const USER_KEY = 'textextract_user';
const CSRF_TOKEN_KEY = 'textextract_csrf_token';

// Use the API instance from our services
const axiosAuth = api;

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [authUser, setAuthUser] = useState(null);
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
    // Clear any existing interceptors
    axiosAuth.interceptors.response.eject(axiosAuth.interceptors.response.use(() => {}));
    
    axiosAuth.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        
        // If error is 401 and we haven't already tried to refresh
        if (error.response?.status === 401 && !originalRequest._retry && refreshToken) {
          originalRequest._retry = true;
          
          try {
            // Try to refresh the token
            const refreshSuccess = await refreshAccessToken();
            
            if (refreshSuccess) {
              // Update the authorization header with the new token
              originalRequest.headers['Authorization'] = `Bearer ${localStorage.getItem(TOKEN_KEY)}`;
              // Retry the original request
              return axiosAuth(originalRequest);
            }
          } catch (refreshError) {
            console.error("Error during token refresh:", refreshError);
            // Logout on refresh failure
            await logout();
            return Promise.reject(refreshError);
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
    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    try {
      if (!storedRefreshToken) {
        return false;
      }
      
      const response = await axiosAuth.post(
        `${API_URL}/auth/refresh`,
        { refresh_token: storedRefreshToken }
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
      logout()
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
    

    // Set CSRF token or generate a new one
    if (storedCsrfToken) {
      setCsrfToken(storedCsrfToken);
      axiosAuth.defaults.headers.common['X-CSRF-TOKEN'] = storedCsrfToken;
    } else {
      generateCsrfToken();
    }

    const initAuth = async () => {
      if (storedToken && storedRefreshToken) {
        setRefreshToken(storedRefreshToken);

        if (isTokenExpired(storedToken)) {
          // Token is expired, try to refresh it
        
          const refreshSuccess = await refreshAccessToken();
          if (!refreshSuccess) {
            // If refresh fails, clear everything
              logout()
          } else if (storedUser) {
            // If refresh succeeds, set user from storage
            try {
              setAuthUser(JSON.parse(storedUser));
            } catch (e) {
              console.error("Error parsing stored user:", e);
            }
          }
        } else {
          // Token is valid, set everything directly
          setToken(storedToken);
          axiosAuth.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
          
          if (storedUser) {
            try {
              setAuthUser(JSON.parse(storedUser));
            } catch (e) {
              console.error("Error parsing stored user:", e);
            }
          }
        }
      }
      
      setLoading(false);
    };

    initAuth();
    
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
      const response = await axiosAuth.post(`/auth/register`, {
        email,
        password,
        full_name: fullName,
      });

      // With the new flow, we just show a message to the user to check their email
      // We don't get tokens or user data until after email verification
      return { 
        success: true, 
        message: response.data.message || 'Please check your email to complete registration'
      };
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
      setAuthUser(user);

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
      setAuthUser(null);

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
    authUser,
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