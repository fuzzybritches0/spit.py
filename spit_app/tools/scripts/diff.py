import sys
import difflib
from pathlib import Path

try:
    p1 = Path(file1)
    p2 = Path(file2)
    if not p1.exists():
        print(f"ERROR: File does not exist: `{p1}`")
        sys.exit(1)
    if not p2.exists():
        print(f"ERROR: File does not exist: `{p2}`")
        sys.exit(1)
    if not p1.is_file():
        print(f"ERROR: Path is not a file: `{p1}`")
        sys.exit(1)
    if not p2.is_file():
        print(f"ERROR: Path is not a file: `{p2}`")
        sys.exit(1)
    if output_format not in ("unified", "context", "side_by_side"):
        print(f"ERROR: invalid output_format: `{output_format}` (use 'unified', 'context', or 'side_by_side')")
        sys.exit(1)
    content1 = p1.read_text(encoding='utf-8')
    content2 = p2.read_text(encoding='utf-8')
    lines1 = content1.splitlines()
    lines2 = content2.splitlines()
    dlines1 = content1.splitlines(keepends=True)
    dlines2 = content2.splitlines(keepends=True)
    if lines1 == lines2:
        print(f"Files `{p1}` and `{p2}` are identical.")
        sys.exit(0)
    sm = difflib.SequenceMatcher(a=lines1, b=lines2, autojunk=False)
    added = sum(j2 - j1 for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag == "insert")
    removed = sum(i2 - i1 for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag == "delete")
    changed = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag == "replace")
    if output_format == "unified":
        diff = difflib.unified_diff(dlines1, dlines2, fromfile=str(p1), tofile=str(p2), n=context)
        print("".join(diff), end="")
    elif output_format == "context":
        diff = difflib.context_diff(dlines1, dlines2, fromfile=str(p1), tofile=str(p2), n=context)
        print("".join(diff), end="")
    else:
        rows = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    rows.append((f"{i1+k+1:5d} {lines1[i1+k]}", f"{j1+k+1:5d} {lines2[j1+k]}", ""))
            else:
                mark = {"delete": "removed", "insert": "added", "replace": "changed"}[tag]
                for k in range(max(i2 - i1, j2 - j1)):
                    left = f"{i1+k+1:5d} {lines1[i1+k]}" if i1 + k < i2 else "      " * 2
                    right = f"{j1+k+1:5d} {lines2[j1+k]}" if j1 + k < j2 else "      " * 2
                    rows.append((left, right, mark))
        left_w = max(len(row[0]) for row in rows)
        print(f"{p1} (old)  vs  {p2} (new)")
        print("-" * 40)
        for left, right, mark in rows:
            line = left.ljust(left_w) + " | " + right
            if mark:
                line += f"  [{mark}]"
            print(line)
    print(f"\nSummary: {added} line(s) added, {removed} line(s) removed, {changed} line(s) changed.")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
