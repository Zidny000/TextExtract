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

  // Extract parameters from URL if present
  const queryParams = new URLSearchParams(location.search);
  const setupIntentId = queryParams.get('setup_intent');
  const setupIntentClientSecret = queryParams.get('setup_intent_client_secret');
  const redirectResult = queryParams.get('redirect_status');

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!isAuthenticated) {
      navigate('/login?redirect=/stripe/setup');
      return;
    }

    // If redirected back from Stripe with a successful result, verify the payment
    if (setupIntentId && redirectResult === 'succeeded') {
      verifySetupIntent(setupIntentId);
    } else if (setupIntentClientSecret) {
      // If we have a client secret but no result yet, show the card form pre-populated
      initializeStripeFormWithClientSecret(setupIntentClientSecret);
    } else {
      // Otherwise initialize a new stripe form
      initializeStripeForm();
    }
  }, [isAuthenticated, setupIntentId, redirectResult, setupIntentClientSecret]);

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
      
      // Initialize Elements with the client secret
      const elements = stripeInstance.elements({
        clientSecret: setupIntentResponse.client_secret,
        appearance: {
          theme: 'stripe',
          variables: {
            colorPrimary: '#3f51b5',
          }
        }
      });
      
      // Create Payment Element instead of Card Element
      const paymentElement = elements.create('payment');
      
      // Store these in state so we can mount the payment element after rendering
      setStripeElements({
        stripe: stripeInstance,
        elements,
      });
      setCardElement(paymentElement);
      setSetupIntent(setupIntentResponse);
      setLoading(false);
      
    } catch (error) {
      console.error('Error initializing Stripe form:', error);
      setError('Failed to initialize payment form. Please try again.');
      setLoading(false);
    }
  };

  const initializeStripeFormWithClientSecret = async (clientSecret) => {
    try {
      setLoading(true);
      setError(null);
      
      // Load Stripe.js
      const stripe = await StripeService.loadStripeScript();
      const stripeInstance = stripe(await StripeService.getPublicKey());
      
      // Initialize Elements
      const elements = stripeInstance.elements({
        clientSecret: clientSecret,
        appearance: {
          theme: 'stripe',
          variables: {
            colorPrimary: '#3f51b5',
          }
        }
      });
      
      // Create Payment Element instead of Card Element
      const paymentElement = elements.create('payment');
      
      // Store these in state so we can mount the payment element after rendering
      setStripeElements({
        stripe: stripeInstance,
        elements,
      });
      setCardElement(paymentElement);
      setSetupIntent({ client_secret: clientSecret });
      setLoading(false);
      
    } catch (error) {
      console.error('Error initializing Stripe form with client secret:', error);
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
      
      // Confirm the setup with the Payment Element
      const { error, setupIntent } = await stripeElements.stripe.confirmSetup({
        elements: stripeElements.elements,
        confirmParams: {
          // Make sure we capture the setup intent ID when redirecting back
          return_url: `${window.location.origin}/stripe/setup?redirect_status={SETUP_INTENT_STATUS}&setup_intent={SETUP_INTENT_ID}`,
        },
        redirect: 'if_required',
      });
      
      if (error) {
        throw error;
      }
      
      // If there's no redirect needed, verify the setup intent immediately
      if (setupIntent && setupIntent.status === 'succeeded') {
        await verifySetupIntent(setupIntent.id);
      }
      // Otherwise, the result will come via redirect and the verifySetupIntent function
      
    } catch (error) {
      console.error('Error confirming setup:', error);
      setError(error.message || 'Failed to process payment method');
      setProcessingPayment(false);
    }
  };

  // Mount payment element when it's available and DOM is ready
  useEffect(() => {
    const mountPaymentElement = () => {
      if (cardElement && !loading && !error) {
        // Check if the element exists before mounting
        const paymentElementContainer = document.getElementById('card-element');
        if (paymentElementContainer) {
          // Unmount first if needed to prevent errors
          try {
            cardElement.unmount();
          } catch (e) {
            // Ignore errors from unmounting (it might not be mounted yet)
          }
          
          // Now mount to the DOM element
          setTimeout(() => {
            try {
              cardElement.mount('#card-element');
              console.log('Payment element mounted successfully');
            } catch (error) {
              console.error('Error mounting payment element:', error);
              setError('Failed to initialize payment form. Please try again.');
            }
          }, 100); // Small delay to ensure DOM is ready
        }
      }
    };

    mountPaymentElement();
  }, [cardElement, loading, error]);

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
      
      {/* Always render the form, but conditionally show buttons */}
      <form onSubmit={handleSubmit} style={{ display: !error ? 'block' : 'none' }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="body1" gutterBottom>
            Please enter your card details:
          </Typography>
          
          {/* Always render the card element container so it's in the DOM */}
          <Box 
            id="card-element" 
            sx={{ 
              border: '1px solid #ccc',
              p: 2,
              borderRadius: 1,
              minHeight: '40px',
              backgroundColor: loading ? '#f5f5f5' : 'transparent'
            }}
          />
        </Box>
        
        {!loading && (
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
        )}
      </form>
    </Box>
  );
}

export default StripeSetup;
