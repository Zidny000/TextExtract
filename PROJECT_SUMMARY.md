# TextExtract Project Summary

TextExtract is a micro SaaS application for extracting text from screen captures. The project is divided into three main components:

## 1. Desktop Application (src/)

The desktop application is the client software users install on their computers, enabling them to:
- Capture screenshots of selected areas
- Extract text using OCR from these captures 
- Copy extracted text to clipboard automatically
- Authenticate with the backend service

**Key Components:**
- `main.py`: Core application entry point managing UI, authentication, and tray icon
- `ocr.py`: Handles OCR processing via API calls to the backend
- `auth.py`: Manages user authentication, tokens, and secure credential storage
- `overlay.py`: Provides screen overlay for selection of capture areas
- `visual_control.py`: Implements floating icon and visual UI elements
- `clipboard.py`: Handles clipboard integration
- `monitor_selector.py`: Manages multi-monitor support

The application uses:
- Tkinter for UI components
- API calls to the backend for OCR and authentication
- Secure credential storage via keyring
- System tray integration for accessibility

## 2. Backend Server (backend/)

The backend server provides API services for:
- OCR processing (using Together.ai API)
- User authentication and management
- Subscription and billing management

**Key Components:**
- `app.py`: Main Flask application and server setup
- `routes/`: API endpoints organized by functionality
  - `auth_routes.py`: User registration, login, token management
  - `user_routes.py`: User profile management
  - `api_routes.py`: OCR and core service endpoints
  - `subscription_routes.py`: Subscription and plan management
  - `stripe_routes.py`: Stripe payment processing
- `database/`: Database models and connection handling
- `payment/`: Payment processing modules
  - `stripe_client.py`: Stripe API integration

Technologies:
- Flask web framework
- Supabase for database
- Together.ai for OCR processing
- JWT for authentication
- Stripe for payment processing
- PayPal for payment processing

## 3. Frontend Web Application (frontend/)

The web application provides the user portal for:
- Account management
- Subscription management
- Usage statistics
- Authentication

**Key Components:**
- React-based SPA with routing
- Material UI components for modern interface
- Pages including:
  - Landing page for marketing
  - Login/Signup flows
  - User profile management
  - Password reset functionality

## Project Architecture

The system follows a client-server architecture:
1. Desktop app captures screenshots and sends to backend
2. Backend authenticates users and processes OCR requests
3. Frontend web portal manages user accounts and subscriptions

## Authentication Flow

1. Users register/login through  web portal
2. Authentication tokens are securely stored on client devices
3. Every OCR request is authenticated with these tokens
4. Token refresh happens automatically when needed

## Business Model

This is a SaaS application with the following business model:
- Free tier with 20 OCR requests per month
- Basic tier with 200 OCR requests per month

## Payment Processing

The application supports multiple payment processors:
1. **Stripe Integration**:
   - Credit card payments using Stripe Checkout
   - Secure webhook processing for payment confirmations
   - Complete subscription management

2. **PayPal Integration**:
   - PayPal account payments
   - Direct payment processing

## Development Environment

- Backend: Python with Flask
- Frontend: React with Material UI
- Desktop App: Python with Tkinter
- OCR Processing: Together.ai API integration
- Database: Supabase (PostgreSQL) 