"""Split reviewed product descriptions into model and configuration attributes."""
import json,re
from pathlib import Path

def normalise(data):
    source={r['sku']:r for r in json.loads(Path(__file__).with_name('catalogue.json').read_text(encoding='utf-8'))}
    models={};configs=[]; equivalent={};aliases={}
    for sku,label,storage,colour in data['product_model']:
        text=label.replace('\u2011','-'); meta=source.get(sku,{})
        family=meta.get('family','Apple Vision Pro');year=meta.get('year',2024 if family=='Apple Vision Pro' else None)
        name=text.split(' (')[0]
        if family=='iPad':name=re.sub(r'\s+\d+(?:\.\d+)?-inch','',name)
        size=re.search(r'(\d+(?:\.\d+)?)-inch',text)
        screen=float(size[1]) if size else None
        case=re.search(r'(\d+)mm',text);case=int(case[1]) if case else None
        chip=meta.get('chip','M2' if family=='Apple Vision Pro' else None)
        if screen is not None:name+=' '+format(screen,'g')+'-inch'
        if case is not None:name+=' '+str(case)+'mm'
        key=(name,family,year)
        if key not in models:models[key]=len(models)+1
        st=re.fullmatch(r'(\d+)(GB|TB)',storage)
        # Decimal GB follows Apple's advertised storage units: 1 TB = 1000 GB.
        capacity=int(st[1])*(1000 if st[2]=='TB' else 1) if st else None
        finish=None if colour=='Not specified by Apple' else colour
        attributes=(models[key],chip,capacity,finish)
        canonical=equivalent.setdefault(attributes,sku)
        aliases[sku]=canonical
        if canonical==sku:configs.append([sku,*attributes])
    data['product_model']=[[i,*k] for k,i in models.items()]
    data['product_configuration']=configs
    for table,column in [('manufacturing_batch',1),('order_line',2)]:
        for row in data[table]:row[column]=aliases[row[column]]
    import csv
    with Path(__file__).with_name('catalogue_sku_aliases.csv').open('w',encoding='utf-8',newline='') as f:
        csv.writer(f).writerows(aliases.items())
    return aliases
