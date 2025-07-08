import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Box, Typography, CircularProgress, Alert } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import StripeService from '../services/StripeService';
import { toast } from 'sonner';

function StripeSetup() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [setupIntent, setSetupIntent] = useState(null);
  const [stripeElements, setStripeElements] = useState(null);
  const [cardElement, setCardElement] = useState(null);
  const [processingPayment, setProcessingPayment] = useState(false);

  // Extract setupIntentId from URL if present
  const queryParams = new URLSearchParams(location.search);
  const setupIntentId = queryParams.get('setup_intent');

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!isAuthenticated) {
      navigate('/login?redirect=/stripe/setup');
      return;
    }

    // If setupIntentId is provided, verify it
    if (setupIntentId) {
      verifySetupIntent(setupIntentId);
    } else {
      // Otherwise initialize the stripe form
      initializeStripeForm();
    }
  }, [isAuthenticated, setupIntentId]);

  const initializeStripeForm = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Create setup intent
      const setupIntentResponse = await StripeService.createPaymentMethodUpdateSession();
      
      if (!setupIntentResponse.success) {
        throw new Error('Failed to create payment setup session');
      }
      
      // Load Stripe.js
      const stripe = await StripeService.loadStripeScript();
      const stripeInstance = stripe(await StripeService.getPublicKey());
      
      // Initialize Elements
      const elements = stripeInstance.elements({
        clientSecret: setupIntentResponse.client_secret,
      });
      
      // Create Card Element
      const card = elements.create('card');
      card.mount('#card-element');
      
      setStripeElements({
        stripe: stripeInstance,
        elements,
      });
      setCardElement(card);
      setSetupIntent(setupIntentResponse);
      setLoading(false);
      
    } catch (error) {
      console.error('Error initializing Stripe form:', error);
      setError('Failed to initialize payment form. Please try again.');
      setLoading(false);
    }
  };

  const verifySetupIntent = async (setupIntentId) => {
    try {
      setLoading(true);
      setError(null);
      
      // Verify the setup intent
      const verifyResponse = await StripeService.verifyPaymentMethodUpdate(setupIntentId);
      
      if (verifyResponse.success) {

        toast.success('Your payment method has been successfully saved.');
        
        // Redirect back to subscription page
        navigate('/subscription');
      } else {
        throw new Error(verifyResponse.error || 'Failed to verify payment method');
      }
      
    } catch (error) {
      console.error('Error verifying payment method:', error);
      setError('Failed to save payment method. Please try again.');
      setLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!stripeElements || !cardElement) {
      setError('Payment form not properly initialized');
      return;
    }
    
    try {
      setProcessingPayment(true);
      
      const { error } = await stripeElements.stripe.confirmSetup({
        elements: stripeElements.elements,
        confirmParams: {
          return_url: `${window.location.origin}/stripe/setup`,
        },
      });
      
      if (error) {
        throw error;
      }
      
      // The result will come via redirect and the verifySetupIntent function
      
    } catch (error) {
      console.error('Error confirming setup:', error);
      setError(error.message || 'Failed to process payment method');
      setProcessingPayment(false);
    }
  };

  return (
    <Box 
      sx={{ 
        maxWidth: 600, 
        mx: 'auto', 
        my: 4,
        p: 3,
        border: '1px solid #e0e0e0',
        borderRadius: 2,
        boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)'
      }}
    >
      <Typography variant="h5" component="h1" gutterBottom>
        Update Payment Method
      </Typography>
      
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {!loading && !error && (
        <form onSubmit={handleSubmit}>
          <Box sx={{ mb: 3 }}>
            <Typography variant="body1" gutterBottom>
              Please enter your card details:
            </Typography>
            
            <Box 
              id="card-element" 
              sx={{ 
                border: '1px solid #ccc',
                p: 2,
                borderRadius: 1
              }}
            />
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <button
              type="submit"
              disabled={processingPayment}
              style={{
                backgroundColor: '#3f51b5',
                color: 'white',
                padding: '10px 20px',
                border: 'none',
                borderRadius: '4px',
                cursor: processingPayment ? 'not-allowed' : 'pointer',
                fontSize: '16px',
                opacity: processingPayment ? 0.7 : 1
              }}
            >
              {processingPayment ? 'Processing...' : 'Save Card'}
            </button>
          </Box>
        </form>
      )}
    </Box>
  );
}

export default StripeSetup;
