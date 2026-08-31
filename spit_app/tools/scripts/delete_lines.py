import re
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

def strip_ending(line):
    for ending in ("\r\n", "\n", "\r"):
        if line.endswith(ending):
            return line[:-len(ending)]
    return line

def read_lines(path):
    with open(path, "r", encoding="utf-8", newline="") as file:
        return file.read().splitlines(keepends=True)

def write_lines(path, lines):
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write("".join(lines))

def render_preview(old_lines, new_lines, path):
    chunks = []
    for chunk in difflib.unified_diff(old_lines, new_lines, fromfile=str(path),
                                      tofile=str(path) + " (deleted)", n=3):
        is_body = chunk[:1] in (" ", "-", "+")
        if is_body and not chunk.endswith(("\n", "\r")):
            chunks.append(chunk + "\n")
            chunks.append("\\ No newline at end of file\n")
        else:
            chunks.append(chunk)
    return "".join(chunks)

def describe_range(start_line, end_line):
    if start_line == end_line:
        return f"line {start_line}"
    return f"lines {start_line}-{end_line}"

def build_scope(start_line, end_line, pattern):
    if start_line is None:
        return f"matching `{pattern}`"
    if pattern is None:
        return describe_range(start_line, end_line)
    return f"{describe_range(start_line, end_line)} matching `{pattern}`"

try:
    p = Path(path)
    if not p.exists():
        err(f"File does not exist: `{p}`")
    if not p.is_file():
        err(f"Path is not a file: `{p}`")
    if end_line is not None and start_line is None:
        err("`end_line` requires `start_line`.")
    if start_line is None and pattern is None:
        err("Nothing to delete: provide `start_line` (optionally `end_line`) or `pattern`.")
    if pattern is not None and not pattern:
        err("Pattern is empty.")
    matcher = None
    if pattern is not None:
        try:
            matcher = re.compile(pattern)
        except re.error as bad_pattern:
            err(f"Invalid regex pattern `{pattern}`: `{bad_pattern}`")
    if start_line is not None:
        start_line = coerce_int(start_line, "start_line")
        if end_line is None:
            end_line = start_line
        else:
            end_line = coerce_int(end_line, "end_line")
        if end_line < start_line:
            err(f"`end_line` {end_line} is before `start_line` {start_line}.")
    lines = read_lines(p)
    total = len(lines)
    if start_line is not None:
        if total == 0:
            err("File is empty: there is no line to delete.")
        if start_line < 1 or start_line > total:
            err(f"`start_line` {start_line} is out of range. Valid: 1 to {total}.")
        if end_line > total:
            err(f"`end_line` {end_line} is out of range. Valid: 1 to {total}.")
        region = range(start_line - 1, end_line)
    else:
        region = range(total)
    doomed = {index for index in region
              if matcher is None or matcher.search(strip_ending(lines[index]))}
    if not doomed:
        print(f"No lines matched `{pattern}` in `{p}`.")
        sys.exit(0)
    kept = [line for index, line in enumerate(lines) if index not in doomed]
    scope = build_scope(start_line, end_line, pattern)
    deleted = len(doomed)
    remaining = total - deleted
    if dry_run:
        print("DRY RUN: preview of changes (file not modified):")
        print(render_preview(lines, kept, p), end="")
        print(f"\n{deleted} line(s) would be deleted ({scope}). File would have {remaining} line(s).")
    else:
        write_lines(p, kept)
        print(f"Deleted {deleted} line(s) from `{p}` ({scope}).")
        print(f"File now has {remaining} line(s).")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
