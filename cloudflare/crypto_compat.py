"""Request-scoped synchronous crypto bridge; no suspension inside SQL writes."""
import hashlib
import traceback
from pathlib import PurePath

from sqlite_storage import REQUEST_SCOPE


def safe_error_report(error):
    """Log fixed categories and code locations, never exception/input values."""
    category = 'unexpected'
    current = error
    for _ in range(8):
        if current is None:
            break
        message = str(current).lower()
        if 'pbkdf' in message and ('iteration counts above' in message or 'iteration' in message and 'not supported' in message):
            category = 'crypto_pbkdf2_iteration_limit'
            break
        if 'no suspender' in message or 'jspi' in message:
            category = 'python_sync_bridge'
            break
        if 'cpu' in message and ('limit' in message or 'exceed' in message):
            category = 'cpu_limit'
            break
        current = current.__cause__ or current.__context__
    frames = traceback.extract_tb(error.__traceback__, limit=8)
    return {'event': '5bmath_backend_error', 'category': category, 'errorType': type(error).__name__,
            'frames': [{'file': PurePath(frame.filename).name, 'function': frame.name, 'line': frame.lineno} for frame in frames]}


def webcrypto_pbkdf2(hash_name, password, salt, iterations, dklen=None):
    scope = REQUEST_SCOPE.get()
    if scope and scope.transaction:
        raise RuntimeError('PBKDF must be prepared before the SQL transaction')
    algorithms = {'sha1': ('SHA-1', 20), 'sha256': ('SHA-256', 32),
                  'sha384': ('SHA-384', 48), 'sha512': ('SHA-512', 64)}
    if hash_name not in algorithms:
        raise ValueError('unsupported hash type')
    if not isinstance(iterations, int) or not 1 <= iterations < 2**31:
        raise ValueError('iteration value must be greater than zero and fit an integer')
    length = algorithms[hash_name][1] if dklen is None else dklen
    if not isinstance(length, int) or not 1 <= length <= 1024:
        raise ValueError('invalid derived key length')
    # Production Workers cap native PBKDF2 at100,000; local workerd does not.
    # Keep the existing600,000-round SHA256 format byte-for-byte, using the
    # standard pad-copy implementation before the SQL write transaction.
    if hash_name == 'sha256' and iterations > 100_000:
        from pbkdf2_fallback import pbkdf2_hmac
        return pbkdf2_hmac(hash_name, password, salt, iterations, length)
    from js import Object, crypto
    from pyodide.ffi import run_sync, to_js
    key = run_sync(crypto.subtle.importKey('raw', to_js(memoryview(password)),
                                         'PBKDF2', False, to_js(['deriveBits'])))
    options = to_js({'name': 'PBKDF2', 'salt': memoryview(salt), 'iterations': iterations,
                     'hash': algorithms[hash_name][0]}, dict_converter=Object.fromEntries)
    result = run_sync(crypto.subtle.deriveBits(options, key, length * 8))
    return bytes(result.to_py())


def install():
    """Install once per isolate; mutable results are kept only in ContextVar."""
    from backend import platform_api, staff_api
    if getattr(platform_api.password_hash, '_worker_cached', False):
        return
    if not hasattr(hashlib, 'pbkdf2_hmac'):
        hashlib.pbkdf2_hmac = webcrypto_pbkdf2
    original_hash = platform_api.password_hash
    original_verify = platform_api.verify_password
    original_limit = platform_api.limit_auth

    def cached_hash(password):
        scope = REQUEST_SCOPE.get()
        if not scope or not isinstance(password, str):
            return original_hash(password)
        key = ('hash', password)
        if key not in scope.crypto:
            scope.crypto[key] = original_hash(password)
        return scope.crypto[key]

    def cached_verify(password, credential):
        scope = REQUEST_SCOPE.get()
        if not scope or not isinstance(password, str):
            return original_verify(password, credential)
        key = ('verify', password, credential)
        if key not in scope.crypto:
            if scope.transaction:
                raise platform_api.APIError('Thông tin đăng nhập vừa thay đổi. Hãy đăng nhập lại.', 401)
            scope.crypto[key] = original_verify(password, credential)
        return scope.crypto[key]

    def limited_once(handler):
        scope = REQUEST_SCOPE.get()
        if not scope or not scope.auth_limited:
            original_limit(handler)
            if scope:
                scope.auth_limited = True

    cached_hash._worker_cached = True
    platform_api.password_hash = staff_api.password_hash = cached_hash
    platform_api.verify_password = staff_api.verify_password = cached_verify
    platform_api.limit_auth = staff_api.limit_auth = limited_once
