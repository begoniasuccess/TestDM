DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'main') THEN
      CREATE DATABASE main;
   END IF;
END
$$;