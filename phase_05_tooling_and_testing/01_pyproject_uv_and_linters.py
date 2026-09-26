"""
01_pyproject_uv_and_linters.py

============================================================
1. CONCEPT
============================================================

Modern Python engineering has consolidated project configuration, dependency
management, static analysis, and code quality into a unified, high-performance toolchain:

1. Unified Project Specification (`pyproject.toml` - PEP 518 & PEP 621):
   - Replaces fragmented legacy files (`setup.py`, `setup.cfg`, `requirements.txt`,
     `.flake8`, `tox.ini`) with a single declarative configuration file.
   - Core Sections:
     - `[build-system]`: Declares the build backend (e.g. `hatchling`, `flit_core`, `setuptools`).
     - `[project]`: Standardized project metadata (name, version, description,
       dependencies, license, readme).
     - `[project.optional-dependencies]`: Development, testing, and documentation groups.
     - `[tool.ruff]`: Linter and formatter rules, line length, rule selections.
     - `[tool.mypy]`: Static type-checking flags and strictness settings.
     - `[tool.pytest.ini_options]`: Test discovery paths, markers, and coverage flags.

2. Next-Gen Dependency Management with `uv`:
   - Written in Rust by Astral; resolves and installs packages 10-100x faster than `pip`.
   - Manages Python versions (`uv python install`), virtual environments (`uv venv`),
     and deterministic cross-platform lockfiles (`uv.lock`).

3. High-Speed Linting & Formatting with `Ruff`:
   - Written in Rust; acts as a drop-in replacement for Flake8, Black, isort,
     pydocstyle, and pyupgrade.
   - Lints and formats an entire repository in tens of milliseconds, eliminating
     pre-commit CI bottlenecks.

4. Static Type Checking with `mypy`:
   - Inspects AST and type annotations statically before runtime.
   - Essential configuration: `disallow_untyped_defs = true` to force complete
     function type annotations across the codebase.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| Project Manifest             | `pyproject.toml`                   | `package.json`                     |
| Fast Package Manager         | `uv`                               | `pnpm` / `bun`                     |
| Lockfile                     | `uv.lock`                          | `package-lock.json` / `pnpm-lock.yaml`|
| Linter & Code Formatter      | `Ruff`                             | `Biome` / `ESLint` + `Prettier`    |
| Static Type Checker          | `mypy` / `pyright`                 | `tsc --noEmit`                     |
| Task / Script Runner         | `uv run <command>`                 | `npm run <script>` / `pnpm run`    |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Tooling Differences:
1. In the JS ecosystem, `package.json` contains runtime scripts (`"scripts": { "build": "..." }`).
   In Python, commands are run directly in the virtual environment via `uv run` or
   custom CLI entry points defined in `[project.scripts]`.
2. Python 3.11+ includes `tomllib` in the standard library, enabling direct built-in
   parsing of `pyproject.toml` files without third-party dependencies.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The PEP 517 Build Pipeline:
   - When a project is built into a wheel (`.whl`), CPython does not run arbitrary
     code in `setup.py`.
   - Instead, the frontend (`build` or `uv`) queries the `[build-system]` table in
     `pyproject.toml` to dynamically import the backend (e.g. `hatchling.build`).
   - The backend produces isolated `.whl` and `.tar.gz` distribution archives.

2. TOML Parsing Mechanics (`tomllib`):
   - Introduced in Python 3.11 (based on `tomli`).
   - `tomllib.loads(toml_str)` parses the configuration directly into native Python
     dictionaries, lists, integers, booleans, and datetimes in $O(N)$ time.

3. Static Analysis vs Runtime Execution:
   - Mypy and Ruff parse source code into Abstract Syntax Trees (ASTs) using
     `ast.parse()` or native Rust parsers without executing the module.
   - Type annotations exist in CPython solely as values in `__annotations__`
     dicts; the bytecode compiler ignores them during execution.


============================================================
4. COMMON GOTCHAS
============================================================

1. Default Mypy Laxity:
   - By default, `mypy` skips functions that do not have type annotations!
   - Writing untyped code gives a false sense of safety.
   - Always configure:
     ```toml
     [tool.mypy]
     strict = true
     disallow_untyped_defs = true
     ```

2. Committing Floating Dependency Ranges Without a Lockfile:
   - Specifying `fastapi >= 0.100.0` in `dependencies` without locking versions.
   - A new minor or patch release can introduce breaking changes in production.
   - Always generate and commit `uv.lock`.

3. Mixing Formatter and Linter Rules:
   - In legacy setups, Black and Flake8 frequently clashed on line lengths and
     whitespace around colons.
   - Ruff unifies formatting and linting into a single cohesive AST engine,
     completely eliminating rule conflicts.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "What is pyproject.toml and why has it become the single source of truth for Python projects?"
Script:
"`pyproject.toml`, standardized across PEPs 517, 518, and 621, consolidated the historically
fragmented Python packaging ecosystem. Previously, projects had to maintain `setup.py` for
installation, `requirements.txt` for pinned dependencies, and half a dozen separate dotfiles
like `.flake8`, `pytest.ini`, and `mypy.ini`. `pyproject.toml` provides a single standardized
declarative file that specifies build backend requirements, standardized package metadata,
runtime dependencies, and tool-specific configurations (such as Ruff, Mypy, and Pytest).
This mirrors `package.json` in Node.js and brings clarity and reproducibility to CI pipelines."

Q2: "Explain the role of Ruff and uv in modern production Python development."
Script:
"`uv` and `Ruff`, developed in Rust by Astral, have fundamentally transformed Python developer
velocity. `Ruff` replaces Flake8, Black, isort, and pyupgrade, running 10 to 100 times faster
than its predecessors while executing linting and formatting simultaneously with zero rule
conflicts. `uv` acts as a drop-in replacement for `pip`, `pip-tools`, and `virtualenv`, resolving
complex dependency graphs in milliseconds using global caching and producing deterministic
lockfiles (`uv.lock`). In production AI and cloud-native workflows, adopting `uv` reduces Docker
build times and CI pipeline durations from minutes down to seconds."

Q3: "How does Mypy type-checking fit into a Python CI/CD pipeline?"
Script:
"Because Python is dynamically typed at runtime, type hints are purely metadata that the
interpreter does not enforce. Mypy functions as a static analysis gate in the CI/CD pipeline,
acting identically to `tsc --noEmit` in TypeScript. By configuring Mypy in `strict` mode with
`disallow_untyped_defs = true`, the pipeline ensures that all functions, parameters, and return
types are explicitly typed and verified before code can be merged into main. This catches
`None`-pointer dereferences, missing attributes, and signature mismatches before runtime."
"""

