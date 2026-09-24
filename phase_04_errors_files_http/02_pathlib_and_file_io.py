"""
Phase 4: Errors, Files, HTTP & Stdlib - Modern Filesystem (pathlib) & JSON
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Modern Python uses 'pathlib.Path' objects instead of legacy 'os.path' string manipulation.
   - Intuitive Path joining with the division operator: 'data_dir / "users" / "config.json"'.
   - Key Path Methods:
     * 'path.exists()', 'path.is_file()', 'path.is_dir()'
     * 'path.mkdir(parents=True, exist_ok=True)'
     * 'path.read_text(encoding="utf-8")', 'path.write_text(content, encoding="utf-8")'
     * 'path.glob("*.py")', 'path.rglob("**/*.json")' (recursive search)
   - Context Managers for streaming file I/O:
     * 'with open(path, "w", encoding="utf-8") as f: f.write(...)'
   - JSON Handling:
     * 'json.dumps(obj, indent=2)': Python dict/list -> JSON string (like JSON.stringify).
     * 'json.loads(json_str)': JSON string -> Python dict/list (like JSON.parse).
     * 'json.dump(obj, file_obj)': Serialize directly to a file handle.
     * 'json.load(file_obj)': Deserialize directly from a file handle.
   - JS/TS Analogy:
     * In Node.js: 'path.join(__dirname, "data.json")' and 'fs.promises.readFile()'.
     * In Python: 'Path(__file__).parent / "data.json"' and 'path.read_text(encoding="utf-8")'.

2. UNDER THE HOOD (CPython & Memory):
   - 'Path' is an object-oriented abstraction over OS file system calls (POSIX on Linux/macOS, WindowsPath on Windows).
   - Context manager 'with open(...) as f:' calls 'f.__enter__' (returning file descriptor) and guarantees
     'f.__exit__' calls 'close()', releasing OS file handles even if unhandled exceptions occur.

3. COMMON GOTCHA:
   - WINDOWS ENCODING TRAP: On Windows, 'open(path)' without 'encoding="utf-8"' defaults to the legacy code
     page (e.g. cp1252), crashing with UnicodeEncodeError when writing emoji or international text!
   - ALWAYS specify 'encoding="utf-8"'.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "Why should you use pathlib instead of os.path in Python, and how does Python
       guarantee file descriptor safety during I/O operations?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. pathlib vs os.path:
      "In modern Python (3.6+), pathlib is the standard because it treats paths as objects
       rather than raw strings. It allows intuitive path composition with the slash operator
       ('base_dir / filename'), eliminates platform-dependent path delimiter bugs between Windows
       and Linux, and packages reading, writing, globbing, and stat checks directly on the Path object."
   2. Deterministic File Clean-Up:
      "Python guarantees file handle safety via Context Managers ('with open(...) as f:').
       Under the hood, CPython enters the context, binds the file descriptor, and guarantees that
       the dunder method __exit__() will invoke close() on the file descriptor upon exiting the block,
       even if a critical exception is raised. In long-running backend microservices, this prevents
       leaking OS file descriptors under high concurrency."
================================================================================
"""

import sys
import json
from pathlib import Path

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def demonstrate_pathlib_operations(temp_dir: Path):
    print("\n--- 1. Pathlib Directory & File Creation ---")
    
    # Create directory tree
    sub_dir = temp_dir / "storage" / "records"
    sub_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Created directory: {sub_dir}")
    
    # Write text directly with UTF-8 encoding
    readme_file = sub_dir / "info.txt"
    readme_file.write_text("Hello from pathlib! 🚀", encoding="utf-8")
    print(f"  Wrote info.txt: '{readme_file.read_text(encoding='utf-8')}'")
    
    # Path introspection
    print(f"  File name: {readme_file.name}")
    print(f"  File suffix: {readme_file.suffix}")
    print(f"  File parent: {readme_file.parent}")
    print(f"  Exists? {readme_file.exists()}")


def demonstrate_json_serialization(temp_dir: Path):
    print("\n--- 2. JSON Serialization & Deserialization ---")
    json_path = temp_dir / "user_profile.json"
    
    sample_data = {
        "user_id": 101,
        "username": "py_architect",
        "roles": ["admin", "developer"],
        "is_active": True,
        "metadata": {"preferred_model": "gemini-3.8-flash", "tokens_processed": 45000}
    }
    
    # 1. Serialize to file using context manager
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=2)
    print(f"  Serialized dictionary to JSON file: {json_path}")
    
    # 2. Deserialize back from file
    with open(json_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    print(f"  Loaded JSON username: '{loaded_data['username']}'")
    print(f"  Roles: {loaded_data['roles']}")
    print(f"  Data matches original? {loaded_data == sample_data}")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

def save_and_load_config(file_path: Path, config_dict: dict) -> dict:
    """Writes config_dict as JSON and reads it back."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(config_dict, indent=2), encoding="utf-8")
    return json.loads(file_path.read_text(encoding="utf-8"))


def find_files_by_extension(directory: Path, extension: str) -> list[str]:
    """Finds all filenames matching extension in directory."""
    pattern = f"*.{extension.lstrip('.')}"
    return sorted([p.name for p in directory.glob(pattern)])


def run_tests():
    print("\n[*] Running automated self-tests for 02_pathlib_and_file_io.py...")
    test_dir = Path(__file__).parent / "_test_scratch"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        config_file = test_dir / "test_config.json"
        data = {"app_name": "ai_tutor", "port": 8000, "debug": False}
        loaded = save_and_load_config(config_file, data)
        assert loaded == data, "Config save and load must produce identical dictionary"
        
        # Test file listing
        (test_dir / "doc1.txt").write_text("a", encoding="utf-8")
        (test_dir / "doc2.txt").write_text("b", encoding="utf-8")
        (test_dir / "image.png").write_bytes(b"dummy")
        
        txt_files = find_files_by_extension(test_dir, "txt")
        assert txt_files == ["doc1.txt", "doc2.txt"], f"Expected ['doc1.txt', 'doc2.txt'], got {txt_files}"
        
        print("[SUCCESS] All self-tests passed cleanly!")
    finally:
        # Cleanup scratch test files
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 4 - Modern Filesystem (pathlib) & JSON")
    print("=" * 65)
    demo_dir = Path(__file__).parent / "_demo_scratch"
    demo_dir.mkdir(parents=True, exist_ok=True)
    try:
        demonstrate_pathlib_operations(demo_dir)
        demonstrate_json_serialization(demo_dir)
        print("-" * 65)
        run_tests()
    finally:
        import shutil
        if demo_dir.exists():
            shutil.rmtree(demo_dir)
    print("=" * 65)
