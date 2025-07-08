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
  async createCheckoutSession(transactionId) {
    try {
      const response = await this.axiosInstance.post('/stripe/create-checkout', {
        transaction_id: transactionId
      });
      return response.data;
    } catch (error) {
      console.error('Error creating Stripe checkout session:', error);
      throw error;
    }
  }

  // Verify a successful Stripe payment
  async verifyPayment(sessionId, transactionId) {
    try {
      const response = await this.axiosInstance.get(`/stripe/success`, {
        params: {
          session_id: sessionId,
          transaction_id: transactionId
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
      const response = await this.axiosInstance.post('/stripe/create-setup-intent');
      return response.data;
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
}

export default new StripeService();
