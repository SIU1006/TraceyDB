"""TraceyDB FastAPI service with Psycopg transactions."""
from pathlib import Path
import os,sys,json,secrets,threading,logging
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'))
import psycopg
import uvicorn
from fastapi import FastAPI,Request,Security
from fastapi.exceptions import RequestValidationError
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse,FileResponse
from pydantic import BaseModel,Field,StrictBool,StrictInt,ConfigDict
from typing import Annotated
PORT=int(os.environ.get('TRACEY_PORT','8765'))
TOKEN=secrets.token_urlsafe(32)
SLOTS=threading.BoundedSemaphore(2)
for k,v in {'PGHOST':'127.0.0.1','PGPORT':'55432','PGUSER':'tracey_web','PGDATABASE':'TraceyDB','PGCONNECT_TIMEOUT':'5','PGCLIENTENCODING':'UTF8'}.items():os.environ.setdefault(k,v)
class DatabaseError(Exception):pass

def transaction(fn,write=False):
    with SLOTS:
        try:
            with psycopg.connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SET LOCAL statement_timeout='20s'")
                    cur.execute("SET LOCAL lock_timeout='5s'")
                    cur.execute("SET LOCAL ROLE supplytrace_app")
                    cur.execute("SET LOCAL search_path=supplytrace,pg_catalog")
                    if not write:cur.execute('SET TRANSACTION READ ONLY')
                    result=fn(cur)
            return result
        except psycopg.Error as e:
            if isinstance(e,psycopg.OperationalError):
                raise DatabaseError('Database unavailable or request timed out. Check PostgreSQL and the connection settings.') from e
            raise DatabaseError(e.diag.message_primary or 'Database operation failed.') from e

def db(query,params=None,write=False):
    def execute(cur):
        result={}
        # Only fixed application SQL is split; values are bound separately by Psycopg.
        for statement in query.split(';'):
            if not statement.strip():continue
            cur.execute(statement,params)
            if cur.description:
                row=cur.fetchone()
                if row and isinstance(row[0],(dict,list)):result=row[0]
        return result
    return transaction(execute,write)

def create_order_transaction(retailer,lines,allocate):
    def execute(cur):
        cur.execute('SELECT pg_advisory_xact_lock(9120,1)')
        cur.execute('SELECT coalesce(max(order_id),0)+1 FROM sales_order')
        ident=cur.fetchone()[0]
        cur.execute('SELECT create_order(%s::integer,%s::integer,%s::text[],%s::integer[])',
                    (ident,retailer,[x['sku'] for x in lines],[x['qty'] for x in lines]))
        if allocate:cur.execute('SELECT allocate_order(%s::integer)',(ident,))
        return {'order_id':ident,'message':'Order saved successfully.'}
    return transaction(execute,True)

def array(query):return "SELECT coalesce(json_agg(t),'[]'::json) FROM ("+query+") t;"
def positive(value):
    if isinstance(value,bool) or not str(value).isdigit() or not 0<int(value)<=2147483647:raise ValueError('Enter a positive whole number.')
    return int(value)

SORT_COLUMNS={
    'products':{'product':'model_name','chip':'chip','storage':'storage_capacity_gb','colour':'colour','sku':'sku','available':'available'},
    'stock':{'product':'model_name','batch':'manufacturing_batch_id','warehouse':'city','on_hand':'on_hand_qty','reserved':'reserved_qty','eligible':'eligible','quality':'quality_status'},
    'orders':{'order':'order_id','retailer':'retailer_name','created':'ordered_at','units':'units','status':'order_status'}
}
def sorted_array(query,resource,p):
    key=p.get('sort',[''])[0]
    direction=p.get('direction',['asc'])[0]
    if direction not in ('asc','desc'):raise ValueError('Invalid sort direction.')
    if key:
        if key not in SORT_COLUMNS[resource]:raise ValueError('Invalid sort column.')
        column=SORT_COLUMNS[resource][key]
        tie={'products':'sku','stock':'inventory_id','orders':'order_id'}[resource]
        # Identifiers come exclusively from the allowlist; no request text becomes SQL.
        ordering=f'{column} {direction.upper()} NULLS LAST, {tie} ASC'
    else:
        ordering={'products':'model_name ASC,release_year DESC,sku ASC','stock':'inventory_id ASC','orders':'order_id DESC'}[resource]
    return array('SELECT * FROM ('+query+') results ORDER BY '+ordering+' LIMIT 31 OFFSET %(offset)s::integer')

