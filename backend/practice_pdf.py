"""Native PDF rendering. No data access; only already-authorized snapshots."""
import base64,io,re
from pathlib import Path
from xml.sax.saxutils import escape
from . import platform_api as api

def ordered_questions(questions):
    return sorted(questions,key=lambda item: {'choice':0,'typed':1}.get(item['payload']['responseMode'],2))

def render_pdf(document,*,include_solutions,frontend):
    document={**document,'questions':ordered_questions(document['questions'])}
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle,KeepTogether
        from reportlab.graphics import renderPDF
        import sys
        if sys.platform=='emscripten':
            from .svg_pdf import svg2rlg
        else:
            from svglib.svglib import svg2rlg
    except ImportError as error:raise api.APIError('Máy chủ này chưa hỗ trợ PDF. Tải PDF hiện chỉ mở trên bản Python/Docker cục bộ.',503) from error
    frontend=Path(frontend);font=frontend/'print-art/DejaVuSans.ttf';bold_font=frontend/'print-art/DejaVuSans-Bold.ttf';watermark=frontend/'print-art/mam-sach-3d.png';logo=frontend/'5bmath-logo.svg'
    if not all(p.is_file() for p in [font,bold_font,watermark,logo]):raise api.APIError('Thiếu tài sản in chính thức; chưa tạo PDF.',503)
    if '5BPrint' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('5BPrint',str(font)))
    if '5BPrintBold' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('5BPrintBold',str(bold_font)))
    pdfmetrics.registerFontFamily('5BPrint',normal='5BPrint',bold='5BPrintBold',italic='5BPrint',boldItalic='5BPrintBold')
    green=colors.HexColor('#1F6248');dark=colors.HexColor('#203A32');apricot=colors.HexColor('#FFBE73');pale=colors.HexColor('#FFF9ED')
    body=ParagraphStyle('Body',fontName='5BPrint',fontSize=10.5,leading=16,textColor=dark,spaceAfter=6,splitLongWords=True)
    question_body=ParagraphStyle('QuestionBody',parent=body,fontName='5BPrintBold')
    question_mode=False
    small=ParagraphStyle('Small',parent=body,fontSize=8,leading=12,textColor=green)
    heading=ParagraphStyle('Heading',parent=body,fontName='5BPrintBold',fontSize=18,leading=24,spaceBefore=8,spaceAfter=10,keepWithNext=True,textColor=green)
    qhead=ParagraphStyle('Question',parent=heading,fontSize=11.5,leading=17,spaceBefore=13,spaceAfter=4)
    section=ParagraphStyle('Section',parent=qhead,fontSize=11,leading=17,spaceBefore=10,spaceAfter=7,backColor=pale,borderColor=colors.HexColor('#E5D8B9'),borderWidth=.4,borderPadding=5)
    answer_style=ParagraphStyle('Answer',parent=body,fontName='5BPrintBold',fontSize=11,leading=17,backColor=colors.HexColor('#EDF5E9'),borderColor=colors.HexColor('#AEC8AA'),borderWidth=.5,borderPadding=6,spaceBefore=7,spaceAfter=10,keepWithNext=True)
    code_style=ParagraphStyle('Code',parent=small,keepWithNext=True,spaceAfter=7)
    story=[]
    def para(text,style=body):return Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    def inline(value):
        if isinstance(value,list):return ''.join(inline(x) for x in value)
        if isinstance(value,(str,int,float)):return escape(str(value)).replace('\n','<br/>')
        if not isinstance(value,dict):return ''
        if value.get('type') in ('text','math'):return escape(str(value.get('text',value.get('latex','')))).replace('\n','<br/>')
        tag=value.get('tag');content=inline(value.get('children',[]))
        if tag in ('strong','b'):return '<b>'+content+'</b>'
        if tag in ('em','i'):return '<i>'+content+'</i>'
        return '<br/>' if tag=='br' else content
    def has_visual(value):
        if isinstance(value,list):return any(has_visual(x) for x in value)
        return isinstance(value,dict) and (value.get('type') in ('media','image','svg') or value.get('assetId') or value.get('asset_id') or any(has_visual(x) for x in value.get('children',[])))
    def prose(value,prefix=''):
        text=prefix+text_only(value)
        answer=bool(re.search(r'(^|[\n.;])\s*(?:Đáp\s*(?:số|án)|Kết\s*quả)\s*:',text,re.I))
        markup=inline(value)
        if not question_mode:
            markup=re.sub(r'(^|<br\s*/?>)(\s*)((?:Tiên quyết|Em thử nghĩ|Dễ nhầm|Thử lại|Vận dụng)(?:\s*:)?)' + r'(?=\s|$|<)',lambda m:m[1]+m[2]+'<b>'+m[3]+'</b>',markup,flags=re.I)
        return Paragraph(escape(prefix)+markup,question_body if question_mode else answer_style if answer else body)
    def drawing(data,width=460,height=245):
        image=svg2rlg(io.BytesIO(data))
        if image is None:raise api.APIError('Hình SVG không thể dựng đầy đủ trong PDF.',503)
        ratio=min(width/image.width,height/image.height,1);image.width*=ratio;image.height*=ratio;image.scale(ratio,ratio)
        # SVG diagrams retain vector geometry; use embedded Vietnamese font.
        def fonts(node):
            if hasattr(node,'fontName'):node.fontName='5BPrint'
            for child in getattr(node,'contents',[]):fonts(child)
        fonts(image);return image
    def media(asset,alt=''):
        raw=base64.b64decode(asset['data'])
        if asset['mime']=='image/svg+xml':result=[drawing(raw)]
        else:
            reader=ImageReader(io.BytesIO(raw));w,h=reader.getSize();ratio=min(460/w,245/h,1);result=[Image(io.BytesIO(raw),width=w*ratio,height=h*ratio)]
        if alt:result.append(para(alt,small))
        return result+[Spacer(1,5)]
    def rich(value,assets):
        if value is None:return []
        if isinstance(value,list):
            result=[]
            for v in value:result.extend(rich(v,assets))
            return result
        if isinstance(value,(str,int,float)):return [prose(value)]
        if not isinstance(value,dict):return []
        kind=value.get('type');tag=value.get('tag')
        if kind=='media':
            asset=assets.get(value.get('sha256'))
            if not asset:raise api.APIError('Thiếu hình đúng phiên bản để in.',503)
            return media(asset,value.get('alt',''))
        if kind in ('image','svg') or value.get('assetId') or value.get('asset_id'):
            key='legacy:'+str(value.get('assetId',value.get('asset_id',value.get('id',''))));asset=assets.get(key)
            if not asset:raise api.APIError('Thiếu hình câu hỏi để in.',503)
            return media(asset,value.get('alt',asset.get('alt','')))
        if kind in ('text','math'):return [prose(value)]
        children=value.get('children',[])
        if tag=='table':
            def rows(nodes):
                result=[]
                for n in nodes:
                    if n.get('tag')=='tr':result.append(n)
                    elif isinstance(n,dict):result.extend(rows(n.get('children',[])))
                return result
            data=[]
            for row in rows(children):data.append([rich(cell.get('children',[]),assets) or [para('')] for cell in row.get('children',[]) if cell.get('tag') in ('td','th')])
            if not data:return []
            count=max(map(len,data));data=[row+[[]]*(count-len(row)) for row in data];table=Table(data,colWidths=[460/count]*count,hAlign='LEFT');table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.HexColor('#cbd9c9')),('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),pale),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7)]));return [table,Spacer(1,8)]
        if tag in ('h3','h4'):return [para(text_only(children),section)]
        if tag in ('p','strong','b','em','i','span') and not has_visual(children):return [prose(value)]
        if tag in ('ol','ul'):
            result=[]
            for n,child in enumerate(children):
                if isinstance(child,dict) and child.get('tag')=='li':
                    if has_visual(child):result.extend(rich(child.get('children',[]),assets))
                    else:result.append(prose(child.get('children',[]),str(n+1)+'. ' if tag=='ol' else '• '))
                else:result.extend(rich(child,assets))
            return result
        if tag=='br':return [Spacer(1,4)]
        return rich(children,assets)
    def text_only(value):
        if isinstance(value,list):return ''.join(text_only(x) for x in value)
        if isinstance(value,(str,int,float)):return str(value)
        if isinstance(value,dict):return str(value.get('text',value.get('latex',''))) if value.get('type') in ('text','math') else text_only(value.get('children',[]))
        return ''
    logo_drawing=svg2rlg(str(logo));logo_ratio=116/logo_drawing.width;logo_drawing.scale(logo_ratio,logo_ratio)
    def page(canvas,doc):
        width,height=A4;canvas.saveState();canvas.setFillAlpha(.065);image=ImageReader(str(watermark));iw,ih=image.getSize();h=400;w=h*iw/ih;canvas.drawImage(image,(width-w)/2,(height-h)/2,width=w,height=h,mask='auto');canvas.restoreState()
        canvas.saveState();renderPDF.draw(logo_drawing,canvas,36,height-57);canvas.setFont('5BPrint',8);canvas.setFillColor(green);canvas.drawRightString(width-36,height-32,'PHIẾU LUYỆN TẬP TOÁN');canvas.drawRightString(width-36,height-45,'Khối '+str(document['grade'])+' | '+('Có lời giải' if include_solutions else 'Đề để in'))
        canvas.setStrokeColor(apricot);canvas.setLineWidth(1);canvas.line(36,height-65,width-36,height-65)
        canvas.setStrokeColor(colors.HexColor('#cbd9c9'));canvas.line(36,49,width-36,49);canvas.setFont('5BPrint',6.8);canvas.setFillColor(dark)
        contacts=[('Website: 5bmath.vn','https://5bmath.vn/'),('Facebook: facebook.com/5bmath','https://www.facebook.com/5bmath'),('Zalo: 0984 763 971','https://zalo.me/0984763971')]
        x=36
        for label,url in contacts:
            canvas.drawString(x,36,label);w=pdfmetrics.stringWidth(label,'5BPrint',6.8);canvas.linkURL(url,(x,34,x+w,44),relative=0);x+=w+15
        canvas.setFont('5BPrint',7);canvas.drawString(36,23,'5BMath - Gieo Mầm Toán | Mã câu giữ đúng phiên bản đã nhận.');canvas.drawRightString(width-36,23,'Trang '+str(doc.page));canvas.restoreState()
    story.extend([para(document['title'],heading),para('Mã đề: '+str(document['examCode'])+' | '+str(len(document['questions']))+' câu',small),para('Mã câu tra cứu tại bản 5BMath đã tạo đề, gắn với tài khoản và phiên bản đã nhận.',small),Spacer(1,8)])
    for n,item in enumerate(document['questions'],1):
        question_start=len(story)
        q=item['payload'];topic=q['topicTitle'];topic='' if re.fullmatch(r'[a-z0-9_.-]+',topic) else topic
        story.extend([para('Câu '+str(n)+(' · '+topic if topic else ''),qhead),para('Mã tra cứu: '+item['code'],code_style)])
        question_mode=True
        story.extend(rich(q['prompt'],q['assets']))
        if not q['prompt']:story.append(para(q['text'],question_body))
        question_mode=False
        if q['responseMode']=='choice':
            for index,option in enumerate(q['options']):story.append(para(chr(65+index)+'. '+option))
        else:story.extend([para('Bài làm: ........................................................................................................'),Spacer(1,12),para('.....................................................................................................................')])
        story[question_start:]=[KeepTogether(story[question_start:])]
    if include_solutions:
        story.extend([PageBreak(),para('Lời giải chi tiết',heading),para('Phần này được tải khi em chủ động chọn Có lời giải. Không thay đổi bài làm đang lưu.',small)])
        for n,item in enumerate(document['questions'],1):
            q=item['payload'];story.extend([para('Câu '+str(n)+' · '+item['code'],qhead),para('Đáp án: '+str(q['answer']),answer_style)])
            lesson=q.get('lesson')
            if lesson:
                opening=rich(lesson.get('overview',[]),q['assets'])
                for flow in opening:
                    if isinstance(flow,Paragraph):flow.style=ParagraphStyle('Opening',parent=flow.style,keepWithNext=True)
                    else:flow.keepWithNext=True
                story.extend(opening)
                for index,part in enumerate(lesson.get('sections',[]),1):story.append(para(str(index)+'. '+part['title'],section));story.extend(rich(part.get('blocks',[]),q['assets']))
            else:
                if q['thinking']:story.append(para('Gợi ý đã lưu',section));story.extend(rich(q['thinking'],q['assets']))
                story.append(para('Các bước giải đã lưu',section));story.extend(rich(q['steps'],q['assets']))
    buf=io.BytesIO();doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=36,leftMargin=36,topMargin=83,bottomMargin=64,title='5BMath - '+document['title'],author='5BMath',subject='Phiếu luyện tập có mã tra cứu phiên bản',pageCompression=1)
    doc.build(story,onFirstPage=page,onLaterPages=page)
    return buf.getvalue()
