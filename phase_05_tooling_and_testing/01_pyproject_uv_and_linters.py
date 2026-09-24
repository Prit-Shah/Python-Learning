"""
Phase 5: Professional Python Tooling - pyproject.toml, uv, Ruff & Mypy
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - 'pyproject.toml' (PEP 518 & PEP 621):
     * The unified configuration standard for Python projects.
     * Replaces legacy setup.py, requirements.txt, setup.cfg, .flake8, and tox.ini into a single file!
     * Contains metadata: [project], dependencies, and tool settings ([tool.ruff], [tool.mypy], [tool.pytest]).
   - Modern Package Management with 'uv':
     * An ultra-fast Python package and project manager written in Rust by Astral (10-100x faster than pip).
     * Replaces pip, pip-tools, virtualenv, and poetry.
     * Core commands: 'uv venv', 'uv pip install', 'uv add <pkg>', 'uv run <script>'.
   - Formatting & Linting with 'Ruff':
     * Extremely fast Rust-based linter and code formatter.
     * Replaces Flake8, Black, isort, pydocstyle, and pyupgrade in milliseconds.
   - Static Type Checking with 'mypy':
     * Type analysis tool that checks type hints statically before execution.
   - JS/TS Analogy:
     * 'package.json' -> 'pyproject.toml'
     * 'pnpm' / 'bun' -> 'uv'
     * 'ESLint' + 'Prettier' / 'Biome' -> 'Ruff'
     * 'tsc' (TypeScript Compiler) -> 'mypy'

2. UNDER THE HOOD (CPython & Memory):
   - Python locates packages by inspecting 'sys.path'. When a virtual environment is active,
     CPython adds '.venv/lib/site-packages' to the front of 'sys.path'.
   - Type hints in Python ('def add(a: int) -> int:') are purely runtime metadata stored in '__annotations__'.
     CPython NEVER enforces type hints at runtime; type safety is enforced by static analyzers like Mypy.

3. COMMON GOTCHA:
   - Forgetting to lock dependencies: Just like committing 'package-lock.json', you should always
     maintain reproducible lockfiles ('requirements.txt' with hashes or 'uv.lock').
   - Not enabling strict mode in Mypy: By default, mypy allows untyped functions. Always configure
     'disallow_untyped_defs = true' in pyproject.toml.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "Explain modern Python tooling and packaging. What is pyproject.toml, and why
       has the ecosystem shifted toward tools like uv and Ruff?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. The pyproject.toml Standard:
      "Historically, the Python packaging ecosystem was fragmented across setup.py, setup.cfg,
       requirements.txt, and separate linter config files. With PEP 518 and PEP 621, 'pyproject.toml'
       became the official single source of truth for project metadata, dependencies, and all developer
       tooling configurations (Ruff, Mypy, Pytest), mirroring package.json in the Node.js ecosystem."
   2. The Rust Tooling Revolution (uv & Ruff):
      "In the past two years, the Python ecosystem underwent a massive speed revolution led by Astral:
       - Ruff replaced Black, Flake8, and isort, running 10-100x faster and eliminating pre-commit CI lag.
       - 'uv' replaced legacy pip, pip-tools, and virtualenv, resolving dependencies in milliseconds
         with global package caching and lockfiles.
       In production AI and backend development, using uv and Ruff dramatically speeds up Docker builds
       and CI/CD pipelines."
   3. Static Typing with Mypy:
      "Because Python is dynamically typed at runtime, we run Mypy in CI with strict type checking
       to catch bugs, type mismatches, and None-pointer exceptions before code ever reaches production."
================================================================================
"""

import sys
import tomllib  # Built-in TOML parser in Python 3.11+
from pathlib import Path

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


SAMPLE_PYPROJECT_TOML = """[project]
name = "python-learning"
version = "0.1.0"
description = "Accelerated Python to AI Engineer Learning Repository"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.28.0",
    "pydantic>=2.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.9.0",
    "mypy>=1.14.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --strict-markers"
"""


def demonstrate_pyproject_parsing():
    print("\n--- 1. Parsing pyproject.toml with Python 3.11+ tomllib ---")
    data = tomllib.loads(SAMPLE_PYPROJECT_TOML)
    
    project_meta = data["project"]
    print(f"  Project Name:     {project_meta['name']}")
    print(f"  Python Version:   {project_meta['requires-python']}")
    print(f"  Dependencies:     {project_meta['dependencies']}")
    print(f"  Dev Dependencies: {project_meta['optional-dependencies']['dev']}")
    print(f"  Ruff Line Length: {data['tool']['ruff']['line-length']}")
    print(f"  Mypy Strict Mode: {data['tool']['mypy']['strict']}")


def demonstrate_type_annotations_metadata():
    print("\n--- 2. Runtime Type Annotations Introspection ---")
    def calculate_tax(income: float, rate: float = 0.2) -> float:
        return income * rate

    # In Python, type hints are stored in __annotations__ dictionary
    print(f"  Function name: calculate_tax")
    print(f"  __annotations__: {calculate_tax.__annotations__}")
    print("  Notice: CPython does NOT enforce this at runtime; Mypy verifies it statically!")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

def validate_pyproject_structure(toml_string: str) -> bool:
    """Validates that a pyproject.toml string contains required sections."""
    parsed = tomllib.loads(toml_string)
    if "project" not in parsed:
        return False
    required_keys = ["name", "version", "requires-python"]
    return all(k in parsed["project"] for k in required_keys)


def run_tests():
    print("\n[*] Running automated self-tests for 01_pyproject_uv_and_linters.py...")
    assert validate_pyproject_structure(SAMPLE_PYPROJECT_TOML) is True
    
    # Invalid missing project section
    assert validate_pyproject_structure("[tool.ruff]\nline-length=88") is False
    
    # Save reference pyproject.toml in phase folder
    ref_file = Path(__file__).parent / "pyproject.reference.toml"
    ref_file.write_text(SAMPLE_PYPROJECT_TOML, encoding="utf-8")
    assert ref_file.exists() is True
    
    print("[SUCCESS] All self-tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 5 - pyproject.toml, uv, Ruff & Mypy")
    print("=" * 65)
    demonstrate_pyproject_parsing()
    demonstrate_type_annotations_metadata()
    print("-" * 65)
    run_tests()
    print("=" * 65)
