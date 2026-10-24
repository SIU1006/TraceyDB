"""Requires a seeded database. Uses psql only; no third-party Python packages.
Set PGHOST, PGPORT, PGUSER, PGDATABASE and PSQL as appropriate.
The concurrency test commits temporary reservations, then restores seed state.
"""
import os, subprocess, json, time
from pathlib import Path

PSQL=os.environ.get('PSQL','psql')
CMD=[PSQL,'-X','-v','ON_ERROR_STOP=1','-A','-t']
OUT=Path(__file__).resolve().parents[1]/'evidence'; OUT.mkdir(exist_ok=True)
results=[]
def run(sql):return subprocess.run(CMD+['-c',sql],capture_output=True,text=True,encoding='utf-8')
def scalar(sql):
    r=run(sql)
    if r.returncode:raise AssertionError(r.stderr)
    return r.stdout.strip()
def test(name,body,error=None,role=False):
    sql='BEGIN; SET search_path=supplytrace,pg_catalog; '+('SET LOCAL ROLE supplytrace_app; ' if role else '')+body+'; SET CONSTRAINTS ALL IMMEDIATE; ROLLBACK;'
    r=run(sql)
    passed=(r.returncode!=0 and error in r.stderr) if error else r.returncode==0
    results.append(dict(test=name,passed=passed,expected_error=error,output=(r.stdout+r.stderr).strip()))
    if not passed:raise AssertionError(name+'\n'+r.stdout+r.stderr)

def assert_sql(condition):return "DO $$ BEGIN IF NOT ("+condition+") THEN RAISE EXCEPTION 'assertion failed'; END IF; END $$"

