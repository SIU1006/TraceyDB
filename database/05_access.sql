\set ON_ERROR_STOP on
-- Run as database owner with CREATEROLE. NOLOGIN role can be assigned to a deployment login.
DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='supplytrace_app') THEN CREATE ROLE supplytrace_app NOLOGIN; END IF; END $$;
GRANT USAGE ON SCHEMA supplytrace TO supplytrace_app;
GRANT SELECT ON ALL TABLES IN SCHEMA supplytrace TO supplytrace_app;
GRANT EXECUTE ON FUNCTION supplytrace.create_order(integer,integer,text[],integer[]),
 supplytrace.allocate_order(integer),supplytrace.dispatch_allocation(bigint,integer),supplytrace.hold_batch(integer) TO supplytrace_app;
