\set ON_ERROR_STOP on
-- Run as the database setup user. Local loopback trust is configured separately.
DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='tracey_web') THEN
 CREATE ROLE tracey_web LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
END IF; END $$;
GRANT supplytrace_app TO tracey_web;
