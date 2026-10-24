\set ON_ERROR_STOP on
CREATE VIEW supplytrace.product_catalogue AS
SELECT c.sku,m.model_id,m.model_name,m.product_family,m.release_year,
 c.chip,c.storage_capacity_gb,c.colour,
 concat_ws(' | ',m.model_name,m.release_year::text,c.chip,
 CASE WHEN c.storage_capacity_gb IS NOT NULL THEN c.storage_capacity_gb::text||' GB' END,c.colour) AS display_name
FROM supplytrace.product_configuration c JOIN supplytrace.product_model m USING(model_id);
GRANT SELECT ON supplytrace.product_catalogue TO supplytrace_app;
