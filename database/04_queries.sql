\set ON_ERROR_STOP on
SET search_path=supplytrace,pg_catalog;
\echo Q1 Available and eligible stock
SELECT m.sku,w.city,sum(i.on_hand_qty) AS on_hand,sum(i.reserved_qty) AS reserved,
 sum(i.on_hand_qty-i.reserved_qty) AS unreserved,
 sum(CASE WHEN m.quality_status='released' THEN i.on_hand_qty-i.reserved_qty ELSE 0 END) AS eligible
FROM inventory i JOIN manufacturing_batch m USING(manufacturing_batch_id) JOIN warehouse w USING(warehouse_id)
GROUP BY m.sku,w.city ORDER BY m.sku,w.city;
\echo Q2 Manufacturing provenance
SELECT u.manufacturing_batch_id,b.component_batch_id,c.component_name,s.supplier_name,u.quantity_used
FROM batch_component_usage u JOIN component_batch b USING(component_batch_id) JOIN component c USING(component_id) JOIN supplier s USING(supplier_id)
WHERE u.manufacturing_batch_id=101 ORDER BY b.component_batch_id;
\echo Q3 Retailer exposure to component batch 11
SELECT r.retailer_id,r.retailer_name,s.shipment_id,i.manufacturing_batch_id,sum(sl.shipped_qty) AS potentially_affected_qty
FROM shipment_line sl JOIN shipment s USING(shipment_id) JOIN sales_order o USING(order_id) JOIN retailer r USING(retailer_id)
JOIN stock_allocation a USING(allocation_id) JOIN inventory i USING(inventory_id)
WHERE EXISTS(SELECT FROM batch_component_usage u WHERE u.component_batch_id=11 AND u.manufacturing_batch_id=i.manufacturing_batch_id)
GROUP BY r.retailer_id,r.retailer_name,s.shipment_id,i.manufacturing_batch_id ORDER BY s.shipment_id;
\echo Q4 Remaining affected stock
SELECT i.manufacturing_batch_id,w.city,i.on_hand_qty,i.reserved_qty FROM inventory i JOIN warehouse w USING(warehouse_id)
WHERE i.on_hand_qty>0 AND EXISTS(SELECT FROM batch_component_usage u WHERE u.component_batch_id=11 AND u.manufacturing_batch_id=i.manufacturing_batch_id)
ORDER BY i.manufacturing_batch_id,w.city;
\echo Q5 Outstanding allocations
SELECT l.order_id,l.line_number,l.sku,l.ordered_qty-coalesce(sum(a.allocated_qty),0) AS outstanding
FROM order_line l LEFT JOIN stock_allocation a USING(order_id,line_number)
GROUP BY l.order_id,l.line_number HAVING l.ordered_qty>coalesce(sum(a.allocated_qty),0) ORDER BY l.order_id,l.line_number;
\echo Q6 Products never ordered
SELECT p.sku FROM product_configuration p WHERE NOT EXISTS(SELECT FROM order_line l WHERE l.sku=p.sku);
