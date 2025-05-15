import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Mock PayPal client for demo purposes
// In a real implementation, you would use the actual PayPal SDK
class PayPalClient {
  constructor() {
    this.isInitialized = false;
  }

  async initialize() {
    // Simulate PayPal SDK initialization
    return new Promise((resolve) => {
      setTimeout(() => {
        this.isInitialized = true;
        resolve(true);
      }, 1000);
    });
  }

  async createOrder(amount, currency = 'USD') {
    // Simulate creating a PayPal order
    return {
      id: `ORDER-${Math.random().toString(36).substring(2, 10)}`,
      status: 'CREATED',
      amount: {
        value: amount,
        currency_code: currency
      }
    };
  }

  async captureOrder(orderId) {
    // Simulate capturing a PayPal order
    return {
      id: orderId,
      status: 'COMPLETED',
      payer: {
        email_address: 'test@example.com'
      }
    };
  }
}

class PayPalService {
  constructor() {
    this.client = new PayPalClient();
    this.axiosInstance = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  // Set the authentication token for API requests
  setAuthToken(token) {
    this.axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  setCsrfToken(token) {
    this.axiosInstance.defaults.headers.common['X-CSRF-TOKEN'] = token
  }

  // Initialize PayPal client
  async initialize() {
    return this.client.initialize();
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

  // Initiate a subscription upgrade
  async initiateUpgrade(planId) {
    try {
      const response = await this.axiosInstance.post('/subscription/upgrade', {
        plan_id: planId
      });
      return response.data;
    } catch (error) {
      console.error('Error initiating subscription upgrade:', error);
      throw error;
    }
  }

  // Process a payment with PayPal
  async processPayment(transactionId, amount, currency = 'USD') {
    try {
      // Create a PayPal order
      const order = await this.client.createOrder(amount, currency);

      // Capture the order (in real implementation this would be done after user approval)
      const captureResult = await this.client.captureOrder(order.id);

      // Complete the payment in our backend
      const response = await this.axiosInstance.post('/subscription/complete-payment', {
        transaction_id: transactionId,
        paypal_order_id: captureResult.id,
        status: captureResult.status
      });

      return response.data;
    } catch (error) {
      console.error('Error processing payment:', error);
      throw error;
    }
  }

  // Get payment transaction history
  async getTransactions(limit = 10, offset = 0) {
    try {
      const response = await this.axiosInstance.get('/subscription/transactions', {
        params: { limit, offset }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching transactions:', error);
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
}

export default new PayPalService(); 