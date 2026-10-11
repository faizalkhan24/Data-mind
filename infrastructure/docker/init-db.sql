-- DataMind PostgreSQL Initialization Script
-- Executed automatically on initial container volume creation

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Ensure target application database exists
SELECT 'CREATE DATABASE datamind'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'datamind')\gexec

\connect datamind;

-- Grant standard privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