def read_api(path,p):
    q=p.get('q',[''])[0][:100];offset=positive(p.get('page',['1'])[0])-1
    params={'q':'%'+q+'%','offset':offset*30,'id':p.get('id',['0'])[0]}
    if path=='/api/summary':
        return db("SELECT json_build_object('models',(SELECT count(*) FROM product_model),'configurations',(SELECT count(*) FROM product_configuration),'components',(SELECT count(*) FROM component),'available',(SELECT sum(i.on_hand_qty-i.reserved_qty) FROM inventory i JOIN manufacturing_batch m USING(manufacturing_batch_id) WHERE m.quality_status='released'),'held',(SELECT count(*) FROM manufacturing_batch WHERE quality_status='held'),'orders',(SELECT count(*) FROM sales_order),'status',(SELECT json_agg(t) FROM (SELECT order_status,count(*) AS count FROM sales_order GROUP BY order_status ORDER BY order_status) t),'database',current_database());")
    if path=='/api/products':
        return db(sorted_array("SELECT p.*,coalesce(s.available,0) AS available FROM product_catalogue p LEFT JOIN (SELECT m.sku,sum(i.on_hand_qty-i.reserved_qty) FILTER(WHERE m.quality_status='released') AS available FROM inventory i JOIN manufacturing_batch m USING(manufacturing_batch_id) GROUP BY m.sku) s USING(sku) WHERE p.display_name ILIKE %(q)s OR p.sku ILIKE %(q)s",'products',p),params)
    if path=='/api/stock':
        return db(sorted_array("SELECT i.*,m.sku,m.quality_status,p.model_name,p.chip,w.city,CASE WHEN m.quality_status='released' THEN i.on_hand_qty-i.reserved_qty ELSE 0 END AS eligible FROM inventory i JOIN manufacturing_batch m USING(manufacturing_batch_id) JOIN product_catalogue p USING(sku) JOIN warehouse w USING(warehouse_id) WHERE p.display_name ILIKE %(q)s OR m.manufacturing_batch_id::text ILIKE %(q)s OR w.city ILIKE %(q)s",'stock',p),params)
    if path=='/api/orders':
        return db(sorted_array("SELECT o.*,r.retailer_name,(SELECT sum(ordered_qty) FROM order_line l WHERE l.order_id=o.order_id) AS units FROM sales_order o JOIN retailer r USING(retailer_id) WHERE o.order_id::text ILIKE %(q)s OR r.retailer_name ILIKE %(q)s OR o.order_status ILIKE %(q)s",'orders',p),params)
    if path=='/api/options':
        return db("SELECT json_build_object('retailers',(SELECT json_agg(t) FROM (SELECT retailer_id,retailer_name FROM retailer ORDER BY retailer_id) t),'products',(SELECT json_agg(t) FROM (SELECT p.sku,p.display_name FROM product_catalogue p ORDER BY p.display_name) t));")
    if path=='/api/order':
        params['id']=positive(params['id'])
        order=db(array("SELECT o.*,r.retailer_name FROM sales_order o JOIN retailer r USING(retailer_id) WHERE order_id=%(id)s::integer"),params)
        if not order:raise ValueError('Order not found.')
        return {'order':order[0],'lines':db(array("SELECT l.*,p.display_name FROM order_line l JOIN product_catalogue p USING(sku) WHERE order_id=%(id)s::integer ORDER BY line_number"),params),'allocations':db(array("SELECT a.*,i.manufacturing_batch_id,w.city,m.quality_status,a.allocated_qty-coalesce((SELECT sum(shipped_qty) FROM shipment_line s WHERE s.allocation_id=a.allocation_id),0) AS remaining FROM stock_allocation a JOIN inventory i USING(inventory_id) JOIN manufacturing_batch m USING(manufacturing_batch_id) JOIN warehouse w USING(warehouse_id) WHERE a.order_id=%(id)s::integer ORDER BY a.allocation_id"),params),'shipments':db(array("SELECT s.*,sl.shipped_qty FROM shipment s JOIN shipment_line sl USING(shipment_id) WHERE order_id=%(id)s::integer ORDER BY shipment_id DESC"),params)}
    if path=='/api/trace':
        params['id']=positive(params['id'])
        lot=db(array("SELECT b.*,c.component_name,s.supplier_name FROM component_batch b JOIN component c USING(component_id) JOIN supplier s USING(supplier_id) WHERE component_batch_id=%(id)s::integer"),params)
        if not lot:raise ValueError('Component lot not found. Try lot 11 for the seeded recall example.')
        return {'lot':lot[0],'batches':db(array("SELECT m.*,p.model_name,u.quantity_used FROM batch_component_usage u JOIN manufacturing_batch m USING(manufacturing_batch_id) JOIN product_catalogue p USING(sku) WHERE component_batch_id=%(id)s::integer ORDER BY manufacturing_batch_id"),params),'stock':db(array("SELECT i.*,w.city,m.quality_status FROM inventory i JOIN warehouse w USING(warehouse_id) JOIN manufacturing_batch m USING(manufacturing_batch_id) WHERE EXISTS(SELECT FROM batch_component_usage u WHERE u.manufacturing_batch_id=i.manufacturing_batch_id AND u.component_batch_id=%(id)s::integer) ORDER BY inventory_id"),params),'recipients':db(array("SELECT s.shipment_id,s.order_id,r.retailer_name,s.delivery_address,i.manufacturing_batch_id,sum(sl.shipped_qty) AS shipped_qty FROM shipment_line sl JOIN shipment s USING(shipment_id) JOIN sales_order o USING(order_id) JOIN retailer r USING(retailer_id) JOIN stock_allocation a USING(allocation_id) JOIN inventory i USING(inventory_id) WHERE EXISTS(SELECT FROM batch_component_usage u WHERE u.manufacturing_batch_id=i.manufacturing_batch_id AND u.component_batch_id=%(id)s::integer) GROUP BY s.shipment_id,r.retailer_name,i.manufacturing_batch_id ORDER BY s.shipment_id"),params)}
    raise ValueError('Unknown endpoint.')

