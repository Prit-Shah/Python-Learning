"""
Phase 3: OOP & Real Application Code - Modules, Packages & Import Mechanics
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Module: A single Python file (.py).
   - Package: A directory containing an '__init__.py' file (Python 3.3+ namespace packages can omit it, but __init__.py is best practice).
   - Import Styles:
     * 'import math' -> math.sqrt(4)
     * 'from math import sqrt' -> sqrt(4)
     * 'from math import sqrt as square_root' (aliasing)
   - '__name__' variable:
     * When executed directly: '__name__ == "__main__"'
     * When imported as a module: '__name__ == "<module_name>"'
   - Absolute vs Relative Imports:
     * Absolute: 'from my_package.services import UserService' (Preferred in production!)
     * Relative: 'from .models import User' (Allowed inside package submodules)
   - JS/TS Analogy:
     * 'import { x } from "./module.js"' vs 'from module import x'.
     * Node uses 'index.js'; Python uses '__init__.py'.
     * Python executes module top-level code ONCE on first import and caches it in 'sys.modules'.

2. UNDER THE HOOD (CPython & Memory):
   - 'sys.modules' is a dictionary caching all loaded modules. Subsequent imports do NOT re-execute the file.
   - 'sys.path' is the list of directory paths Python searches sequentially for imports.
   - Circular imports happen when module A imports B, and B imports A at top-level before A completes execution!

3. COMMON GOTCHA:
   - Circular Import Trap:
     # a.py: from b import func_b
     # b.py: from a import func_a
     # Raises: ImportError: cannot import name 'func_a' from partially initialized module 'a'
     # FIX 1: Refactor shared dependencies into a third module (e.g. models.py).
     # FIX 2: Defer import inside function body (lazy import).

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does Python's import system work, what is sys.modules, and how do you resolve
       circular import errors in production code?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. The Import Lifecycle:
      "When Python executes an import statement, it first checks the sys.modules dictionary cache.
       If the module is already cached, it returns the existing module object immediately.
       If not, it searches the directories listed in sys.path, compiles the code to bytecode,
       creates a new module namespace, and executes the top-level code once from top to bottom."
   2. Circular Imports & Why They Happen:
      "A circular import occurs when Module A imports Module B at top level, while Module B attempts
       to import a symbol from Module A before Module A has finished defining it. This results in an
       'ImportError: cannot import name from partially initialized module'."
   3. The Senior Solutions:
      "In production architectures, there are three clean ways to fix it:
       First and most architectural: Refactor shared types or schemas into a dedicated module (e.g. models.py or types.py).
       Second: Use local imports—importing the dependency inside the specific function that uses it instead of module top-level.
       Third: If only needed for type checking, use 'if typing.TYPE_CHECKING:' with string annotations or from __future__ import annotations."
================================================================================
"""

import sys
import os

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def demonstrate_import_internals():
    print("\n--- 1. sys.modules & sys.path Diagnostics ---")
    print(f"  Current __name__: '{__name__}'")
    print(f"  Python executable: {sys.executable}")
    print(f"  Total cached modules in sys.modules: {len(sys.modules)}")
    
    # Inspect top sys.path search roots
    print("  First 3 sys.path search entries:")
    for path in sys.path[:3]:
        print(f"    - {path}")


def demonstrate_circular_import_solution():
    print("\n--- 2. Circular Import Pattern & Deferred Import Fix ---")
    # Demonstrating lazy / local import inside function:
    def process_order(order_id: int):
        # Lazy import: executed only when called, breaking top-level circular lock
        import json
        return json.dumps({"order_id": order_id, "status": "CONFIRMED"})
    
    result = process_order(101)
    print(f"  Lazy import execution result: {result}")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

def check_module_cached(mod_name: str) -> bool:
    """Verifies if a module name is currently cached in sys.modules."""
    return mod_name in sys.modules


def run_tests():
    print("\n[*] Running automated self-tests for 04_modules_and_imports.py...")
    assert check_module_cached("sys") is True, "'sys' must be present in sys.modules"
    assert check_module_cached("os") is True, "'os' must be present in sys.modules"
    
    # Non-imported module should not be in sys.modules
    import math
    assert check_module_cached("math") is True, "'math' should now be cached"
    
    print("[SUCCESS] All self-tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 3 - Modules, Packages & Import Mechanics")
    print("=" * 65)
    demonstrate_import_internals()
    demonstrate_circular_import_solution()
    print("-" * 65)
    run_tests()
    print("=" * 65)
