"""Cloudflare adapter for the explicitly requested localhost learning features.

The source's draft/demo labels stay intact. No local account database is bundled.
"""
import hashlib
import json
import threading
from base64 import b64decode
from pathlib import Path
from backend.local_pilot import LocalPilot, safe_svg
from backend.answers import requires_choice
from backend.mcq_import import load_json
from backend.practice_catalogue import Practice
from backend.knowledge_catalogue import Knowledge
from learning_storage import LearningDatabase
from backend.local_test_games import NativeLocalTestGames
from backend import platform_api as api


class CloudLearning(LocalPilot):
    # Mirror identities cannot authenticate with a password. Every request is
    # authorized through the main session before mapping to this isolated store.
    mirror_credential = '!main-session-only-no-password!'
    def __init__(self, database):
        root = Path(__file__).resolve().parent
        if not (root / 'pilot-inputs').exists():
            root = root.parent
        self.path = LearningDatabase(database)
        self.inputs = root / 'pilot-inputs'
        self.lock = threading.RLock()
        self.week_cache = None
        seal = load_json(self.inputs / 'manifest.json')
        expected = {'questions-mcq60.json', 'batch-manifest.json', 'questions-typed-subset.json', 'typed-manifest.json', 'sources.json', 'lessons-bundle.json'}
        if {r['path'] for r in seal['files']} != expected:
            raise ValueError('Sealed learning inputs required')
        for row in seal['files']:
            data = (self.inputs / row['path']).read_bytes()
            if hashlib.sha256(data).hexdigest() != row['sha256'] or len(data) != row['bytes']:
                raise ValueError('Learning source SHA mismatch')
        self.choice = load_json(self.inputs / 'questions-mcq60.json')
        self.original_manifest = load_json(self.inputs / 'batch-manifest.json')
        self.typed = load_json(self.inputs / 'questions-typed-subset.json')
        self.original_typed = load_json(self.inputs / 'typed-manifest.json')
        self.sources = load_json(self.inputs / 'sources.json')
        self.choice_required = {q['contentKey'] for q in self.typed['questions'] if requires_choice(q)}
        self.typed_eligible = set(self.original_typed['eligibleContentKeys']) - self.choice_required
        self.bundle = load_json(self.inputs / 'lessons-bundle.json')
        self.lessons = {x['source']['contentKey']: x for x in self.bundle['lessons']}
        self.assets = {a['sha256']: safe_svg(b64decode(a['base64'], validate=True)) for a in self.bundle['assets']}
        if any(hashlib.sha256(data).hexdigest() != sha for sha, data in self.assets.items()):
            raise ValueError('Learning asset SHA mismatch')
        self.practice = Practice(self, load_json(root / 'restructure-inputs/mapping60.json'))
        self.knowledge = Knowledge.__new__(Knowledge)
        self.knowledge.provider = self
        self.knowledge.inputs = root / 'restructure-inputs'

    def ensure_week(self):
        # Never cache transaction-owned state across rollback or preflight replay.
        self.week_cache = None
        return super().ensure_week()

    def catalogue(self,*args):
        result=super().catalogue(*args)
        result['notice']=result['notice'].replace('Thí điểm cục bộ','Học tập bản mẫu')
        return result


class CloudDemoGames(NativeLocalTestGames):
    """Same labeled synthetic game source as localhost, explicitly opted in.

    It is not an approval of a question bank or a commercial game policy.
    """
    def __init__(self):
        super().__init__({19061})

    def allowed(self,handler):
        return bool(getattr(handler.server,'cloud_demo_games',None) is self and api.same_origin(handler))

    def metadata(self,kind):
        value=super().metadata(kind)
        value.update(label=value['label'].replace('cục bộ','mẫu'),status='demo',localTest=True)
        return value
