import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Paper,
  Button,
  Grid,
  Divider,
  Alert,
  LinearProgress,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';

const ProfilePage = () => {
  const { user, logout, axiosAuth } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [usageStats, setUsageStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchUsageStats = async () => {
      try {
        setError('');
        const response = await axiosAuth.get('/users/profile');
        if (response.data && response.data.usage) {
          setUsageStats(response.data.usage);
        } else {
          setError('No usage data available');
        }
      } catch (error) {
        console.error('Error fetching usage stats:', error);
        setError('Failed to load usage statistics. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchUsageStats();
    }
  }, [user, axiosAuth]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (!user) {
    return null;
  }

  const getUsagePercentage = () => {
    if (!usageStats) return 0;
    return Math.min((usageStats.monthly_requests / usageStats.plan_limit) * 100, 100);
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          My Profile
        </Typography>
        {message && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {message}
          </Alert>
        )}
        <Paper elevation={3} sx={{ p: 3 }}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Account Information
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Typography>
                <strong>Name:</strong> {user.full_name}
              </Typography>
              <Typography>
                <strong>Email:</strong> {user.email}
              </Typography>
              <Typography>
                <strong>Plan:</strong> {user.plan_type.toUpperCase() || 'Free'}
              </Typography>
              <Typography>
                <strong>Status:</strong> {user.status || 'Active'}
              </Typography>
              <Typography>
                <strong>Email Verified:</strong> {user.email_verified ? 'Yes' : 'No'}
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Usage Statistics
              </Typography>
              <Divider sx={{ mb: 2 }} />
              {loading ? (
                <LinearProgress />
              ) : usageStats ? (
                <>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Montly API Requests
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Box sx={{ flexGrow: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={getUsagePercentage()}
                          sx={{ height: 10, borderRadius: 5 }}
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {usageStats.monthly_requests} / {usageStats.plan_limit}
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Remaining Requests
                    </Typography>
                    <Typography variant="h6">
                      {usageStats.remaining_requests}
                    </Typography>
                  </Box>
                </>
              ) : (
                <Typography color="error">{error || 'Failed to load usage statistics'}</Typography>
              )}
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Subscription
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Card variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="h5" gutterBottom>
                    {user.plan_type.toUpperCase()} PLAN
                  </Typography>
                  <List dense>
                    <ListItem>
                      <ListItemText 
                        primary="Monthly OCR Requests" 
                        secondary={usageStats?.plan_limit || "Loading..."}
                      />
                    </ListItem>
                    {usageStats?.renewal_date && (
                      <ListItem>
                        <ListItemText 
                          primary="Renewal Date" 
                          secondary={new Date(usageStats.renewal_date).toLocaleDateString()}
                        />
                      </ListItem>
                    )}
                  </List>
                  <Button 
                    variant="contained" 
                    color="primary"
                    onClick={() => navigate('/subscription')}
                    sx={{ mt: 2 }}
                  >
                    {user.plan_type === 'free' ? 'Upgrade Plan' : 'Manage Subscription'}
                  </Button>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Account Actions
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={() => navigate('/change-password')}
                >
                  Change Password
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={handleLogout}
                >
                  Logout
                </Button>
              </Box>
            </Grid>
          </Grid>
        </Paper>
      </Box>
    </Container>
  );
};

export default ProfilePage;