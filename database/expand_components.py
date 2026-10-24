"""Family-level educational assemblies, not Apple service parts or actual BOMs."""
from pathlib import Path
from collections import defaultdict
import json

PARTS = {
 'iPhone': ['display assembly','battery pack','storage assembly','memory package','rear camera assembly','front camera assembly','speaker and microphone set','wireless communication assembly','motion sensor assembly','enclosure and buttons'],
 'iPad': ['display assembly','battery pack','storage assembly','memory package','rear camera assembly','front camera assembly','speaker and microphone set','Wi-Fi and Bluetooth assembly','touch input assembly','enclosure and buttons'],
 'MacBook Air': ['display assembly','battery pack','storage assembly','memory package','keyboard assembly','trackpad assembly','camera assembly','speaker and microphone set','Wi-Fi and Bluetooth assembly','enclosure and hinge set'],
 'MacBook Pro': ['display assembly','battery pack','storage assembly','memory package','keyboard assembly','trackpad assembly','camera assembly','speaker and microphone set','cooling fan assembly','enclosure and hinge set'],
 'iMac': ['display assembly','power supply assembly','storage assembly','memory package','camera assembly','speaker and microphone set','Wi-Fi and Bluetooth assembly','cooling assembly','enclosure and stand'],
 'Mac mini': ['power supply assembly','storage assembly','memory package','Wi-Fi and Bluetooth assembly','speaker assembly','cooling assembly','I/O connector assembly','enclosure'],
 'Mac Studio': ['power supply assembly','storage assembly','memory package','Wi-Fi and Bluetooth assembly','speaker assembly','cooling assembly','I/O connector assembly','enclosure'],
 'Mac Pro': ['power supply assembly','storage assembly','memory package','Wi-Fi and Bluetooth assembly','speaker assembly','cooling assembly','PCIe slot assembly','enclosure'],
 'Apple Watch': ['display assembly','battery pack','storage assembly','optical heart sensor assembly','motion sensor assembly','speaker and microphone set','haptic assembly','enclosure and crown'],
 'AirPods': ['rechargeable battery set','audio driver pair','microphone set','motion sensor set','wireless antenna set','headphone enclosure set'],
 'Apple Vision Pro': ['display assembly','external battery pack','storage assembly','memory package','tracking camera set','motion sensor assembly','speaker and microphone set','Wi-Fi and Bluetooth assembly','enclosure and head band'],
}

def expand_components(data):
    models={r[0]:r for r in data['product_model']}
    configs={r[0]:r for r in data['product_configuration']}
    # Reuse the existing, more specific fixture parts rather than count a second
    # display or battery. Other families use deliberately abstract assemblies.
    special={('IP17P-','display assembly'):2,('IP17P-','battery pack'):1,
             ('MBA13M4-','display assembly'):6,('MBA13M4-','battery pack'):4,
             ('VP-M2-','display assembly'):9,('VP-M2-','external battery pack'):10}
    next_id=max(r[0] for r in data['component'])+1
    ids={}; metadata=[]
    for family,parts in PARTS.items():
        for part in parts:
            cid=next_id;next_id+=1;ids[family,part]=cid
            # A unit is one complete named assembly/set, never each member.
            data['component'].append([cid,f'{family} {part}'])
            metadata.append({'component_id':cid,'family':family,'assembly':part,'quantity_per_finished_unit':1})
    batches={r[0]:r for r in data['component_batch']}
    usage=defaultdict(set)
    for cb,mb,q in data['batch_component_usage']:usage[mb].add(batches[cb][2])
    # Explicit chip compatibility includes configurations that have no stock.
    chip_ids={r[1]:r[0] for r in data['component']}
    plans={}
    for sku,c in configs.items():
        family=models[c[1]][2]
        selected=[]
        for part in PARTS[family]:
            cid=next((v for (prefix,p),v in special.items() if sku.startswith(prefix) and p==part),ids[family,part])
            selected.append(cid)
        if sku.startswith('IP17P-'):selected.append(5)
        elif sku.startswith('MBA13M4-'):selected.append(3)
        elif sku.startswith('VP-M2-'):selected.extend([7,8])
        elif c[2]:selected.append(chip_ids['Apple '+c[2]+' chip'])
        plans[sku]=sorted(set(selected))
    # Stable new lot IDs; two simulated suppliers per assembly, with receipts
    # predating all production and quantities derived from actual consumption.
    new_lots={}; totals=defaultdict(int)
    for mb,sku,date,qty,status in data['manufacturing_batch']:
        required=set(plans[sku])
        assert usage[mb] <= required,(mb,usage[mb]-required)
        for cid in sorted(required-usage[mb]):
            bucket=mb%2;cb=100000+cid*2+bucket
            new_lots[cb]=cid;totals[cb]+=qty
            data['batch_component_usage'].append([cb,mb,qty])
    for cb,cid in sorted(new_lots.items()):
        data['component_batch'].append([cb,1+(cid*7+cb%2)%50,cid,f'SIM-ASSEMBLY-{cb}','2026-01-01',totals[cb]+max(100,totals[cb]//10)])
    # Register catalogue-only assemblies with a receipt as a sourcing example.
    used={r[2] for r in data['component_batch']}
    for row in metadata:
        cid=row['component_id']
        if cid not in used:data['component_batch'].append([100000+cid*2,1+(cid*7)%50,cid,f'SIM-RESERVE-{cid}','2026-01-01',100])
    Path(__file__).with_name('component_assumptions.json').write_text(json.dumps({'scope':'Abstract family-level simulation specifications; not physical interchangeability claims or Apple part numbers. Each set is one unit. Chip packages and memory/storage inputs are educational accounting boundaries, not asserted assembly stages.','components':metadata},indent=2)+'\n',encoding='utf-8')
    return plans
