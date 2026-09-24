"""
1. CONCEPT & JS/TS ANALOGY
Virtual environments and packages.
JS/TS Analogy: `venv` + `pip` is like `node_modules` + `npm`. `pyproject.toml` / `requirements.txt` is like `package.json`.

2. UNDER THE HOOD (CPython & Memory)
Virtual environments copy or symlink the Python binary. `pip` installs packages into `site-packages` within `sys.prefix`.

3. COMMON GOTCHA
Forgetting to activate the virtual environment before pip installing, resulting in packages being installed globally.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "How does Python dependency management differ from npm/yarn?"
Script: "In Node, dependencies are installed locally in a `node_modules` folder by default. In Python, global installation is the default. To achieve isolation similar to `node_modules`, we must explicitly create and activate a virtual environment (venv) for each project. Tools like `uv` or `Poetry` are bridging the gap, providing faster, more robust dependency resolution via `pyproject.toml`, akin to modern JS package managers."

5. SELF-TESTS
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_site_packages_info():
    import site
    return site.getsitepackages()

def run_tests():
    site_packages = get_site_packages_info()
    print("Site packages locations:", site_packages)
    assert len(site_packages) > 0, "Should have at least one site-packages directory."
    print("Tests passed for 02_venv_and_packages.py")

if __name__ == "__main__":
    run_tests()
