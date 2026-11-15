"""Admin catalogue editor: optimistic revisions, no edits to paid snapshots/history."""
import json,re,secrets,sqlite3,unicodedata
from urllib.parse import parse_qs,urlsplit
from . import platform_api as api

KINDS={'series':('video_series','slug'),'videos':('series_videos','id'),
       'products':('exam_products','slug'),'sets':('premium_sets','slug')}
TRACKS={'super-hard':'Câu siêu khó','classification':'Phân loại học sinh','olympiad':'Thi học sinh giỏi','school':'Ôn theo trường'}
SCHOOLS={'cau-giay':'THCS Cầu Giấy','ngoai-ngu':'THCS Ngoại ngữ','ntt':'Nguyễn Tất Thành'}

def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(value).replace('đ','d').replace('Đ','D')).casefold() if not unicodedata.combining(c))

def controls(db):
    row=db.execute("SELECT value_json,revision FROM system_settings WHERE name='premium'").fetchone()
    return {**json.loads(row['value_json']),'revision':row['revision']}

def require_open(db,key):
    if not controls(db).get(key,True):raise api.APIError('Chức năng này đang được quản trị viên tạm dừng.',403)

def text(body,key,maximum=180,empty=False):
    value=body.get(key,'')
    if not isinstance(value,str) or len(value)>maximum or (not empty and not value.strip()):raise api.APIError('Kiểm tra nội dung '+key+'.')
    return value.strip()

def integer(value,minimum,maximum,label):
    if type(value) is not int or not minimum<=value<=maximum:raise api.APIError(label+' không hợp lệ.')
    return value

def slug(body,title):
    value=body.get('slug')
    if not value:
        plain=unicodedata.normalize('NFKD',title.replace('đ','d').replace('Đ','D')).encode('ascii','ignore').decode().lower()
        value=re.sub(r'[^a-z0-9]+','-',plain).strip('-')[:65]+'-'+secrets.token_hex(3)
    if not isinstance(value,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}',value):raise api.APIError('Mã nội dung chỉ dùng chữ thường không dấu, số và dấu gạch nối.')
    return value

def summary(row):
    r=dict(row)
    if 'question_version_ids_json' in r:r['questionIds']=json.loads(r.pop('question_version_ids_json'));r['questionCount']=len(r['questionIds'])
    return r

def question(db,identity):
    row=db.execute('SELECT v.id,v.status,v.difficulty,v.prompt_json,q.question_code,q.grade_id,v.options_json FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE v.id=?',(identity,)).fetchone()
    if not row:return {'id':identity,'status':'missing','title':'Câu không còn trong kho'}
    prompt=' '.join(str(b.get('text','')) for b in json.loads(row['prompt_json']) if isinstance(b,dict))
    return {'id':row['id'],'code':row['question_code'],'grade':row['grade_id'],'status':row['status'],'title':prompt[:300],
            'format':'Trắc nghiệm' if json.loads(row['options_json']) else 'Điền đáp án','difficulty':row['difficulty']}

def get_item(db,kind,identity):
    table,key=KINDS[kind];row=db.execute('SELECT * FROM '+table+' WHERE '+key+'=?',(identity,)).fetchone()
    if not row:raise api.APIError('Không tìm thấy nội dung.',404)
    result=summary(row)
    if kind in ('products','sets'):result['questions']=[question(db,q) for q in result['questionIds']]
    return result

def listing(db,kind,query):
    table,key=KINDS[kind];q=query.get('q',[''])[0][:160];state=query.get('status',['all'])[0];grade=query.get('grade',['0'])[0]
    if state not in ('all','published','draft','archived','active'):raise api.APIError('Bộ lọc trạng thái không hợp lệ.')
    try:page=integer(int(query.get('page',['1'])[0]),1,100000,'Số trang');grade=integer(int(grade),0,5,'Khối')
    except ValueError:raise api.APIError('Bộ lọc không hợp lệ.')
    where=' WHERE 1=1';args=[]
    if state=='archived':where+=' AND archived=1'
    elif state!='all':
        where+=' AND archived=0'
        if kind!='series' and state in ('published','draft'):where+=' AND published=?';args.append(int(state=='published'))
    if grade and kind in ('products','sets'):where+=' AND grade=?';args.append(grade)
    if kind=='videos' and query.get('series',[''])[0]:where+=' AND series_slug=?';args.append(query['series'][0])
    order='position,'+key if kind in ('series','videos') else 'title,'+key
    if q:
        matches=[row[key] for row in db.execute('SELECT '+key+',title FROM '+table+where+' ORDER BY '+order,args) if fold(q) in fold(row['title']+' '+str(row[key]))]
        total=len(matches);rows=[summary(db.execute('SELECT * FROM '+table+' WHERE '+key+'=?',(identity,)).fetchone()) for identity in matches[(page-1)*25:page*25]]
    else:
        total=db.execute('SELECT count(*) FROM '+table+where,args).fetchone()[0]
        rows=[summary(row) for row in db.execute('SELECT * FROM '+table+where+' ORDER BY '+order+' LIMIT 25 OFFSET ?',(*args,(page-1)*25))]
    return {'rows':rows,'total':total,'page':page,'pageSize':25,'series':[dict(r) for r in db.execute('SELECT slug,title,archived FROM video_series ORDER BY position,slug')],'tracks':TRACKS,'schools':SCHOOLS}

