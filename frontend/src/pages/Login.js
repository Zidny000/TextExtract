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
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isDesktopAuth, setIsDesktopAuth] = useState(false);
  const [redirectParams, setRedirectParams] = useState(null);
  
  const location = useLocation();
  const navigate = useNavigate();
  const { login } = useAuth();

  // Check if this is a desktop authentication request by parsing query parameters
  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const redirectUri = queryParams.get('redirect_uri');
    const deviceId = queryParams.get('device_id');
    const state = queryParams.get('state');

    if (redirectUri) {
      setIsDesktopAuth(true);
      setRedirectParams({
        redirect_uri: redirectUri,
        device_id: deviceId,
        state: state
      });
    }
  }, [location]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
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
        
        // Redirect to dashboard after successful login
        if (authResponse.success) {
          navigate('/dashboard');
          return;
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to log in. Please try again.');
    } finally {
      setLoading(false);
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
              {loading ? <CircularProgress size={24} /> : 'Sign In'}
            </Button>
            <Grid container>
              <Grid item xs>
                <Link href="/forgot-password" variant="body2">
                  Forgot password?
                </Link>
              </Grid>
              <Grid item>
                <Link href="/signup" variant="body2">
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