try:
    test('T01 baseline consistency','SELECT assert_consistent()')
    test('T02 valid app allocation and partial dispatch',"SELECT allocate_order(1008); SELECT dispatch_allocation((SELECT min(allocation_id) FROM stock_allocation WHERE order_id=1008),1); "+assert_sql("(SELECT order_status='partially_dispatched' FROM sales_order WHERE order_id=1008)"),role=True)
    test('T03 duplicate inventory position',"INSERT INTO inventory VALUES(999,1,101,0,0)",'duplicate key')
    test('T04 negative stock',"UPDATE inventory SET on_hand_qty=-1 WHERE inventory_id=1",'check constraint')
    test('T05 unknown product foreign key',"SELECT create_order(2000,1,ARRAY['UNKNOWN'],ARRAY[1])",'foreign key')
    test('T06 insufficient stock',"SELECT allocate_order(1005)",'insufficient eligible stock',True)
    test('T07 held-only stock rejected',"SELECT allocate_order(1007)",'insufficient eligible stock',True)
    test('T08 failure on second line rolls back first line',"""DO $$ DECLARE before_res bigint; failed boolean:=false; BEGIN
      SELECT sum(reserved_qty) INTO before_res FROM inventory;
      BEGIN PERFORM allocate_order(1006); EXCEPTION WHEN raise_exception THEN
        IF SQLERRM NOT LIKE 'insufficient eligible stock%' THEN RAISE; END IF; failed:=true; END;
      IF NOT failed OR EXISTS(SELECT FROM stock_allocation WHERE order_id=1006) OR (SELECT sum(reserved_qty) FROM inventory)<>before_res OR (SELECT order_status FROM sales_order WHERE order_id=1006)<>'submitted' THEN RAISE EXCEPTION 'rollback assertion failed'; END IF;
      END $$""")
    test('T09 full order allocated across multiple inventories',assert_sql("(SELECT count(*)=3 AND sum(allocated_qty)=10 FROM stock_allocation WHERE order_id=1002)"))
    test('T10 reallocation rejected',"SELECT allocate_order(1002)",'order already allocated',True)
    test('T11 over-dispatch rejected',"SELECT dispatch_allocation((SELECT min(allocation_id) FROM stock_allocation WHERE order_id=1002),99)",'dispatch exceeds allocation',True)
    test('T12 hold blocks dispatch but preserves reservation',"SELECT hold_batch(101); SELECT dispatch_allocation((SELECT min(allocation_id) FROM stock_allocation WHERE order_id=1002),1)",'batch is held',True)
    test('T13 empty submitted order rejected',"INSERT INTO sales_order VALUES(2000,1,current_timestamp,'submitted')",'order requires a line')
    test('T14 reservation summary mismatch',"UPDATE inventory SET reserved_qty=1 WHERE inventory_id=5",'reservation summary mismatch')
    test('T15 app cannot bypass functions',"UPDATE inventory SET reserved_qty=0 WHERE inventory_id=1",'permission denied',True)
    test('T16 trace query identifies two recipients',assert_sql("(SELECT count(DISTINCT o.retailer_id)=2 FROM shipment_line sl JOIN shipment s USING(shipment_id) JOIN sales_order o USING(order_id) JOIN stock_allocation a USING(allocation_id) JOIN inventory i USING(inventory_id) WHERE EXISTS(SELECT FROM batch_component_usage u WHERE u.component_batch_id=11 AND u.manufacturing_batch_id=i.manufacturing_batch_id))"))
    test('T17 product mismatch rejected',"UPDATE order_line SET sku='MBA13M4-256-SB' WHERE order_id=1002",'allocation product mismatch')
    test('T18 shipment warehouse mismatch rejected',"UPDATE shipment SET warehouse_id=2 WHERE shipment_id=1",'shipment order or warehouse mismatch')
    test('T19 complete dispatch updates status',"SELECT allocate_order(1008); SELECT dispatch_allocation((SELECT min(allocation_id) FROM stock_allocation WHERE order_id=1008),2); "+assert_sql("(SELECT order_status='dispatched' FROM sales_order WHERE order_id=1008)"),role=True)
    test('T20 component overconsumption rejected',"UPDATE batch_component_usage SET quantity_used=101 WHERE component_batch_id=11 AND manufacturing_batch_id=101",'component consumption exceeds receipt')
    test('T21 finished stock conservation',"UPDATE inventory SET on_hand_qty=100 WHERE inventory_id=6",'finished stock exceeds production')
    test('T22 immutable historical destination',"UPDATE retailer SET delivery_address='New address' WHERE retailer_id=1; "+assert_sql("(SELECT delivery_address='10 Example Street, Sydney NSW' FROM shipment WHERE shipment_id=1)"))
    manifest=json.loads((OUT.parent/'data_manifest.json').read_text())
    for table,count in manifest['table_rows'].items():
        if scalar('SELECT count(*) FROM supplytrace.'+table)!=str(count): raise AssertionError('row count mismatch: '+table)
    results.append(dict(test='T24 all fifteen table counts match manifest',passed=True))
    test('T25 chronological operational records',assert_sql("NOT EXISTS(SELECT FROM shipment s JOIN sales_order o USING(order_id) WHERE s.dispatched_at<o.ordered_at) AND NOT EXISTS(SELECT FROM batch_component_usage u JOIN component_batch c USING(component_batch_id) JOIN manufacturing_batch m USING(manufacturing_batch_id) WHERE c.received_date>m.production_date) AND NOT EXISTS(SELECT FROM shipment_line sl JOIN shipment s USING(shipment_id) JOIN stock_allocation a USING(allocation_id) JOIN inventory i USING(inventory_id) JOIN manufacturing_batch m USING(manufacturing_batch_id) JOIN sales_order o ON o.order_id=a.order_id WHERE a.allocated_at<o.ordered_at OR s.dispatched_at<a.allocated_at OR m.production_date>a.allocated_at::date)"))
    actual=scalar("SELECT m.sku||'|'||c.component_id FROM supplytrace.batch_component_usage u JOIN supplytrace.component_batch c USING(component_batch_id) JOIN supplytrace.manufacturing_batch m USING(manufacturing_batch_id)")
    for pair in actual.splitlines():
        sku,cid=pair.split('|')
        if int(cid) not in manifest['product_components'][sku]: raise AssertionError('component mismatch: '+pair)
    results.append(dict(test='T26 component family compatibility',passed=True))
    test('T27 original configurations preserved',assert_sql("(SELECT count(*)=9 FROM product_configuration WHERE sku LIKE 'IP17P-%') AND (SELECT count(*)=16 FROM product_configuration WHERE sku LIKE 'MBA13M4-%') AND (SELECT count(*)=3 FROM product_configuration WHERE sku LIKE 'VP-M2-%')"))
    import csv,io
    for table in ['product_model','product_configuration']:
        with (OUT.parent/'data'/f'{table}.csv').open(encoding='utf-8',newline='') as f: expected={tuple(r) for r in csv.reader(f)}
        actual=run(f'COPY (SELECT * FROM supplytrace.{table}) TO STDOUT WITH CSV')
        if actual.returncode or set(map(tuple,csv.reader(io.StringIO(actual.stdout))))!=expected: raise AssertionError('catalogue differs from reviewed seed: '+table)
    results.append(dict(test='T28 structured catalogue matches seed',passed=True))
    test('T29 configuration requires an existing model',"INSERT INTO product_configuration(sku,model_id) VALUES('BAD-MODEL',-1)",'foreign key')
    test('T30 storage must be positive',"UPDATE product_configuration SET storage_capacity_gb=0 WHERE sku='IP17P-256-DB'",'check constraint')
    test('T31 optional storage remains null',assert_sql("NOT EXISTS(SELECT FROM product_catalogue WHERE product_family='AirPods' AND storage_capacity_gb IS NOT NULL)"))
    test('T32 model supports chip variants and size identity',assert_sql("EXISTS(SELECT model_id FROM product_catalogue WHERE model_name='MacBook Pro 14-inch' AND release_year=2023 GROUP BY model_id HAVING count(DISTINCT chip)>1) AND EXISTS(SELECT FROM product_model WHERE model_name='Apple Watch Series 9 41mm') AND EXISTS(SELECT FROM product_model WHERE model_name='Apple Watch Series 9 45mm')"))
    test('T33 equivalent configurations rejected',"INSERT INTO product_configuration SELECT 'DUPLICATE-SKU',model_id,chip,storage_capacity_gb,colour FROM product_configuration WHERE sku='IP17P-256-DB'",'duplicate key')
    test('T34 removed columns absent',assert_sql("NOT EXISTS(SELECT FROM information_schema.columns WHERE table_schema='supplytrace' AND table_name IN ('product_model','product_configuration','product_catalogue') AND column_name IN ('generation','release_period','screen_size_inches','case_size_mm','connectivity','case_material','port_variant'))"))
    # Session A keeps the shared writer lock for two seconds after reserving six units.
    sql_a="BEGIN; SET LOCAL ROLE supplytrace_app; SELECT supplytrace.allocate_order(1003); SELECT pg_sleep(2); COMMIT;"
    proc=subprocess.Popen(CMD+['-c',sql_a],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        if scalar("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND classid=9120 AND objid=1 AND granted")=='1':break
        time.sleep(.05)
    else:raise AssertionError('session A did not acquire advisory lock')
    started=time.monotonic()
    b=run("BEGIN; SET LOCAL ROLE supplytrace_app; SELECT supplytrace.allocate_order(1004); COMMIT;")
    elapsed=time.monotonic()-started
    ao,ae=proc.communicate(timeout=15)
    state=scalar("SELECT on_hand_qty||','||reserved_qty||','||(on_hand_qty-reserved_qty) FROM supplytrace.inventory WHERE inventory_id=5")
    passed=proc.returncode==0 and b.returncode!=0 and 'insufficient eligible stock' in b.stderr and state=='10,6,4'
    results.append(dict(test='T23 concurrent orders cannot oversell',passed=passed,session_a=ao+ae,session_b=b.stdout+b.stderr,session_b_elapsed_seconds=round(elapsed,3),final_on_hand_reserved_available=state))
    if not passed:raise AssertionError('concurrency failure')
finally:
    # Restore only the two test orders. No shipments are created for them.
    clean=run("BEGIN; SET search_path=supplytrace,pg_catalog; SELECT pg_advisory_xact_lock(9120,1); DELETE FROM stock_allocation WHERE order_id IN (1003,1004); UPDATE inventory SET reserved_qty=0 WHERE inventory_id=5; UPDATE sales_order SET order_status='submitted' WHERE order_id IN (1003,1004); SET CONSTRAINTS ALL IMMEDIATE; COMMIT;")
    results.append(dict(test='cleanup restores concurrency fixtures',passed=clean.returncode==0,output=clean.stderr))
    (OUT/'test_results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(results),'passed':sum(r['passed'] for r in results)},indent=2))
if not all(r['passed'] for r in results):raise SystemExit(1)
