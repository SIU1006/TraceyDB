"""Append the reviewed catalogue and illustrative chip provenance to seed records."""
import json
from pathlib import Path

def expand(data,families):
    rows=json.loads(Path(__file__).with_name('catalogue.json').read_text(encoding='utf-8'))
    existing={(r[1],r[2],r[3]):r[0] for r in data['product_model']}
    components={r[1]:r[0] for r in data['component']}
    next_component=max(r[0] for r in data['component'])+1
    represented=set()
    index=0
    for r in rows:
        key=(r['model_name'],r['storage_capacity'],r['colour'])
        if key in existing:
            r['sku']=existing[key]
            continue
        sku=r['sku'];existing[key]=sku
        data['product_model'].append([sku,*key])
        if not r['chip']:continue
        component='Apple '+r['chip']+' chip'
        if component not in components:
            components[component]=next_component
            data['component'].append([next_component,component]);next_component+=1
        cid=components[component];families[sku]=[cid]
        # Each additional older model has one illustrative stock position.
        # New 2026 releases remain catalogue-only until receipt data is supplied.
        if r['year'] is None or r['year']>=2026 or r['model_name'] in represented:continue
        represented.add(r['model_name'])
        bid=50000+index;wh=index%20+1
        data['component_batch'].append([bid,index%50+1,cid,f'SIM-CATALOGUE-{bid}','2026-10-01',100])
        data['manufacturing_batch'].append([bid,sku,'2026-10-15',20,'released'])
        data['batch_component_usage'].append([bid,bid,20])
        data['inventory'].append([bid,wh,bid,20,0])
        index+=1
    return rows
