"""
1. CONCEPT & JS/TS ANALOGY
Verifying Python environment setup.
JS/TS Analogy: Similar to checking `node -v` and `npm -v`.

2. UNDER THE HOOD (CPython & Memory)
Python executables are usually CPython. Virtual environments (venvs) create isolated sys.prefix directories to prevent global package pollution.

3. COMMON GOTCHA
Running `python` instead of `python3` (or vice versa) and using the system Python rather than an activated virtual environment.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "Walk me through how you set up a new Python project from scratch"
Script: "I first ensure I'm using the correct Python version (usually 3.10+). Then I create a virtual environment using `python -m venv .venv` to isolate dependencies. I activate it, upgrade pip, and typically use `uv` or standard `pip` with a `requirements.txt` or `pyproject.toml` to manage dependencies. Finally, I set up a `.gitignore` and my IDE, like VS Code, pointing it to the virtual environment's Python interpreter."

5. SELF-TESTS
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os
import platform

def check_env():
    version = sys.version_info
    assert version.major >= 3, "Python 3 or higher is required."
    
    in_venv = sys.prefix != sys.base_prefix
    
    return {
        "version": f"{version.major}.{version.minor}.{version.micro}",
        "in_venv": in_venv,
        "os": platform.system()
    }

def run_tests():
    env_info = check_env()
    print("Environment Info:", env_info)
    assert isinstance(env_info["version"], str)
    assert isinstance(env_info["in_venv"], bool)
    print("Tests passed for 01_environment_check.py")

if __name__ == "__main__":
    run_tests()
