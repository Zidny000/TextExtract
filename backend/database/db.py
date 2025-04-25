import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    logger.error("Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY environment variables.")
    raise ValueError("Supabase credentials not found")

try:
    supabase: Client = create_client(supabase_url, supabase_key)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise

def db_init():
    """
    Initialize database structure.
    
    This function checks if tables exist and tries to create them if they don't.
    It will first attempt direct database connection if tables are missing.
    """
    try:
        # Check if tables exist by attempting to query them
        tables_to_check = ["users", "api_requests", "devices", "usage_stats", "billing"]
        tables_to_create = []
        
        for table in tables_to_check:
            try:
                # Attempt to query the table
                supabase.table(table).select("*", count="exact").limit(1).execute()
                logger.info(f"Table '{table}' exists")
            except Exception as e:
                logger.warning(f"Table '{table}' does not exist: {str(e)}")
                tables_to_create.append(table)
        
        # If all tables exist, we're done
        if not tables_to_create:
            logger.info("All database tables exist")
            return True
            
        logger.warning(f"Missing tables: {tables_to_create}")
        
        # Try to create tables using direct database connection
        try:
            from . import supabase_setup
            logger.info("Attempting to create tables using direct PostgreSQL connection...")
            
            if supabase_setup.create_tables():
                logger.info("Tables created successfully via direct connection")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create tables via direct connection: {str(e)}")
            
            # Provide instructions for manual creation if automatic creation fails
            logger.info("Please create the missing tables through the Supabase dashboard")
            logger.info("""
            To create tables manually, go to your Supabase dashboard:
            1. Navigate to 'SQL Editor'
            2. Copy and paste the content from database/create_tables.sql
            3. Run the SQL script
            
            Or use the SQL Editor to run the create_tables.sql script directly.
            """)
        
        # Return True to allow the application to continue (even if tables don't exist yet)
        return True
        
    except Exception as e:
        logger.error(f"Error checking database tables: {str(e)}")
        raise 