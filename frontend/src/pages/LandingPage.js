import React from 'react';
import { Container, Typography, Box, Button, Grid, Paper } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const LandingPage = () => {
  const { user } = useAuth();

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4, textAlign: 'center' }}>
        <Typography variant="h2" component="h1" gutterBottom>
          Welcome to TextExtract
        </Typography>
        <Typography variant="h5" color="text.secondary" paragraph>
          Extract text from your screen with ease
        </Typography>
        {!user && (
          <Box sx={{ mt: 4 }}>
            <Button
              variant="contained"
              color="primary"
              size="large"
              component={RouterLink}
              to="/signup"
              sx={{ mr: 2 }}
            >
              Get Started
            </Button>
            <Button
              variant="outlined"
              color="primary"
              size="large"
              component={RouterLink}
              to="/login"
            >
              Login
            </Button>
          </Box>
        )}
      </Box>

      <Grid container spacing={4} sx={{ mt: 4 }}>
        <Grid item xs={12} md={4}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" gutterBottom>
              Easy to Use
            </Typography>
            <Typography>
              Simply upload your documents and let TextExtract do the work. Our advanced OCR technology
              ensures accurate text extraction every time.
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" gutterBottom>
              Multiple Formats
            </Typography>
            <Typography>
              Support for various document formats including PDF, images, and more. Extract text from
              any document with ease.
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" gutterBottom>
              Secure & Private
            </Typography>
            <Typography>
              Your documents are processed securely and never stored longer than necessary. Your privacy
              is our top priority.
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default LandingPage; 