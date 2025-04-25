-- Create a PostgreSQL function that uses SECURITY DEFINER to bypass RLS
-- This function needs to be run in the Supabase SQL Editor

CREATE OR REPLACE FUNCTION public.create_new_user(
  user_email TEXT,
  user_password_hash TEXT,
  user_full_name TEXT DEFAULT NULL,
  user_plan_type TEXT DEFAULT 'free'
) RETURNS SETOF public.users AS $$
DECLARE
  new_user public.users;
BEGIN
  INSERT INTO public.users (
    email, 
    password_hash, 
    full_name, 
    plan_type, 
    created_at, 
    updated_at
  ) VALUES (
    user_email,
    user_password_hash,
    user_full_name,
    user_plan_type,
    NOW(),
    NOW()
  ) RETURNING * INTO new_user;
  
  RETURN NEXT new_user;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 