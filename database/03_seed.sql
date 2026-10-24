\set ON_ERROR_STOP on
-- Run from the project root in a fresh schema, BEFORE 02_operations.sql.
BEGIN;
SET search_path=supplytrace,pg_catalog;
\copy supplier FROM 'database/data/supplier.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy component FROM 'database/data/component.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy component_batch FROM 'database/data/component_batch.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy product_model FROM 'database/data/product_model.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy product_configuration FROM 'database/data/product_configuration.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy manufacturing_batch FROM 'database/data/manufacturing_batch.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy batch_component_usage FROM 'database/data/batch_component_usage.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy warehouse FROM 'database/data/warehouse.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy inventory FROM 'database/data/inventory.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy retailer FROM 'database/data/retailer.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy sales_order FROM 'database/data/sales_order.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy order_line FROM 'database/data/order_line.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy stock_allocation FROM 'database/data/stock_allocation.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy shipment FROM 'database/data/shipment.csv' WITH (FORMAT csv, ENCODING 'UTF8')
\copy shipment_line FROM 'database/data/shipment_line.csv' WITH (FORMAT csv, ENCODING 'UTF8')
SELECT setval(pg_get_serial_sequence('supplytrace.stock_allocation','allocation_id'),(SELECT max(allocation_id) FROM stock_allocation));
SELECT setval(pg_get_serial_sequence('supplytrace.shipment','shipment_id'),(SELECT max(shipment_id) FROM shipment));
COMMIT;
ANALYZE;
