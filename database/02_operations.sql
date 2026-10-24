\set ON_ERROR_STOP on
BEGIN;
SET search_path=supplytrace,pg_catalog;
-- Deferred whole-schema audit. Correctness-oriented prototype, not a throughput design.
CREATE FUNCTION assert_consistent() RETURNS void LANGUAGE plpgsql SET search_path=supplytrace,pg_catalog AS $$
BEGIN
 IF EXISTS(SELECT FROM manufacturing_batch m WHERE NOT EXISTS(SELECT FROM batch_component_usage u WHERE u.manufacturing_batch_id=m.manufacturing_batch_id)) THEN RAISE EXCEPTION 'manufacturing batch requires component usage'; END IF;
 IF EXISTS(SELECT FROM sales_order o WHERE NOT EXISTS(SELECT FROM order_line l WHERE l.order_id=o.order_id)) THEN RAISE EXCEPTION 'order requires a line'; END IF;
 IF EXISTS(SELECT FROM shipment s WHERE NOT EXISTS(SELECT FROM shipment_line l WHERE l.shipment_id=s.shipment_id)) THEN RAISE EXCEPTION 'shipment requires a line'; END IF;
 IF EXISTS(SELECT FROM component_batch b WHERE (SELECT coalesce(sum(quantity_used),0) FROM batch_component_usage u WHERE u.component_batch_id=b.component_batch_id)>b.received_qty) THEN RAISE EXCEPTION 'component consumption exceeds receipt'; END IF;
 IF EXISTS(SELECT FROM stock_allocation a JOIN order_line l USING(order_id,line_number) JOIN inventory i USING(inventory_id) JOIN manufacturing_batch m USING(manufacturing_batch_id) WHERE l.sku<>m.sku) THEN RAISE EXCEPTION 'allocation product mismatch'; END IF;
 IF EXISTS(SELECT FROM order_line l WHERE (SELECT coalesce(sum(allocated_qty),0) FROM stock_allocation a WHERE a.order_id=l.order_id AND a.line_number=l.line_number)>l.ordered_qty) THEN RAISE EXCEPTION 'allocation exceeds demand'; END IF;
 IF EXISTS(SELECT FROM stock_allocation a WHERE (SELECT coalesce(sum(shipped_qty),0) FROM shipment_line sl WHERE sl.allocation_id=a.allocation_id)>a.allocated_qty) THEN RAISE EXCEPTION 'dispatch exceeds allocation'; END IF;
 IF EXISTS(SELECT FROM shipment_line sl JOIN shipment s USING(shipment_id) JOIN stock_allocation a USING(allocation_id) JOIN inventory i USING(inventory_id) WHERE s.order_id<>a.order_id OR s.warehouse_id<>i.warehouse_id) THEN RAISE EXCEPTION 'shipment order or warehouse mismatch'; END IF;
 IF EXISTS(SELECT FROM inventory i WHERE i.reserved_qty<>(SELECT coalesce(sum(a.allocated_qty-(SELECT coalesce(sum(sl.shipped_qty),0) FROM shipment_line sl WHERE sl.allocation_id=a.allocation_id)),0) FROM stock_allocation a WHERE a.inventory_id=i.inventory_id)) THEN RAISE EXCEPTION 'reservation summary mismatch'; END IF;
 IF EXISTS(SELECT FROM manufacturing_batch m WHERE
   coalesce((SELECT sum(i.on_hand_qty) FROM inventory i WHERE i.manufacturing_batch_id=m.manufacturing_batch_id),0)+
   coalesce((SELECT sum(sl.shipped_qty) FROM shipment_line sl JOIN stock_allocation a USING(allocation_id) JOIN inventory i USING(inventory_id) WHERE i.manufacturing_batch_id=m.manufacturing_batch_id),0)>m.produced_qty) THEN RAISE EXCEPTION 'finished stock exceeds production'; END IF;
 IF EXISTS(SELECT FROM sales_order o WHERE
  (SELECT coalesce(sum(allocated_qty),0) FROM stock_allocation a WHERE a.order_id=o.order_id) NOT IN (0,(SELECT sum(ordered_qty) FROM order_line l WHERE l.order_id=o.order_id))) THEN RAISE EXCEPTION 'partial order allocation'; END IF;
 IF EXISTS(SELECT FROM sales_order o WHERE o.order_status <>
  CASE WHEN NOT EXISTS(SELECT FROM stock_allocation a WHERE a.order_id=o.order_id) THEN 'submitted'
   WHEN NOT EXISTS(SELECT FROM shipment s WHERE s.order_id=o.order_id) THEN 'allocated'
   WHEN (SELECT sum(sl.shipped_qty) FROM shipment_line sl JOIN shipment s USING(shipment_id) WHERE s.order_id=o.order_id)=(SELECT sum(ordered_qty) FROM order_line l WHERE l.order_id=o.order_id) THEN 'dispatched'
   ELSE 'partially_dispatched' END) THEN RAISE EXCEPTION 'order status mismatch'; END IF;
END $$;
CREATE FUNCTION check_deferred() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=supplytrace,pg_catalog,pg_temp AS $$ BEGIN PERFORM assert_consistent(); RETURN NULL; END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['component_batch','manufacturing_batch','batch_component_usage','inventory','sales_order','order_line','stock_allocation','shipment','shipment_line'] LOOP
 EXECUTE format('CREATE CONSTRAINT TRIGGER consistency_check AFTER INSERT OR UPDATE OR DELETE ON %I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_deferred()',t);
 END LOOP;
