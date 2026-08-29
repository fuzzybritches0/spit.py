import sys
import re
from pathlib import Path

try:
    path = Path(path)
    if not path.exists():
        print(f"ERROR: Path does not exist: `{path}`")
        sys.exit(1)
    
    if not path.is_file():
        print(f"ERROR: Path is not a file: `{path}`")
        sys.exit(1)
    content = path.read_text(encoding='utf-8')
    if use_regex:
        pattern = re.compile(find)
        matches = list(pattern.finditer(content))
        num_matches = len(matches)
    else:
        matches = []
        start = 0
        while True:
            idx = content.find(find, start)
            if idx == -1:
                break
            matches.append((idx, idx + len(find)))
            start = idx + 1
        num_matches = len(matches)
    if num_matches == 0:
        print(f"No matches found for `{find}` in `{path}`.")
        sys.exit(0)
    max_matches = num_matches
    if not max_replacements == 0:
        if num_matches > max_replacements:
            max_matches = max_replacements
    if dry_run:
        print(f"DRY RUN: Found {num_matches} match(es) for `{find}` in `{path}`.")
        print(f"Would replace {max_matches} with `{replace}`. File not modified.")
        sys.exit(0)
    if use_regex:
        new_content, num_replaced = pattern.subn(replace, content, count=max_matches)
    else:
        new_content = content
        num_replaced = max_matches
        count = 0
        for start_idx, end_idx in matches[:max_matches]:
            offset = count * (len(find) - len(replace))
            new_content = new_content[:start_idx-offset] + replace + new_content[end_idx-offset:]
            count += 1
    path.write_text(new_content, encoding='utf-8')
    print(f"Replaced {num_replaced} of {num_matches} match(es) in `{path}`.")
    sys.exit(0)
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
