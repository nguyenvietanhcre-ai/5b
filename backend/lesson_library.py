"""Versioned, local lesson authoring bank. Not wired to student API or live DB.

JSON content trees + fixed semantic sections, never executable HTML in SQLite.
SVG media is validated, content-addressed, and stored inside the database so a
database backup retains every diagram. The renderer produces escaped HTML.
"""
import argparse
import base64
import hashlib
import html
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from xml.etree import ElementTree as ET
from .rich_content import validate_blocks

SECTIONS = [('thinking', 'Định hướng tư duy'), ('key', 'Điểm mấu chốt'),
            ('detail', 'Bài giải chi tiết')]
TAGS = set('p b strong em i small span mark div aside figure figcaption ol ul li h3 h4 table caption thead tbody tr th td button details summary br a'.split())
ATTRS = {'class', 'id', 'role', 'aria-label', 'aria-live', 'aria-describedby',
         'scope', 'type', 'disabled', 'hidden', 'href', 'open'}
SVG_TAGS = set('svg g path circle rect line polyline polygon ellipse text tspan title desc defs marker'.split())
SVG_ATTRS = set('viewBox role aria-labelledby id d fill stroke stroke-width stroke-dasharray x y x1 y1 x2 y2 cx cy r rx ry width height points text-anchor class marker-end marker-start refX refY markerWidth markerHeight orient transform opacity fill-opacity stroke-opacity font-size font-family font-weight'.split())
ID = re.compile(r'^[a-z][a-z0-9-]{0,100}$')
SCHEMA = """
CREATE TABLE IF NOT EXISTS lesson_documents (
 id TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS lesson_revisions (
 lesson_id TEXT NOT NULL REFERENCES lesson_documents(id), revision INTEGER NOT NULL CHECK(revision>0),
 schema_version INTEGER NOT NULL CHECK(schema_version=1), title TEXT NOT NULL,
 grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 5), status TEXT NOT NULL CHECK(status='draft'),
 reviewer_type TEXT NOT NULL CHECK(reviewer_type='assistant'), source_json TEXT NOT NULL CHECK(json_valid(source_json)),
 document_json TEXT NOT NULL CHECK(json_valid(document_json)), digest TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(lesson_id,revision));
CREATE TABLE IF NOT EXISTS lesson_media (
 sha256 TEXT PRIMARY KEY, mime_type TEXT NOT NULL CHECK(mime_type='image/svg+xml'), content BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS lesson_revision_media (
 lesson_id TEXT NOT NULL, revision INTEGER NOT NULL, sha256 TEXT NOT NULL REFERENCES lesson_media(sha256),
 PRIMARY KEY(lesson_id,revision,sha256), FOREIGN KEY(lesson_id,revision) REFERENCES lesson_revisions(lesson_id,revision));
"""


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def validate_svg(raw):
    if len(raw) > 500_000 or b'<!' in raw or b'<?' in raw:
        raise ValueError('Invalid SVG size or declaration')
    root = ET.fromstring(raw)
    if root.tag.split('}')[-1] != 'svg':
        raise ValueError('Expected SVG root')
    for element in root.iter():
        if element.tag.split('}')[-1] not in SVG_TAGS:
            raise ValueError('Unsupported SVG element')
        for name, value in element.attrib.items():
            if name not in SVG_ATTRS or re.search(r'url\((?!#[a-zA-Z0-9_-]+\))', value, re.I):
                raise ValueError('Unsafe SVG attribute/reference')
    return raw


