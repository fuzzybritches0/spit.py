import sys
import os
from pathlib import Path
import fnmatch

try:
    path = Path(path)
    if not path.exists():
        print(f"ERROR: Path does not exist: `{path}`")
        sys.exit(1)
    if not path.is_dir():
        print(f"ERROR: Path is not a directory: `{path}`")
        sys.exit(1)
    results = []
    if recursive:
        iterator = path.rglob(pattern)
    else:
        iterator = path.glob(pattern)
    print("```")
    for item in iterator:
        if len(results) > max_results:
            break
        if item.is_file():
            results.append(str(item))
        elif item.is_dir():
            results.append(str(item) + "/")
    print(f"Found {len(results)} file(s):")
    for result in results:
        print(f"  {result}")
    print("```")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
