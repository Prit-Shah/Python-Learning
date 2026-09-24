"""
Phase 0: Environment & Python Setup Verification
------------------------------------------------
Concept Overview:
    This file verifies that Python 3.x is properly installed, inspects virtual environment status,
    and demonstrates basic debugging and environment diagnostic tools.

JS/TS Analogy:
    Similar to checking `node -v` and checking if `process.env.NODE_ENV` or `package.json` is set up.
"""

import sys
import os
import platform

# Ensure standard output uses UTF-8 on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def verify_environment() -> None:
    """Prints diagnostic information about the current Python environment."""
    print("=" * 60)
    print("Python Learning Environment Diagnostic")
    print("=" * 60)
    
    # 1. Python Version
    print(f"[*] Python Version: {platform.python_version()}")
    print(f"[*] Executable Path: {sys.executable}")
    
    # 2. Virtual Environment Check
    # In Python, VIRTUAL_ENV env var or sys.prefix != sys.base_prefix indicates an active venv.
    in_venv = sys.prefix != sys.base_prefix or "VIRTUAL_ENV" in os.environ
    venv_path = os.environ.get("VIRTUAL_ENV", sys.prefix if in_venv else "Not active")
    
    print(f"[*] Virtual Environment Active: {in_venv}")
    print(f"[*] Virtual Environment Path: {venv_path}")
    
    # 3. OS & System Info
    print(f"[*] Operating System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print("=" * 60)
    
    if in_venv:
        print("[SUCCESS] Virtual environment is active!")
    else:
        print("[NOTICE] Virtual environment is NOT active. Recommended: run 'python -m venv .venv'")

if __name__ == "__main__":
    verify_environment()