def validate_document(doc, media):
    if doc.get('schemaVersion') != 1 or not ID.fullmatch(doc.get('id', '')):
        raise ValueError('Invalid schema version/id')
    if type(doc.get('revision')) is not int or doc['revision'] < 1:
        raise ValueError('Invalid revision')
    if type(doc.get('grade')) is not int or not 1 <= doc['grade'] <= 5:
        raise ValueError('Invalid grade')
    if doc.get('status') != 'draft' or doc.get('reviewerType') != 'assistant':
        raise ValueError('This authoring bank only accepts assistant-reviewed drafts')
    for name in ['title', 'eyebrow', 'sourceLabel']:
        if not isinstance(doc.get(name), str) or not doc[name].strip():
            raise ValueError('Missing '+name)
    if not isinstance(doc.get('source'), dict) or not doc['source'].get('kind'):
        raise ValueError('Source provenance required')
    sections = doc.get('sections', [])
    if [(s.get('key'), s.get('title')) for s in sections] != SECTIONS:
        raise ValueError('Exactly three canonical sections required')
    if any(not s.get('blocks') for s in sections) or not doc.get('prompt'):
        raise ValueError('Prompt and section content required')
    count, refs, ids = 0, set(), set()

    def walk(node, depth=0):
        nonlocal count
        count += 1
        if depth > 30 or count > 6000 or not isinstance(node, dict):
            raise ValueError('Invalid/deep/oversize content tree')
        kind = node.get('type')
        if kind == 'text':
            if not isinstance(node.get('text'), str) or len(node['text']) > 30_000:
                raise ValueError('Invalid text')
        elif kind == 'media':
            if node.get('sha256') not in media or not node.get('alt'):
                raise ValueError('Missing media or alternative text')
            refs.add(node['sha256'])
        elif kind == 'math':
            validate_blocks([node])
        elif kind == 'element':
            if node.get('tag') not in TAGS or not isinstance(node.get('attrs', {}), dict):
                raise ValueError('Unsupported content element')
            for key, value in node.get('attrs', {}).items():
                if key not in ATTRS or not isinstance(value, str):
                    raise ValueError('Unsafe attribute')
                if key == 'href' and not re.fullmatch(r'#[a-z][a-z0-9-]*', value):
                    raise ValueError('Only document anchor links allowed')
                if key == 'id':
                    if not ID.fullmatch(value) or value in ids:
                        raise ValueError('Invalid/duplicate content id')
                    ids.add(value)
            for child in node.get('children', []):
                walk(child, depth+1)
        else:
            raise ValueError('Unknown block type')
    for blocks in [doc['prompt'], doc.get('overview', [])] + [s['blocks'] for s in sections]:
        if not isinstance(blocks, list):
            raise ValueError('Blocks must be lists')
        for node in blocks:
            walk(node)
    return refs


@contextmanager
def connect(path):
    db = sqlite3.connect(path)
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()


