# PyCryptodome for Python Workers

Pinned Pyodide wheel: PyCryptodome 3.23.0, PyEmscripten 2026.0, wasm32.

Source: https://cdn.jsdelivr.net/pyodide/v314.0.6/full/pycryptodome-3.23.0-cp37-abi3-pyemscripten_2026_0_wasm32.whl

SHA256: `33e595030bf16622b5afc467cac5504ae91f5529c236e99e8a0ac2b4c0b90f14`.

`cloudflare/build_worker.py` verifies the checksum and extracts the Crypto package into the ignored `python_modules/` build directory. No network dependency or runtime package download. The wheel retains upstream license metadata. Upstream: https://github.com/Legrandin/pycryptodome, https://github.com/pyodide/pyodide.

Only the Worker uses this package. Local CPython/Docker keeps OpenSSL's `hashlib.pbkdf2_hmac`. Password format, SHA256, 600,000 iterations and existing credentials are unchanged. Worker startup fails if the native package cannot load, rather than silently returning to the slow Python loop. Host-only oracle tests can still exercise the Python fallback without installing the WASM package.
