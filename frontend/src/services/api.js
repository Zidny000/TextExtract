import axios from 'axios';

// Get API URL based on environment
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Create a new axios instance with default configuration
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Set up CSRF protection for all requests
api.interceptors.request.use(config => {
  const csrfToken = localStorage.getItem('textextract_csrf_token');
  if (csrfToken && 
      config.method !== 'get' && 
      !config.url.startsWith('/auth/login') && 
      !config.url.startsWith('/auth/register') &&
      !config.url.startsWith('/auth/complete-web-login') &&
      !config.url.startsWith('/auth/request-password-reset')) {
    config.headers['X-CSRF-TOKEN'] = csrfToken;
  }
  return config;
});

export { api, API_URL };
