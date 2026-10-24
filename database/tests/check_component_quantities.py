"""Check whole component counts with rolled-back SQL writes. Uses test-runner PG variables."""
import os,subprocess,json
from pathlib import Path
cmd=[os.environ.get('PSQL','psql'),'-X','-v','ON_ERROR_STOP=1','-At']
results=[]
for table,column,predicate in [('component_batch','received_qty','component_batch_id=11'),('batch_component_usage','quantity_used','component_batch_id=11 AND manufacturing_batch_id=101')]:
    for value in ['0.5','1.0001','0','-1',"'Infinity'::numeric","'NaN'::numeric",'100000000000']:
        sql=f'BEGIN; UPDATE supplytrace.{table} SET {column}={value} WHERE {predicate}; SET CONSTRAINTS ALL IMMEDIATE; ROLLBACK;'
        r=subprocess.run(cmd+['-c',sql],capture_output=True,text=True,encoding='utf-8')
        passed=r.returncode!=0 and 'check constraint' in r.stderr
        results.append({'column':column,'input':value,'expected':'rejected by CHECK','passed':passed})
    value='100' if table=='component_batch' else '12'
    r=subprocess.run(cmd+['-c',f'BEGIN; UPDATE supplytrace.{table} SET {column}={value} WHERE {predicate}; SET CONSTRAINTS ALL IMMEDIATE; ROLLBACK;'],capture_output=True,text=True,encoding='utf-8')
    results.append({'column':column,'input':value,'expected':'valid whole count accepted then rolled back','passed':r.returncode==0})
out=Path(__file__).resolve().parents[1]/'evidence/component_quantity_checks.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
assert all(r['passed'] for r in results),results
print(f'All {len(results)} component quantity checks passed; writes rolled back.')
