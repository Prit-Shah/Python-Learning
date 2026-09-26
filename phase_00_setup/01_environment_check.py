"""
01_environment_check.py

============================================================
1. CONCEPT
============================================================

The Python runtime environment is governed by the interpreter binary, execution
flags, standard library paths, and platform-specific ABI configurations:

1. Python Version & Interpreter:
   - `sys.version_info`: Named tuple `(major, minor, micro, releaselevel, serial)`
     enabling programmatic version requirement checks (e.g. Python >= 3.10 for
     match/case and union syntax).
   - `sys.executable`: Absolute path to the currently executing Python binary.
   - `sys.platform`: Operating system platform identifier (`"win32"`, `"linux"`, `"darwin"`).

2. Virtual Environment Detection:
   - Python determines environment isolation by comparing `sys.prefix` and `sys.base_prefix`:
     - In global / system Python: `sys.prefix == sys.base_prefix`.
     - Inside a virtual environment: `sys.prefix != sys.base_prefix`.
     - `sys.prefix` points to the root of the active virtual environment containing
       its local `pyvenv.cfg`, `Scripts` (Windows) or `bin` (Unix), and `Lib/site-packages`.

3. CPython Architecture:
   - The reference implementation of Python is CPython, written in C.
   - 64-bit architecture verification: `sys.maxsize > 2**32` confirms a 64-bit pointer space.
   - Bytecode compilation: `.py` files are compiled into `.pyc` bytecode executed
     by the evaluation loop (`ceval.c`).

4. UTF-8 and Standard Streams:
   - PEP 540 introduced Python UTF-8 Mode, ensuring reproducible cross-platform
     handling of UTF-8 encoding across `sys.stdin`, `sys.stdout`, and `sys.stderr`.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Runtime Version              | `sys.version_info`                 | `process.version` / `process.versions.node`|
| Executable Binary Path       | `sys.executable`                   | `process.execPath`                 |
| OS Platform                  | `sys.platform` / `platform.system()`| `process.platform`                |
| Architecture Bit Width       | `sys.maxsize > 2**32`              | `process.arch`                     |
| Environment Variables        | `os.environ`                       | `process.env`                      |
| Command-line Arguments       | `sys.argv`                         | `process.argv`                     |
| Standard Output Encoding     | `sys.stdout.encoding`              | Streams default to UTF-8 buffers   |
| Virtual Environment Check    | `sys.prefix != sys.base_prefix`    | Local `node_modules` detection     |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Runtime Differences:
- In Node.js, `process.env` is a simple JavaScript object snapshot. In Python,
  `os.environ` is a live mapping; mutating `os.environ["KEY"] = "val"` updates the
  underlying C-level process environment table (`putenv`).
- In Node.js, module resolution defaults to local `node_modules` automatically.
  In Python, global installation is the default unless a virtual environment (`venv`)
  is explicitly configured and activated.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The Execution Lifecycle:
   - Initialization: CPython initializes core runtime structures, sets up built-in
     types (`int`, `str`, `dict`), allocates small integer caches, and initializes
     the import system (`importlib`).
   - Compilation: Source code is parsed into an Abstract Syntax Tree (AST), then
     compiled into a `PyCodeObject` consisting of bytecode instructions.
   - Evaluation Loop: The Python Virtual Machine iterates through bytecode opcodes
     in a continuous loop (`_PyEval_EvalFrameDefault`), dispatching operations to
     underlying C functions.

2. Architecture & Pointer Sizing:
   - In 64-bit CPython, `sys.maxsize` is `2**63 - 1` (9,223,372,036,854,775,807).
   - Every `PyObject` header contains an 8-byte reference counter and an 8-byte
     type pointer, making the minimum object size in 64-bit Python 16 bytes.

3. The pyvenv.cfg Anchor:
   - When CPython boots, it inspects the directory containing the executable.
   - If a `pyvenv.cfg` file exists in the directory or parent directory, CPython
     switches into virtual environment mode: it sets `sys.base_prefix` to the
     system Python path recorded in `pyvenv.cfg`, and sets `sys.prefix` to the
     virtual environment folder.


============================================================
4. COMMON GOTCHAS
============================================================

1. Windows Python Launcher vs Store Alias:
   - On Windows, typing `python` in cmd without Python installed triggers the
     Windows Store prompt.
   - Best practice: Always invoke via explicit virtual environment path
     (`.venv/Scripts/python.exe`) or the Python Launcher (`py -3`).

2. System Python Pollution:
   - Running `pip install <package>` without an active virtual environment installs
     packages globally into the system Python or user AppData directory, leading
     to version conflicts across projects.

3. String Comparison for Version Checks:
   - Anti-pattern: `if sys.version >= "3.10":`
   - Problem: In lexicographical string comparison, `"3.9"` is GREATER than `"3.10"`!
   - Idiomatic fix: Always compare numeric tuples: `sys.version_info >= (3, 10)`.

4. Windows Console Encoding:
   - On older Windows terminals, `sys.stdout.encoding` defaults to `cp1252` or
     `cp437`, which crashes with `UnicodeEncodeError` when printing emojis or unicode.
   - Fix: Use `sys.stdout.reconfigure(encoding="utf-8")` or set `PYTHONUTF8=1`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How do you programmatically verify whether a Python script is running inside a virtual environment?"
Script:
"In Python, we check whether `sys.prefix != sys.base_prefix`. When running under the global
system interpreter, both attributes point to the same directory. However, when running inside
an active virtual environment, CPython detects the `pyvenv.cfg` configuration file upon startup,
setting `sys.base_prefix` to the underlying global Python installation and `sys.prefix` to
the virtual environment root. If `sys.prefix` does not equal `sys.base_prefix`, the script
is executing within an isolated virtual environment."

Q2: "Why is comparing sys.version as a string dangerous, and what is the correct approach?"
Script:
"Comparing `sys.version` as a string is dangerous because string comparison is lexicographical,
not numerical. For example, the string `'3.9'` evaluates as greater than `'3.10'`, which will
silently fail version gate checks for Python 3.10+ features like structural pattern matching.
The standard, robust method is to compare `sys.version_info`, which is a named tuple of
integers `(major, minor, micro)`. In Python, tuple comparison compares element by element
numerically, correctly evaluating `(3, 10) >= (3, 9)` as `True`."

Q3: "Walk me through how you set up a new production Python project from scratch."
Script:
"First, I verify the installed Python version meets requirements (typically 3.11+).
Second, I initialize a clean virtual environment using `python -m venv .venv` to ensure
complete dependency isolation. Third, I configure `pyproject.toml` as the single source
of truth for build metadata, packaging, dependencies, and tooling configuration like Ruff
and Pytest. Fourth, I install modern package management tooling like `uv` for lightning-fast
deterministic lockfile generation. Finally, I configure a `.gitignore` to exclude `.venv`,
`__pycache__`, and build artifacts, and set up editor settings to bind to the virtual environment."
"""

