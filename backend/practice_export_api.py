"""Native localhost-only export adapter; no PDF imports before auth/gates."""
from http.server import HTTPServer
from urllib.parse import urlsplit,parse_qs
import hmac
from pathlib import Path
from . import platform_api as api

def available(handler):
    server=handler.server
    if getattr(server,'cloud_pdf_enabled',False) is True:
        return bool(getattr(server,'cloud_learning_provider',None) is getattr(server,'local_pilot',None) and api.same_origin(handler))
    if not isinstance(server,HTTPServer) or getattr(server,'native_python_backend',False) is not True or getattr(server,'practice_export_enabled',False) is not True:return False
    try:
        host=urlsplit('//'+handler.headers.get('Host',''))
        if host.username or host.password or host.path or host.query or host.fragment:return False
        if host.hostname not in ('localhost','127.0.0.1','::1') or host.port not in getattr(server,'practice_export_ports',frozenset()):return False
        public=api.public_origin()
        if public and urlsplit(public).hostname not in ('localhost','127.0.0.1','::1'):return False
    except (ValueError,AttributeError):return False
    return True

def dispatch(handler,method,path,body):
    if not available(handler):raise api.APIError('Tải PDF và tra cứu mã hiện chỉ mở trên bản Python/Docker localhost đã cấu hình.',503)
    export=path=='/api/v1/practice-export'
    if (export and method!='POST') or (not export and method!='GET'):raise api.APIError('Phương thức không hợp lệ.',405)
    query=parse_qs(urlsplit(handler.path).query)
    if export:
        provider=body.get('provider')
        if provider not in ('main','pilot'):raise api.APIError('Nguồn bài luyện tập không hợp lệ.')
    else:
        from .practice_export import normalize_code
        code=normalize_code(query.get('code',[''])[0]);query['code']=[code]
        if query.get('solutions',['0'])[0] not in ('0','1'):raise api.APIError('Lựa chọn lời giải không hợp lệ.')
        provider='pilot' if code.startswith('5B-P-') else 'main'
    if provider=='pilot':
        pilot=getattr(handler.server,'local_pilot',None)
        if pilot is None:raise api.APIError('Nguồn luyện tập cục bộ chưa sẵn sàng.',503)
        return pilot.request(handler,method,'practice/export' if export else 'practice/lookup',body,query),200
    from .practice_export import export_pdf,lookup
    with api.connect(handler.server.database_path,export) as db:
        session=api.read_session(handler,db)
        if not session:raise api.APIError('Em hãy đăng nhập để tiếp tục.',401)
        if export and (not api.same_origin(handler) or not hmac.compare_digest(handler.headers.get('X-CSRF-Token',''),session['csrf_token'])):raise api.APIError('Phiên đăng nhập cần được tải lại.',403)
        result=export_pdf(db,session,body,provider='main',frontend=Path(__file__).resolve().parents[1]/'frontend') if export else lookup(db,session,code,solutions=query.get('solutions',['0'])[0]=='1')
        return result,200
