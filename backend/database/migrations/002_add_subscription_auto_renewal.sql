-- Migration to add auto-renewal and payment status fields to subscriptions table
ALTER TABLE IF EXISTS subscriptions 
    ADD COLUMN IF NOT EXISTS auto_renewal BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) DEFAULT 'paid',
    ADD COLUMN IF NOT EXISTS last_payment_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS grace_period_end_date TIMESTAMP;

-- Migration to add payment_methods table if it doesn't exist
CREATE TABLE IF NOT EXISTS payment_methods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL, -- stripe, paypal, etc.
    provider_payment_id VARCHAR(255), -- external ID from payment provider
    card_last4 VARCHAR(4),
    card_brand VARCHAR(50),
    card_exp_month INT,
    card_exp_year INT,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Update or add status options to the subscription status enum
-- Note: You may need to adapt this based on your actual database setup
DO $$
BEGIN
    ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'payment_failed';
    ALTER TYPE subscription_status ADD VALUE IF NOT EXISTS 'expired';
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions (status);
CREATE INDEX IF NOT EXISTS idx_payment_methods_user_id ON payment_methods (user_id);