def import_bundle(database, bundle):
    if bundle.get('schemaVersion') != 1 or not bundle.get('lessons'):
        raise ValueError('Invalid/empty bundle')
    media = {}
    for asset in bundle.get('assets', []):
        raw = base64.b64decode(asset['base64'], validate=True)
        if asset.get('mimeType') != 'image/svg+xml' or hashlib.sha256(raw).hexdigest() != asset['sha256']:
            raise ValueError('Invalid media type or checksum')
        media[asset['sha256']] = validate_svg(raw)
    documents = bundle['lessons']
    if len({(d['id'], d['revision']) for d in documents}) != len(documents):
        raise ValueError('Duplicate lesson revision in batch')
    refs = [validate_document(doc, media) for doc in documents]
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    with connect(database) as db:
        db.executescript(SCHEMA)
        for doc, links in zip(documents, refs):
            body = packed(doc)
            digest = hashlib.sha256(body.encode()).hexdigest()
            old = db.execute('SELECT digest FROM lesson_revisions WHERE lesson_id=? AND revision=?',
                             (doc['id'], doc['revision'])).fetchone()
            if old:
                if old[0] != digest:
                    raise ValueError('Revision conflict; create a new revision')
                continue
            db.execute('INSERT OR IGNORE INTO lesson_documents(id) VALUES (?)', (doc['id'],))
            db.execute('INSERT INTO lesson_revisions(lesson_id,revision,schema_version,title,grade,status,reviewer_type,source_json,document_json,digest) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (doc['id'], doc['revision'], 1, doc['title'], doc['grade'], doc['status'], doc['reviewerType'], packed(doc['source']), body, digest))
            for sha in links:
                db.execute('INSERT OR IGNORE INTO lesson_media VALUES (?,?,?)', (sha, 'image/svg+xml', media[sha]))
                db.execute('INSERT INTO lesson_revision_media VALUES (?,?,?)', (doc['id'], doc['revision'], sha))
    return len(documents)


def load_bundle(database):
    """Latest revision per lesson, with only its referenced assets."""
    with connect(database) as db:
        rows = db.execute('SELECT r.document_json FROM lesson_revisions r WHERE revision=(SELECT MAX(revision) FROM lesson_revisions WHERE lesson_id=r.lesson_id) ORDER BY lesson_id').fetchall()
        docs = sorted([json.loads(r[0]) for r in rows], key=lambda d: (d.get('sortOrder', 0), d['id']))
        media = {r[0]: bytes(r[1]) for r in db.execute('SELECT sha256,content FROM lesson_media')}
    refs = set()
    for doc in docs:
        refs.update(validate_document(doc, media))
    for sha in refs:
        if hashlib.sha256(media[sha]).hexdigest() != sha:
            raise ValueError('Stored media checksum mismatch')
    return {'schemaVersion': 1, 'lessons': docs, 'assets': [
        {'sha256': sha, 'mimeType': 'image/svg+xml', 'base64': base64.b64encode(validate_svg(media[sha])).decode()}
        for sha in sorted(refs)]}


def render_articles(bundle):
    media = {a['sha256']: validate_svg(base64.b64decode(a['base64'], validate=True)).decode('utf8') for a in bundle['assets']}

    def render(node):
        if node['type'] == 'text':
            return html.escape(node['text'])
        if node['type'] == 'media':
            # Embedded SVG retains viewBox, accessible title/description, and CSS.
            return media[node['sha256']]
        if node['type'] == 'math':
            return node['mathml']
        attrs = ''.join(' '+k+'="'+html.escape(v, quote=True)+'"' for k, v in node.get('attrs', {}).items())
        tag = node['tag']
        return '<'+tag+attrs+'>'+('' if tag == 'br' else ''.join(render(n) for n in node.get('children', []))+'</'+tag+'>')

    result = []
    for doc in bundle['lessons']:
        validate_document(doc, media)
        ident = doc['id']
        content = '<article class="lesson" id="'+ident+'"><div class="lesson-head"><span class="eyebrow">'+html.escape(doc['eyebrow'])+'</span><h2>'+html.escape(doc['title'])+'</h2><p class="source">'+html.escape(doc['sourceLabel'])+'</p></div>'
        content += '<nav class="section-nav" aria-label="Các phần bài '+ident+'">'+''.join('<a href="#'+ident+'-phan-'+str(i)+'">'+str(i)+'. '+title+'</a>' for i, (_, title) in enumerate(SECTIONS, 1))+'</nav>'
        content += '<section class="prompt">'+''.join(map(render, doc['prompt']))+'</section>'+''.join(map(render, doc.get('overview', [])))
        for i, section in enumerate(doc['sections'], 1):
            content += '<section class="'+section['key']+' block"><h3 id="'+ident+'-phan-'+str(i)+'"><span class="section-number">'+str(i)+'</span> '+section['title']+'</h3>'+''.join(map(render, section['blocks']))+'</section>'
        result.append(content+'</article>')
    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('import').add_argument('bundle')
    sub.add_parser('export').add_argument('output')
    sub.add_parser('render').add_argument('output')
    args = parser.parse_args()
    if args.command == 'import':
        print('Draft lessons saved:', import_bundle(args.db, json.loads(Path(args.bundle).read_text(encoding='utf-8-sig'))))
    else:
        bundle = load_bundle(args.db)
        Path(args.output).write_text(packed(bundle) if args.command == 'export' else render_articles(bundle), encoding='utf8')
        print('Exported:', args.output)


if __name__ == '__main__':
    main()
