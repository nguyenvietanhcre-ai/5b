"""Read-only preview for the existing MCQ QA importer; never creates a database."""
from collections import Counter
from contextlib import closing
from difflib import SequenceMatcher
import json
from pathlib import Path
import sqlite3
import unicodedata

from .mcq_import import (ImportFailure, digest, normalize_question, require_qa,
                         source_registry, validate)


def preview_package(path, package, manifest, sources, *, allow_draft_qa=False):
    target=Path(path).resolve()
    if not target.is_file(): raise ImportFailure('database: existing synthetic QA database required')
    rows=[]; errors=[]; registry={}
    try: registry=source_registry(sources)
    except (ImportFailure, TypeError, AttributeError) as exc: errors.append(str(exc))
    questions=package.get('questions',[]) if isinstance(package,dict) else []
    if not isinstance(questions,list): questions=[]
    counts=Counter(q.get('contentKey') for q in questions if isinstance(q,dict) and isinstance(q.get('contentKey'),str))
    normalized=[]
    with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row; db.execute('PRAGMA query_only=ON'); require_qa(db)
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for index,q in enumerate(questions):
            entry={'index':index,'contentKey':q.get('contentKey') if isinstance(q,dict) else None,
                   'status':'invalid','reasons':[],'warnings':[]}
            rows.append(entry)
            try:
                item,_=normalize_question(q,registry,allow_draft_qa)
                ck=q['contentKey']; rev=q['revision']; entry.update(revision=rev,quotaKey=q['quotaKey'])
                if counts[ck]>1: raise ImportFailure(ck+': duplicate contentKey in package')
                existing=db.execute('SELECT * FROM mcq_versions WHERE content_key=? AND revision=?',(ck,rev)).fetchone() if 'mcq_versions' in tables else None
                identity=db.execute('SELECT * FROM mcq_versions WHERE content_key=? LIMIT 1',(ck,)).fetchone() if 'mcq_versions' in tables else None
                current=db.execute('SELECT * FROM pilot_content WHERE content_key=?',(ck,)).fetchone()
                entry['status']='new_revision' if identity else 'new'
                reason=None
                if existing:
                    if existing['payload_hash']==digest(q) and existing['source_hash']==item['sourceHash']:
                        entry['status']='exact_duplicate'
                    else: reason='same identity/revision has different immutable payload/source hash'
                if identity and (identity['quota_key'],identity['source_key'],identity['source_revision'],identity['source_hash'])!=(q['quotaKey'],q['sourceContentKey'],q['sourceRevision'],item['sourceHash']):
                    reason='cannot retarget identity/lineage; mapping review required'
                if current and not identity: reason='unmapped existing key; explicit legacy mapping required'
                if current and current['proposed_access']!=q['proposedAccess'].lower(): reason='access change requires separate policy decision'
                if reason: entry['status']='conflict';entry['reasons'].append(reason)
                normalized.append((entry,item))
            except (ImportFailure, TypeError, AttributeError, KeyError) as exc:
                entry['status']='invalid';entry['reasons'].append(str(exc))
        try:
            _,info=validate(package,manifest,sources,allow_draft_qa=allow_draft_qa)
            for ck,rev in manifest['contentRevisions'].items():
                candidate=next((q for q in questions if q['contentKey']==ck and q['revision']==rev),None)
                stored=db.execute('SELECT 1 FROM mcq_versions WHERE content_key=? AND revision=?',(ck,rev)).fetchone() if 'mcq_versions' in tables else None
                if not candidate and not stored: errors.append('manifest.contentRevisions.'+ck+': pinned version not imported')
            old=db.execute('SELECT manifest_hash FROM mcq_manifests WHERE set_key=?',(manifest['setKey'],)).fetchone() if 'mcq_manifests' in tables else None
            if old and old[0]!=digest(manifest): errors.append('manifest: immutable manifest hash conflict')
            if not old and db.execute('SELECT 1 FROM pilot_sets WHERE grade=5 AND window_start=? AND slot=1',(info['start'],)).fetchone():
                errors.append('manifest: window/slot already occupied')
        except (ImportFailure, TypeError, AttributeError, KeyError) as exc: errors.append(str(exc))
        # Similar text is a warning only, never an identity/quota decision.
        norm=lambda value:' '.join(unicodedata.normalize('NFKC',value).split()).casefold()
        candidates=[]
        if 'mcq_versions' in tables:
            for r in db.execute('SELECT content_key,metadata_json FROM mcq_versions'):
                m=json.loads(r['metadata_json'])
                from .platform_api import blocks_text
                from .mcq_import import blocks
                candidates.append((r['content_key'],norm(blocks_text(blocks(m['prompt'],'stored.prompt')))))
        from .platform_api import blocks_text
        candidates += [(item['raw']['contentKey'],norm(blocks_text(item['prompt']))) for _,item in normalized]
        for entry,item in normalized:
            prompt=norm(blocks_text(item['prompt']))
            similar=sorted({ck for ck,other in candidates if ck!=entry['contentKey'] and SequenceMatcher(None,prompt,other).ratio()>=0.9})
            if similar: entry['warnings'].append({'nearSimilarKeys':similar,'action':'review only; no automatic merge'})
    summary={name:sum(r['status']==name for r in rows) for name in ('new','exact_duplicate','new_revision','conflict','invalid')}
    return {'qaOnly':True,'mode':'preview','databaseChanged':False,
            'importable':not errors and not summary['conflict'] and not summary['invalid'],
            'summary':summary,'errors':errors,'questions':rows,
            'packageHash':digest(package),'manifestHash':digest(manifest),'sourceRegistryHash':digest(sources),
            'notice':'Read-only snapshot; commit revalidates inside its own transaction. Source database mapping still pending.'}
