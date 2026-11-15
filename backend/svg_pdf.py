"""Small SVG-to-ReportLab adapter for the project's sealed vector artwork.

Uses standard XML and ReportLab's SVG path parser, without native XML libraries.
No URLs, external resources, scripts or CSS documents are loaded.
"""
import math,re
import xml.etree.ElementTree as ET
from pathlib import Path

NUMBER=re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')
IDENTITY=(1,0,0,1,0,0)

def number(value,default=0):
    match=NUMBER.match(str(value).strip())
    return float(match[0]) if match else default

def multiply(a,b):
    return (a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],
            a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],
            a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5])

def transform(value):
    matrix=IDENTITY
    for name,args in re.findall(r'([a-zA-Z]+)\s*\(([^)]*)\)',value or ''):
        v=[float(x) for x in NUMBER.findall(args)]
        if name=='matrix' and len(v)==6:m=tuple(v)
        elif name=='translate' and len(v) in (1,2):m=(1,0,0,1,v[0],v[1] if len(v)==2 else 0)
        elif name=='scale' and len(v) in (1,2):m=(v[0],0,0,v[1] if len(v)==2 else v[0],0,0)
        elif name=='rotate' and len(v) in (1,3):
            angle=math.radians(v[0]);c,s=math.cos(angle),math.sin(angle);m=(c,s,-s,c,0,0)
            if len(v)==3:m=multiply(multiply((1,0,0,1,v[1],v[2]),m),(1,0,0,1,-v[1],-v[2]))
        elif name in ('skewX','skewY') and len(v)==1:
            t=math.tan(math.radians(v[0]));m=(1,0,t,1,0,0) if name=='skewX' else (1,t,0,1,0,0)
        else:raise ValueError('Unsupported SVG transform')
        matrix=multiply(matrix,m)
    return matrix

def svg2rlg(source):
    from reportlab.graphics.shapes import Drawing,Group,Rect,Line,Circle,Ellipse,Polygon,PolyLine,String
    from reportlab.graphics.svgpath import SvgPath
    from reportlab.lib.colors import toColor
    data=source.read() if hasattr(source,'read') else Path(source).read_bytes()
    if isinstance(data,str):data=data.encode('utf-8')
    if len(data)>2*1024*1024 or re.search(br'<!DOCTYPE|<!ENTITY',data,re.I):raise ValueError('Unsafe SVG document')
    root=ET.fromstring(data)
    if root.tag.rsplit('}',1)[-1]!='svg':raise ValueError('SVG root required')
    if sum(1 for _ in root.iter())>5000:raise ValueError('SVG node limit')
    view=[float(x) for x in NUMBER.findall(root.get('viewBox',''))]
    width=number(root.get('width'),view[2] if len(view)==4 else 300)
    height=number(root.get('height'),view[3] if len(view)==4 else 150)
    if not 0<width<=10000 or not 0<height<=10000:raise ValueError('Invalid SVG size')
    drawing=Drawing(width,height)
    coordinate=Group()
    coordinate.transform=((width/view[2],0,0,-height/view[3],-view[0]*width/view[2],height+view[1]*height/view[3]) if len(view)==4 else (1,0,0,-1,0,height))
    drawing.add(coordinate)
    inherited={'fill':'black','stroke':'none','stroke-width':'1','font-size':'16','font-weight':'normal','text-anchor':'start','_opacity':1}
    def color(value):return None if value in ('none','transparent') else toColor(value)
    def node(element,parent,style):
        tag=element.tag.rsplit('}',1)[-1]
        if tag in ('title','desc','defs','marker'):return
        if any(k.lower().startswith('on') or k.rsplit('}',1)[-1] in ('href','src') for k in element.attrib):raise ValueError('External SVG content is not supported')
        current=dict(style);current.update(element.attrib)
        for item in element.get('style','').split(';'):
            if ':' in item:
                k,v=item.split(':',1);current[k.strip()]=v.strip()
        current['_opacity']=style.get('_opacity',1)*number(element.get('opacity','1'),1)
        if current.get('display')=='none' or current.get('visibility')=='hidden':return
        group=Group();group.transform=transform(element.get('transform',''));parent.add(group)
        if tag in ('svg','g'):
            for child in element:node(child,group,current)
            return
        a=lambda key,default=0:number(element.get(key),default)
        props={'fillColor':color(current.get('fill','black')),'strokeColor':color(current.get('stroke','none')),'strokeWidth':number(current.get('stroke-width','1'),1),
               'fillOpacity':current['_opacity']*number(current.get('fill-opacity','1'),1),'strokeOpacity':current['_opacity']*number(current.get('stroke-opacity','1'),1),
               'strokeLineCap':{'butt':0,'round':1,'square':2}.get(current.get('stroke-linecap'),0),'strokeLineJoin':{'miter':0,'round':1,'bevel':2}.get(current.get('stroke-linejoin'),0)}
        dash=current.get('stroke-dasharray','none')
        if dash!='none':props['strokeDashArray']=[float(x) for x in NUMBER.findall(dash)]
        def permitted(cls):return {k:v for k,v in props.items() if k in cls._attrMap}
        if tag=='rect':shape=Rect(a('x'),a('y'),a('width'),a('height'),rx=a('rx'),ry=a('ry',a('rx')),**permitted(Rect))
        elif tag=='circle':shape=Circle(a('cx'),a('cy'),a('r'),**permitted(Circle))
        elif tag=='ellipse':shape=Ellipse(a('cx'),a('cy'),a('rx'),a('ry'),**permitted(Ellipse))
        elif tag=='line':shape=Line(a('x1'),a('y1'),a('x2'),a('y2'),**permitted(Line))
        elif tag in ('polygon','polyline'):
            cls=Polygon if tag=='polygon' else PolyLine;shape=cls([float(x) for x in NUMBER.findall(element.get('points',''))],**permitted(cls))
        elif tag=='path':shape=SvgPath(element.get('d',''),fillMode=0 if current.get('fill-rule')=='evenodd' else 1,**permitted(SvgPath))
        elif tag=='text':
            text=''.join(element.itertext());size=number(current.get('font-size','16'),16)
            font='5BPrintBold' if current.get('font-weight') in ('bold','600','700','800','900') else '5BPrint'
            baseline=a('y')+(size*.35 if current.get('dominant-baseline') in ('middle','central') else 0)
            text_group=Group();text_group.transform=(1,0,0,-1,0,0);group.add(text_group)
            shape=String(a('x'),-baseline,text,fontName=font,fontSize=size,textAnchor=current.get('text-anchor','start'),**permitted(String))
            text_group.add(shape);return
        else:raise ValueError('Unsupported SVG shape: '+tag)
        group.add(shape)
    node(root,coordinate,inherited)
    return drawing
