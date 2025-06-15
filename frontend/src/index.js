import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

// Set up default axios configuration
axios.defaults.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
axios.defaults.headers.post['Content-Type'] = 'application/json';
axios.defaults.headers.put['Content-Type'] = 'application/json';
axios.defaults.headers.patch['Content-Type'] = 'application/json';

// Set up CSRF protection for all requests
axios.interceptors.request.use(config => {
  // Skip for GET requests and auth endpoints
  if (config.method === 'get' || 
      config.url.startsWith('/auth/login') || 
      config.url.startsWith('/auth/register') ||
      config.url.startsWith('/auth/refresh')) {
    return config;
  }
  
  // Add CSRF token from localStorage if available
  const csrfToken = localStorage.getItem('textextract_csrf_token');
  if (csrfToken) {
    config.headers['X-CSRF-TOKEN'] = csrfToken;
  }
  
  return config;
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