END $$;
-- All supported application writes share this lock, including quality holds.
-- Deliberately coarse: correctness and an explainable demonstration take priority over throughput.
CREATE FUNCTION allocate_order(p_order integer) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=supplytrace,pg_catalog,pg_temp AS $$
DECLARE l record; r record; remaining integer; take_qty integer; st text;
BEGIN
 PERFORM pg_advisory_xact_lock(9120,1);
 SELECT order_status INTO st FROM sales_order WHERE order_id=p_order FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown order %',p_order; END IF;
 IF st<>'submitted' THEN RAISE EXCEPTION 'order already allocated'; END IF;
 IF NOT EXISTS(SELECT FROM order_line WHERE order_id=p_order) THEN RAISE EXCEPTION 'order requires a line'; END IF;
 FOR l IN SELECT * FROM order_line WHERE order_id=p_order ORDER BY line_number LOOP
  remaining:=l.ordered_qty;
  FOR r IN SELECT i.inventory_id,i.on_hand_qty-i.reserved_qty AS available FROM inventory i JOIN manufacturing_batch m USING(manufacturing_batch_id)
   WHERE m.sku=l.sku AND m.quality_status='released' AND i.on_hand_qty>i.reserved_qty ORDER BY i.inventory_id FOR UPDATE OF i LOOP
   take_qty:=least(remaining,r.available);
   INSERT INTO stock_allocation(order_id,line_number,inventory_id,allocated_qty) VALUES(p_order,l.line_number,r.inventory_id,take_qty);
   UPDATE inventory SET reserved_qty=reserved_qty+take_qty WHERE inventory_id=r.inventory_id;
   remaining:=remaining-take_qty;
   EXIT WHEN remaining=0;
  END LOOP;
  IF remaining>0 THEN RAISE EXCEPTION 'insufficient eligible stock for order %, line %',p_order,l.line_number; END IF;
 END LOOP;
 UPDATE sales_order SET order_status='allocated' WHERE order_id=p_order;
END $$;
CREATE FUNCTION dispatch_allocation(p_allocation bigint,p_qty integer) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=supplytrace,pg_catalog,pg_temp AS $$
DECLARE a record; sid bigint; sent bigint; demand bigint;
BEGIN
 PERFORM pg_advisory_xact_lock(9120,1);
 IF p_qty IS NULL OR p_qty<=0 THEN RAISE EXCEPTION 'dispatch quantity must be positive'; END IF;
 SELECT sa.*,i.warehouse_id,i.manufacturing_batch_id,m.quality_status INTO a FROM stock_allocation sa JOIN inventory i USING(inventory_id) JOIN manufacturing_batch m USING(manufacturing_batch_id) WHERE sa.allocation_id=p_allocation FOR UPDATE OF sa,i;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown allocation'; END IF;
 IF a.quality_status<>'released' THEN RAISE EXCEPTION 'batch is held'; END IF;
 SELECT coalesce(sum(shipped_qty),0) INTO sent FROM shipment_line WHERE allocation_id=p_allocation;
 IF p_qty>a.allocated_qty-sent THEN RAISE EXCEPTION 'dispatch exceeds allocation'; END IF;
 INSERT INTO shipment(order_id,warehouse_id,delivery_address) SELECT a.order_id,a.warehouse_id,r.delivery_address FROM sales_order o JOIN retailer r USING(retailer_id) WHERE o.order_id=a.order_id RETURNING shipment_id INTO sid;
 INSERT INTO shipment_line VALUES(sid,1,p_allocation,p_qty);
 UPDATE inventory SET on_hand_qty=on_hand_qty-p_qty,reserved_qty=reserved_qty-p_qty WHERE inventory_id=a.inventory_id;
 SELECT sum(sl.shipped_qty) INTO sent FROM shipment_line sl JOIN shipment s USING(shipment_id) WHERE s.order_id=a.order_id;
 SELECT sum(ordered_qty) INTO demand FROM order_line WHERE order_id=a.order_id;
 UPDATE sales_order SET order_status=CASE WHEN sent=demand THEN 'dispatched' ELSE 'partially_dispatched' END WHERE order_id=a.order_id;
 RETURN sid;
END $$;
CREATE FUNCTION hold_batch(p_batch integer) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=supplytrace,pg_catalog,pg_temp AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(9120,1);
 UPDATE manufacturing_batch SET quality_status='held' WHERE manufacturing_batch_id=p_batch;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown manufacturing batch'; END IF;
END $$;
CREATE FUNCTION create_order(p_order integer,p_retailer integer,p_skus text[],p_quantities integer[]) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=supplytrace,pg_catalog,pg_temp AS $$
DECLARE n integer; BEGIN
 PERFORM pg_advisory_xact_lock(9120,1);
 n:=cardinality(p_skus);
 IF n IS NULL OR n=0 OR cardinality(p_quantities) IS DISTINCT FROM n THEN RAISE EXCEPTION 'order arrays must have equal nonzero length'; END IF;
 INSERT INTO sales_order VALUES(p_order,p_retailer,current_timestamp,'submitted');
 INSERT INTO order_line SELECT p_order,ordinality,sku,qty FROM unnest(p_skus,p_quantities) WITH ORDINALITY AS x(sku,qty,ordinality);
END $$;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA supplytrace FROM PUBLIC;
COMMIT;
