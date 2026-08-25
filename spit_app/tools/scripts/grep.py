import sys
import re
from pathlib import Path

try:
    path = Path(path)
    if not path.exists():
        print(f"ERROR: Path does not exist: `{path}`")
        sys.exit(1)
    if not path.is_file() and not path.is_dir():
        print(f"ERROR: Path is neither a file nor a directory: `{path}`")
        sys.exit(1)
    try:
        regex = re.compile(pattern)
    except re.error as err:
        print(f"ERROR: Invalid regular expression `{pattern}`: `{err}`")
        sys.exit(1)
    if path.is_file():
        files = [path]
    elif recursive:
        files = sorted(p for p in path.rglob(file_pattern) if p.is_file())
    else:
        files = sorted(p for p in path.glob(file_pattern) if p.is_file())
    total_matches = 0
    truncated = False
    skipped = 0
    output = []
    for f in files:
        if total_matches >= max_results:
            truncated = True
            break
        try:
            lines = f.read_text(encoding='utf-8').splitlines()
        except (UnicodeDecodeError, OSError):
            skipped += 1
            continue
        match_lines = [i for i, line in enumerate(lines, 1)
                       if regex.search(line)]
        if not match_lines:
            continue
        match_set = set(match_lines)
        ranges = []
        if context > 0:
            for ln in match_lines:
                start = max(1, ln - context)
                end = min(len(lines), ln + context)
                if ranges and start <= ranges[-1][1] + 1:
                    ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
                else:
                    ranges.append((start, end))
        else:
            ranges = [(ln, ln) for ln in match_lines]
        for start, end in ranges:
            for ln in range(start, end + 1):
                text = lines[ln - 1]
                if ln in match_set:
                    total_matches += 1
                    output.append(f"{f}:{ln}: {text}")
                    if total_matches >= max_results:
                        truncated = True
                        break
                else:
                    output.append(f"{f}-{ln}-{text}")
            if truncated:
                break
    if total_matches == 0:
        print(f"No matches found for `{pattern}` in `{path}`.")
    else:
        print(f"Found {total_matches} match(es) for `{pattern}` in `{path}`:")
        print("")
        for line in output:
            print(line)
        if truncated:
            print(f"Results truncated at {max_results} match(es).")
        if skipped:
            print(f"Skipped {skipped} binary/unreadable file(s).")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
