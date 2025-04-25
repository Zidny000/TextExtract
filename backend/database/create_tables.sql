-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'active',
    plan_type VARCHAR(50) DEFAULT 'free',
    subscription_id VARCHAR(255),
    subscription_start_date TIMESTAMP WITH TIME ZONE,
    subscription_end_date TIMESTAMP WITH TIME ZONE,
    max_requests_per_day INTEGER DEFAULT 50,
    email_verified BOOLEAN DEFAULT FALSE
);

-- Create api_requests table
CREATE TABLE IF NOT EXISTS api_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    request_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'success',
    response_time_ms INTEGER,
    error_message TEXT,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    ip_address VARCHAR(50),
    user_agent TEXT,
    device_info JSONB,
    is_billable BOOLEAN DEFAULT TRUE
);

-- Create devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    device_identifier VARCHAR(255) NOT NULL,
    device_name VARCHAR(255),
    device_type VARCHAR(50),
    os_name VARCHAR(50),
    os_version VARCHAR(50),
    app_version VARCHAR(50),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    UNIQUE(user_id, device_identifier)
);

-- Create usage_stats table
CREATE TABLE IF NOT EXISTS usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    date DATE NOT NULL,
    requests_count INTEGER DEFAULT 0,
    total_response_time_ms INTEGER DEFAULT 0,
    average_response_time_ms INTEGER DEFAULT 0,
    billable_requests_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    UNIQUE(user_id, date)
);

-- Create billing table
CREATE TABLE IF NOT EXISTS billing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    transaction_id VARCHAR(255),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'pending',
    payment_method VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    payment_date TIMESTAMP WITH TIME ZONE,
    billing_period_start DATE,
    billing_period_end DATE,
    invoice_url TEXT
);

-- Grant permissions on tables for service role and anon role
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow authenticated users to access their own data
CREATE POLICY users_policy ON users
    FOR ALL USING (auth.uid() = id);
    
CREATE POLICY api_requests_policy ON api_requests
    FOR ALL USING (auth.uid() = user_id);
    
CREATE POLICY devices_policy ON devices
    FOR ALL USING (auth.uid() = user_id);
    
CREATE POLICY usage_stats_policy ON usage_stats
    FOR ALL USING (auth.uid() = user_id);
    
CREATE POLICY billing_policy ON billing
    FOR ALL USING (auth.uid() = user_id); 