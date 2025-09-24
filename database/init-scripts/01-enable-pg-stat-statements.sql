
-- Enable pg_stat_statements extension (safe)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Try to set shared_preload_libraries if available (requires restart to take effect)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_settings WHERE name = 'shared_preload_libraries') THEN
    PERFORM pg_catalog.set_config('shared_preload_libraries', 'pg_stat_statements', false);
  END IF;
END;
$$;

-- Reload config (may not apply shared_preload_libraries without restart)
SELECT pg_reload_conf();

-- Ensure extension exists
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Set pg_stat_statements.* parameters only if they exist
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_settings WHERE name = 'pg_stat_statements.max') THEN
    EXECUTE 'ALTER SYSTEM SET pg_stat_statements.max = ''10000''';
  END IF;

  IF EXISTS (SELECT 1 FROM pg_settings WHERE name = 'pg_stat_statements.track') THEN
    EXECUTE 'ALTER SYSTEM SET pg_stat_statements.track = ''all''';
  END IF;

  IF EXISTS (SELECT 1 FROM pg_settings WHERE name = 'pg_stat_statements.track_utility') THEN
    EXECUTE 'ALTER SYSTEM SET pg_stat_statements.track_utility = ''on''';
  END IF;
END;
$$;

-- Grant read stats role only if role exists
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'secondbrain') THEN
    GRANT pg_read_all_stats TO secondbrain;
  END IF;
END;
$$;

-- Create view for recent queries only if extension is present
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements') THEN
    EXECUTE $view$
      CREATE OR REPLACE VIEW recent_queries AS
      SELECT 
          query,
          calls,
          total_exec_time,
          mean_exec_time,
          max_exec_time,
          stddev_exec_time
      FROM pg_stat_statements
      ORDER BY max_exec_time DESC
      LIMIT 100;
    $view$;
  END IF;
END;
$$;
