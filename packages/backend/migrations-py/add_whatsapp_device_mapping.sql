-- Migration: Add WhatsApp Device Mapping for Admin Tenant
-- Purpose: Enable QR code generation for the system admin dashboard
-- Date: 2026-02-17

-- Step 1: Create whatsapp_devices table if it doesn't exist
CREATE TABLE IF NOT EXISTS whatsapp_devices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  device_id TEXT NOT NULL UNIQUE,
  device_name TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 2: Add foreign key constraint (if tenants table exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tenants') THEN
    ALTER TABLE whatsapp_devices
    ADD CONSTRAINT fk_whatsapp_devices_tenant
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
  END IF;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

-- Step 3: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_whatsapp_devices_tenant ON whatsapp_devices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_devices_device_id ON whatsapp_devices(device_id);

-- Step 4: Insert admin device mapping
INSERT INTO whatsapp_devices (tenant_id, device_id, device_name, is_active)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'w3j-admin-device',
  'W3J Admin WhatsApp',
  true
)
ON CONFLICT (device_id) DO UPDATE SET
  device_name = EXCLUDED.device_name,
  is_active = EXCLUDED.is_active,
  updated_at = NOW();

-- Step 5: Verify the insertion
SELECT
  id,
  tenant_id,
  device_id,
  device_name,
  is_active,
  created_at
FROM whatsapp_devices
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';
