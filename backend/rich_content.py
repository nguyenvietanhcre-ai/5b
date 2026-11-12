"""Validate portable text, LaTeX/MathML and image references before storing JSON."""

from xml.etree import ElementTree

MATH_NAMESPACE = 'http://www.w3.org/1998/Math/MathML'
MATH_TAGS = {'math', 'mrow', 'mfrac', 'mn', 'mo', 'mi', 'msup', 'msub', 'msqrt', 'mtext'}


def validate_blocks(blocks):
    if not isinstance(blocks, list) or len(blocks) > 100:
        raise ValueError('Content must be a bounded list of blocks')
    for block in blocks:
        if not isinstance(block, dict):
            raise ValueError('Invalid content block')
        kind = block.get('type')
        if kind == 'text':
            if not isinstance(block.get('text'), str) or len(block['text']) > 20000:
                raise ValueError('Invalid text')
        elif kind == 'math':
            if not isinstance(block.get('latex'), str) or len(block['latex']) > 2000:
                raise ValueError('Invalid LaTeX')
            markup = block.get('mathml')
            if not isinstance(markup, str) or len(markup) > 10000:
                raise ValueError('Invalid MathML')
            try:
                root = ElementTree.fromstring(markup)
            except ElementTree.ParseError as error:
                raise ValueError('Invalid MathML') from error
            if root.tag != '{' + MATH_NAMESPACE + '}math':
                raise ValueError('MathML root required')
            for element in root.iter():
                if element.tag not in {'{' + MATH_NAMESPACE + '}' + tag for tag in MATH_TAGS}:
                    raise ValueError('Unsupported MathML element')
                if any(name != 'display' or value not in ('block', 'inline') for name, value in element.attrib.items()):
                    raise ValueError('Unsupported MathML attribute')
        elif kind == 'image':
            if type(block.get('asset_id')) is not int or block['asset_id'] <= 0:
                raise ValueError('Invalid image reference')
        else:
            raise ValueError('Unsupported content block')
