"""
02_pathlib_and_file_io.py

============================================================
1. CONCEPT
============================================================

File system operations and persistent serialization in modern Python are
anchored by `pathlib.Path`, streaming context managers, and deterministic encoding:

1. Modern Filesystem Abstraction (`pathlib.Path` - PEP 428):
   - Replaces legacy string-based `os.path` functions with rich object-oriented
     path instances.
   - Cross-Platform Path Composition: Uses the division operator `/`
     (`base_dir / "data" / "payload.json"`), automatically applying the correct
     OS delimiter (`/` on POSIX, `\\` on Windows).
   - Path Anatomy:
     - `path.name`: Full filename with extension (`"report.tar.gz"`).
     - `path.stem`: Filename without final extension (`"report.tar"`).
     - `path.suffix`: Extension including dot (`".gz"`).
     - `path.parent`: Immediate containing directory.
     - `path.resolve()`: Resolves symlinks and relative segments into a canonical
       absolute path.
   - Path Transformation Helpers: `path.with_name()`, `path.with_suffix()`.

2. File I/O: High-Level vs Streaming:
   - High-Level Convenience (Whole-File in RAM):
     `path.read_text(encoding="utf-8")` and `path.write_text(content, encoding="utf-8")`.
     `path.read_bytes()` and `path.write_bytes(raw_bytes)`.
   - Low-Memory Streaming (Chunk / Line-by-Line):
     `with open(path, mode="r", encoding="utf-8") as f: for line in f: ...`
     Memory consumption remains strictly $O(1)$ regardless of whether the file
     is 100 KB or 100 GB.

3. Directory Operations & Globbing:
   - Safe creation: `path.mkdir(parents=True, exist_ok=True)`.
   - Safe deletion: `path.unlink(missing_ok=True)` for files; `path.rmdir()` for directories.
   - Pattern Matching: `path.glob("*.json")` (shallow) and `path.rglob("*.py")` (recursive).

4. JSON Serialization (`json` module):
   - In-memory strings: `json.dumps(obj, indent=2)` and `json.loads(json_str)`.
   - Streaming file handles: `json.dump(obj, f)` and `json.load(f)`.
   - Custom serialization: The `default` callable hook to serialize datetimes,
     sets, and UUIDs.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Path Construction            | `base / "sub" / "file.txt"`        | `path.join(base, "sub", "file.txt")|
| Current Script Directory     | `Path(__file__).parent`            | `__dirname` / `import.meta.dirname`|
| Canonical Absolute Path      | `path.resolve()`                   | `path.resolve(p)`                  |
| Read Entire Text File        | `path.read_text(encoding="utf-8")` | `await fs.promises.readFile(p, "utf8")|
| Write Entire Text File       | `path.write_text(data, ...)`       | `await fs.promises.writeFile(p, data)|
| Line-by-line Streaming       | `for line in file_handle:`         | `readline.createInterface({ ... })`|
| JSON Serialization (String)  | `json.dumps(obj, indent=2)`        | `JSON.stringify(obj, null, 2)`     |
| JSON Deserialization (String)| `json.loads(json_str)`             | `JSON.parse(json_str)`             |
| Recursive Directory Scan     | `path.rglob("*.ts")`               | `glob("**/*.ts")` or `fs.readdir`  |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python File I/O Differences:
1. In Python, an open file object is directly iterable: `for line in f:` streams
   lines lazily using an internal buffer without loading the whole file into RAM.
2. The Windows Encoding Trap: In Node.js, `readFile()` defaults to UTF-8 when
   given an encoding parameter. In Python, omitting `encoding="utf-8"` defaults to
   the operating system's locale code page (like `cp1252` on Windows), resulting in
   `UnicodeEncodeError` when non-ASCII characters appear!


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Concrete vs Pure Paths:
   - `pathlib` separates logic into `PurePath` (pure string path computation, no I/O)
     and `Path` (concrete class executing OS system calls).
   - Calling `Path(...)` instantiates `WindowsPath` on Windows and `PosixPath` on
     Linux/macOS, utilizing the OS-specific file system C runtime calls (`CreateFileW`
     on Windows, `open()` syscall on POSIX).

2. Buffered I/O Stream Layers:
   - When calling `open(path, "r", encoding="utf-8")`, CPython constructs a
     3-layer I/O stack:
     1. `FileIO` (Raw OS binary file descriptor).
     2. `BufferedReader` (In-memory buffer, typically 8 KB, reducing OS syscalls).
     3. `TextIOWrapper` (Decodes bytes to Python Unicode strings on the fly).

3. Deterministic Resource Reclamation via `__exit__`:
   - A file object implements the context manager protocol.
   - Entering `with open(...) as f:` calls `f.__enter__()` (returning `f`).
   - Exiting calls `f.__exit__()`, which invokes `f.close()`, releasing the OS
     file descriptor immediately even if exceptions occur.


============================================================
4. COMMON GOTCHAS
============================================================

1. The Windows Default Encoding Trap:
   - `open("data.txt", "w").write("Rocket 🚀")`
   - Crashes on Windows with: `UnicodeEncodeError: 'charmap' codec can't encode character`.
   - Fix: ALWAYS pass `encoding="utf-8"`.

2. Loading Massive Files with `.read()` or `.readlines()`:
   - Calling `f.read()` or `f.readlines()` reads the entire file into RAM at once.
   - For a 10 GB log file, this causes memory exhaustion (OOM).
   - Fix: Stream line-by-line: `for line in f: process(line)`.

3. Mixing Raw String Manipulation with Path Objects:
   - Concatenating path strings: `str(path) + "/file.txt"`.
   - Fix: Use the `/` operator: `path / "file.txt"`.

4. Unhandled File Deletion Errors:
   - Calling `path.unlink()` raises `FileNotFoundError` if the file is absent.
   - Fix: Use `path.unlink(missing_ok=True)`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Why is pathlib superior to os.path, and how does path composition work?"
Script:
"`pathlib` replaces legacy string-based file manipulation with object-oriented abstractions.
Instead of passing raw strings to standalone functions like `os.path.join` and `os.path.exists`,
paths are represented as `Path` objects that encapsulate attributes like `.stem`, `.suffix`,
and `.parent`, along with methods for reading, writing, and directory creation. Furthermore,
`pathlib` overloads the division operator `/` to compose paths cleanly—such as
`base_dir / 'subdir' / 'config.json'`—automatically handling platform-specific path separators
between Windows and Linux."

Q2: "How do you stream and process a 20 GB file in Python without causing an Out-Of-Memory error?"
Script:
"To process a 20 GB file with minimal memory footprint, we open the file inside a context
manager using streaming mode: `with open(path, 'r', encoding='utf-8') as f: for line in f:`.
Python's file object implements the iterator protocol backed by a buffered C reader.
Instead of loading the file into RAM like `.read()` or `.readlines()` would, the `for line in f`
loop reads chunks into a small 8 KB internal buffer and yields one line at a time. The auxiliary
memory complexity remains strictly $O(1)$, consuming only a few kilobytes of RAM regardless
of file size."

Q3: "How do json.dump and json.dumps differ, and how do you serialize custom objects like datetime?"
Script:
"`json.dumps()` serializes a Python object into an in-memory JSON formatted string, whereas
`json.dump()` serializes directly into an open writable file stream, minimizing RAM usage
for large payloads. By default, the `json` module only supports standard primitives. To serialize
custom objects like `datetime` or `UUID`, we pass a custom callable to the `default` parameter
of `dumps`—for instance, `default=lambda obj: obj.isoformat() if isinstance(obj, datetime) else str(obj)`.
Alternatively, modern applications leverage Pydantic models with `.model_dump_json()`."
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def custom_json_serializer(obj):
    """Custom serializer for non-primitive types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def run_tests():
    # ============================================================
    # 1. PATH ANATOMY & MANIPULATION
    # ============================================================

    sample_path = Path("projects") / "backend" / "analytics_report.tar.gz"

    # Name: full file name
    assert sample_path.name == "analytics_report.tar.gz"

    # Stem: name without final suffix
    assert sample_path.stem == "analytics_report.tar"

    # Suffix: final file extension
    assert sample_path.suffix == ".gz"

    # Suffixes: list of all extensions
    assert sample_path.suffixes == [".tar", ".gz"]

    # Parent directory
    assert sample_path.parent == Path("projects") / "backend"

    # Path transformation: changing suffix
    json_path = sample_path.with_suffix(".json")
    assert json_path.name == "analytics_report.tar.json"

    # Path transformation: changing name
    config_path = sample_path.with_name("config.yaml")
    assert config_path.name == "config.yaml"


    # ============================================================
    # 2. FILESYSTEM OPERATIONS & HIGH-LEVEL I/O
    # ============================================================

    # Using temporary directory for safe isolated tests
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # Create nested directory tree (parents=True, exist_ok=True)
        target_dir = temp_dir / "services" / "auth"
        target_dir.mkdir(parents=True, exist_ok=True)
        assert target_dir.is_dir() is True

        # High-level write_text with explicit UTF-8
        data_file = target_dir / "service_config.txt"
        test_content = "Service: AuthGateway\nStatus: Operational 🚀\nRegion: us-east-1"
        data_file.write_text(test_content, encoding="utf-8")

        assert data_file.exists() is True
        assert data_file.is_file() is True

        # High-level read_text
        read_back = data_file.read_text(encoding="utf-8")
        assert read_back == test_content

        # Stat verification
        file_stat = data_file.stat()
        assert file_stat.st_size > 0

        # Safe deletion with missing_ok=True
        data_file.unlink(missing_ok=True)
        assert data_file.exists() is False


    # ============================================================
    # 3. STREAMING FILE I/O (LINE-BY-LINE)
    # ============================================================

    with tempfile.TemporaryDirectory() as temp_dir_str:
        stream_file = Path(temp_dir_str) / "large_dataset.csv"

        # Write lines
        lines_to_write = [f"record_id_{i},{i*10}\n" for i in range(5)]
        with open(stream_file, mode="w", encoding="utf-8") as f:
            f.writelines(lines_to_write)

        # Stream line-by-line (Constant O(1) memory)
        read_records = []
        with open(stream_file, mode="r", encoding="utf-8") as f:
            for line in f:
                read_records.append(line.strip())

        assert len(read_records) == 5
        assert read_records[0] == "record_id_0,0"
        assert read_records[4] == "record_id_4,40"


    # ============================================================
    # 4. GLOBBING AND DIRECTORY SEARCH
    # ============================================================

    with tempfile.TemporaryDirectory() as temp_dir_str:
        base = Path(temp_dir_str)
        (base / "a.json").write_text("{}", encoding="utf-8")
        (base / "b.json").write_text("{}", encoding="utf-8")
        (base / "c.txt").write_text("text", encoding="utf-8")

        sub = base / "subfolder"
        sub.mkdir()
        (sub / "nested.json").write_text("{}", encoding="utf-8")

        # Shallow glob: matches only in base
        shallow_json_files = sorted([p.name for p in base.glob("*.json")])
        assert shallow_json_files == ["a.json", "b.json"]

        # Recursive rglob: matches nested files
        recursive_json_files = sorted([p.name for p in base.rglob("*.json")])
        assert recursive_json_files == ["a.json", "b.json", "nested.json"]


    # ============================================================
    # 5. JSON SERIALIZATION & DESERIALIZATION
    # ============================================================

    payload = {
        "cluster": "prod-cluster-01",
        "active": True,
        "nodes": [1, 2, 3],
        "created_at": datetime(2026, 9, 26, 12, 0, 0),
    }

    # In-memory serialization with custom default serializer
    json_string = json.dumps(payload, default=custom_json_serializer, indent=2)
    assert '"cluster": "prod-cluster-01"' in json_string
    assert '"created_at": "2026-09-26T12:00:00"' in json_string

    # In-memory deserialization
    parsed_payload = json.loads(json_string)
    assert parsed_payload["cluster"] == "prod-cluster-01"
    assert parsed_payload["active"] is True
    assert parsed_payload["nodes"] == [1, 2, 3]

    # File stream serialization (json.dump / json.load)
    with tempfile.TemporaryDirectory() as temp_dir_str:
        json_file = Path(temp_dir_str) / "data.json"

        simple_data = {"version": "2.0", "status": "OK"}
        with open(json_file, mode="w", encoding="utf-8") as f:
            json.dump(simple_data, f, indent=2)

        with open(json_file, mode="r", encoding="utf-8") as f:
            loaded_from_disk = json.load(f)

        assert loaded_from_disk == {"version": "2.0", "status": "OK"}


if __name__ == "__main__":
    run_tests()
    print("02_pathlib_and_file_io.py tests passed!")
