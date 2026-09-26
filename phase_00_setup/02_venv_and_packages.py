"""
02_venv_and_packages.py

============================================================
1. CONCEPT
============================================================

Virtual environments (`venv`) and package management form the cornerstone of
dependency isolation and deterministic build pipelines in Python:

1. What is a Virtual Environment?
   - A self-contained directory tree containing a Python executable, shell activation
     scripts, and an isolated `site-packages` directory.
   - Creation: `python -m venv .venv` (using the standard library `venv` module).
   - Core Structural Components:
     - Root: `pyvenv.cfg` containing configuration metadata (`home`, `version`).
     - Binaries / Scripts: `.venv/Scripts/` (Windows) or `.venv/bin/` (Unix).
     - Library packages: `.venv/Lib/site-packages/` (Windows) or `.venv/lib/pythonX.Y/site-packages/` (Unix).

2. How "Activation" Actually Works:
   - Activation is purely a shell-level convenience; it modifies environment variables:
     1. It prepends `.venv/Scripts` (or `bin`) to the shell's `PATH` variable.
     2. It sets `VIRTUAL_ENV = <path_to_venv>`.
     3. It adjusts the shell prompt to display `(.venv)`.
   - Because `PATH` now lists `.venv/Scripts` first, typing `python` or `pip` in the
     terminal resolves to the virtual environment's binaries rather than system Python.
   - Running WITHOUT Activation:
     You do NOT have to activate the venv to use it! Invoking `.venv/Scripts/python.exe`
     or `.venv/Scripts/pip.exe` directly works identically because `python.exe` detects
     the neighboring `pyvenv.cfg` and configures `sys.prefix` automatically.

3. Package Installation & site-packages:
   - Packages installed via `pip` are unpacked into the virtual environment's
     `site-packages` directory.
   - Each installed distribution includes a `.dist-info` directory containing
     metadata: `METADATA`, `RECORD`, `entry_points.txt`, and license details.
   - Python's `site` module automatically adds `site-packages` to `sys.path`.

4. Modern Packaging Tooling:
   - `pyproject.toml` (PEP 517/518/621): The unified configuration standard for Python
     projects, replacing legacy `setup.py` and `requirements.txt`.
   - `uv`: Extremely fast Rust-based package installer and resolver developed by Astral,
     providing `uv pip install`, `uv venv`, and deterministic lockfiles (`uv.lock`).


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Local Dependency Directory   | `.venv/Lib/site-packages/`         | `./node_modules/`                  |
| Project Metadata & Config    | `pyproject.toml`                   | `package.json`                     |
| Lockfile                     | `uv.lock` / `poetry.lock`          | `package-lock.json` / `pnpm-lock.yaml`|
| Package Installer            | `pip` / `uv`                       | `npm` / `pnpm` / `yarn`            |
| Executable Isolation         | Explicit `.venv` interpreter       | Per-project `npx` / node resolution|
| Global Default Risk          | High: `pip` installs globally      | Low: `npm install` defaults to local|
| CLI Entry Points             | `[project.scripts]` in toml        | `"bin"` field in `package.json`    |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Packaging Difference:
- In Node.js, running `npm install lodash` automatically puts the files inside the
  nearest `node_modules` folder.
- In Python, running `pip install requests` without a virtual environment installs
  the package into the user's global machine-wide site-packages. This is why virtual
  environment creation (`python -m venv .venv`) is the absolute first step for any
  Python project.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The pyvenv.cfg Boot Discovery Protocol:
   - When CPython launches, the executable locates its own path via OS APIs
     (e.g., `GetModuleFileNameW` on Windows).
   - It searches its directory and parent directory for a file named `pyvenv.cfg`.
   - If found:
     - `sys.base_prefix` is set to the value of `home` in `pyvenv.cfg`.
     - `sys.prefix` is set to the directory containing `pyvenv.cfg`.
     - `site.py` adds `<sys.prefix>/lib/site-packages` to `sys.path`.
   - If not found:
     - `sys.prefix` and `sys.base_prefix` both equal the system Python installation.

2. Distribution Metadata (`importlib.metadata`):
   - Python 3.8+ includes `importlib.metadata` in the standard library.
   - It parses `.dist-info` directories to query installed package versions,
     dependencies, and entry-point specifications without importing the packages.

3. Namespace Packages vs Regular Packages:
   - A regular package has an `__init__.py` file in its directory.
   - A namespace package (PEP 420) omits `__init__.py`, allowing multiple packages
     installed in different paths to contribute modules under a shared root namespace.


============================================================
4. COMMON GOTCHAS
============================================================

1. The Global Pip Install Trap:
   - Running `pip install <pkg>` in a terminal where the venv is NOT active.
   - Result: Packages are written to global Python or user local AppData.
   - Detection: Check `sys.prefix != sys.base_prefix` or run `where pip` / `which pip`.

2. Hardcoding Paths in Scripts:
   - Virtual environments cannot simply be moved or renamed! The activation scripts
     and `pyvenv.cfg` contain absolute paths to the underlying Python binary.
   - If the folder is moved, recreate it: `python -m venv .venv --clear`.

3. Mixing Global Tools with Project Environments:
   - Avoid installing CLI tools like Ruff, Black, or Mypy globally where they can
     drift across versions.
   - Install them inside the project's virtual environment or use `pipx` / `uvx`.

4. Neglecting `.gitignore`:
   - Never commit `.venv/` or `node_modules/` to version control.
   - Always commit `pyproject.toml` and lockfiles (`uv.lock`).


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How does a Python virtual environment work under the hood, and what actually happens when you activate it?"
Script:
"Under the hood, a virtual environment is an isolated directory tree anchored by a
`pyvenv.cfg` file. When the virtual environment's Python executable launches, it reads
`pyvenv.cfg`, which directs CPython to set `sys.prefix` to the venv directory while
keeping `sys.base_prefix` pointed at the core system installation. This directs the `site`
module to load third-party packages exclusively from the venv's `site-packages` directory.
'Activating' the venv does not alter any binaries; it is simply a shell script that prepends
the venv's `Scripts` or `bin` directory to the shell's `PATH` environment variable and sets
the `VIRTUAL_ENV` variable. This ensures that typing `python` or `pip` in that terminal session
executes the virtual environment's local binaries."

Q2: "What is the difference between pip, requirements.txt, and modern pyproject.toml?"
Script:
"Historically, Python projects used `requirements.txt` as a flat list of top-level package
names, often pinned with exact versions. However, `requirements.txt` lacks standardized project
build metadata and cannot distinguish between direct application dependencies and transitive
dependencies. PEP 517, 518, and 621 introduced `pyproject.toml` as the unified declarative standard
for Python packaging, housing build requirements, project metadata, tool configurations (like Ruff
and Pytest), and dependency specifications in a single file. Combined with modern package resolvers
like `uv` or Poetry, this enables deterministic dependency locking via lockfiles, mirroring the
reliability of `package.json` and `package-lock.json` in the Node ecosystem."

Q3: "How does Python locate third-party packages at runtime?"
Script:
"When an import statement is evaluated, Python searches the directories listed in `sys.path`.
During startup, the standard library `site` module is automatically executed. It inspects
`sys.prefix` and appends the appropriate `site-packages` directory to `sys.path`. When `pip`
installs a package, it unpacks the wheel into `site-packages` along with a `.dist-info`
directory containing metadata. Because `site-packages` is in `sys.path`, Python's `PathFinder`
discovers and imports the installed packages seamlessly."
"""

