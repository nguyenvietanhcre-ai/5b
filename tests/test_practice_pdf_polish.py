"""Print presentation must preserve snapshot identity and solution opt-in."""
import base64,copy,io,unittest
from pathlib import Path
from pypdf import PdfReader
from backend.practice_pdf import render_pdf
from backend.practice_export import identity
R=Path(__file__).resolve().parents[1]

class PrintPresentation(unittest.TestCase):
 def payload(self):
  return {'provider':'pilot','versionId':7,'revision':9,'questionKey':'PRINT-TEST','grade':5,'topicTitle':'Tỉ số và số phần','prompt':[{'type':'text','text':'Có 63 quyển sách, hai giá theo tỉ số 4 : 5. Tính số sách mỗi giá.'}],'text':'','responseMode':'choice','options':['28 quyển; 35 quyển','35 quyển; 28 quyển','27 quyển; 36 quyển','21 quyển; 42 quyển'],'answer':'28 quyển; 35 quyển','steps':['Tổng là 4 + 5 = 9 phần.','Một phần là 63 : 9 = 7 quyển.','Đáp số: Giá A 28 quyển; giá B 35 quyển.'],'thinking':[],'lesson':None,'assets':{}}
 def pdf(self,q=None,solutions=True,title='Luyện đề tổng hợp'):
  q=q or self.payload();code,digest=identity(q);document={'title':title,'examCode':'PRINT-ONLY','grade':5,'questions':[{'payload':q,'code':code}]};before=copy.deepcopy(document)
  data=render_pdf(document,include_solutions=solutions,frontend=R/'frontend');self.assertEqual(before,document);self.assertEqual((code,digest),identity(q));return PdfReader(io.BytesIO(data)),code
 def text(self,reader):return '\n'.join(p.extract_text() for p in reader.pages)
 def test_removed_print_copy_keeps_revision_identity_and_title(self):
  reader,code=self.pdf(title='Luyện theo nội dung · Tỉ số và số phần');text=self.text(reader)
  for old in ['Học liệu thí điểm tự biên soạn, chưa có giáo viên độc lập duyệt.','Họ và tên:',' · Phiên bản 9']:self.assertNotIn(old,text)
  self.assertIn('Luyện theo nội dung · Tỉ số và số phần',text);self.assertIn(code,text);self.assertIn('28 quyển; 35 quyển',text)
 def test_real_bold_font_embedded_for_answer_and_headings(self):
  reader,_=self.pdf();runs=[]
  for page in reader.pages:page.extract_text(visitor_text=lambda text,cm,tm,font,size:runs.append((text,str(font.get('/BaseFont','')) if font else '')))
  self.assertTrue(any('Đáp án:' in t and 'DejaVuSans-Bold' in font for t,font in runs));self.assertTrue(any('Luyện đề tổng hợp' in t and 'DejaVuSans-Bold' in font for t,font in runs))
  fonts=[font.get_object() for p in reader.pages for font in p['/Resources']['/Font'].values()];bold=[f for f in fonts if 'DejaVuSans-Bold' in str(f.get('/BaseFont'))];self.assertTrue(bold);self.assertTrue(all('/FontFile2' in f['/FontDescriptor'].get_object() for f in bold))
 def test_without_solutions_has_no_answer_or_lesson_payload(self):
  q=self.payload();q['steps']=['PRIVATE_SOLUTION_PRINT_SENTINEL'];reader,_=self.pdf(q,False);text=self.text(reader);self.assertNotIn('Đáp án:',text);self.assertNotIn('PRIVATE_SOLUTION_PRINT_SENTINEL',text);self.assertNotIn('Lời giải chi tiết',text);self.assertNotIn('/EmbeddedFiles',str(reader.trailer));self.assertNotIn('/JavaScript',str(reader.trailer))
 def test_rich_headings_inline_answer_and_vector_diagram_preserved(self):
  q=self.payload();svg='<svg xmlns="http://www.w3.org/2000/svg" width="360" height="140"><rect x="10" y="10" width="330" height="120" fill="#fff9ed" stroke="#1f6248"/><text x="25" y="65">A: 4 phần; B: 5 phần</text></svg>'
  q['assets']={'diagram':{'mime':'image/svg+xml','data':base64.b64encode(svg.encode()).decode()}};q['lesson']={'overview':[],'sections':[{'title':'Định hướng tư duy','blocks':[{'tag':'p','children':[{'type':'text','text':'Chia theo số phần bằng nhau.'}]}]},{'title':'Điểm mấu chốt','blocks':[{'tag':'p','children':[{'tag':'strong','children':[{'type':'text','text':'Tổng có 9 phần.'}]}]}]},{'title':'Bài giải chi tiết','blocks':[{'type':'media','sha256':'diagram','alt':'Sơ đồ tỉ số'},{'tag':'p','children':[{'type':'text','text':'Đáp số: '},{'tag':'strong','children':[{'type':'text','text':'Giá A 28 quyển; giá B 35 quyển.'}]}]}]}]}
  reader,_=self.pdf(q);text=self.text(reader)
  for expected in ['Định hướng tư duy','Điểm mấu chốt','Bài giải chi tiết','A: 4 phần; B: 5 phần','Giá A 28 quyển; giá B 35 quyển.']:self.assertIn(expected,text)
 def test_official_links_and_no_question_code_orphan(self):
  q=self.payload();code,_=identity(q);document={'title':'Luyện theo nội dung','examCode':'MULTIPAGE','grade':5,'questions':[{'payload':q,'code':code} for _ in range(20)]};reader=PdfReader(io.BytesIO(render_pdf(document,include_solutions=False,frontend=R/'frontend')));self.assertGreater(len(reader.pages),1)
  for p in reader.pages:
   text=p.extract_text();uris={str(a.get_object().get('/A',{}).get('/URI','')) for a in p.get('/Annots',[])};self.assertTrue({'https://5bmath.vn/','https://www.facebook.com/5bmath','https://zalo.me/0984763971'}<=uris)
   if code in text:self.assertIn('Có 63 quyển sách',text)

if __name__=='__main__':unittest.main()
