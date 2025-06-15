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
import PayPalService from '../services/PayPalService';
import StripeService from '../services/StripeService';

const SubscriptionPage = () => {
  const { user, axiosAuth } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [plans, setPlans] = useState([]);
  const [userPlan, setUserPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [upgradeStatus, setUpgradeStatus] = useState({ loading: false, success: false, error: '' });
  const [activeDialog, setActiveDialog] = useState({ open: false, planId: null, planName: '', price: 0 });
  const [paymentMethod, setPaymentMethod] = useState('paypal');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });  // Initialize payment services on component mount
  useEffect(() => {
    const initPaymentSystems = async () => {
      try {
        // Initialize PayPal
        await PayPalService.initialize();
        
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
            const userPlanData = await PayPalService.getUserPlan();
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
  }, [location.search, user]);
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
          PayPalService.setAuthToken(token);
          PayPalService.setCsrfToken(csrf_token);
          StripeService.setAuthToken(token);
          StripeService.setCsrfToken(csrf_token);
        }

        // Load subscription plans
        const plansData = await PayPalService.getPlans();
        setPlans(plansData);

        // Load user plan if logged in
        if (user) {
          const userPlanData = await PayPalService.getUserPlan();
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
  }, [user, axiosAuth.defaults.headers.common]);

  const handleUpgradeClick = (planId, planName, price) => {
    // Check if user is logged in before showing the payment dialog
    if (!user) {
      // Redirect to login page with return URL set to subscription page
      navigate('/login', { state: { from: '/subscription' } });
      return;
    }
    
    // If user is logged in, show the payment dialog
    setActiveDialog({
      open: true,
      planId,
      planName,
      price
    });
  };

  const handleDialogClose = () => {
    setActiveDialog({ ...activeDialog, open: false });
  };
  const handlePaymentMethodChange = (event, newValue) => {
    if (newValue !== null) {
      setPaymentMethod(newValue);
    }
  };

  const handleStripeCheckout = async (upgradeResponse) => {
    try {
      // Create Stripe checkout session
      const checkoutResponse = await StripeService.createCheckoutSession(upgradeResponse.transaction_id);
      
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
      // Initiate the upgrade process
      const upgradeResponse = await PayPalService.initiateUpgrade(activeDialog.planId);
      
      // If it's a free plan, we're done
      if (activeDialog.price === 0) {
        setUpgradeStatus({
          loading: false,
          success: true,
          error: ''
        });
        
        // Close the dialog
        setActiveDialog({ ...activeDialog, open: false });
        
        // Reload user plan
        const userPlanData = await PayPalService.getUserPlan();
        setUserPlan(userPlanData);
        
        return;
      }
      
      // Process payment based on selected payment method
      if (paymentMethod === 'stripe') {
        await handleStripeCheckout(upgradeResponse);
      } else {
        // For PayPal
        const paymentResponse = await PayPalService.processPayment(
          upgradeResponse.transaction_id,
          upgradeResponse.amount,
          upgradeResponse.currency
        );
        
        // Update status
        setUpgradeStatus({
          loading: false,
          success: true,
          error: ''
        });
        
        // Close the dialog
        setActiveDialog({ ...activeDialog, open: false });
        
        // Reload user plan

        
      }
      const userPlanData = await PayPalService.getUserPlan();
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
        await PayPalService.cancelSubscription();
        // Reload user plan
        const userPlanData = await PayPalService.getUserPlan();
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
                      primary={`${userPlan.plan.device_limit} devices allowed`} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <CheckIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText 
                      primary={`$${userPlan.plan.price.toFixed(2)}/${userPlan.plan.interval}`} 
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
                      secondary={userPlan.usage.status.toUpperCase()} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Requests This Month" 
                      secondary={`${userPlan.usage.month_requests} / ${userPlan.usage.max_requests} (${userPlan.usage.current_month})`} 
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Device Usage" 
                      secondary={`${userPlan.usage.device_count} / ${userPlan.usage.device_limit}`} 
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
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={handleCancelSubscription}
                >
                  Cancel Subscription
                </Button>
              </Box>
            )}
          </Paper>
        )}

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          Available Plans
        </Typography>

        <Grid container spacing={3}>
          {plans.map((plan) => (
            <Grid item xs={12} md={6} key={plan.id}>
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
                      /{plan.interval}
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
                    <ListItem>
                      <ListItemIcon>
                        <CheckIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText primary={`${plan.device_limit} devices allowed`} />
                    </ListItem>
                  </List>
                </CardContent>
                <CardActions>
                  <Button 
                    fullWidth 
                    variant="contained" 
                    endIcon={<ArrowIcon />}
                    disabled={userPlan && userPlan.plan.name === plan.name}
                    onClick={() => handleUpgradeClick(plan.id, plan.name, plan.price)}
                  >
                    {userPlan && userPlan.plan.name === plan.name ? 'Current Plan' : 'Purchase'}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>        {/* Upgrade Confirmation Dialog */}
        <Dialog open={activeDialog.open} onClose={handleDialogClose} maxWidth="sm" fullWidth>
          <DialogTitle>
            Upgrade to {activeDialog.planName.toUpperCase()}
          </DialogTitle>
          <DialogContent>
            <DialogContentText gutterBottom>
              {activeDialog.price > 0 ? (
                <>
                  You are about to upgrade to the {activeDialog.planName.toUpperCase()} plan for ${activeDialog.price.toFixed(2)}/month.
                </>
              ) : (
                <>
                  You are about to switch to the {activeDialog.planName.toUpperCase()} plan.
                </>
              )}
            </DialogContentText>
            
            {activeDialog.price > 0 && (
              <Box sx={{ mt: 3, mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Select Payment Method:
                </Typography>
                <ToggleButtonGroup
                  value={paymentMethod}
                  exclusive
                  onChange={handlePaymentMethodChange}
                  aria-label="payment method"
                  sx={{ width: '100%', mt: 1 }}
                >
                  <ToggleButton value="paypal" aria-label="PayPal" sx={{ width: '50%' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <img 
                        src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_37x23.jpg" 
                        alt="PayPal" 
                        style={{ height: 30, marginBottom: 8 }} 
                      />
                      <Typography variant="body2">PayPal</Typography>
                    </Box>
                  </ToggleButton>
                  <ToggleButton value="stripe" aria-label="Credit Card" sx={{ width: '50%' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <CreditCardIcon sx={{ fontSize: 30, mb: 1 }} />
                      <Typography variant="body2">Credit Card</Typography>
                    </Box>
                  </ToggleButton>
                </ToggleButtonGroup>
              </Box>
            )}
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
              {activeDialog.price > 0 ? 'Proceed to Payment' : 'Confirm'}
            </Button>
          </DialogActions>        </Dialog>

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