import sys
import tomllib

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Sample production pyproject.toml content for parsing and validation
SAMPLE_PYPROJECT_TOML = """
[build-system]
requires = ["hatchling>=1.20.0"]
build-backend = "hatchling.build"

[project]
name = "apex-ai-service"
version = "2.1.0"
description = "High-performance AI inference and streaming gateway"
readme = "README.md"
requires-python = ">=3.11"
authors = [
    { name = "Lead Architect", email = "architect@apex.internal" }
]
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.7.0",
    "fastapi>=0.111.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "mypy>=1.10.0",
    "ruff>=0.4.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
disallow_untyped_defs = true
warn_unused_ignores = true

[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
"""


def run_tests():
    # ============================================================
    # 1. PARSING pyproject.toml WITH tomllib (Python 3.11+)
    # ============================================================

    parsed_config = tomllib.loads(SAMPLE_PYPROJECT_TOML)
    assert isinstance(parsed_config, dict)

    # ------------------------------------------------------------
    # Validating [build-system] table
    # ------------------------------------------------------------
    assert "build-system" in parsed_config
    build_sys = parsed_config["build-system"]
    assert build_sys["build-backend"] == "hatchling.build"
    assert "hatchling>=1.20.0" in build_sys["requires"]

    # ------------------------------------------------------------
    # Validating [project] metadata (PEP 621)
    # ------------------------------------------------------------
    assert "project" in parsed_config
    proj = parsed_config["project"]
    assert proj["name"] == "apex-ai-service"
    assert proj["version"] == "2.1.0"
    assert proj["requires-python"] == ">=3.11"

    # Runtime dependencies verification
    deps = proj["dependencies"]
    assert len(deps) == 3
    assert any("fastapi" in d for d in deps)
    assert any("pydantic" in d for d in deps)
    assert any("httpx" in d for d in deps)

    # Dev dependencies verification
    dev_deps = proj["optional-dependencies"]["dev"]
    assert any("pytest" in d for d in dev_deps)
    assert any("mypy" in d for d in dev_deps)
    assert any("ruff" in d for d in dev_deps)


    # ============================================================
    # 2. VALIDATING TOOL CONFIGURATIONS: RUFF & MYPY
    # ============================================================

    # Tool table exists
    assert "tool" in parsed_config
    tools = parsed_config["tool"]

    # Ruff configuration validation
    assert "ruff" in tools
    ruff_conf = tools["ruff"]
    assert ruff_conf["line-length"] == 100
    assert ruff_conf["target-version"] == "py311"
    assert "I" in ruff_conf["lint"]["select"]  # isort enabled

    # Mypy configuration validation
    assert "mypy" in tools
    mypy_conf = tools["mypy"]
    assert mypy_conf["strict"] is True
    assert mypy_conf["disallow_untyped_defs"] is True

    # Pytest configuration validation
    assert "pytest" in tools
    pytest_conf = tools["pytest"]["ini_options"]
    assert pytest_conf["testpaths"] == ["tests"]


    # ============================================================
    # 3. VERSION TUPLE COMPARISON LOGIC
    # ============================================================

    def parse_semver(version_str: str) -> tuple[int, int, int]:
        parts = [int(p) for p in version_str.split(".")]
        return tuple(parts)

    v1 = parse_semver("2.1.0")
    v2 = parse_semver("2.0.9")
    v3 = parse_semver("2.1.0")

    assert v1 > v2
    assert v1 == v3


if __name__ == "__main__":
    run_tests()
    print("01_pyproject_uv_and_linters.py tests passed!")
