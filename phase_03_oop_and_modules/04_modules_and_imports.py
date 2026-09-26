"""
04_modules_and_imports.py

============================================================
1. CONCEPT
============================================================

Python organizes code into modular, reusable namespaces via modules, packages,
and a deterministic import pipeline:

1. Modules and Packages:
   - Module: A single Python file (`.py`) defining functions, classes, and variables.
   - Regular Package: A filesystem directory containing an `__init__.py` file.
     The `__init__.py` runs upon package import and exposes the package's public API.
   - Namespace Package (PEP 420): A directory without `__init__.py` spanning multiple
     disjoint directory locations (useful for large distributed monorepos).
   - `__all__`: A sequence of string identifiers explicitly defining what symbols
     are exported when a consumer executes `from package import *`.

2. The Entry-Point Idiom (`if __name__ == '__main__':`):
   - When a script is executed directly from the terminal (`python script.py`),
     Python sets its top-level namespace `__name__ = "__main__"`.
   - When imported as a module (`import script`), `__name__` is set to the module's
     qualified import path (e.g. `"phase_03_oop_and_modules.04_modules_and_imports"`).
   - The guard ensures executable entry-point scripts can also be imported safely
     as libraries without triggering unwanted side effects.

3. The Import Pipeline:
   - Cache Check: CPython consults `sys.modules`. If the module is already cached,
     it returns the existing module object immediately ($O(1)$ lookup).
   - Search: Searches directories listed in `sys.path` in sequential order.
   - Loading & Execution: CPython compiles the source code to bytecode, allocates
     a new module object (`PyModuleObject`), and executes its top-level statements
     from top to bottom once, caching the resulting namespace in `sys.modules`.

4. Circular Imports:
   - Occurs when Module A imports Module B at top-level, and Module B imports a
     symbol from Module A before Module A has completed its initial execution.
   - CPython raises `ImportError: cannot import name 'X' from partially initialized module`.
   - Architectural Resolutions:
     1. Refactor shared types/interfaces into a leaf module (e.g., `types.py`).
     2. Defer import locally inside the function that requires it.
     3. Guard type annotations with `if typing.TYPE_CHECKING:` (PEP 563).

5. Dynamic Imports (`importlib`):
   - `importlib.import_module(module_name)`: Enables plugin systems and dynamic dispatch.
   - `importlib.reload(module)`: Reloads an already imported module at runtime.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| File as Module               | Yes (`.py`)                        | Yes (`.js` / `.ts` ESM)            |
| Package Entry Point          | `__init__.py`                      | `index.js` or `package.json` main  |
| Import Cache                 | `sys.modules` dictionary           | `require.cache` or ESM module map  |
| Module Search Path           | `sys.path` list                    | `NODE_PATH` / `node_modules` lookup|
| Entry Point Detection        | `if __name__ == '__main__':`       | `require.main === module` / ESM url|
| Export Control               | `__all__ = ["func_a", "ClassB"]`   | `export { funcA, ClassB }`         |
| Dynamic Import               | `importlib.import_module("mod")`   | `await import("mod")`              |
| Type-Only Imports            | `if TYPE_CHECKING:`                | `import type { User } from ...`    |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Nuances:
1. Python executes top-level code ONCE upon first import. Variables defined at
   the top level become module attributes (`module.attr`).
2. Unlike JavaScript where circular dependencies often silently evaluate to
   `undefined`, Python explicitly raises an `ImportError` if an uninitialized
   attribute is requested from a partially executed module.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. `sys.modules` Singleton Cache:
   - `sys.modules` is an ordinary Python `dict` mapping fully-qualified module
     names (strings) to `PyModuleObject` instances.
   - Subsequent `import x` statements simply retrieve the reference from `sys.modules`.
   - Deleting an entry from `sys.modules` (`del sys.modules["x"]`) forces CPython
     to re-import and re-execute the file on next import.

2. `sys.meta_path` and Importers:
   - CPython implements PEP 302 import hooks via `sys.meta_path`.
   - Contains a list of finder objects (e.g. `BuiltinImporter`, `FrozenImporter`,
     `PathFinder`).
   - `PathFinder` handles directory scans based on `sys.path`.

3. Module Objects (`PyModuleObject`):
   - In CPython, a module is an instance of `types.ModuleType`.
   - The module namespace is stored in its `__dict__` attribute.
   - Built-in attributes: `__name__`, `__file__`, `__doc__`, `__package__`, `__spec__`.


============================================================
4. COMMON GOTCHAS
============================================================

1. The Circular Import Trap:
   - Module `a.py` does `from b import func_b`, while `b.py` does `from a import func_a`.
   - When `a.py` runs, it pauses to load `b.py`. `b.py` tries to read `func_a` from `a`,
     which has not yet been executed!
   - Result: `ImportError: cannot import name 'func_a' from partially initialized module 'a'`.

2. Name Shadowing Standard Library Modules:
   - Naming a local script `math.py`, `random.py`, `json.py`, or `email.py`.
   - When standard libraries attempt to import the real `math`, CPython finds the
     local file first in `sys.path[0]`, breaking the entire application.

3. Wildcard Imports (`from module import *`):
   - Pollutes the local namespace with unknown identifiers.
   - Obscures where variables originate and breaks linters/type checkers.
   - Restrict with `__all__` if supporting library packages.

4. Modifying `sys.path` Unsafely:
   - Appending to `sys.path` with `sys.path.append(...)` puts your path AFTER
     installed site-packages.
   - If a library with the same name exists, it will take precedence over your local code.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how Python's import mechanism works from source file to sys.modules."
Script:
"When an `import` statement executes, CPython first checks the `sys.modules` cache.
If the module key is present, it returns the cached module object in $O(1)$ time.
If not, it iterates through the directory entries in `sys.path` using finder hooks
in `sys.meta_path` to locate the file spec. Once found, a loader creates a new module
object, registers it in `sys.modules` to prevent circular re-entry, and executes the
compiled bytecode from top to bottom. Any functions, classes, or top-level assignments
populate the module's `__dict__` namespace."

Q2: "What causes circular imports in Python, and how do you resolve them in production?"
Script:
"A circular import happens when Module A imports Module B at the top level, and Module B
attempts to import a symbol from Module A before Module A has completed its initial execution.
Because Module A's namespace has not yet bound the requested symbol, CPython raises an
`ImportError` for a partially initialized module. In production architectures, there are three
clean solutions: first, extract the shared types or models into a third leaf module that neither
depends on; second, defer the import by placing it inside the function or method where it is
actually used; and third, if the import is only needed for type annotations, wrap it inside
`if typing.TYPE_CHECKING:` combined with `from __future__ import annotations`."

Q3: "What is the purpose of if __name__ == '__main__' in Python scripts?"
Script:
"The `if __name__ == '__main__':` construct checks the execution context of the file.
When a script is run directly from the command line, CPython assigns the string `'__main__'`
to the module-level variable `__name__`. However, when the file is imported into another
module, `__name__` is set to its actual module path. Placing execution logic, CLI parsing,
or test routines inside this block ensures that the code runs when executed directly, but
remains inert when imported by other modules or test suites."
"""

