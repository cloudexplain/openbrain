-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create user and database if not exists (redundant but safe)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'secondbrain') THEN
        CREATE USER secondbrain WITH PASSWORD 'secondbrain_password';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE secondbrain TO secondbrain;
GRANT ALL ON SCHEMA public TO secondbrain;
GRANT CREATE ON SCHEMA public TO secondbrain;