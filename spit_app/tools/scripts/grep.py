import sys
import os
import re
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
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        print(f"ERROR: Invalid regex pattern: `{e}`")
        sys.exit(1)
    results = []
    total_matches = 0
    if recursive:
        file_iterator = path.rglob(file_pattern)
    else:
        file_iterator = path.glob(file_pattern)
    for file_path in file_iterator:
        if len(results) >= max_results:
            break
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding='utf-8', errors='replace')
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    if len(results) >= max_results:
                        break
                    start = max(0, line_num - 1 - context)
                    end = min(len(lines), line_num + context)
                    match_info = {
                        'file': str(file_path),
                        'line': line_num,
                        'text': line.strip(),
                        'context': lines[start:end]
                    }
                    results.append(match_info)
                    total_matches += 1
                    break
        except Exception as e:
            continue
    if not results:
        print(f"No matches found for pattern: `{pattern}`")
    else:
        print(f"Found {total_matches} match(es) in {len(set(r['file'] for r in results))} file(s):")
        print("~~~~")
        for result in results:
            print(f"{result['file']}:{result['line']}: {result['text']}")
            if context > 0:
                for i, ctx_line in enumerate(result['context']):
                    line_num = max(0, result['line'] - 1 - context) + i
                    if line_num != result['line'] - 1:
                        print(f"  {line_num}: {ctx_line}")
            print()
        print("~~~~")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
