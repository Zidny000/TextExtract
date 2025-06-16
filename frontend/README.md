# TextExtract Frontend

This is the frontend application for TextExtract, a web application for extracting text from documents.

## Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)

## Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:

For development (using local backend at http://localhost:5000):
```bash
npm run start:dev
```
or use the provided batch file:
```bash
start_dev.bat
```

For production (using deployed backend at https://textextract.onrender.com):
```bash
npm run start:prod
```
or use the provided batch file:
```bash
start_prod.bat
```

The application will run on http://localhost:3000

## Features

- User authentication (login/signup)
- Profile management
- Document text extraction
- Responsive design

## Technologies Used

- React
- Material-UI
- React Router
- Axios

## Backend Integration

The frontend is configured to communicate with the backend server using environment variables:

- Development mode: http://localhost:5000
- Production mode: https://textextract.onrender.com

## Building for Deployment

To build the application for deployment:

For development build:
```bash
npm run build:dev
```
or use the provided batch file:
```bash
build_dev.bat
```

For production build:
```bash
npm run build:prod
```
or use the provided batch file:
```bash
build_prod.bat
```

The build artifacts will be stored in the `build/` directory.
