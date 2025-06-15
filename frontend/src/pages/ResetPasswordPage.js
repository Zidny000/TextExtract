import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Alert,
} from '@mui/material';
import axios from 'axios';

const ResetPasswordPage = () => {
  const navigate = useNavigate();
  const { token } = useParams();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      const response = await axios.post('http://localhost:5000/auth/reset-password', {
        token: token,
        new_password: password,
      });

      if (response.data.message) {
        setSuccess('Password has been reset successfully');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      }
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to reset password');
    }
  };

  if (!token) {
    return (
      <Container maxWidth="sm">
        <Box sx={{ my: 4 }}>
          <Alert severity="error">
            Invalid or missing reset token
          </Alert>
          <Button
            variant="contained"
            onClick={() => navigate('/login')}
            sx={{ mt: 2 }}
          >
            Back to Login
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="sm">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Reset Password
        </Typography>
        <Paper elevation={3} sx={{ p: 3 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          {success && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {success}
            </Alert>
          )}
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="New Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
            />
            <TextField
              fullWidth
              label="Confirm New Password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              margin="normal"
              required
            />
            <Box sx={{ mt: 2 }}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                fullWidth
              >
                Reset Password
              </Button>
            </Box>
          </form>
        </Paper>
      </Box>
    </Container>
  );
};

export default ResetPasswordPage; 