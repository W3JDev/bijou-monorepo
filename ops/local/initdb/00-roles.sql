-- Align the Supabase service roles with the password this stack uses.
--
-- IMPORTANT: this file is mounted as a FILE directly into
-- /docker-entrypoint-initdb.d/, not as a directory. The postgres entrypoint
-- does not recurse — it logs "ignoring /docker-entrypoint-initdb.d/<dir>" and
-- moves on — so a directory mount silently never runs. That is exactly what
-- happened on the first attempt at this stack: GoTrue and PostgREST then
-- crash-looped with
--     FATAL: password authentication failed for user "authenticator"
--     FATAL: password authentication failed for user "supabase_auth_admin"
--
-- The `zz-` prefix on the mount target matters too: the supabase/postgres
-- image ships its own migrate.sh which creates anon / authenticated /
-- service_role / authenticator / supabase_auth_admin. This file must run
-- AFTER that, so it can ALTER what already exists rather than fight it.
--
-- Runs once, on an empty volume. `docker compose down -v` to re-run.

-- ── Passwords ─────────────────────────────────────────────────────────────
-- ALTER, not CREATE: the image already made these roles. An earlier version
-- of this file used CREATE ROLE guarded by IF NOT EXISTS, which meant the
-- guard always fired and the password was never set.
ALTER ROLE authenticator        WITH LOGIN PASSWORD 'postgres';
ALTER ROLE supabase_auth_admin  WITH LOGIN PASSWORD 'postgres';

-- ── Belt and braces for anything the image did not create ─────────────────
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon NOLOGIN NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOLOGIN NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    -- BYPASSRLS is what makes service_role behave like the cloud one. RLS was
    -- hardened to service-role-only (ops/_fix_rls_v6.js), so without it the
    -- app would be locked out of its own tables locally but not in production
    -- — the worst kind of environment difference to debug.
    CREATE ROLE service_role NOLOGIN NOINHERIT BYPASSRLS;
  END IF;
END
$$;

ALTER ROLE service_role WITH BYPASSRLS;
GRANT anon, authenticated, service_role TO authenticator;

-- ── Schemas ───────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS auth       AUTHORIZATION supabase_auth_admin;
CREATE SCHEMA IF NOT EXISTS storage;
CREATE SCHEMA IF NOT EXISTS extensions;

GRANT USAGE  ON SCHEMA public  TO anon, authenticated, service_role;
GRANT USAGE  ON SCHEMA storage TO anon, authenticated, service_role;
GRANT ALL    ON SCHEMA auth    TO supabase_auth_admin;
GRANT CREATE ON SCHEMA auth    TO supabase_auth_admin;

-- New tables in public reachable by the API roles by default, matching cloud
-- behaviour. RLS still governs what they can actually see.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON TABLES    TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON FUNCTIONS TO anon, authenticated, service_role;

-- ── Extensions the app relies on ──────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS "pgcrypto"  WITH SCHEMA extensions;
-- knowledge_chunks stores embeddings; requirements.txt pins pgvector.
CREATE EXTENSION IF NOT EXISTS "vector";