def save_item(db,user,kind,body):
    from .staff_api import audit
    table,key=KINDS[kind];identity=body.get('identity');old=get_item(db,kind,identity) if identity is not None else None
    if kind=='videos' and identity is not None:integer(identity,1,2**63-1,'Mã video')
    if old and (type(body.get('revision')) is not int or body['revision']!=old['revision']):raise api.APIError('Nội dung vừa thay đổi. Tải lại trước khi lưu.',409)
    allowed={'identity','revision','title','slug','archived','position','series_slug','media_url','published','description','price','grade','duration_minutes','questionIds','track','school'}
    if not isinstance(body,dict) or set(body)-allowed:raise api.APIError('Trường dữ liệu không hợp lệ.')
    title=text(body,'title');archived=body.get('archived',False)
    if type(archived) is not bool:raise api.APIError('Trạng thái lưu trữ không hợp lệ.')
    values={'title':title,'archived':int(archived)}
    if kind in ('series','videos'):
        position=body.get('position')
        if position is None:position=db.execute('SELECT coalesce(max(position),0)+1 FROM '+table).fetchone()[0]
        values['position']=integer(position,1,1000000,'Thứ tự')
    if kind=='videos':
        series=text(body,'series_slug',100);parent=db.execute('SELECT archived FROM video_series WHERE slug=?',(series,)).fetchone()
        if not parent:raise api.APIError('Chọn series đã có.')
        url=text(body,'media_url',2000,empty=True);p=urlsplit(url)
        if url and (p.scheme!='https' or not p.netloc or p.username or p.password or '\\' in url or any(ord(c)<32 for c in url)):raise api.APIError('Dùng liên kết video HTTPS hợp lệ.')
        values.update(series_slug=series,media_url=url)
    if kind!='series':
        published=body.get('published',False)
        if type(published) is not bool or (published and archived):raise api.APIError('Nội dung lưu trữ không thể phát hành.')
        values['published']=int(published)
        if kind=='videos' and published and (not values['media_url'] or parent['archived']):raise api.APIError('Cần video HTTPS và series đang hoạt động trước khi phát hành.')
    if kind in ('products','sets'):
        grade=integer(body.get('grade'),1,5,'Khối');minutes=integer(body.get('duration_minutes'),1,180,'Thời gian')
        ids=body.get('questionIds',[])
        if not isinstance(ids,list) or len(ids)>100 or any(type(q) is not int or q<1 for q in ids) or len(set(ids))!=len(ids):raise api.APIError('Chọn tối đa 100 phiên bản câu, không trùng.')
        if values['published'] and not ids:raise api.APIError('Chọn câu hỏi trước khi phát hành.')
        for q in ids:
            found=question(db,q)
            if found.get('grade')!=grade or (values['published'] and found['status']!='published'):raise api.APIError('Có câu không cùng khối hoặc chưa phát hành; lưu nháp để rà lại.')
        values.update(grade=grade,duration_minutes=minutes,question_version_ids_json=api.packed(ids))
        if kind=='products':values.update(description=text(body,'description',4000,True),price=integer(body.get('price'),1,10**12,'Giá bán'))
        else:
            track=body.get('track');school=body.get('school') or None
            if track not in TRACKS:raise api.APIError('Nhóm nội dung không hợp lệ.')
            if track=='school' and (grade!=5 or school not in SCHOOLS):raise api.APIError('Ôn theo trường dành cho khối 5 và cần chọn trường.')
            values.update(track=track,school=school if track=='school' else None)
    try:
        if old:
            db.execute('UPDATE '+table+' SET '+','.join(k+'=?' for k in values)+',revision=revision+1 WHERE '+key+'=?',(*values.values(),identity))
        else:
            if key=='slug':values['slug']=slug(body,title)
            cols=','.join(values);new=db.execute('INSERT INTO '+table+'('+cols+') VALUES ('+','.join('?' for _ in values)+')',tuple(values.values())).lastrowid
            identity=values['slug'] if key=='slug' else new
    except sqlite3.IntegrityError:raise api.APIError('Mã hoặc thứ tự đang trùng nội dung khác. Hãy chọn giá trị khác.',409)
    audit(db,user,'update' if old else 'create','catalogue_'+kind,str(identity),title+(' · Lưu trữ' if archived else ' · Phát hành' if values.get('published') else ' · Bản nháp' if kind!='series' else ''))
    return {'item':get_item(db,kind,identity),'saved':True}

