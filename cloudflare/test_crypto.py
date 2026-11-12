import sys
import unittest
import hashlib
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crypto_compat import safe_error_report, webcrypto_pbkdf2
from pbkdf2_fallback import pbkdf2_hmac
from sqlite_storage import REQUEST_SCOPE, RequestScope

NATIVE_ORACLE = hashlib.pbkdf2_hmac


def fallback_vectors():
    randomizer = random.Random(1234)
    vectors = [(b'password', b'salt', iterations, length)
               for iterations in (1, 2, 4096) for length in (1, 16, 31, 32, 33, 64, 65)]
    vectors += [(randomizer.randbytes(length), randomizer.randbytes(salt_length),
                 randomizer.choice((1, 2, 7, 500)), randomizer.choice((1, 32, 33, 64)))
                for length in (0, 1, 63, 64, 65, 127, 200) for salt_length in (0, 1, 16, 65)]
    vectors += [(b'pass\0word', b'sa\0lt', 100, 32),
                ('Mật khẩu tiếng Việt'.encode(), b'long salt' * 20, 5000, 64),
                (b'local-probe-password', b'0000000000000000', 600_000, None)]
    assert len(vectors) == 52
    return vectors


class CryptoDiagnosticsTests(unittest.TestCase):
    def test_iteration_limit_reports_no_exception_values(self):
        try:
            raise RuntimeError('NotSupportedError: Pbkdf2 failed: iteration counts above 100000 are not supported; secret-fixture-value')
        except RuntimeError as error:
            report = safe_error_report(error)
        self.assertEqual(report['category'], 'crypto_pbkdf2_iteration_limit')
        self.assertNotIn('secret-fixture-value', str(report))
        self.assertEqual(report['errorType'], 'RuntimeError')
        self.assertTrue(report['frames'])
        self.assertTrue(all(set(frame) == {'file', 'function', 'line'} for frame in report['frames']))

    def test_unknown_exception_body_is_not_logged(self):
        report = safe_error_report(RuntimeError('private-student-row'))
        self.assertEqual(report['category'], 'unexpected')
        self.assertNotIn('private-student-row', str(report))

    def test_sha256_fallback_matches_cpython_across_blocks_and_buffer_types(self):
        for index, (password, salt, iterations, length) in enumerate(fallback_vectors()):
            with self.subTest(vector=index, iterations=iterations, dklen=length):
                self.assertEqual(pbkdf2_hmac('sha256', password, salt, iterations, length),
                                 NATIVE_ORACLE('sha256', password, salt, iterations, length))
        for password, salt, iterations, length in (
                (bytearray(b'buffer password'), memoryview(b'buffer salt'), 2, None),
                (memoryview(b'buffer password'), bytearray(b'buffer salt'), 3, 1024),
                (b'', b'', True, 1)):
            self.assertEqual(pbkdf2_hmac('sha256', password, salt, iterations, length),
                             NATIVE_ORACLE('sha256', password, salt, iterations, length))
        for bad_iterations in (0, -1, False, 1.5, None):
            with self.assertRaises((ValueError, TypeError)):
                pbkdf2_hmac('sha256', b'p', b's', bad_iterations)
            with self.assertRaises((ValueError, TypeError)):
                NATIVE_ORACLE('sha256', b'p', b's', bad_iterations)
        for bad_length in (0, -1, False, 1.5):
            with self.assertRaises((ValueError, TypeError)):
                pbkdf2_hmac('sha256', b'p', b's', 1, bad_length)
            with self.assertRaises((ValueError, TypeError)):
                NATIVE_ORACLE('sha256', b'p', b's', 1, bad_length)
        for password, salt in (('password', b'salt'), (b'password', 'salt'), (None, b'salt')):
            with self.assertRaises(TypeError):
                pbkdf2_hmac('sha256', password, salt, 1)
        for algorithm, iterations, length in (('sha512', 1, 32), ('sha256', 2**31, 32), ('sha256', 1, 1025)):
            with self.assertRaises(ValueError):
                pbkdf2_hmac(algorithm, b'p', b's', iterations, length)

    def test_real_600000_round_worker_bridge_preserves_existing_hash(self):
        password, salt = b'local-probe-password', b'0000000000000000'
        # Host Python has no js module: this also proves the production path
        # never asks native WebCrypto for the unsupported600k count.
        self.assertEqual(webcrypto_pbkdf2('sha256', password, salt, 600_000),
                         NATIVE_ORACLE('sha256', password, salt, 600_000))

    def test_fallback_still_refuses_hashing_inside_sql_transaction(self):
        token = REQUEST_SCOPE.set(RequestScope(transaction=True))
        try:
            with self.assertRaisesRegex(RuntimeError, 'before the SQL transaction'):
                webcrypto_pbkdf2('sha256', b'fixture', b'salt', 600_000)
        finally:
            REQUEST_SCOPE.reset(token)


if __name__ == '__main__':
    unittest.main()
