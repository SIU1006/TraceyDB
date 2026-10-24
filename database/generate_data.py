"""Deterministic educational data; run from any directory using Python 3."""
import csv
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parent
TABLES = 'supplier component component_batch product_model manufacturing_batch batch_component_usage warehouse inventory retailer sales_order order_line stock_allocation shipment shipment_line'.split()
data = {t: [] for t in TABLES}
def add(t, *row):
    data[t].append(list(row))
def stamp(day, hours=0):
    return (datetime(2026, 7, 1, tzinfo=timezone.utc)+timedelta(days=day,hours=hours)).isoformat()

for n in range(1,51): add('supplier',n,f'Simulation Components {n:03}', ['Australia','Singapore','Japan','Taiwan','South Korea'][n%5])
components = ['iPhone 17 Pro lithium-ion battery','6.3-inch Super Retina XDR OLED display','Apple M4 chip (10-core CPU, 8-core GPU)','MacBook Air 53.8Wh lithium-polymer battery','Apple A19 Pro chip','13.6-inch Liquid Retina display','Apple M2 chip (8-core CPU, 10-core GPU)','Apple R1 chip','Apple Vision Pro micro-OLED display system','Apple Vision Pro external battery']
for n,name in enumerate(components,1): add('component',n,name)
families = {}
for storage in ['256','512','1TB']:
    for colour,code in [('Silver','SL'),('Cosmic Orange','CO'),('Deep Blue','DB')]:
        sku=f'IP17P-{storage}-{code}'
        add('product_model',sku,'iPhone 17 Pro',storage if 'TB' in storage else storage+'GB',colour)
        families[sku]=[1,2,5]
for storage in ['256','512','1TB','2TB']:
    for colour,code in [('Sky Blue','SB'),('Silver','SL'),('Starlight','ST'),('Midnight','MN')]:
        sku=f'MBA13M4-{storage}-{code}'
        add('product_model',sku,'MacBook Air (13-inch, M4, 2025)',storage if 'TB' in storage else storage+'GB',colour)
        families[sku]=[3,4,6]
for storage in ['256','512','1TB']:
    sku=f'VP-M2-{storage}'
    add('product_model',sku,'Apple Vision Pro (2024)',storage if 'TB' in storage else storage+'GB','Not specified by Apple')
    families[sku]=[7,8,9]
fixture_skus=['IP17P-256-DB','IP17P-512-SL','MBA13M4-256-SB','MBA13M4-512-MN','VP-M2-1TB']
for bid,cid in [(11,1),(12,2),(13,3),(14,4),(15,5),(16,6),(17,1)]:
    add('component_batch',bid,1+(cid%3),cid,f'SIM-FIX-{bid}','2026-09-01',100)
pools={c:[] for c in range(1,11)}
for j in range(2993):
    cid=j%10+1; bid=10000+j
    add('component_batch',bid,j%50+1,cid,f'SIM-LOT-{bid}','2026-01-15',50000)
    pools[cid].append(bid)
for bid,sku,qty,status,cbs in [(101,fixture_skus[0],12,'released',[11,12,15]),(102,fixture_skus[0],10,'released',[11,12,15]),(103,fixture_skus[1],6,'held',[17,12,15]),(104,fixture_skus[2],10,'released',[13,14,16]),(105,fixture_skus[0],5,'released',[17,12,15])]:
    add('manufacturing_batch',bid,sku,'2026-09-10',qty,status)
    for cb in cbs: add('batch_component_usage',cb,bid,qty)
