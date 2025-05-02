import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Paper, 
  Typography, 
  TextField, 
  Button, 
  Grid, 
  Link, 
  Box, 
  CircularProgress, 
  Alert 
} from '@mui/material';
import { useLocation, useNavigate, Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import LoadingSpinner from '../components/LoadingSpinner';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loadingButton, setLoadingButton] = useState(false);
  const [error, setError] = useState('');
  const [isDesktopAuth, setIsDesktopAuth] = useState(false);
  const [redirectParams, setRedirectParams] = useState(null);
  
  const location = useLocation();
  const navigate = useNavigate();
  const { login, isAuthenticated, user, axiosAuth, loading } = useAuth();

  // Get the redirect URL from location state (if navigated from a protected route)
  const from = location.state?.from || '/profile';

  // Check if this is a desktop authentication request by parsing query parameters
  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const redirectUri = queryParams.get('redirect_uri');
    const deviceId = queryParams.get('device_id');
    const state = queryParams.get('state');
    console.log('redirectUri', redirectUri)
    if (redirectUri) {
      setIsDesktopAuth(true);
      setRedirectParams({
        redirect_uri: redirectUri,
        device_id: deviceId,
        state: state
      });
    }
    console.log('isAuthenticated', isAuthenticated())
    if(isAuthenticated() && isDesktopAuth) {
      alreadyLoggedIn();
    }
    if(isAuthenticated() && !isDesktopAuth) {
      navigate(from, { replace: true });
    }
  }, [location,loading]);


  const alreadyLoggedIn = async () => {
    const response = await axiosAuth.post(`${API_URL}/auth/direct-web-login`, {
      email:user.email,
      redirect_uri: redirectParams.redirect_uri,
      device_id: redirectParams.device_id,
      state: redirectParams.state
    });
    if (response.data.success && response.data.callback_url) {
      // Redirect to the callback URL which will be handled by the desktop app
      window.location.href = response.data.callback_url;
      return;
    }
  }

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoadingButton(true);
    setError('');

    try {
      if (isDesktopAuth && redirectParams) {
        // This is a desktop app authentication request
        const response = await axios.post(`${API_URL}/auth/complete-web-login`, {
          email,
          password,
          redirect_uri: redirectParams.redirect_uri,
          device_id: redirectParams.device_id,
          state: redirectParams.state
        });

        if (response.data.success && response.data.callback_url) {
          // Redirect to the callback URL which will be handled by the desktop app
          window.location.href = response.data.callback_url;
          return;
        }
      } else {
        // Regular web login
        const authResponse = await login(email, password);
        
        // Redirect to the intended page after successful login
        if (authResponse.success) {
          navigate(from, { replace: true });
          return;
        } else if (authResponse.error) {
          setError(authResponse.error);
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to log in. Please try again.');
    } finally {
      setLoadingButton(false);
    }
  };

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
          <Typography component="h1" variant="h5" align="center" gutterBottom>
            {isDesktopAuth ? 'TextExtract Desktop Authentication' : 'Sign in to your account'}
          </Typography>
          
          {isDesktopAuth && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Please log in to continue using TextExtract desktop application.
            </Alert>
          )}
          
          {/* Show a message if user was redirected from a protected page */}
          {location.state?.from && !isDesktopAuth && (
            <Alert severity="info" sx={{ mb: 2 }}>
              You need to log in to access that page.
            </Alert>
          )}
          
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          
          <Box component="form" onSubmit={handleLogin} sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="email"
              label="Email Address"
              name="email"
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type="password"
              id="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loadingButton ? <CircularProgress size={24} /> : 'Sign In'}
            </Button>
            <Grid container>
              <Grid item xs>
                <Link component={RouterLink} to="/forgot-password" variant="body2">
                  Forgot password?
                </Link>
              </Grid>
              <Grid item>
                <Link component={RouterLink} to="/signup" variant="body2">
                  Don't have an account? Sign Up
                </Link>
              </Grid>
            </Grid>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}

export default Login; 