-- ============================================================================
-- WhatsApp Bridge Database Migration: Add tenant_id Support
-- ============================================================================
-- 
-- Problem: Bridge tables 'chats' and 'messages' are missing tenant_id column
-- Error: "SQL logic error: table chats has no column named tenant_id (1)"
--
-- This migration adds tenant_id to support multi-tenant WhatsApp sessions.
--
-- Run this against the WHATSAPP_DB_URL PostgreSQL database
-- ============================================================================

-- Step 1: Add tenant_id column to chats table
ALTER TABLE chats 
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

-- Step 2: Add tenant_id column to messages table  
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

-- Step 3: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_chats_tenant_id ON chats(tenant_id);
CREATE INDEX IF NOT EXISTS idx_messages_tenant_id ON messages(tenant_id);

-- Step 4: Update existing rows with default tenant ID (if any exist)
-- This assumes you have one existing tenant - update the UUID to match yours
UPDATE chats 
SET tenant_id = '87dcc712-1eb3-4772-a682-d74f67d13f92' 
WHERE tenant_id IS NULL;

UPDATE messages 
SET tenant_id = '87dcc712-1eb3-4772-a682-d74f67d13f92' 
WHERE tenant_id IS NULL;

-- Step 5: (Optional) Make tenant_id NOT NULL after backfilling
-- Uncomment these if you want to enforce tenant_id requirement:
-- ALTER TABLE chats ALTER COLUMN tenant_id SET NOT NULL;
-- ALTER TABLE messages ALTER COLUMN tenant_id SET NOT NULL;

-- ============================================================================
-- Verification Queries (run these after migration)
-- ============================================================================

-- Check chats table structure
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'chats';

-- Check messages table structure  
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns 
-- WHERE table_name = 'messages';

-- Check if existing data has tenant_id
-- SELECT tenant_id, COUNT(*) FROM chats GROUP BY tenant_id;
-- SELECT tenant_id, COUNT(*) FROM messages GROUP BY tenant_id;

-- ============================================================================
-- How to Run This Migration
-- ============================================================================
--
-- Option 1: Via Fly.io SSH (if psql is available):
--   flyctl ssh console -a whatsapp-bridge-staging-w3j
--   psql $WHATSAPP_DB_URL -f /path/to/this/file.sql
--
-- Option 2: Via Supabase SQL Editor (if using Supabase for bridge DB):
--   1. Copy the SQL above
--   2. Go to Supabase SQL Editor
--   3. Paste and run
--
-- Option 3: Via local psql (if you have the DB URL):
--   psql "postgres://..." -f migrations/bridge_add_tenant_id.sql
--
-- ============================================================================