cities=['Sydney','Melbourne','Brisbane','Perth','Adelaide','Canberra','Newcastle','Hobart','Darwin','Geelong']
for n in range(1,21): add('warehouse',n,f'Simulation Distribution {n:02}',cities[(n-1)%10])
for row in [(1,1,101,4,4),(2,2,101,4,4),(3,2,102,9,1),(4,1,103,6,0),(5,1,104,10,0),(6,2,105,5,0)]: add('inventory',*row)
bulk_skus=[s for s in families if s not in fixture_skus]
counters={c:0 for c in pools}
for j in range(2000):
    bid=10000+j; sku=bulk_skus[j%len(bulk_skus)]; qty=200+(j%7)*20; wh=(j//2)%20+1
    add('manufacturing_batch',bid,sku,'2026-05-20',qty,'released')
    for cid in families[sku]:
        cb=pools[cid][counters[cid]%len(pools[cid])]; counters[cid]+=1
        add('batch_component_usage',cb,bid,qty)
    add('inventory',10000+2*j,wh,bid,qty//2,0)
    add('inventory',10001+2*j,wh%20+1,bid,qty-qty//2,0)
addresses=['10 Example Street, Sydney NSW','20 Sample Road, Melbourne VIC','30 Demonstration Avenue, Sydney NSW','40 Test Lane, Newcastle NSW']
for n in range(1,1001): add('retailer',n,f'Simulation Retailer {n:04}',addresses[n-1] if n<=4 else f'{n} Simulation Road, {cities[n%10]} (synthetic address)')
for oid,rid,status,lines in [(1001,1,'dispatched',[(fixture_skus[0],4)]),(1002,2,'partially_dispatched',[(fixture_skus[0],10)]),(1003,3,'submitted',[(fixture_skus[2],6)]),(1004,4,'submitted',[(fixture_skus[2],6)]),(1005,1,'submitted',[(fixture_skus[0],1000)]),(1006,2,'submitted',[(fixture_skus[0],2),(fixture_skus[3],1)]),(1007,3,'submitted',[(fixture_skus[1],1)]),(1008,1,'submitted',[(fixture_skus[0],2)])]:
    add('sales_order',oid,rid,stamp(90),status)
    for ln,(sku,qty) in enumerate(lines,1): add('order_line',oid,ln,sku,qty)
for aid,oid,iid,qty in [(1,1001,1,4),(2,1002,1,4),(3,1002,2,4),(4,1002,3,2)]: add('stock_allocation',aid,oid,1,iid,qty,stamp(90,1))
add('shipment',1,1001,1,stamp(91),addresses[0]); add('shipment_line',1,1,1,4)
add('shipment',2,1002,2,stamp(91),addresses[1]); add('shipment_line',2,1,4,1)
inventories={r[0]:r for r in data['inventory']}
aid=10000; sid=10000
for j in range(8000):
    oid=10000+j; rid=j%1000+1; day=j%110; line_count=2 if j<3000 else 1
    total=sent=0; dispatch=[]
    for ln in range(1,line_count+1):
        b=j%2000 if ln==1 else (j%2000)^1
        sku=bulk_skus[b%len(bulk_skus)]; qty=1+(j+ln)%5; iid=10000+2*b; total+=qty
        add('order_line',oid,ln,sku,qty)
        if j<5000:
            add('stock_allocation',aid,oid,ln,iid,qty,stamp(day,1))
            shipped=(qty if j%3 else max(1,qty//2)) if j<2000 else 0
            inventories[iid][3]-=shipped; inventories[iid][4]+=qty-shipped
            if shipped: dispatch.append((aid,shipped,iid)); sent+=shipped
            aid+=1
    status='submitted' if j>=5000 else ('allocated' if not sent else ('dispatched' if sent==total else 'partially_dispatched'))
    add('sales_order',oid,rid,stamp(day),status)
    if dispatch:
        groups=[[d] for d in dispatch] if j<1000 else [dispatch]
        for group in groups:
            add('shipment',sid,oid,inventories[group[0][2]][1],stamp(day+1),data['retailer'][rid-1][2])
            for ln,(alloc,qty,_) in enumerate(group,1): add('shipment_line',sid,ln,alloc,qty)
            sid+=1

from expand_catalogue import expand
catalogue=expand(data,families)
from normalise_catalogue import normalise
aliases=normalise(data)
families={aliases[sku]:ids for sku,ids in families.items()}
from expand_components import expand_components
families=expand_components(data)
TABLES.insert(TABLES.index('product_model')+1,'product_configuration')
assert all(r[3]>=r[4]>=0 for r in data['inventory'])
counts={t:len(rows) for t,rows in data.items()}
assert 50000 <= sum(counts.values()) <= 80000, counts
(ROOT/'data').mkdir(exist_ok=True)
for table,rows in data.items():
    with (ROOT/'data'/f'{table}.csv').open('w',encoding='utf-8',newline='') as f: csv.writer(f).writerows(rows)
sql=['\\set ON_ERROR_STOP on','-- Run from the project root in a fresh schema, BEFORE 02_operations.sql.','BEGIN;','SET search_path=supplytrace,pg_catalog;']
for t in TABLES: sql.append(f"\\copy {t} FROM 'database/data/{t}.csv' WITH (FORMAT csv, ENCODING 'UTF8')")
for t,c in [('stock_allocation','allocation_id'),('shipment','shipment_id')]:
    sql.append(f"SELECT setval(pg_get_serial_sequence('supplytrace.{t}','{c}'),(SELECT max({c}) FROM {t}));")
sql+=['COMMIT;','ANALYZE;']
(ROOT/'03_seed.sql').write_text('\n'.join(sql)+'\n',encoding='utf-8')
manifest={'total_rows':sum(counts.values()),'table_rows':counts,'generation':'deterministic arithmetic, no randomness','snapshot_date':'2026-10-22','product_components':families,'scope':'Public product specifications; synthetic organisations, component lots, partial bills of materials and all operational events. SKUs are internal educational identifiers.'}
manifest['catalogue_models']=len(data['product_model'])
manifest['catalogue_families']=sorted(set(r['family'] for r in catalogue)|{'Apple Vision Pro'})
(ROOT/'data_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(counts,indent=2)); print('TOTAL',sum(counts.values()))
