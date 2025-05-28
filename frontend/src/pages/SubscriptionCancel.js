import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Container, Typography, Box, Paper, Button 
} from '@mui/material';
import { Cancel as CancelIcon } from '@mui/icons-material';

const SubscriptionCancel = () => {
  const navigate = useNavigate();
  
  const handleGoBack = () => {
    navigate('/subscription');
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 8 }}>
        <Paper elevation={3} sx={{ p: 4, textAlign: 'center' }}>
          <Box sx={{ py: 4 }}>
            <CancelIcon color="action" sx={{ fontSize: 60, mb: 2 }} />
            <Typography variant="h4" gutterBottom>
              Payment Canceled
            </Typography>
            <Typography variant="body1" paragraph>
              You've canceled the payment process. No charges have been applied to your account.
            </Typography>
            <Typography variant="body1" paragraph>
              If you have any questions or concerns about our subscription plans, please feel free to contact our support team.
            </Typography>
            <Button 
              variant="contained" 
              color="primary" 
              onClick={handleGoBack}
              sx={{ mt: 2 }}
            >
              Return to Subscription Page
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default SubscriptionCancel;
