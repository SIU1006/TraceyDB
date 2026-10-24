\set ON_ERROR_STOP on
-- Install in a fresh database. No destructive reset is performed.
BEGIN;
CREATE SCHEMA supplytrace;
SET search_path = supplytrace, pg_catalog;
CREATE TABLE supplier(supplier_id integer PRIMARY KEY, supplier_name text NOT NULL, country text NOT NULL);
CREATE TABLE component(component_id integer PRIMARY KEY, component_name text NOT NULL);
CREATE TABLE component_batch(component_batch_id integer PRIMARY KEY,
 supplier_id integer NOT NULL REFERENCES supplier, component_id integer NOT NULL REFERENCES component,
 supplier_lot_code text NOT NULL, received_date date NOT NULL, received_qty numeric NOT NULL CHECK(received_qty>0) CONSTRAINT component_receipt_whole_count CHECK(received_qty=trunc(received_qty) AND received_qty<=99999999999));
CREATE TABLE product_model(
 model_id integer PRIMARY KEY,
 model_name text NOT NULL CHECK (length(trim(model_name))>0),
 product_family text NOT NULL,
 release_year integer CHECK(release_year BETWEEN 1976 AND 2100));
CREATE TABLE product_configuration(
 sku text PRIMARY KEY,
 model_id integer NOT NULL REFERENCES product_model,
 chip text,
 storage_capacity_gb integer CHECK(storage_capacity_gb>0),
 colour text,
 UNIQUE NULLS NOT DISTINCT(model_id,chip,storage_capacity_gb,colour));
CREATE INDEX configuration_model_idx ON product_configuration(model_id);
CREATE TABLE manufacturing_batch(manufacturing_batch_id integer PRIMARY KEY, sku text NOT NULL REFERENCES product_configuration,
 production_date date NOT NULL, produced_qty integer NOT NULL CHECK(produced_qty>0),
 quality_status text NOT NULL CHECK(quality_status IN ('released','held')));
CREATE TABLE batch_component_usage(component_batch_id integer REFERENCES component_batch,
 manufacturing_batch_id integer REFERENCES manufacturing_batch, quantity_used numeric NOT NULL CHECK(quantity_used>0) CONSTRAINT component_usage_whole_count CHECK(quantity_used=trunc(quantity_used) AND quantity_used<=99999999999),
 PRIMARY KEY(component_batch_id,manufacturing_batch_id));
CREATE TABLE warehouse(warehouse_id integer PRIMARY KEY, warehouse_name text NOT NULL, city text NOT NULL);
CREATE TABLE inventory(inventory_id integer PRIMARY KEY, warehouse_id integer NOT NULL REFERENCES warehouse,
 manufacturing_batch_id integer NOT NULL REFERENCES manufacturing_batch, on_hand_qty integer NOT NULL CHECK(on_hand_qty>=0),
 reserved_qty integer NOT NULL DEFAULT 0 CHECK(reserved_qty>=0 AND reserved_qty<=on_hand_qty),
 UNIQUE(warehouse_id,manufacturing_batch_id));
CREATE TABLE retailer(retailer_id integer PRIMARY KEY, retailer_name text NOT NULL, delivery_address text NOT NULL);
CREATE TABLE sales_order(order_id integer PRIMARY KEY, retailer_id integer NOT NULL REFERENCES retailer, ordered_at timestamptz NOT NULL,
 order_status text NOT NULL CHECK(order_status IN ('submitted','allocated','partially_dispatched','dispatched')));
CREATE TABLE order_line(order_id integer REFERENCES sales_order, line_number integer CHECK(line_number>0),
 sku text NOT NULL REFERENCES product_configuration, ordered_qty integer NOT NULL CHECK(ordered_qty>0), PRIMARY KEY(order_id,line_number));
CREATE TABLE stock_allocation(allocation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 order_id integer NOT NULL, line_number integer NOT NULL, inventory_id integer NOT NULL REFERENCES inventory,
 allocated_qty integer NOT NULL CHECK(allocated_qty>0), allocated_at timestamptz NOT NULL DEFAULT current_timestamp,
 FOREIGN KEY(order_id,line_number) REFERENCES order_line);
CREATE TABLE shipment(shipment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, order_id integer NOT NULL REFERENCES sales_order,
 warehouse_id integer NOT NULL REFERENCES warehouse, dispatched_at timestamptz NOT NULL DEFAULT current_timestamp, delivery_address text NOT NULL);
CREATE TABLE shipment_line(shipment_id bigint REFERENCES shipment, shipment_line_no integer CHECK(shipment_line_no>0),
 allocation_id bigint NOT NULL REFERENCES stock_allocation, shipped_qty integer NOT NULL CHECK(shipped_qty>0),
 PRIMARY KEY(shipment_id,shipment_line_no));
CREATE INDEX allocation_inventory_idx ON stock_allocation(inventory_id);
CREATE INDEX allocation_order_idx ON stock_allocation(order_id,line_number);
CREATE INDEX shipment_allocation_idx ON shipment_line(allocation_id);
CREATE INDEX usage_manufacturing_idx ON batch_component_usage(manufacturing_batch_id);
CREATE INDEX inventory_manufacturing_idx ON inventory(manufacturing_batch_id);
CREATE INDEX shipment_order_idx ON shipment(order_id);
COMMIT;
