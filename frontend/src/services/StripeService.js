import { sub } from 'date-fns';
import { api, API_URL } from './api';

class StripeService {
  constructor() {
    this.axiosInstance = api;
  }

  // Set the authentication token for API requests
  setAuthToken(token) {
    this.axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  setCsrfToken(token) {
    this.axiosInstance.defaults.headers.common['X-CSRF-TOKEN'] = token;
  }

  // Get Stripe public key
  async getPublicKey() {
    try {
      const response = await this.axiosInstance.get('/stripe/public-key');
      return response.data.publicKey;
    } catch (error) {
      console.error('Error fetching Stripe public key:', error);
      throw error;
    }
  }

  // Create a Stripe checkout session for a transaction
  async createCheckoutSession(stripePriceId, planId) {
    try {
      const response = await this.axiosInstance.post('/stripe/create-checkout', {
        stripe_price_id: stripePriceId,
        plan_id: planId
      });
      return response.data;
    } catch (error) {
      console.error('Error creating Stripe checkout session:', error);
      throw error;
    }
  }

  // Verify a successful Stripe payment
  async verifyPayment(sessionId) {
    try {
      const response = await this.axiosInstance.get(`/stripe/success`, {
        params: {
          session_id: sessionId,
        }
      });
      return response.data;
    } catch (error) {
      console.error('Error verifying Stripe payment:', error);
      throw error;
    }
  }

  // Load Stripe script
  loadStripeScript() {
    return new Promise((resolve, reject) => {
      if (window.Stripe) {
        resolve(window.Stripe);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://js.stripe.com/v3/';
      script.async = true;
      script.onload = () => resolve(window.Stripe);
      script.onerror = (error) => reject(new Error('Failed to load Stripe.js'));
      
      document.body.appendChild(script);
    });
  }

  // Initialize Stripe with public key
  async initStripe(publicKey) {
    try {
      const stripeJs = await this.loadStripeScript();
      return stripeJs(publicKey);
    } catch (error) {
      console.error('Error initializing Stripe:', error);
      throw error;
    }
  }

  // Redirect to Stripe Checkout
  redirectToCheckout(checkoutUrl) {
    window.location.href = checkoutUrl;
  }
  
  // Create a session to update payment method
  async createPaymentMethodUpdateSession() {
    try {
      // First notify the subscription service
      const response = await this.axiosInstance.post('/subscription/update-payment-method', {
        payment_provider: 'stripe'
      });
      
      if (response.data.success) {
        try {
          return response.data;
        } catch (setupError) {
          console.error('Error creating setup intent:', setupError);
          throw new Error('Failed to create payment setup intent');
        }
      } else {
        throw new Error('Failed to initialize payment method update');
      }
    } catch (error) {
      console.error('Error creating payment method update session:', error);
      throw error;
    }
  }
  
  // Verify a successful payment method update
  async verifyPaymentMethodUpdate(setupIntentId) {
    try {
      const response = await this.axiosInstance.post('/stripe/verify-setup-intent', {
        setup_intent_id: setupIntentId
      });
      return response.data;
    } catch (error) {
      console.error('Error verifying payment method update:', error);
      throw error;
    }
  }

  // Initiate a subscription upgrade
  async initiateUpgrade(subscriptionId, planId, autoRenewal = false) {
    try {
      const response = await this.axiosInstance.post('/subscription/upgrade', {
        subscription_id: subscriptionId,
        plan_id: planId,
        auto_renewal: autoRenewal
      });
      return response.data;
    } catch (error) {
      console.error('Error initiating subscription upgrade:', error);
      throw error;
    }
  }

  // Get all available subscription plans
  async getPlans() {
    try {
      const response = await this.axiosInstance.get('/subscription/plans');
      return response.data;
    } catch (error) {
      console.error('Error fetching subscription plans:', error);
      throw error;
    }
  }

  // Get current user plan details
  async getUserPlan() {
    try {
      const response = await this.axiosInstance.get('/subscription/user-plan');
      return response.data;
    } catch (error) {
      console.error('Error fetching user plan:', error);
      throw error;
    }
  }

  // Cancel a subscription
  async cancelSubscription() {
    try {
      const response = await this.axiosInstance.post('/subscription/cancel');
      return response.data;
    } catch (error) {
      console.error('Error cancelling subscription:', error);
      throw error;
    }
  }

  // Buy OCR credits
  async buyCredit(amount, price) {
    try {
      if (!amount || !price) {
        throw new Error('Amount and price are required to buy credits');
      }
      const response = await this.axiosInstance.post('/stripe/create-buy-credit-checkout', {
        amount,
        price
      });
      return response.data;
    } catch (error) {
      console.error('Error validating credit purchase:', error);
      throw error;
    }
    
  }
}

export default new StripeService();
