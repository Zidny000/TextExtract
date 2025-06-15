# TextExtract Backend

This is the backend service for TextExtract, an OCR application that extracts text from images.

## Setup Instructions

### Prerequisites
- Python 3.8+
- Supabase account with project created

### Environment Setup

1. Create a virtual environment:
   ```
   python -m venv myenv
   ```

2. Activate the virtual environment:
   - Windows: `myenv\Scripts\activate`
   - Linux/Mac: `source myenv/bin/activate`

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your `.env` file:
   - Copy the `.env.example` file to `.env` (if not already present)
   - Fill in your API keys and configuration values

### Database Setup

The application uses Supabase for database storage. You need to create the required tables:

1. Log in to your Supabase dashboard
2. Go to the SQL Editor
3. Run the SQL script in `database/create_tables.sql` to create all required tables
4. Alternatively, you can create the tables manually through the Table Editor UI

### Running the Server

1. Make sure your virtual environment is activated
2. Start the server:
   ```
   python app.py
   ```
3. The server will start on port 5000 by default (configurable in `.env`)

## API Endpoints

- `/` - Health check endpoint
- `/api/ocr` - Authenticated OCR endpoint
- `/api/ocr-legacy` - Legacy OCR endpoint (to be deprecated)
- `/api/auth/register` - User registration
- `/api/auth/login` - User login

## Environment Variables

- `TOGETHER_API_KEY` - API key for Together.ai
- `PORT` - Port to run the server on
- `SUPABASE_URL` - URL of your Supabase project
- `SUPABASE_KEY` - API key for Supabase
- `JWT_SECRET` - Secret for JWT token generation
- `DATABASE_URL` - Direct database connection string (for advanced usage)

## Troubleshooting

If you see a "relation does not exist" error, it means your database tables have not been created. Follow the Database Setup instructions above to create the tables in Supabase. 