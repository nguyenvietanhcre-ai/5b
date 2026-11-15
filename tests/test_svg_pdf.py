"""Vector PDF content and input boundaries; no network or native XML library."""
import io,unittest
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPDF
from pypdf import PdfReader
from backend.svg_pdf import svg2rlg

class SVGPrintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[1]/'frontend/print-art'
        for name,file in [('5BPrint','DejaVuSans.ttf'),('5BPrintBold','DejaVuSans-Bold.ttf')]:
            if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(root/file)))

    def test_vietnamese_text_is_searchable_in_vector_pdf(self):
        d=svg2rlg(io.BytesIO('<svg viewBox="0 0 240 80"><rect x="1" y="1" width="238" height="78" fill="#FFF9ED"/><text x="10" y="35" font-size="16">Số phần bằng nhau</text></svg>'.encode()))
        data=renderPDF.drawToString(d)
        self.assertIn('Số phần bằng nhau',PdfReader(io.BytesIO(data)).pages[0].extract_text())

    def test_logo_preserves_all_paths_inside_viewbox(self):
        d=svg2rlg(Path(__file__).resolve().parents[1]/'frontend/5bmath-logo.svg')
        x1,y1,x2,y2=d.getBounds()
        self.assertTrue(0<=x1<x2<=d.width and 0<=y1<y2<=d.height)

    def test_external_resources_and_entities_are_refused(self):
        for data in [b'<!DOCTYPE svg [<!ENTITY x "private">]><svg/>',b'<svg><image href="https://example.invalid/a.png"/></svg>',b'<svg><script>alert(1)</script></svg>']:
            with self.subTest(svg=data[:35]),self.assertRaises(ValueError):svg2rlg(io.BytesIO(data))
