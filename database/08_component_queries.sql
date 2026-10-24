\set ON_ERROR_STOP on
-- Catalogue and the number of source lots, including stocked but unused parts.
SELECT c.component_id,c.component_name,
 count(DISTINCT b.component_batch_id) AS received_lots,
 count(DISTINCT u.manufacturing_batch_id) AS manufacturing_batches
FROM supplytrace.component c
LEFT JOIN supplytrace.component_batch b USING(component_id)
LEFT JOIN supplytrace.batch_component_usage u USING(component_batch_id)
GROUP BY c.component_id ORDER BY c.component_id;

-- Example: all recorded inputs for the original iPhone manufacturing batch.
SELECT m.manufacturing_batch_id,c.component_name,s.supplier_name,
 b.supplier_lot_code,u.quantity_used,m.produced_qty,
 u.quantity_used/m.produced_qty AS units_per_device
FROM supplytrace.manufacturing_batch m
JOIN supplytrace.batch_component_usage u USING(manufacturing_batch_id)
JOIN supplytrace.component_batch b USING(component_batch_id)
JOIN supplytrace.component c USING(component_id)
JOIN supplytrace.supplier s USING(supplier_id)
WHERE m.manufacturing_batch_id=101 ORDER BY c.component_id;

-- Unconsumed component stock by supplier lot; receipts are not duplicated.
SELECT c.component_name,s.supplier_name,b.supplier_lot_code,b.received_qty,
 coalesce(sum(u.quantity_used),0) AS used_qty,
 b.received_qty-coalesce(sum(u.quantity_used),0) AS remaining_qty
FROM supplytrace.component_batch b
JOIN supplytrace.component c USING(component_id)
JOIN supplytrace.supplier s USING(supplier_id)
LEFT JOIN supplytrace.batch_component_usage u USING(component_batch_id)
GROUP BY b.component_batch_id,c.component_name,s.supplier_name
ORDER BY b.component_batch_id;
