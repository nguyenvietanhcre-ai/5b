"""Persistent site-wide maintenance switch and a self-contained recovery portal."""
import base64
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from . import platform_api as api

PORTAL = '/quan-tri/bao-tri/'
ENDPOINT = '/api/staff/site-visibility'
RECOVERY = {ENDPOINT, ENDPOINT+'/session', ENDPOINT+'/login', ENDPOINT+'/logout'}

def state(db):
    row = db.execute("SELECT value_json,revision,updated_at FROM system_settings WHERE name='website_visibility'").fetchone()
    if not row:return {'hidden':False,'revision':0,'updatedAt':None}
    value=json.loads(row['value_json'])
    if type(value.get('hidden')) is not bool:raise api.APIError('Chưa đọc được trạng thái website.',503)
    return {'hidden':value['hidden'],'revision':row['revision'],'updatedAt':row['updated_at']}

def read(path):
    if hasattr(path,'connect'):
        with api.connect(path) as db:return state(db)
    # A status probe must never create a database if storage is unavailable.
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=15)) as db:
        db.row_factory=sqlite3.Row
        return state(db)

def save(db,user,body):
    from .staff_api import require_admin,audit
    require_admin(user)
    if not isinstance(body,dict) or set(body)!={'hidden','revision'} or type(body['hidden']) is not bool or type(body['revision']) is not int:
        raise api.APIError('Chọn trạng thái website hợp lệ.')
    current=state(db)
    if body['revision']!=current['revision']:raise api.APIError('Trạng thái vừa được admin khác thay đổi. Tải lại trước khi lưu.',409)
    if body['hidden']==current['hidden']:return {'visibility':current}
    values=(json.dumps({'hidden':body['hidden']}),api.stamp(),user['id'])
    if current['revision']==0:
        db.execute("INSERT INTO system_settings(name,value_json,updated_at,staff_id) VALUES ('website_visibility',?,?,?)",values)
    else:
        cursor=db.execute("UPDATE system_settings SET value_json=?,updated_at=?,staff_id=?,revision=revision+1 WHERE name='website_visibility' AND revision=?",(*values,current['revision']))
        if cursor.rowcount!=1:raise api.APIError('Trạng thái vừa thay đổi. Tải lại trước khi lưu.',409)
    audit(db,user,'visibility','website','main','Ẩn website để bảo trì' if body['hidden'] else 'Mở website công khai')
    return {'visibility':state(db)}

def exempt(method,path):
    return (path in RECOVERY and method in ('GET','POST') or
            path in (PORTAL,PORTAL.rstrip('/')) and method in ('GET','HEAD') or
            path=='/api/health' and method in ('GET','HEAD') or
            path=='/api/webhooks/sepay' and method=='POST')

STYLE='''*{box-sizing:border-box}html{color-scheme:light}body{margin:0;min-height:100svh;display:grid;place-items:center;padding:24px 16px;background:#FFF9ED;color:#203A32;font:17px/1.6 Arial,sans-serif}main{width:min(100%,720px);padding:clamp(24px,6vw,60px);background:#fffdf7;border:1px solid #e3dfc4;border-radius:32px;box-shadow:0 18px 65px #1f624815;text-align:center}img{width:clamp(160px,42vw,240px);height:auto;max-width:100%}.mark{display:grid;place-items:center;margin:30px auto 20px;width:88px;height:88px;border-radius:30px;background:#edf3dc;font-size:42px;color:#1F6248}h1{font-size:clamp(26px,5vw,38px);line-height:1.25;margin:16px 0}p{margin:12px 0}.subtitle{font-size:clamp(18px,3vw,22px);color:#486254}.line{width:56px;height:5px;background:#FFBE73;border-radius:5px;margin:28px auto}footer{font-size:14px;color:#597164;margin-top:30px}form{text-align:left;margin-top:24px}label{display:block;margin:14px 0}input[type=text],input[type=password]{display:block;width:100%;font:inherit;border:1px solid #a0b8a4;border-radius:12px;padding:12px;margin-top:5px}fieldset{border:1px solid #b7cbb6;border-radius:16px;padding:12px 18px}fieldset label{min-height:44px;display:flex;gap:12px;align-items:center}input[type=radio]{width:20px;height:20px;accent-color:#1F6248}button,a.btn{display:inline-block;font:inherit;font-weight:700;border:0;border-radius:14px;background:#1F6248;color:#fff;padding:12px 20px;min-height:48px;cursor:pointer;text-decoration:none;margin:8px 4px 8px 0}button:disabled{opacity:.6;cursor:wait}button.secondary{background:#edf3dc;color:#203A32}a{color:#1F6248;overflow-wrap:anywhere}small{display:block;color:#597164}#status{min-height:28px;overflow-wrap:anywhere}#status.error{color:#a33119}[hidden]{display:none!important}:focus-visible{outline:3px solid #FFBE73;outline-offset:4px}@media(max-height:500px){body{place-items:start center}main{padding:24px}.mark{margin:18px auto}}'''

