-- First, make sure RLS is enabled (it should be since we're getting RLS errors)
ALTER TABLE "public"."users" ENABLE ROW LEVEL SECURITY;

-- Drop the existing policy that's not working properly
DROP POLICY IF EXISTS "Enable insert for all users" ON "public"."users";

-- Create a new policy that explicitly allows inserts from anonymous users for registration
CREATE POLICY "Allow anonymous user registration" 
ON "public"."users"
FOR INSERT 
TO anon, authenticated
WITH CHECK (true);

-- Also add a policy to let users read only their own data
CREATE POLICY "Users can view their own data" 
ON "public"."users"
FOR SELECT 
TO authenticated
USING (auth.uid() = id);

-- Service role can do anything (if you're using service role for your backend)
CREATE POLICY "Service role can do anything" 
ON "public"."users"
TO service_role
USING (true) 
WITH CHECK (true); 