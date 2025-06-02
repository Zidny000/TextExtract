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

      <Grid container  spacing={6} sx={{ my: 4 }} justifyContent="center">
        <Grid item size={10}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" gutterBottom>
              Extract Text From Anywhere on Your Screen
            </Typography>
            <Typography>
              Simply select an area on your screen and TextExtract instantly copies all visible text to your clipboard.
            </Typography>
          </Paper>
        </Grid>
        <Grid item size={10}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" gutterBottom>
              Copy to Clipboard Instantly
            </Typography>
            <Typography>
              No need to click “copy”—TextExtract puts extracted text right into your clipboard, ready to paste.
            </Typography>
          </Paper>
        </Grid>
        <Grid item size={10}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" gutterBottom>
              Supports Multiple Languages
            </Typography>
            <Typography>
              TextExtract is built with multilingual OCR capabilities—perfect for users around the world.
            </Typography>
          </Paper>
        </Grid>
        <Grid item size={10}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" gutterBottom>
              Accurate and Fast OCR with AI
            </Typography>
            <Typography>
              Powered by advanced AI technology for quick and reliable text extraction from images, PDFs, or apps.
            </Typography>
          </Paper>
        </Grid>
        <Grid item size={10}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" gutterBottom>
              Multi-Monitor Support
            </Typography>
            <Typography>
              Using more than one screen? Easily choose which monitor to capture from within the app.
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item size={10}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Typography variant="h5" gutterBottom>
              Secure & Private
            </Typography>
            <Typography>
              Your data is processed securely and never get stored in the system. Your privacy
              is our top priority.
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default LandingPage; 