-- Device Session Schema Migration
-- Purpose: Add multi-tenant device session support for WhatsApp GOWA integration
-- Run this in Supabase SQL Editor

-- Step 1: Add device-related columns to tenants table
ALTER TABLE tenants 
ADD COLUMN IF NOT EXISTS device_id TEXT,
ADD COLUMN IF NOT EXISTS whatsapp_jid TEXT,
ADD COLUMN IF NOT EXISTS session_active BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS session_connected_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ;

-- Step 2: Create device_sessions table for multi-device management
CREATE TABLE IF NOT EXISTS device_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    device_id TEXT NOT NULL UNIQUE,
    whatsapp_jid TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'disconnected', 'expired')),
    qr_code_url TEXT,
    qr_expires_at TIMESTAMPTZ,
    connected_at TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 3: Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_device_sessions_device_id ON device_sessions(device_id);
CREATE INDEX IF NOT EXISTS idx_device_sessions_tenant_id ON device_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_device_sessions_status ON device_sessions(status);
CREATE INDEX IF NOT EXISTS idx_tenants_device_id ON tenants(device_id);

-- Step 4: Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create trigger for auto-updating updated_at
DROP TRIGGER IF EXISTS update_device_sessions_updated_at ON device_sessions;
CREATE TRIGGER update_device_sessions_updated_at
    BEFORE UPDATE ON device_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Step 6: Enable RLS on device_sessions table
ALTER TABLE device_sessions ENABLE ROW LEVEL SECURITY;

-- Step 7: Add RLS policies for device_sessions table

-- Allow service role full access
DROP POLICY IF EXISTS "Allow service role full access to device_sessions" ON device_sessions;
CREATE POLICY "Allow service role full access to device_sessions"
    ON device_sessions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Allow authenticated users to view their own device sessions
DROP POLICY IF EXISTS "Users can view their own device sessions" ON device_sessions;
CREATE POLICY "Users can view their own device sessions"
    ON device_sessions
    FOR SELECT
    TO authenticated
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE owner_id = auth.uid()
        )
    );

-- Verification queries (optional, uncomment to check)
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'tenants' AND column_name LIKE '%device%';
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'device_sessions';
-- SELECT COUNT(*) as device_session_count FROM device_sessions;
