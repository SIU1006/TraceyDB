"""Validate broader seed coverage and quantities independently of SQL constraints."""
import csv,json
from pathlib import Path
from collections import defaultdict
root=Path(__file__).resolve().parents[1]
def rows(table):return list(csv.reader((root/'data'/f'{table}.csv').open(encoding='utf-8')))
components={int(r[0]):r for r in rows('component')}
lots={int(r[0]):r for r in rows('component_batch')}
models={r[0]:r for r in rows('product_model')}
configs={r[0]:r for r in rows('product_configuration')}
manufacturing={int(r[0]):r for r in rows('manufacturing_batch')}
manifest=json.loads((root/'data_manifest.json').read_text())
actual=defaultdict(dict);consumed=defaultdict(float)
for cb,mb,q in rows('batch_component_usage'):
    cb,mb,q=int(cb),int(mb),float(q)
    cid=int(lots[cb][2]);assert cid not in actual[mb],('duplicate component',mb,cid)
    actual[mb][cid]=q;consumed[cb]+=q
    assert lots[cb][4]<=manufacturing[mb][2]
family_counts=defaultdict(set)
for mb,row in manufacturing.items():
    sku=row[1];family=models[configs[sku][1]][2]
    assert set(actual[mb])==set(manifest['product_components'][sku]),mb
    assert all(q==int(row[3]) for q in actual[mb].values()),mb
    assert len(actual[mb])>=7,(mb,family)
    names=[components[c][1].lower() for c in actual[mb]]
    assert any('chip' in n for n in names)
    assert any('speaker' in n or 'audio driver' in n for n in names)
    assert any('enclosure' in n for n in names)
    if family in ('Mac mini','Mac Studio','Mac Pro'):
        assert not any('display' in n or 'battery' in n for n in names)
    if family=='MacBook Air':assert not any('fan' in n for n in names)
    if family=='AirPods':assert not any('display' in n or 'keyboard' in n for n in names)
    family_counts[family].update(actual[mb])
for cb,q in consumed.items():assert q<=float(lots[cb][5]),cb
result={'component_types':len(components),'manufacturing_batches_checked':len(manufacturing),'usage_rows':len(rows('batch_component_usage')),'minimum_inputs_per_batch':min(map(len,actual.values())),'maximum_inputs_per_batch':max(map(len,actual.values())),'represented_product_families':sorted(family_counts),'checks':'Every batch has exactly the planned assemblies, one unit/set per finished unit, valid receipt dates and sufficient receipts; selected inappropriate-family inputs excluded.'}
(root/'evidence').mkdir(exist_ok=True)
(root/'evidence'/'component_coverage.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