import importlib.metadata
import os
import site
import sys
from pathlib import Path

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_tests():
    # ============================================================
    # 1. SITE-PACKAGES DIRECTORY DISCOVERY
    # ============================================================

    site_pkg_dirs = site.getsitepackages()
    assert isinstance(site_pkg_dirs, list)
    assert len(site_pkg_dirs) > 0

    # Ensure at least one site-packages path exists on disk
    primary_site_pkg = site_pkg_dirs[0]
    assert isinstance(primary_site_pkg, str)
    assert os.path.exists(primary_site_pkg)


    # ============================================================
    # 2. sys.path INTEGRATION
    # ============================================================

    # Verify that site-packages is included in sys.path for import resolution
    site_in_path = any(
        os.path.normpath(p) == os.path.normpath(primary_site_pkg)
        for p in sys.path
    )
    assert site_in_path is True, "Primary site-packages directory must reside in sys.path"


    # ============================================================
    # 3. VIRTUAL ENVIRONMENT CONFIGURATION (pyvenv.cfg)
    # ============================================================

    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        # Locate and inspect pyvenv.cfg in sys.prefix
        cfg_path = Path(sys.prefix) / "pyvenv.cfg"
        assert cfg_path.exists(), "pyvenv.cfg must exist at the root of an active virtual environment"

        cfg_content = cfg_path.read_text(encoding="utf-8")
        assert "home =" in cfg_content or "home=" in cfg_content


    # ============================================================
    # 4. DISTRIBUTION METADATA INSPECTION (importlib.metadata)
    # ============================================================

    # Query installed distributions using standard library importlib.metadata
    installed_dists = list(importlib.metadata.distributions())
    assert isinstance(installed_dists, list)

    # If distributions exist in the environment, verify distribution attributes
    if installed_dists:
        sample_dist = installed_dists[0]
        assert hasattr(sample_dist, "name")
        assert hasattr(sample_dist, "version")
        assert isinstance(sample_dist.name, str)
        assert isinstance(sample_dist.version, str)


    # ============================================================
    # 5. ENVIRONMENT VARIABLE SIMULATION (PATH & VIRTUAL_ENV)
    # ============================================================

    # Simulating what shell activation scripts do:
    # 1. Set VIRTUAL_ENV
    simulated_venv_path = "C:/fake/path/.venv"
    os.environ["VIRTUAL_ENV"] = simulated_venv_path
    assert os.environ.get("VIRTUAL_ENV") == simulated_venv_path
    del os.environ["VIRTUAL_ENV"]

    # 2. PATH resolution order
    current_path = os.environ.get("PATH", "")
    assert isinstance(current_path, str)


if __name__ == "__main__":
    run_tests()
    print("02_venv_and_packages.py tests passed!")