import importlib
import importlib.util
import sys
import types
from typing import TYPE_CHECKING

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Publicly exported symbols when using `from module import *`
__all__ = ["calculate_metric", "ServiceRegistry"]


def calculate_metric(value: float, factor: float = 1.5) -> float:
    """Public utility function."""
    return value * factor


class ServiceRegistry:
    """Registry maintaining active service instances."""
    def __init__(self):
        self._services = {}

    def register(self, name: str, service_obj):
        self._services[name] = service_obj

    def get(self, name: str):
        return self._services.get(name)


def run_tests():
    # ============================================================
    # 1. sys.modules CACHE VERIFICATION
    # ============================================================
    # Modules imported once are cached in sys.modules

    assert "sys" in sys.modules
    assert isinstance(sys.modules["sys"], types.ModuleType)

    # Importing already cached module returns the same object reference
    import math
    import math as math_alias

    assert math is math_alias
    assert sys.modules["math"] is math


    # ============================================================
    # 2. sys.path INSPECTION & SEARCH ROOTS
    # ============================================================
    # sys.path is an iterable list of directory search paths

    assert isinstance(sys.path, list)
    assert len(sys.path) > 0

    # sys.path[0] is typically the current working directory or script path
    assert isinstance(sys.path[0], str)


    # ============================================================
    # 3. DYNAMIC IMPORTING VIA importlib
    # ============================================================
    # importlib.import_module allows string-based runtime imports

    json_module = importlib.import_module("json")
    assert isinstance(json_module, types.ModuleType)

    encoded = json_module.dumps({"status": "healthy", "code": 200})
    assert encoded == '{"status": "healthy", "code": 200}'

    decoded = json_module.loads(encoded)
    assert decoded["code"] == 200


    # ============================================================
    # 4. RESOLVING CIRCULAR IMPORTS: DEFERRED / LOCAL IMPORT
    # ============================================================
    # Local imports inside function bodies break top-level circular locks

    def export_telemetry():
        # Local import executed only when function is called
        import hashlib
        data_hash = hashlib.sha256(b"telemetry_event").hexdigest()
        return data_hash

    hash_res = export_telemetry()
    assert isinstance(hash_res, str)
    assert len(hash_res) == 64


    # ============================================================
    # 5. DYNAMIC RELOADING WITH importlib.reload
    # ============================================================
    # Demonstrating runtime reloading of an in-memory module object

    # Create a dynamic module using types.ModuleType
    dynamic_mod = types.ModuleType("dynamic_test_module")
    dynamic_mod.version = "1.0.0"
    sys.modules["dynamic_test_module"] = dynamic_mod

    assert sys.modules["dynamic_test_module"].version == "1.0.0"

    # Mutate attribute
    sys.modules["dynamic_test_module"].version = "2.0.0"
    assert sys.modules["dynamic_test_module"].version == "2.0.0"

    # Clean up test module from sys.modules
    del sys.modules["dynamic_test_module"]
    assert "dynamic_test_module" not in sys.modules


    # ============================================================
    # 6. BYTECODE CACHING & __pycache__ (.pyc) MECHANICS
    # ============================================================
    # Python compiles .py to .pyc stored in __pycache__ with PEP 3147 tags

    # sys.dont_write_bytecode controls whether .pyc files are generated
    assert isinstance(sys.dont_write_bytecode, bool)

    # Magic number identifies the CPython bytecode version
    magic_number = importlib.util.MAGIC_NUMBER
    assert isinstance(magic_number, bytes)
    assert len(magic_number) == 4  # 4-byte header tag


    # ============================================================
    # 7. __all__ EXPORT SPECIFICATION & NAMESPACE FILTERING
    # ============================================================

    assert "__all__" in globals()
    assert "calculate_metric" in __all__
    assert "ServiceRegistry" in __all__


    # ============================================================
    # 8. TYPE CHECKING CONDITIONAL (TYPE_CHECKING)
    # ============================================================
    # TYPE_CHECKING evaluates to False at runtime, True during mypy analysis

    assert TYPE_CHECKING is False

    # Code inside `if TYPE_CHECKING:` is never executed at runtime
    type_checking_executed = False
    if TYPE_CHECKING:
        type_checking_executed = True
    assert type_checking_executed is False


if __name__ == "__main__":
    run_tests()
    print("04_modules_and_imports.py tests passed!")