def write_api(path,data):
    if path=='/api/orders':
        retailer=positive(data.get('retailer_id'))
        lines=data.get('lines');allocate=data.get('allocate',False)
        if not isinstance(allocate,bool):raise ValueError('Invalid allocation option.')
        if not isinstance(lines,list) or not 1<=len(lines)<=20:raise ValueError('Add between 1 and 20 order lines.')
        clean=[]
        for line in lines:
            if not isinstance(line,dict):raise ValueError('Invalid order line.')
            sku=line.get('sku','')
            if not isinstance(sku,str) or not 1<=len(sku)<=100:raise ValueError('Select a valid product.')
            clean.append({'sku':sku,'qty':positive(line.get('qty'))})
        return create_order_transaction(retailer,clean,allocate)
    ident=positive(data.get('id'))
    if path=='/api/allocate':return db("SELECT allocate_order(%(id)s::integer); SELECT json_build_object('message','Stock allocated.');",{'id':ident},True)
    if path=='/api/hold':return db("SELECT hold_batch(%(id)s::integer); SELECT json_build_object('message','Batch placed on quality hold.');",{'id':ident},True)
    if path=='/api/dispatch':return db("SELECT json_build_object('shipment_id',dispatch_allocation(%(id)s::bigint,%(qty)s::integer),'message','Shipment dispatched.');",{'id':ident,'qty':positive(data.get('qty'))},True)
    raise ValueError('Unknown action.')


app=FastAPI(title='TraceyDB API',version='1.0.0',description='Local supply-chain operations backed by PostgreSQL transactions.')