SCRIPT=r'''(()=>{let csrf='',revision=0;const $=id=>document.getElementById(id),note=(s,bad=false)=>{$('status').textContent=s;$('status').className=bad?'error':'';};async function call(path,body){const r=await fetch('/api/staff/site-visibility'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body===undefined?undefined:JSON.stringify(body)});const data=await r.json();if(!r.ok)throw Error(data.error||'Chưa kết nối được máy chủ.');return data;}async function refresh(){const s=await call('/session');$('login').hidden=s.authenticated;$('control').hidden=true;if(!s.authenticated){csrf='';return;}csrf=s.csrf;const v=(await call('')).visibility;revision=v.revision;document.querySelector('[name=visibility][value='+String(v.hidden)+']').checked=true;$('current').textContent=v.hidden?'Website đang ẩn · khách truy cập chỉ thấy thông báo bảo trì.':'Website đang công khai · các chức năng hoạt động bình thường.';$('control').hidden=false;}async function run(form,fn){const b=form.querySelector('button[type=submit]');if(b.disabled)return;b.disabled=true;try{await fn();}catch(e){note(e.message,true);}finally{b.disabled=false;}}$('login').onsubmit=e=>{e.preventDefault();run(e.target,async()=>{const f=new FormData(e.target);await call('/login',{login:f.get('login'),password:f.get('password')});e.target.reset();await refresh();note('Đã đăng nhập quản trị.');});};$('control').onsubmit=e=>{e.preventDefault();run(e.target,async()=>{const hidden=new FormData(e.target).get('visibility')==='true';if(hidden&&!confirm('Ẩn toàn bộ website và hiển thị thông báo bảo trì?'))return;await call('',{hidden,revision});await refresh();note(hidden?'Đã ẩn website. Anh có thể mở lại tại trang này.':'Đã mở website công khai.');});};$('logout').onclick=async()=>{try{await call('/logout',{});await refresh();note('Đã đăng xuất.');}catch(e){note(e.message,true);}};refresh().catch(e=>note(e.message,true));})();'''

def page(admin=False):
    logo=base64.b64encode((Path(__file__).resolve().parent.parent/'frontend/5bmath-logo.svg').read_bytes()).decode()
    if admin:
        title='Vận hành website'
        content='''<h1>Vận hành website</h1><p>Chỉ quản trị viên được đổi trạng thái công khai hoặc ẩn website.</p><p id="status" role="status" aria-live="polite"></p><form id="login"><h2>Đăng nhập quản trị</h2><label>Tên đăng nhập<input name="login" type="text" autocomplete="username" required maxlength="100"></label><label>Mật khẩu<input name="password" type="password" autocomplete="current-password" required maxlength="128"></label><button type="submit">Đăng nhập</button></form><form id="control" hidden><p id="current"></p><fieldset><legend>Trạng thái website</legend><label><input name="visibility" type="radio" value="false">Công khai website</label><label><input name="visibility" type="radio" value="true">Ẩn website để bảo trì</label></fieldset><p><small>Khi ẩn, mọi đường dẫn thông thường đều hiển thị thông báo cập nhật. Lối quản trị này luôn được giữ để mở lại website. Dữ liệu được giữ nguyên.</small></p><button type="submit">Lưu trạng thái website</button><button type="button" class="secondary" id="logout">Đăng xuất</button><p><a href="/quan-tri/#operations">Về trang quản trị khi website công khai</a></p></form><noscript><p>Cần bật JavaScript để đăng nhập và đổi trạng thái website.</p></noscript>'''
    else:
        title='Hệ thống đang được cập nhật'
        content='<div class="mark" aria-hidden="true">🌱</div><h1>Hệ thống đang được cập nhật</h1><p class="subtitle">Vui lòng quay lại sau.</p><div class="line" aria-hidden="true"></div><p>5BMath đang chăm chút để mang đến trải nghiệm học Toán tốt hơn.</p>'
    return ('<!doctype html><html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>'+title+' | 5BMath</title><style>'+STYLE+'</style></head><body><main><img src="data:image/svg+xml;base64,'+logo+'" alt="5BMath — Gieo Mầm Toán" width="628" height="168">'+content+'<footer>5BMath · Gieo Mầm Toán</footer></main>'+('<script>'+SCRIPT+'</script>' if admin else '')+'</body></html>').encode()

def headers(admin=False):
    policy="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    if admin:policy+="; connect-src 'self'; script-src 'sha256-"+base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()+"'"
    return {'Cache-Control':'no-store','Content-Type':'text/html; charset=utf-8','X-Robots-Tag':'noindex, nofollow','X-Content-Type-Options':'nosniff','Content-Security-Policy':policy,**({} if admin else {'Retry-After':'300','X-5BMath-Maintenance':'1'})}
