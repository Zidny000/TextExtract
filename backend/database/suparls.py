import os
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime
import logging
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)


try:

    
    response = (
        supabase.table("users")
        .insert({
            "email": "ani@gmail.com",
            "password_hash": "password_hash",
            "full_name": "full_name",
         
        }).execute()

    )
    
    if len(response.data) > 0:
        print(response.data[0])
    
except Exception as e:
    logger.error(f"Error creating user: {str(e)}")
    raise

