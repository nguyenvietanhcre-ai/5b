"""Bundle an explicit source allowlist; never traverse work or local secrets."""
import shutil
import argparse
import importlib.metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'cloudflare' / 'runtime'
MODULES = ('backend_worker.py', 'sqlite_storage.py', 'crypto_compat.py', 'pbkdf2_fallback.py', 'transfer.py')
BACKEND_MODULES = ('__init__.py', 'admissions.py', 'arena.py', 'content.py', 'database.py',
                   'learning_update.py', 'nickname_policy.py', 'notifications.py', 'payments.py',
                   'platform_api.py', 'question_bank.py', 'referral_support.py', 'rich_content.py',
                   'staff_api.py', 'system_settings.py', 'tuition.py', 'zoom_classroom.py')


def vendor_sdk():
    distribution = importlib.metadata.distribution('workers-runtime-sdk')
    if distribution.version != '1.9.6':
        raise ValueError('Install workers-runtime-sdk==1.9.6 for reproducible packaging')
    destination = ROOT / 'cloudflare' / 'python_modules'
    destination.mkdir(exist_ok=True)
    for item in distribution.files:
        if item.parts[0] == 'workers' or item.name.startswith('_workers_sdk') and item.suffix == '.py':
            if item.suffix == '.pyc' or '__pycache__' in item.parts:
                continue
            target = destination / item
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(distribution.locate_file(item), target)


def build(include_sdk=False):
    if include_sdk:
        vendor_sdk()
    if TARGET.exists():
        if TARGET.resolve() != (ROOT / 'cloudflare' / 'runtime').absolute():
            raise ValueError('Unexpected runtime build target')
        shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in MODULES:
        shutil.copy2(ROOT / 'cloudflare' / name, TARGET / name)
    backend = TARGET / 'backend'
    backend.mkdir(exist_ok=True)
    for name in BACKEND_MODULES:
        shutil.copy2(ROOT / 'backend' / name, backend / name)
    for name in ('learning-catalog.json', 'nickname-policy.json'):
        shutil.copy2(ROOT / 'backend' / name, backend / name)
    (backend / 'migrations').mkdir(exist_ok=True)
    for path in (ROOT / 'backend' / 'migrations').glob('*.sql'):
        shutil.copy2(path, backend / 'migrations' / path.name)
    (TARGET / 'frontend').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'frontend' / 'demo-rectangle.svg', TARGET / 'frontend' / 'demo-rectangle.svg')
    print(f'Worker runtime staged: {TARGET}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vendor-sdk', action='store_true', help='Stage the pinned SDK installed in this Python environment')
    build(parser.parse_args().vendor_sdk)
