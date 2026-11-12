"""One public asset allowlist, shared with the browser and static builder."""
import json
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / 'frontend'
CORE = ('index.html', 'admissions.html', 'app.js', 'platform-api.js',
        'nickname-policy.js', 'themes.js', 'themes.css', 'styles.css',
        '5bmath-logo.svg', '5bmath-icon.svg', 'demo-rectangle.svg',
        'mascots.webp', 'admissions.js', 'admissions.css')


def public_assets():
    source = (FRONTEND / 'runtime-assets.js').read_text(encoding='utf-8')
    manifest = json.loads(source.split('/* RUNTIME_MANIFEST_START */', 1)[1]
                          .split('/* RUNTIME_MANIFEST_END */', 1)[0])
    files = set(CORE) | set(manifest['files'])
    for folder in ('arena-art', 'theme-art'):
        for item in (FRONTEND / folder).rglob('*'):
            if item.is_file() and item.suffix in ('.webp', '.png', '.svg', '.json', '.js'):
                files.add(item.relative_to(FRONTEND).as_posix())
    for name in files:
        resolved = (FRONTEND / name).resolve()
        if not resolved.is_relative_to(FRONTEND.resolve()) or not resolved.is_file():
            raise ValueError('Invalid public asset: ' + name)
    return {'/' + name: name for name in files} | {'/': 'index.html'}
