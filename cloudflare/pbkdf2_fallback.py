"""PBKDF2-HMAC-SHA256 using the runtime's native SHA256 compression.

Keeps existing PBKDF2 credentials byte-for-byte compatible when Web Crypto's
iteration ceiling cannot evaluate them. This does not reduce the work factor.
Precomputed HMAC pad contexts avoid creating an hmac object on every round.
"""
import hashlib


def pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
    """Derive SHA256 keys; supports the app's existing hashlib call signature."""
    if hash_name != 'sha256':
        raise ValueError('fallback supports sha256 only')
    if not isinstance(iterations, int) or not 1 <= iterations < 2**31:
        raise ValueError('invalid iteration count')
    length = 32 if dklen is None else dklen
    if not isinstance(length, int) or not 1 <= length <= 1024:
        raise ValueError('invalid derived key length')
    password = memoryview(password).tobytes()
    salt = memoryview(salt).tobytes()
    sha256 = hashlib.sha256
    if len(password) > 64:
        password = sha256(password).digest()
    key = password.ljust(64, b'\0')
    inner_base = sha256(bytes(value ^ 0x36 for value in key))
    outer_base = sha256(bytes(value ^ 0x5c for value in key))
    inner_copy, outer_copy = inner_base.copy, outer_base.copy
    integer = int.from_bytes
    output = bytearray()
    for block in range(1, (length + 31) // 32 + 1):
        inner = inner_copy()
        inner.update(salt)
        inner.update(block.to_bytes(4, 'big'))
        outer = outer_copy()
        outer.update(inner.digest())
        digest = outer.digest()
        accumulated = integer(digest, 'big')
        for _ in range(iterations - 1):
            inner = inner_copy()
            inner.update(digest)
            outer = outer_copy()
            outer.update(inner.digest())
            digest = outer.digest()
            accumulated ^= integer(digest, 'big')
        output.extend(accumulated.to_bytes(32, 'big'))
    return bytes(output[:length])
