import React from 'react';
import { Toaster } from 'sonner';

export default function ToastProvider() {
  return (
    <Toaster 
      position="top-right"
      richColors
      closeButton
      theme="system"
      toastOptions={{
        duration: 5000,
      }}
    />
  );
}
