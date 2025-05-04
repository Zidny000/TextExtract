import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container, Box, Typography, Paper, Button, Grid, Divider,
  Alert, CircularProgress, Card, CardContent, CardActions,
  List, ListItem, ListItemText, ListItemIcon, Dialog, DialogTitle,
  DialogContent, DialogContentText, DialogActions
} from '@mui/material';
import { CheckCircle as CheckIcon, ArrowForward as ArrowIcon } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import PayPalService from '../services/PayPalService';

const SubscriptionPage = () => {
  const { user, axiosAuth } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [userPlan, setUserPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [upgradeStatus, setUpgradeStatus] = useState({ loading: false, success: false, error: '' });
  const [activeDialog, setActiveDialog] = useState({ open: false, planId: null, planName: '', price: 0 });

  // Initialize PayPal on component mount
  useEffect(() => {
    const initPayPal = async () => {
      try {
        await PayPalService.initialize();
      } catch (error) {
        console.error('Error initializing PayPal:', error);
        setError('Failed to initialize payment system');
      }
    };

    initPayPal();
  }, []);

  // Load subscription plans and user plan
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError('');
      try {
        // Set auth token for PayPal service
        if (axiosAuth.defaults.headers.common['Authorization']) {
          const token = axiosAuth.defaults.headers.common['Authorization'].split(' ')[1];
          PayPalService.setAuthToken(token);
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
      
      // For paid plans, process the payment
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
                    {userPlan && userPlan.plan.name === plan.name ? 'Current Plan' : 'Upgrade'}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Upgrade Confirmation Dialog */}
        <Dialog open={activeDialog.open} onClose={handleDialogClose}>
          <DialogTitle>
            Upgrade to {activeDialog.planName.toUpperCase()}
          </DialogTitle>
          <DialogContent>
            <DialogContentText>
              {activeDialog.price > 0 ? (
                <>
                  You are about to upgrade to the {activeDialog.planName.toUpperCase()} plan for ${activeDialog.price.toFixed(2)}/month.
                  Your payment will be processed through PayPal.
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
              disabled={upgradeStatus.loading}
              endIcon={upgradeStatus.loading ? <CircularProgress size={16} /> : null}
            >
              Confirm
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  );
};

export default SubscriptionPage; 