import os
import psycopg2
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def create_tables():
    """Create all required tables in the Supabase database using direct PostgreSQL connection"""
    
    # Get database connection
    USER = os.getenv("user")
    PASSWORD = os.getenv("password")
    HOST = os.getenv("host")
    PORT = os.getenv("portdb")
    DBNAME = os.getenv("dbname")
    
    logger.info(f"Connecting to database: {DBNAME}")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Read SQL file content - Use absolute path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file_path = os.path.join(current_dir, 'create_tables.sql')
        
        if not os.path.exists(sql_file_path):
            logger.error(f"SQL file not found at: {sql_file_path}")
            return False
            
        logger.info(f"Found SQL file at: {sql_file_path}")
        
        with open(sql_file_path, 'r') as sql_file:
            sql_script = sql_file.read()
        
        # Execute the SQL script
        logger.info("Executing SQL script...")
        cursor.execute(sql_script)
        
        # Close connection
        cursor.close()
        conn.close()
        
        logger.info("Database tables created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        return False

if __name__ == "__main__":
    # Run the script directly
    success = create_tables()
    if success:
        print("✅ Database setup completed successfully")
    else:
        print("❌ Database setup failed")