def question_list(db,query):
    try:grade=integer(int(query.get('grade',['5'])[0]),1,5,'Khối');page=integer(int(query.get('page',['1'])[0]),1,100000,'Trang')
    except ValueError:raise api.APIError('Bộ lọc câu không hợp lệ.')
    q=query.get('q',[''])[0][:160]
    where=" FROM question_versions v JOIN questions q ON q.id=v.question_id WHERE q.grade_id=? AND v.status='published' AND v.revision=(SELECT max(n.revision) FROM question_versions n WHERE n.question_id=q.id AND n.status='published') AND (instr(lower(q.question_code),lower(?))>0 OR instr(lower(v.prompt_json),lower(?))>0)"
    total=db.execute('SELECT count(*)'+where,(grade,q,q)).fetchone()[0]
    return {'rows':[question(db,r[0]) for r in db.execute('SELECT v.id'+where+' ORDER BY q.question_code LIMIT 25 OFFSET ?',(grade,q,q,(page-1)*25))],'total':total,'page':page,'pageSize':25}

def move_item(db,user,kind,body):
    from .staff_api import audit
    table,key=KINDS[kind];old=get_item(db,kind,body.get('identity'))
    if type(body.get('revision')) is not int or body['revision']!=old['revision']:raise api.APIError('Thứ tự vừa thay đổi. Tải lại.',409)
    direction=body.get('direction')
    if direction not in ('up','down'):raise api.APIError('Hướng sắp xếp không hợp lệ.')
    where=' AND series_slug=?' if kind=='videos' else '';args=[old['position']]+([old['series_slug']] if kind=='videos' else [])
    compare,order=('<','DESC') if direction=='up' else ('>','ASC')
    other=db.execute('SELECT * FROM '+table+' WHERE position'+compare+'?'+where+' ORDER BY position '+order+' LIMIT 1',args).fetchone()
    if other:
        temporary=db.execute('SELECT max(position)+1 FROM '+table).fetchone()[0]
        db.execute('UPDATE '+table+' SET position=? WHERE '+key+'=?',(temporary,old[key]))
        db.execute('UPDATE '+table+' SET position=?,revision=revision+1 WHERE '+key+'=?',(old['position'],other[key]))
        db.execute('UPDATE '+table+' SET position=?,revision=revision+1 WHERE '+key+'=?',(other['position'],old[key]))
        audit(db,user,'reorder','catalogue_'+kind,str(old[key]),old['title']+' · '+direction)
    return {'saved':True}

