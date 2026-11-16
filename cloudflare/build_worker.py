"""Bundle an explicit source allowlist; never traverse work or local secrets."""
import shutil
import argparse
import importlib.metadata
import hashlib
import zipfile
import json
import tomllib
from urllib.request import urlopen
from urllib.parse import urlsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'cloudflare' / 'runtime'
MODULES = ('backend_worker.py', 'sqlite_storage.py', 'crypto_compat.py', 'pbkdf2_fallback.py', 'transfer.py', 'learning_storage.py', 'native_learning.py')
BACKEND_MODULES = ('__init__.py', 'site_visibility.py', 'admissions.py', 'answers.py', 'arena.py', 'content.py', 'database.py',
                   'group_games.py', 'group_game_bots.py', 'game_claims.py', 'content_retirement.py',
                   'learning_update.py', 'nickname_policy.py', 'notifications.py', 'payments.py',
                   'platform_api.py', 'scratchpads.py', 'premium_content.py', 'exam_commerce.py', 'question_bank.py', 'referral_support.py', 'rich_content.py',
                   'staff_api.py', 'local_pilot.py', 'wallet_qa.py', 'free_vip_pilot.py', 'content_batch_qa.py', 'mcq_import.py', 'practice_catalogue.py', 'knowledge_catalogue.py', 'practice_export.py', 'practice_export_api.py', 'practice_pdf.py', 'svg_pdf.py', 'assets.py', 'arena_qa_source.py', 'group_games_qa.py', 'local_test_games.py', 'admin_catalogue.py', 'admin_native.py', 'system_settings.py', 'tuition.py', 'zoom_classroom.py')


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


def vendor_crypto():
    """Verified Pyodide wheel: compiled PBKDF2, no network or unpinned install."""
    wheel = ROOT / 'cloudflare/vendor/pycryptodome-3.23.0.wasm.whl'
    expected = '33e595030bf16622b5afc467cac5504ae91f5529c236e99e8a0ac2b4c0b90f14'
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != expected:
        raise ValueError('Pinned crypto WASM wheel checksum mismatch')
    destination = ROOT / 'cloudflare/python_modules'
    with zipfile.ZipFile(wheel) as archive:
        for entry in archive.infolist():
            if entry.filename.startswith('Crypto/') and not entry.is_dir():
                target = destination / entry.filename
                if not target.resolve().is_relative_to(destination.resolve()):
                    raise ValueError('Invalid wheel path')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))


def vendor_locked_packages():
    """Use the reviewed WASM lock without invoking local platform installers."""
    lock=tomllib.loads((ROOT/'cloudflare/pylock.toml').read_text(encoding='utf-8'))
    cache=ROOT/'work/python-worker-wheels';cache.mkdir(parents=True,exist_ok=True)
    destination=ROOT/'cloudflare/python_modules';destination.mkdir(exist_ok=True)
    for package in lock['packages']:
        if 'archive' in package:
            entry=package['archive'];wheel=ROOT/'cloudflare'/entry['path']
        else:
            choices=package['wheels']
            entry=next((v for v in choices if v['url'].endswith('-py3-none-any.whl')),choices[0])
            parsed=urlsplit(entry['url'])
            if parsed.scheme!='https' or parsed.hostname not in ('files.pythonhosted.org','cdn.jsdelivr.net'):
                raise ValueError('Unapproved wheel host')
            wheel=cache/Path(parsed.path).name
            if not wheel.exists():
                with urlopen(entry['url'],timeout=60) as response:data=response.read(32*1024*1024+1)
                if len(data)>32*1024*1024:raise ValueError('Wheel exceeds bound')
                if hashlib.sha256(data).hexdigest()!=entry['hashes']['sha256']:raise ValueError('Wheel checksum mismatch')
                wheel.write_bytes(data)
        if hashlib.sha256(wheel.read_bytes()).hexdigest()!=entry['hashes']['sha256']:raise ValueError('Locked wheel checksum mismatch')
        with zipfile.ZipFile(wheel) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or entry.filename.endswith('.pyc'):continue
                target=destination/entry.filename
                if not target.resolve().is_relative_to(destination.resolve()):raise ValueError('Invalid package path')
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(entry))
    (destination/'pyvenv.cfg').touch()


def verify_learning_seal():
    seal=json.loads((ROOT/'cloudflare/learning-source-seal.json').read_text(encoding='utf-8'))
    if seal.get('containsAccounts') is not False or seal.get('containsSessions') is not False:
        raise ValueError('Account-free learning artifact proof required')
    for row in seal['files']:
        path=ROOT/row['path']
        if not path.resolve().is_relative_to(ROOT.resolve()):raise ValueError('Invalid sealed input path')
        data=path.read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('Private learning source changed; regenerate and review release seal')


def trim_vendor():
    """Exclude unused package demos, bundled fonts and unrelated crypto APIs.

    The app embeds its own licensed DejaVu fonts. Password derivation retains
    the pinned native KDF/Hash/Cipher/Random/Util implementation and its tests.
    """
    target=(ROOT/'cloudflare/python_modules').resolve()
    if not target.is_relative_to(ROOT.resolve()):raise ValueError('Invalid vendor root')
    directories=['lxml','svglib','cssselect2','tinycss2','webencodings','Crypto/PublicKey','Crypto/Signature','Crypto/IO','Crypto/SelfTest','Crypto/Math',
                 'reportlab/fonts','reportlab/graphics/samples','reportlab/graphics/charts',
                 'reportlab/graphics/barcode','lxml/html','lxml/includes']
    for name in directories:
        path=(target/name).resolve()
        if not path.is_relative_to(target):raise ValueError('Invalid prune path')
        if path.exists():shutil.rmtree(path)
    patterns={'PIL':('_imagingft*','_webp*','_imagingmath*','_imagingmorph*','_imagingtk*'),
              'lxml':('objectify*.so','builder*.so','sax*.so')}
    for package,globs in patterns.items():
        for glob in globs:
            for path in (target/package).glob(glob):
                if not path.resolve().is_relative_to(target):raise ValueError('Invalid prune file')
                path.unlink()


def build(include_sdk=False):
    if include_sdk:
        vendor_sdk()
    vendor_crypto()
    vendor_locked_packages()
    trim_vendor()
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
    for name in ('learning-names.json',):
        shutil.copy2(ROOT / 'cloudflare' / name, TARGET / name)
    if (ROOT/'cloudflare/learning-seed.sql').exists():
        verify_learning_seal()
        shutil.copy2(ROOT/'cloudflare/learning-seed.sql',TARGET/'learning-seed.sql')
        for name in ('pilot-inputs','restructure-inputs'):
            shutil.copytree(ROOT/name,TARGET/name)
    else:
        print('Private learning inputs absent: base-runtime CI only; native release requires private-data QA.')
    (TARGET / 'frontend').mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'frontend/print-art',TARGET / 'frontend/print-art')
    shutil.copy2(ROOT / 'frontend/5bmath-logo.svg',TARGET / 'frontend/5bmath-logo.svg')
    shutil.copy2(ROOT / 'frontend' / 'demo-rectangle.svg', TARGET / 'frontend' / 'demo-rectangle.svg')
    print(f'Worker runtime staged: {TARGET}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vendor-sdk', action='store_true', help='Stage the pinned SDK installed in this Python environment')
    build(parser.parse_args().vendor_sdk)
