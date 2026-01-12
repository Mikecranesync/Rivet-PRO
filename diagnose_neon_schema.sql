-- DIAGNOSTIC QUERIES - Run these in Neon SQL Editor

-- 1. Check which SCHEMA the ralph tables are in
SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_name LIKE 'ralph_%'
ORDER BY table_schema, table_name;

-- 2. Check current database and search_path
SELECT current_database(), current_schema();

-- 3. Show all schemas
SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name;

-- 4. Check table ownership and permissions
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE tablename LIKE 'ralph_%';

-- 5. Grant explicit permissions (run this if tables exist but n8n can't access)
GRANT USAGE ON SCHEMA public TO neondb_owner;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO neondb_owner;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO neondb_owner;

-- 6. Set search_path if needed
ALTER DATABASE neondb SET search_path TO public;

-- 7. Verify ralph_executions specifically
SELECT EXISTS (
    SELECT FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename = 'ralph_executions'
) as ralph_executions_exists;
