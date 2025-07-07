import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import SignupPage from './pages/SignupPage';
import ProfilePage from './pages/ProfilePage';
import ChangePasswordPage from './pages/ChangePasswordPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import LogoutPage from './pages/LogoutPage';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import PublicOnlyRoute from './components/PublicOnlyRoute';
import SubscriptionPage from './pages/SubscriptionPage';
import SubscriptionSuccess from './pages/SubscriptionSuccess';
import SubscriptionCancel from './pages/SubscriptionCancel';
import ExampleComponent from './components/ExampleComponent';
import ToastProvider from './components/ui/toast-provider';


function App() {
  return (

      <AuthProvider>          
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              minHeight: '100vh',
            }}
          >
            <ToastProvider />
            <Navbar />
            <Box component="main" sx={{ flexGrow: 1 }}>
            <Routes>
              {/* Public routes accessible to everyone */}
              <Route path="/" element={<LandingPage />} />
              
              {/* Routes that should only be accessible when NOT logged in */}
              <Route 
                path="/login" 
                element={
                    <Login />
                } 
              />
              <Route 
                path="/signup" 
                element={
                  <PublicOnlyRoute>
                    <SignupPage />
                  </PublicOnlyRoute>
                } 
              />
              <Route 
                path="/forgot-password" 
                element={
                  <PublicOnlyRoute>
                    <ForgotPasswordPage />
                  </PublicOnlyRoute>
                } 
              />
              <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
              
              {/* UI Components Demo Route */}
              <Route path="/ui-components" element={<ExampleComponent />} />
              
              {/* Protected routes that require authentication */}
              <Route 
                path="/profile" 
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/change-password" 
                element={
                  <ProtectedRoute>
                    <ChangePasswordPage />
                  </ProtectedRoute>
                } 
              />
              <Route path="/logout" element={<LogoutPage />} />
              <Route 
                path="/subscription" 
                element={
                  <SubscriptionPage />
                } 
              />
              <Route 
                path="/subscription/success" 
                element={
                  <ProtectedRoute>
                    <SubscriptionSuccess />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/subscription/cancel" 
                element={
                  <SubscriptionCancel />
                } 
              />
              
              {/* Fallback route - redirect to landing page */}
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </Box>
          <Footer />
        </Box>
      </AuthProvider>
  );
}

export default App;