def management(handler,db):
    from .system_settings import settings
    from .admin_native import overview as native_overview
    from .payments import automation_enabled,bank_configuration
    counters={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('video_series','series_videos','exam_products','premium_sets','accounts','exam_attempts','account_scratchpads')}
    native=native_overview(handler)
    return {'counts':counters,'native':native,'controls':controls(db),'platform':settings(db),
            'payments':{'automationEnabled':automation_enabled(),'bankConfigured':all(bank_configuration())},
            'groups':[
                {'title':'Nội dung và học tập','items':[
                    {'title':'Series và video','tab':'videoSeries','copy':'Tạo series, thêm video HTTPS, sắp thứ tự, nháp/phát hành/lưu trữ.'},
                    {'title':'Gói đề bán riêng','tab':'examProducts','copy':'Giá, khối, thời gian, chọn câu và thứ tự; đơn cũ giữ snapshot.'},
                    {'title':'Nội dung VIP+','tab':'vipContent','copy':'Ôn theo trường, câu siêu khó, phân loại, HSG.'},
                    {'title':'Bài giảng lớp 5 đang dùng','tab':'nativeLessons','copy':'Biên tập ba khung, lưu nháp/phát hành phiên bản mới, giữ bản cũ và câu tự kiểm tra.'},
                    {'title':'Chuyên đề, bài giảng và ngân hàng quản trị','tab':'content','copy':'Quản lý học liệu và phiên bản câu của kho chính; kho thí điểm lớp 5 được tách rõ.'}]},
                {'title':'Học sinh và lớp học','items':[
                    {'title':'Học sinh và gói quyền','tab':'accounts','copy':'Hồ sơ, khối, Free/VIP/VIP+/SVip, hạn quyền, linh vật/XP, khóa/khôi phục.'},
                    {'title':'Lớp Zoom và học phí','tab':'classes','copy':'Lịch/buổi học, ghi danh, bài tập/tệp nộp, điểm danh, chấm điểm, tính phí.'},
                    {'title':'Đăng ký đầu vào','tab':'admissions','copy':'Phụ huynh, nhu cầu học, trạng thái tư vấn và ghi chú.'}]},
                {'title':'Kinh doanh và vận hành','items':[
                    {'title':'Đối soát và giao dịch','tab':'payments','copy':'VIP/VIP+, mua đề, học phí, giao dịch ngân hàng và hỗ trợ thưởng giới thiệu.'},
                    {'title':'Gửi thông báo','tab':'notifications','copy':'Theo nhóm gói, gồm VIP+, hoặc theo lớp; xem số người nhận trước khi gửi.'},
                    {'title':'Cấu hình chức năng và hạn mức','tab':'settings','copy':'Bật/tạm dừng đăng ký, học, luyện, game, bảng hạng và hạn mức Free.'},
                    {'title':'Video, bán đề và quyền học nâng cao','tab':'operations','copy':'Bật/tạm dừng từng nhóm, xem trạng thái dữ liệu/thanh toán.'},
                    {'title':'Nhân sự và phân quyền','tab':'users','copy':'Giáo viên/admin, lớp phụ trách, khóa tài khoản và đổi mật khẩu.'},
                    {'title':'Nhật ký thay đổi','tab':'audit','copy':'Lịch sử người lưu, nội dung và thời gian; nhật ký bài giảng lớp 5 có trong mục tương ứng.'}]}],
            'protected':[
                'Đáp án, điểm, đơn đã thanh toán và lịch sử bài làm được quản lý qua đúng nghiệp vụ; không sửa trực tiếp để tránh mất tính nhất quán.',
                'Kho câu luyện lớp 5 thí điểm và ảnh/animation/luật game dùng nguồn đã kiểm soát. Trang này có điều khiển vận hành, không sửa mã game hoặc thay nguồn đã khóa.',
                'Nháp tài khoản và thứ tự PDF hoạt động tự động. Video nhập bằng URL, chưa tải tệp video lên máy chủ.',
                'Khóa ngân hàng/webhook và triển khai website thuộc cấu hình vận hành riêng, không đưa bí mật vào biểu mẫu quản trị.']}

def dispatch(handler,db,user,method,path,body):
    if method=='POST' and not isinstance(body,dict):raise api.APIError('Dữ liệu cần là một đối tượng JSON.')
    query=parse_qs(urlsplit(handler.path).query)
    if path=='/api/staff/management' and method=='GET':return management(handler,db),200
    move=re.fullmatch(r'/api/staff/catalogue/(series|videos)/move',path)
    if move and method=='POST':return move_item(db,user,move[1],body),200
    if path=='/api/staff/catalogue/questions' and method=='GET':return question_list(db,query),200
    if path=='/api/staff/catalogue/controls':
        if method=='GET':return {'controls':controls(db)},200
        current=controls(db)
        if type(body.get('revision')) is not int or body['revision']!=current['revision']:raise api.APIError('Cấu hình vừa thay đổi. Tải lại.',409)
        keys=('videos_open','sales_open','advanced_open')
        if set(body)!={'revision',*keys} or any(type(body.get(k)) is not bool for k in keys):raise api.APIError('Cấu hình không hợp lệ.')
        db.execute("UPDATE system_settings SET value_json=?,revision=revision+1,updated_at=?,staff_id=? WHERE name='premium'",(api.packed({k:body[k] for k in keys}),api.stamp(),user['id']))
        from .staff_api import audit
        audit(db,user,'update','settings','premium','Bật/tạm dừng video, mở bán đề, nội dung VIP+')
        return {'controls':controls(db)},200
    match=re.fullmatch(r'/api/staff/catalogue/(series|videos|products|sets)(?:/([a-zA-Z0-9-]+))?',path)
    if match:
        kind,identity=match.groups()
        if identity is not None and kind=='videos':
            try:identity=int(identity)
            except ValueError:raise api.APIError('Mã video không hợp lệ.')
        if method=='GET':return ({'item':get_item(db,kind,identity)} if identity is not None else listing(db,kind,query)),200
        if method=='POST' and identity is None:return save_item(db,user,kind,body),200
    raise api.APIError('API quản lý nội dung không tồn tại.',404)
