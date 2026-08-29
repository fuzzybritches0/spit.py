import sys
import difflib
from pathlib import Path

def err(message):
    print(f"ERROR: {message}")
    sys.exit(1)

def coerce_int(value, name):
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        err(f"`{name}` must be an integer, got `{value}`")

try:
    p = Path(path)
    if not p.exists():
        err(f"File does not exist: `{p}`")
    if not p.is_file():
        err(f"Path is not a file: `{p}`")
    if not content:
        err("Content is empty.")
    after_line_set = after_line is not None
    line_number_set = line_number != 1
    if after_line_set and line_number_set:
        err("Cannot use both `line_number` and `after_line` — they are mutually exclusive.")
    if after_line_set:
        after_line = coerce_int(after_line, "after_line")
        insert_at = after_line + 1
    else:
        line_number = coerce_int(line_number, "line_number")
        insert_at = line_number
    original = p.read_text(encoding='utf-8')
    lines = original.splitlines()
    n = len(lines)
    orig_has_nl = original == "" or original.endswith("\n")
    if insert_at < 1 or insert_at > n + 1:
        err(f"Position {insert_at} is out of range. Valid: 1 to {n + 1}.")
    new_lines = content.splitlines()
    if not new_lines:
        err("Content is empty.")
    result_lines = lines[:insert_at - 1] + new_lines + lines[insert_at - 1:]
    result = "\n".join(result_lines)
    if result_lines and orig_has_nl:
        result += "\n"
    elif not lines and result_lines:
        result += "\n"
    if insert_at == 1:
        where = "at the beginning"
    elif insert_at > n:
        where = "at the end"
    else:
        where = f"before line {insert_at}"
    added = len(new_lines)
    if dry_run:
        if result == original:
            print("DRY RUN: would make no changes.")
        else:
            print("DRY RUN: preview of changes (file not modified):")
            a = original.splitlines(keepends=True)
            b = result.splitlines(keepends=True)
            diff = difflib.unified_diff(a, b, fromfile=str(p),
                     tofile=str(p) + " (inserted)", n=3)
            print("".join(diff), end="")
        print(f"\n{added} line(s) would be inserted {where}. File would have {len(result_lines)} line(s).")
    else:
        p.write_text(result, encoding='utf-8')
        print(f"Inserted {added} line(s) into `{p}` {where}.")
        print(f"File now has {len(result_lines)} line(s).")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