@app.middleware('http')
async def protect(request:Request,call_next):
    if request.headers.get('host') not in (f'127.0.0.1:{PORT}',f'localhost:{PORT}'):
        return JSONResponse({'error':'Invalid host.'},status_code=403)
    if request.method=='POST':
        if request.headers.get('X-Tracey-Token')!=TOKEN:
            return JSONResponse({'error':'Reload this page before submitting.'},status_code=403)
        if request.headers.get('origin') not in (None,f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
            return JSONResponse({'error':'Invalid origin.'},status_code=403)
        body=b''
        async for chunk in request.stream():
            body+=chunk
            if len(body)>20000:return JSONResponse({'error':'Invalid request size.'},status_code=413)
        request._body=body
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    # FastAPI's interactive documentation uses its standard CDN assets.
    if request.url.path not in ('/docs','/redoc'):
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    return response

@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    return JSONResponse({'error':'Invalid request: '+ '; '.join('.'.join(map(str,e['loc']))+': '+e['msg'] for e in exc.errors())},status_code=400)
@app.exception_handler(ValueError)
async def value_error(request,exc):return JSONResponse({'error':str(exc)},status_code=400)
@app.exception_handler(DatabaseError)
async def database_error(request,exc):
    write=request.method=='POST'
    return JSONResponse({'error':str(exc),'rolled_back':write},status_code=409 if write else 503)

PositiveInt=Annotated[StrictInt,Field(gt=0,le=2147483647)]
class InputModel(BaseModel):
    model_config=ConfigDict(extra='forbid')
class OrderLine(InputModel):
    sku:str=Field(min_length=1,max_length=100)
    qty:PositiveInt
class CreateOrder(InputModel):
    retailer_id:PositiveInt
    lines:list[OrderLine]=Field(min_length=1,max_length=20)
    allocate:StrictBool=False
class Action(InputModel):
    id:PositiveInt
class Dispatch(Action):
    qty:PositiveInt

csrf_header=APIKeyHeader(name='X-Tracey-Token',auto_error=False,description='Use the token from GET /api/session.')

@app.get('/api/session')
def session():return {'token':TOKEN}
@app.get('/api/summary')
def summary():return read_api('/api/summary',{})
@app.get('/api/options')
def options():return read_api('/api/options',{})
@app.get('/api/products')
def products(q:str='',page:int=1,sort:str='',direction:str='asc'):return read_api('/api/products',{'q':[q],'page':[str(page)],'sort':[sort],'direction':[direction]})
@app.get('/api/stock')
def stock(q:str='',page:int=1,sort:str='',direction:str='asc'):return read_api('/api/stock',{'q':[q],'page':[str(page)],'sort':[sort],'direction':[direction]})
@app.get('/api/orders')
def orders(q:str='',page:int=1,sort:str='',direction:str='asc'):return read_api('/api/orders',{'q':[q],'page':[str(page)],'sort':[sort],'direction':[direction]})
@app.get('/api/order')
def order(id:int):return read_api('/api/order',{'id':[str(id)]})
@app.get('/api/trace')
def trace(id:int):return read_api('/api/trace',{'id':[str(id)]})
@app.post('/api/orders',dependencies=[Security(csrf_header)])
def save_order(body:CreateOrder):return write_api('/api/orders',body.model_dump())
@app.post('/api/allocate',dependencies=[Security(csrf_header)])
def allocate(body:Action):return write_api('/api/allocate',body.model_dump())
@app.post('/api/dispatch',dependencies=[Security(csrf_header)])
def dispatch(body:Dispatch):return write_api('/api/dispatch',body.model_dump())
@app.post('/api/hold',dependencies=[Security(csrf_header)])
def hold(body:Action):return write_api('/api/hold',body.model_dump())
@app.get('/',include_in_schema=False)
def index():return FileResponse(ROOT/'static/index.html')
@app.get('/app.js',include_in_schema=False)
def script():return FileResponse(ROOT/'static/app.js',media_type='text/javascript')
@app.get('/style.css',include_in_schema=False)
def style():return FileResponse(ROOT/'static/style.css',media_type='text/css')

if __name__=='__main__':
    uvicorn.run(app,host='127.0.0.1',port=PORT)
