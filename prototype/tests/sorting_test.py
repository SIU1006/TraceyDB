"""Read-only sorting regression checks against the running local API."""
import json,urllib.request,urllib.error
from pathlib import Path
BASE='http://127.0.0.1:8765'
def get(path):
    with urllib.request.urlopen(BASE+path,timeout=30) as r:return json.load(r)
columns={'products':['product','chip','storage','colour','sku','available'],'stock':['product','batch','warehouse','on_hand','reserved','eligible','quality'],'orders':['order','retailer','created','units','status']}
results=[]
for resource,keys in columns.items():
    for key in keys:
        for direction in ['asc','desc']:
            rows=get(f'/api/{resource}?sort={key}&direction={direction}')
            assert len(rows)==31,(resource,key,direction,rows)
    results.append(resource+': every column accepts ascending and descending sorting')
for resource,key,field,identity in [('products','available','available','sku'),('stock','on_hand','on_hand_qty','inventory_id'),('orders','units','units','order_id')]:
    for direction in ['asc','desc']:
        one=get(f'/api/{resource}?sort={key}&direction={direction}')
        two=get(f'/api/{resource}?sort={key}&direction={direction}&page=2')
        assert one[30][identity]==two[0][identity]
        rows=one[:30]+two
        values=[r[field] for r in rows]
        assert values==sorted(values,reverse=direction=='desc')
        assert len({r[identity] for r in rows})==len(rows)
    results.append(resource+': numeric ordering and stable pagination verified in both directions')
for query in ['sort=unknown','sort=sku%3BDROP%20TABLE%20supplier','direction=invalid']:
    try:get('/api/products?'+query);raise AssertionError('Invalid sort accepted')
    except urllib.error.HTTPError as e:assert e.code==400
results.append('Invalid sort identifiers and directions rejected')
rows=get('/api/products?q=iPhone&sort=available&direction=desc');assert rows and all('iPhone' in r['display_name'] for r in rows)
results.append('Search and sorting work together')
output=Path(__file__).resolve().parents[1].joinpath('evidence/sorting_checks.json')
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(results,indent=2))
print('\n'.join(results))
