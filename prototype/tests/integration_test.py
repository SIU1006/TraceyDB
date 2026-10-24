import os,subprocess,sys,json,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];os.chdir(ROOT);BIN=Path(r'C:\Program Files\PostgreSQL\18\bin');DB='TraceyDB_prototype_verify'
env=os.environ.copy();env.update(PGHOST='127.0.0.1',PGPORT='55432',PGUSER='supplytrace_test',PGDATABASE=DB,PSQL=str(BIN/'psql.exe'),PYTHONUTF8='1')
results=[]
def run(args):
    r=subprocess.run(list(map(str,args)),env=env,capture_output=True,text=True,encoding='utf-8');assert r.returncode==0,r.stdout+r.stderr
    return r.stdout
def sql(q):return run([BIN/'psql.exe','-X','-At','-v','ON_ERROR_STOP=1','-c',q]).strip()
def check(name,condition):
    assert condition,name
    results.append({'test':name,'passed':True});print('PASS',name,flush=True)
token='';base='http://127.0.0.1:8766';proc=None
def api(path,data=None,with_token=True):
    headers={'Content-Type':'application/json'}
    if with_token:headers['X-Tracey-Token']=token
    r=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
    try:
        with urllib.request.urlopen(r,timeout=35) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as e:return e.code,json.load(e)
run([BIN/'createdb.exe',DB])
try:
    for f in ['01_schema.sql','03_seed.sql','02_operations.sql','05_access.sql','07_catalogue_view.sql']:
        run([BIN/'psql.exe','-X','-v','ON_ERROR_STOP=1','-f',ROOT/'database'/f])
    run([BIN/'psql.exe','-X','-v','ON_ERROR_STOP=1','-f',ROOT/'prototype/setup_access.sql'])
    webenv=env.copy();webenv.update(PGUSER='tracey_web',TRACEY_PORT='8766')
    (ROOT/'tmp').mkdir(exist_ok=True)
    log=(ROOT/'tmp/prototype-test-server.log').open('w',encoding='utf-8')
    proc=subprocess.Popen([sys.executable,str(ROOT/'prototype/server.py')],env=webenv,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    for _ in range(50):
        try:token=api('/api/session')[1]['token'];break
        except OSError:time.sleep(.1)
    check('readiness and session token',bool(token))
    status,d=api('/api/summary');check('dashboard reads real PostgreSQL data',status==200 and d['configurations']==1453 and d['components']==143)
    for endpoint in ['products','stock','orders','options']:
        check(endpoint+' endpoint',api('/api/'+endpoint)[0]==200)
    d=api('/api/trace?id=11')[1];check('component recall recipients',len(d['recipients'])==2 and sum(x['shipped_qty'] for x in d['recipients'])==5)
    check('missing lot handled',api('/api/trace?id=99999999')[0]==400)
    check('missing CSRF token rejected',api('/api/orders',{},False)[0]==403)
    check('literal search injection is harmless',api('/api/products?q=%27%3B%20DROP%20TABLE%20supplier%3B--')[0]==200)
    before=sql('SELECT count(*) FROM supplytrace.sales_order');stock=sql('SELECT sum(reserved_qty) FROM supplytrace.inventory')
    status,d=api('/api/orders',{'retailer_id':1,'allocate':True,'lines':[{'sku':'IP17P-256-DB','qty':2},{'sku':'MBA13M4-512-MN','qty':1}]})
    check('failed second line rolls back entire create-and-allocate transaction',status==409 and 'insufficient' in d['error'] and before==sql('SELECT count(*) FROM supplytrace.sales_order') and stock==sql('SELECT sum(reserved_qty) FROM supplytrace.inventory'))
    check('fractional order quantity rejected',api('/api/orders',{'retailer_id':1,'lines':[{'sku':'IP17P-256-DB','qty':1.5}]})[0]==400)
    status,d=api('/api/orders',{'retailer_id':1,'allocate':True,'lines':[{'sku':'IP17P-256-DB','qty':2}]});check('create and allocate succeeds',status==200);oid=d['order_id']
    d=api('/api/order?id='+str(oid))[1];check('order details show allocations',d['order']['order_status']=='allocated' and len(d['allocations'])>0)
    allocation=d['allocations'][0]['allocation_id'];status,d=api('/api/dispatch',{'id':allocation,'qty':1});check('partial dispatch persists shipment',status==200 and api('/api/order?id='+str(oid))[1]['order']['order_status']=='partially_dispatched')
    status,d=api('/api/dispatch',{'id':allocation,'qty':1});check('remaining dispatch completes order',status==200 and api('/api/order?id='+str(oid))[1]['order']['order_status']=='dispatched')
    check('over-dispatch rejected',api('/api/dispatch',{'id':allocation,'qty':1})[0]==409)
    status,d=api('/api/orders',{'retailer_id':1,'allocate':False,'lines':[{'sku':'IP17P-256-DB','qty':1}]});oid=d['order_id']
    check('submitted order can be allocated later',api('/api/allocate',{'id':oid})[0]==200)
    allocation=api('/api/order?id='+str(oid))[1]['allocations'][0]
    check('quality hold succeeds',api('/api/hold',{'id':allocation['manufacturing_batch_id']})[0]==200)
    check('held batch cannot dispatch',api('/api/dispatch',{'id':allocation['allocation_id'],'qty':1})[0]==409)
    sql('SELECT supplytrace.assert_consistent()');check('final whole-database consistency',True)
    check('web role has no direct write permission',sql("SELECT has_table_privilege('tracey_web','supplytrace.inventory','UPDATE')")=='f')
finally:
    if proc:proc.terminate();proc.wait(timeout=10)
    run([BIN/'dropdb.exe',DB])
    Path('prototype/evidence').mkdir(exist_ok=True)
    Path('prototype/evidence/api_tests.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('Completed',len(results),'API checks; temporary database removed.')