import os
import platform
import struct
import sys

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_runtime_environment_diagnostics() -> dict:
    """Collects comprehensive system, interpreter, and environment diagnostics."""
    v = sys.version_info
    is_64bit = sys.maxsize > 2**32
    pointer_size_bytes = struct.calcsize("P")
    in_virtual_env = sys.prefix != sys.base_prefix

    return {
        "python_version_tuple": (v.major, v.minor, v.micro),
        "python_version_string": f"{v.major}.{v.minor}.{v.micro}",
        "executable_path": sys.executable,
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "is_64bit": is_64bit,
        "pointer_size_bytes": pointer_size_bytes,
        "in_virtual_environment": in_virtual_env,
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
    }


def run_tests():
    # ============================================================
    # 1. PYTHON VERSION VERIFICATION (sys.version_info)
    # ============================================================

    diagnostics = get_runtime_environment_diagnostics()

    # Verify Python 3.10+ requirement
    assert sys.version_info >= (3, 10), "This codebase requires Python 3.10 or higher."
    assert sys.version_info.major == 3
    assert isinstance(sys.version_info.minor, int)

    # String vs Tuple comparison verification
    assert sys.version_info >= (3, 9)
    # Correct numerical tuple comparison
    assert (3, 11) > (3, 9)


    # ============================================================
    # 2. VIRTUAL ENVIRONMENT VERIFICATION (sys.prefix vs sys.base_prefix)
    # ============================================================

    # Check whether running inside a virtual environment
    is_venv = sys.prefix != sys.base_prefix
    assert isinstance(is_venv, bool)
    assert diagnostics["in_virtual_environment"] == is_venv

    # sys.prefix must be a non-empty string pointing to a directory
    assert isinstance(sys.prefix, str)
    assert len(sys.prefix) > 0
    assert os.path.exists(sys.prefix)


    # ============================================================
    # 3. 64-BIT ARCHITECTURE & POINTER SIZING
    # ============================================================

    # 64-bit systems have pointer size of 8 bytes (64 bits)
    assert diagnostics["pointer_size_bytes"] == 8
    assert diagnostics["is_64bit"] is True
    assert sys.maxsize == (2**63 - 1)


    # ============================================================
    # 4. OS ENVIRONMENT & PLATFORM ATTRIBUTES
    # ============================================================

    # platform.system() returns 'Windows', 'Linux', or 'Darwin'
    assert diagnostics["platform_system"] in {"Windows", "Linux", "Darwin"}

    # os.environ is a live mapping
    test_key = "ANTIGRAVITY_TEST_ENV_VAR"
    os.environ[test_key] = "active"
    assert os.getenv(test_key) == "active"
    del os.environ[test_key]
    assert os.getenv(test_key) is None


    # ============================================================
    # 5. STANDARD STREAMS & ENCODING
    # ============================================================

    assert sys.stdin is not None
    assert sys.stdout is not None
    assert sys.stderr is not None

    # Verify stdout encoding is available
    assert sys.stdout.encoding is not None


if __name__ == "__main__":
    run_tests()
    print("01_environment_check.py tests passed!")
