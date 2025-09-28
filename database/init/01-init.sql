-- Initial database setup
-- This file is executed when the PostgreSQL container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The application will create the tables via SQLAlchemy
-- This file is for any initial SQL setup that needs to be done