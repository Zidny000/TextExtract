import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Container, Typography, Box, Paper, CircularProgress, Button 
} from '@mui/material';
import { CheckCircle as CheckIcon } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import StripeService from '../services/StripeService';

const SubscriptionSuccess = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { authUser, axiosAuth } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (axiosAuth.defaults.headers.common['Authorization']) {
      const token = axiosAuth.defaults.headers.common['Authorization'].split(' ')[1];
      const csrf_token = axiosAuth.defaults.headers.common['X-CSRF-TOKEN'];
      StripeService.setAuthToken(token);
      StripeService.setCsrfToken(csrf_token);
    }
    // Process Stripe payment confirmation
    const processPayment = async () => {
      try {
        setLoading(true);
        
        // Get URL parameters
        const queryParams = new URLSearchParams(location.search);
        const sessionId = queryParams.get('session_id');
        
        if (!sessionId) {
          setError('Invalid payment information. Missing required parameters.');
          return;
        }
        
        // Verify the payment with our backend
        const result = await StripeService.verifyPayment(sessionId);
        
        if (result.success) {
          setSuccess(true);
        } else {
          setError('Unable to verify payment. Please contact support.');
        }
      } catch (error) {
        console.error('Payment verification error:', error);
        setError('Failed to verify payment. Please contact support.');
      } finally {
        setLoading(false);
      }
    };
    
    if (authUser) {
      processPayment();
    }
  }, [location.search, authUser, axiosAuth]);
  
  const handleContinue = () => {
    navigate('/subscription');
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 8 }}>
        <Paper elevation={3} sx={{ p: 4, textAlign: 'center' }}>
          {loading ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4 }}>
              <CircularProgress size={60} sx={{ mb: 3 }} />
              <Typography variant="h5">Processing your payment...</Typography>
              <Typography color="textSecondary" sx={{ mt: 2 }}>
                This will only take a moment. Please don't close this page.
              </Typography>
            </Box>
          ) : error ? (
            <Box sx={{ py: 4 }}>
              <Typography variant="h5" color="error" gutterBottom>
                Payment Error
              </Typography>
              <Typography variant="body1" paragraph>
                {error}
              </Typography>
              <Button 
                variant="contained" 
                color="primary" 
                onClick={handleContinue}
                sx={{ mt: 2 }}
              >
                Return to Subscription Page
              </Button>
            </Box>
          ) : (
            <Box sx={{ py: 4 }}>
              <CheckIcon color="success" sx={{ fontSize: 60, mb: 2 }} />
              <Typography variant="h4" gutterBottom>
                Payment Successful!
              </Typography>
              <Typography variant="body1" paragraph>
                Thank you for your purchase. Your account has been upgraded successfully.
              </Typography>
              <Button 
                variant="contained" 
                color="primary" 
                onClick={handleContinue}
                sx={{ mt: 2 }}
              >
                Go to My Subscription
              </Button>
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default SubscriptionSuccess;
