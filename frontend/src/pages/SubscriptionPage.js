import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Container, Box, Typography, Paper, Button, Grid, Divider,
  Alert, CircularProgress, Card, CardContent, CardActions,
  List, ListItem, ListItemText, ListItemIcon, Dialog, DialogTitle,
  DialogContent, DialogContentText, DialogActions, ToggleButtonGroup,
  ToggleButton, Snackbar, IconButton
} from '@mui/material';
import { CheckCircle as CheckIcon, ArrowForward as ArrowIcon,
         CreditCard as CreditCardIcon, Close as CloseIcon } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';

import StripeService from '../services/StripeService';

const SubscriptionPage = () => {
  const { authUser, axiosAuth } = useAuth();
  const [user, setUser] = useState(authUser);
  const navigate = useNavigate();
  const location = useLocation();
  const [plans, setPlans] = useState([]);
  const [userPlan, setUserPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [upgradeStatus, setUpgradeStatus] = useState({ loading: false, success: false, error: '' });
  const [activeDialog, setActiveDialog] = useState({ open: false, stripePriceId:'', planId: '', planName: '', price: 0});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [ocrCredits, setOcrCredits] = useState({
    amount: '100',
    price: 2.99
  });  // Initialize payment services on component mount

  useEffect(() => {
    const initPaymentSystems = async () => {
      try {
        
        // Set up Stripe
        if (axiosAuth.defaults.headers.common['Authorization']) {
          const token = axiosAuth.defaults.headers.common['Authorization'].split(' ')[1];
          const csrf_token = axiosAuth.defaults.headers.common['X-CSRF-TOKEN'];
          StripeService.setAuthToken(token);
          StripeService.setCsrfToken(csrf_token);
        }
      } catch (error) {
        console.error('Error initializing payment systems:', error);
        setError('Failed to initialize payment systems');
      }
    };

    initPaymentSystems();
  }, [axiosAuth.defaults.headers.common]);
  
  // Handle Stripe payment success
  useEffect(() => {
    // Check for Stripe payment success query parameters
    const query = new URLSearchParams(location.search);
    const sessionId = query.get('session_id');
    const transactionId = query.get('transaction_id');
    
    if (sessionId && transactionId && user) {
      const verifyStripePayment = async () => {
        try {
          setLoading(true);
          const verificationResult = await StripeService.verifyPayment(sessionId, transactionId);
          
          if (verificationResult.success) {
            // Refresh user plan
            const userPlanData = await StripeService.getUserPlan();
            setUserPlan(userPlanData);
            
            // Show success message
            setSnackbar({
              open: true, 
              message: 'Payment successful! Your subscription has been updated.',
              severity: 'success'
            });
            
            // Clean up URL
            window.history.replaceState({}, document.title, '/subscription');
          }
        } catch (error) {
          console.error('Error verifying Stripe payment:', error);
          setSnackbar({
            open: true, 
            message: 'Failed to verify payment. Please contact support.',
            severity: 'error'
          });
        } finally {
          setLoading(false);
        }
      };
      
      verifyStripePayment();
    }
  }, [location.search, authUser]);
  // Load subscription plans and user plan
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError('');
      try {
        // Set auth tokens for services
        if (axiosAuth.defaults.headers.common['Authorization']) {
          const token = axiosAuth.defaults.headers.common['Authorization'].split(' ')[1];
          const csrf_token = axiosAuth.defaults.headers.common['X-CSRF-TOKEN']
          StripeService.setAuthToken(token);
          StripeService.setCsrfToken(csrf_token);
        }

        // Load subscription plans
        const plansData = await StripeService.getPlans();
        setPlans(plansData);

        // Load user plan if logged in
        if (authUser) {
          const userPlanData = await StripeService.getUserPlan();
          setUserPlan(userPlanData);
        }
      } catch (error) {
        console.error('Error loading subscription data:', error);
        setError('Failed to load subscription information');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [authUser, axiosAuth.defaults.headers.common]);

  const handleUpgradeClick = (stripePriceId, planId, planName, price) => {
    // Check if user is logged in before showing the payment dialog
    if (!user) {
      // Redirect to login page with return URL set to subscription page
      navigate('/login', { state: { from: '/subscription' } });
      return;
    }
    
    // If user is logged in, show the payment dialog
    setActiveDialog({
      open: true,
      stripePriceId,
      planId,
      planName,
      price
    });
  };

  const handleDialogClose = () => {
    setActiveDialog({ ...activeDialog, open: false });
  };

  const handleStripeCheckout = async (stripePriceId, planId) => {
    try {
      // Create Stripe checkout session
      const checkoutResponse = await StripeService.createCheckoutSession(stripePriceId, planId);

      if (checkoutResponse.success) {
        // Redirect to Stripe checkout
        StripeService.redirectToCheckout(checkoutResponse.checkout_url);
      } else {
        throw new Error('Failed to create Stripe checkout session');
      }
    } catch (error) {
      console.error('Stripe checkout error:', error);
      setUpgradeStatus({
        loading: false,
        success: false,
        error: 'Failed to redirect to payment page. Please try again.'
      });
    }
  };

  const handleUpgradeConfirm = async () => {
    setUpgradeStatus({ loading: true, success: false, error: '' });
    try {
      // Get auto-renewal setting if applicable
      const autoRenewal = userPlan?.usage?.auto_renewal ?? false;
      
      // Initiate the upgrade process
     

      // If it's a free plan, we're done
      if (activeDialog.price === 0) {
         // Initiate the upgrade process
      await StripeService.initiateUpgrade(userPlan.usage.subscription_id, activeDialog.planId, autoRenewal);
        setUpgradeStatus({
          loading: false,
          success: true,
          error: ''
        });
        
        // Close the dialog
        setActiveDialog({ ...activeDialog, open: false });
        
        // Reload user plan
        const userPlanData = await StripeService.getUserPlan();
        setUserPlan(userPlanData);
        
        return;
      }
      
      // Process payment based on selected payment method
      await handleStripeCheckout(activeDialog.stripePriceId, activeDialog.planId);

      const userPlanData = await StripeService.getUserPlan();
      setUserPlan(userPlanData);
      
    } catch (error) {
      console.error('Error upgrading subscription:', error);
      setUpgradeStatus({
        loading: false,
        success: false,
        error: 'Failed to process subscription upgrade. Please try again.'
      });
    }
  };

  const handleCancelSubscription = async () => {
    if (window.confirm('Are you sure you want to cancel your subscription? You will be downgraded to the free plan.')) {
      try {
        setLoading(true);
        await StripeService.cancelSubscription();
        // Reload user plan
        const userPlanData = await StripeService.getUserPlan();
        setUserPlan(userPlanData);
        alert('Subscription cancelled successfully');
      } catch (error) {
        console.error('Error cancelling subscription:', error);
        setError('Failed to cancel subscription');
      } finally {
        setLoading(false);
      }
    }
  };


  const handleUpdatePaymentMethod = async () => {
    setUpgradeStatus({ loading: true, success: false, error: '' });
    try {
      // Process payment method update based on selected payment method
   
      // Create a session to update payment method
      const updateResponse = await StripeService.createPaymentMethodUpdateSession();
      
      if (updateResponse.success) {
        // Redirect to Stripe to update payment method
        StripeService.redirectToCheckout(updateResponse.checkout_url);
      } else {
        throw new Error('Failed to create payment method update session');
      }
      
      // Reset upgrade status
      setUpgradeStatus({
        loading: false,
        success: true,
        error: ''
      });
    } catch (error) {
      console.error('Error updating payment method:', error);
      setUpgradeStatus({
        loading: false,
        success: false,
        error: 'Failed to update payment method. Please try again.'
      });
    }
  };

  const buyCreditRequest = async () => {
    try{
      const amount = ocrCredits.amount;
      const price = ocrCredits.price;
      // Check if user is logged in
      if (!authUser) {
        navigate('/login', { state: { from: '/subscription' } });
        return;
      }
      console.log(amount,price)
      setUpgradeStatus({ loading: true, success: false, error: '' });

      // Create Stripe checkout session
      const checkoutResponse = await StripeService.buyCredit(amount, price);

      if (checkoutResponse.success) {
        // Redirect to Stripe checkout
        StripeService.redirectToCheckout(checkoutResponse.checkout_url);
      } else {
        throw new Error('Failed to create Stripe checkout session');
      }
      // Reset upgrade status
      setUpgradeStatus({
        loading: false,
        success: true,
        error: ''
      });
    } catch (error) {
      console.error('Error buying OCR credits:', error);
      setUpgradeStatus({
        loading: false,
        success: false,
        error: 'Failed to purchase OCR credits. Please try again.'
      });
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md">
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 8 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Subscription Plans
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {upgradeStatus.success && (
          <Alert severity="success" sx={{ mb: 3 }}>
            Subscription upgraded successfully!
          </Alert>
        )}
        
        {userPlan && userPlan.usage.status === 'expired' && (
          <Alert severity="error" sx={{ mb: 3 }}>
            Your subscription has expired! {userPlan.usage.in_grace_period ? 
              'You are currently in the grace period, but you will lose access soon. Please renew your subscription to avoid interruption.' : 
              'Please renew your subscription to continue using the service.'}
          </Alert>
        )}
        
        {userPlan && userPlan.usage.status === 'payment_failed' && (
          <Alert severity="error" sx={{ mb: 3 }}>
            Your last payment attempt failed. Please update your payment method to continue using the service.
          </Alert>
        )}

        {userPlan && (
          <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
            <Typography variant="h6" gutterBottom>
              Your Current Plan: {userPlan.plan.name.toUpperCase()}
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle1" gutterBottom>
                  Plan Details
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemIcon>
                      <CheckIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText 
                      primary={`${userPlan.plan.max_requests_per_month} OCR requests per month`} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <CheckIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText 
                      primary={`$${userPlan.plan.price.toFixed(2)}/month`} 
                    />
                  </ListItem>
                </List>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle1" gutterBottom>
                  Usage Statistics
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText 
                      primary="Status" 
                      secondary={
                        <Box sx={{ 
                        
                          color: userPlan.usage.status === 'active' ? 'success.main' : 
                                 userPlan.usage.status === 'past_due' ? 'error.main' : 
                                 userPlan.usage.status === 'free_tier' ? '#007FFF' : 'text.primary'
                        }}>
                          {userPlan.usage.status == 'past_due' ? 'PAST DUE ( Please complete payment within '+new Date(new Date(userPlan.usage.start_date).setDate(new Date(userPlan.usage.start_date).getDate() + 5)).toLocaleDateString()+' or Your subscription will be cancelled. Change the payment method if the current payment method fails to complete the payment )' : userPlan.usage.status == 'free_tier' ? 'FREE TIER' : userPlan.usage.status.toUpperCase()}
                        </Box>
                      } 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Requests Made" 
                      secondary={`${userPlan.usage.month_requests}`} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Credit OCR Requests" 
                      secondary={`${userPlan.usage.credit_requests}`} 
                    />
                  </ListItem>
                  {userPlan.usage.renewal_date && (
                    <ListItem>
                      <ListItemText 
                        primary="Next Renewal" 
                        secondary={new Date(userPlan.usage.renewal_date).toLocaleDateString()} 
                      />
                    </ListItem>
                  )}
                </List>
              </Grid>
            </Grid>

            {userPlan.plan.name !== 'free' && (
              <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
             
                
                <Button
                  variant="outlined"
                  color="primary"
                  onClick={handleUpdatePaymentMethod}
                >
                  Manage Subscription
                </Button>
              </Box>
            )}
          </Paper>
        )}

        {/* Credit OCR Requests Box */}
        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          Credit OCR Requests
        </Typography>
        <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ mb: { xs: 2, md: 0 }, width: { xs: '100%', md: 'auto' } }}>
              <Typography variant="h6" gutterBottom>
                Purchase Additional OCR Credits
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Need more OCR requests? Purchase additional credits anytime.
              </Typography>
              
              {/* OCR Credit Packages Dropdown */}
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Box sx={{ minWidth: 120, mr: 2 }}>
                  <select 
                    className="MuiSelect-root"
                    style={{ 
                      padding: '10px', 
                      borderRadius: '4px', 
                      border: '1px solid #ccc',
                      width: '100%',
                      backgroundColor: 'transparent'
                    }}
                    value={ocrCredits.amount}
                    onChange={(e) => {
                      const amount = e.target.value;
                      let price = 2.99;
                      
                      if (amount === '200') price = 5.99;
                      else if (amount === '300') price = 7.99;
                      
                      setOcrCredits({ amount, price });
                    }}
                  >
                    <option value="100">100 OCR Requests</option>
                    <option value="200">200 OCR Requests</option>
                    <option value="300">300 OCR Requests</option>
                  </select>
                </Box>
                <Typography variant="h5" color="primary">
                  ${ocrCredits.price.toFixed(2)}
                </Typography>
              </Box>
            </Box>
            
            <Button 
              variant="contained" 
              color="primary" 
              size="large"
              endIcon={<CreditCardIcon />}
              sx={{ 
                mt: { xs: 2, md: 0 },
                width: { xs: '100%', md: 'auto' } 
              }}
              onClick={buyCreditRequest}
            >
              Buy Now
            </Button>
          </Box>
        </Paper>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          Available Plans
        </Typography>

        <Grid container spacing={3} sx={{ flexWrap: 'nowrap', overflowX: { xs: 'auto', md: 'visible' } }}>
          {plans.map((plan) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={plan.id} sx={{ minWidth: { xs: '90%', sm: 'auto' } }}>
              <Card 
                elevation={3}
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  borderColor: userPlan && userPlan.plan.name === plan.name ? 'primary.main' : 'transparent',
                  borderWidth: userPlan && userPlan.plan.name === plan.name ? 2 : 0,
                  borderStyle: 'solid'
                }}
              >
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h5" component="div" gutterBottom>
                    {plan.name.toUpperCase()}
                  </Typography>
                  <Typography variant="h4" color="primary" gutterBottom>
                    ${plan.price.toFixed(2)}
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                      / month
                    </Typography>
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {plan.description}
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <List dense>
                    <ListItem>
                      <ListItemIcon>
                        <CheckIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText primary={`${plan.max_requests_per_month} OCR requests per month`} />
                    </ListItem>
                  </List>
                </CardContent>
                <CardActions>
                  <Button 
                    fullWidth 
                    variant="contained" 
                    endIcon={ userPlan && userPlan.plan.name === plan.name ? null : <ArrowIcon />}
                    disabled={userPlan && userPlan.plan.name === plan.name}
                    onClick={() => handleUpgradeClick(plan.stripe_price_id, plan.id, plan.name, plan.price)}
                  >
                    {userPlan && userPlan.plan.name === plan.name ? 'Current Plan' : 'Subscribe'}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
        
        
        
        {/* Upgrade Confirmation Dialog */}
        <Dialog open={activeDialog.open} onClose={handleDialogClose} maxWidth="sm" fullWidth>
          <DialogTitle>
            {activeDialog.isPaymentUpdate ? 'Update Payment Method' : `Upgrade to ${activeDialog.planName.toUpperCase()}`}
          </DialogTitle>
          <DialogContent>
            <DialogContentText gutterBottom>
              {activeDialog.isPaymentUpdate ? (
                <>
                  Update your payment method for your {userPlan?.plan?.name?.toUpperCase()} subscription.
                </>
              ) : (
                <>
                  You are about to switch to the {activeDialog.planName.toUpperCase()} plan.
                </>
              )}
            </DialogContentText>
            
          </DialogContent>
          <DialogActions>
            <Button onClick={handleDialogClose} disabled={upgradeStatus.loading}>
              Cancel
            </Button>
            <Button 
              onClick={handleUpgradeConfirm}
              color="primary"
              variant="contained"
              disabled={upgradeStatus.loading}
              endIcon={upgradeStatus.loading ? <CircularProgress size={16} /> : null}
            >
              {activeDialog.isPaymentUpdate ? 'Update Payment Method' : 
               activeDialog.price > 0 ? 'Proceed to Payment' : 'Confirm'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          message={snackbar.message}
          action={
            <IconButton
              size="small"
              color="inherit"
              onClick={() => setSnackbar({ ...snackbar, open: false })}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          }
        />
      </Box>
    </Container>
  );
};

export default SubscriptionPage;
