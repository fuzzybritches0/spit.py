import sys
import re
import difflib
from pathlib import Path

def err(message):
    print(f"ERROR: {message}")
    sys.exit(1)

try:
    p = Path(path)
    if not p.exists():
        err(f"File does not exist: `{p}`")
    if not p.is_file():
        err(f"Path is not a file: `{p}`")
    dp = Path(diff)
    if dp.is_file() and dp.resolve() != p.resolve():
        content = dp.read_text(encoding='utf-8')
        print(f"Reading diff from file `{dp}`.")
    else:
        content = diff
    lines = [line for line in content.splitlines() if line]
    if not lines:
        err("Diff is empty or contains no hunks.")
    # A header is matched in full (with or without the optional counts, which
    # `diff` omits when a count is 1) but only the two start line numbers are
    # captured: the counts are derived from the body and never trusted.
    hunk_re = re.compile(r"^@@ -(?P<old_start>\d+)(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@")

    # A real file header always comes as a `--- old` line directly followed
    # by a `+++ new` line. A body line whose text starts with `--`/`++`
    # renders as `---…`/`+++…` but is NOT part of such a pair, so pairing is
    # how we tell a header apart from a body line without a hunk header.
    def is_header_pair(arr, i):
        if arr[i][:3] == "---":
            return i + 1 < len(arr) and arr[i + 1][:3] == "+++"
        if arr[i][:3] == "+++":
            return i > 0 and arr[i - 1][:3] == "---"
        return False

    def new_hunk(old_start, new_start, implicit=False):
        return {
            "old_start": old_start,
            "new_start": new_start,
            "old_count": 0,
            "new_count": 0,
            "old": [],
            "new": [],
            "ctx": 0,
            "old_eof": False,
            "new_eof": False,
            "last": None,
            "implicit": implicit,
        }

    hunks = []
    cur = None
    for idx, line in enumerate(lines):
        m = hunk_re.match(line)
        if m:
            cur = new_hunk(int(m["old_start"]), int(m["new_start"]))
            hunks.append(cur)
            continue
        if line[:1] in (" ", "-", "+"):
            if cur is None:
                if is_header_pair(lines, idx):
                    continue  # `--- old` / `+++ new` file header, not a body line
                # body without a header: implicit hunk (must match in exactly one place)
                cur = new_hunk(1, 1, implicit=True)
                hunks.append(cur)
            cur["last"] = line[0]
            if line[0] in " -":
                cur["old"].append(line[1:])
            if line[0] in " +":
                cur["new"].append(line[1:])
            if line[0] == " ":
                cur["ctx"] += 1
        elif line.startswith("\\") and cur is not None and cur["last"]:
            # `\ No newline at end of file`
            if cur["last"] in " -":
                cur["old_eof"] = True
            if cur["last"] in " +":
                cur["new_eof"] = True
        # anything else (---, +++, Index:, diff --git, ...) is ignored

    if not hunks:
        err("No hunks found!")
    for i, h in enumerate(hunks, 1):
        if not h["old"] and not h["new"]:
            err(f"Hunk {i} is empty.")
    # a patch is either fully headed or fully headerless; mixing is an error
    missing = [i for i, h in enumerate(hunks, 1) if h["implicit"]]
    if 0 < len(missing) < len(hunks):
        subject = (f"Hunk {missing[0]} has no header" if len(missing) == 1
                   else "Hunks " + ", ".join(str(i) for i in missing) + " have no header")
        err(f"{subject}, but the other hunks do — either every hunk needs a header or none of them do.")
    # The body is the ground truth: a hunk's line span is what its lines are,
    # whatever the header's counts claim (or fail to claim).
    for h in hunks:
        h["old_count"], h["new_count"] = len(h["old"]), len(h["new"])
    original = read_text_raw(p)
    newline_style = detect_newline(original)
    orig_lines = original.splitlines()

    def find_all(lines_, block):
        # all 0-based positions where `block` appears in `lines_`
        n, m = len(lines_), len(block)
        if m > n:
            return []
        return [i for i in range(n - m + 1) if lines_[i:i + m] == block]

    def describe_mismatch(exp, start, work):
        # first position within the expected block that differs from the file,
        # so the error names the real culprit line instead of always line 1.
        for k, want in enumerate(exp):
            at = start + k
            have = work[at] if 0 <= at < len(work) else None
            if have != want:
                found = "`" + have + "`" if have is not None else "<past end of file>"
                return f"line {at + 1}: expected `{want}`, found {found}"
        return "the block matches at its start but not as a whole (internal)"

    orig_has_nl = original == "" or original.endswith(newline_style)
    work = list(orig_lines)
    offset = 0
    for i, h in enumerate(hunks, 1):
        if reverse:
            exp, rep, start = h["new"], h["old"], h["new_start"]
        else:
            exp, rep, start = h["old"], h["new"], h["old_start"]
        hint = start - 1 + offset
        if not exp:
            # pure insertion hunk
            if h["implicit"]:
                err(f"Hunk {i} is ambiguous — it only inserts lines and has no header!")
            pos = max(0, min(hint, len(work)))
        else:
            positions = find_all(work, exp)
            if not positions:
                print(f"ERROR: Hunk {i} does not match the file.")
                probe = max(0, min(hint, len(work) - 1)) if work else 0
                print(describe_mismatch(exp, probe, work))
                sys.exit(1)
            if h["implicit"]:
                if len(positions) > 1:
                    where = ", ".join(f"line {pos_ + 1}" for pos_ in positions)
                    err(f"Hunk {i} is ambiguous — its body matches the file at {where}!")
                pos = positions[0]
            elif hint in positions:
                pos = hint
            else:
                # nearest to the header position; equidistant -> earlier
                pos = min(positions, key=lambda pos_: (abs(pos_ - hint), pos_))
        work[pos:pos + len(exp)] = rep
        offset += (pos - hint) + (len(rep) - len(exp))
    # trailing newline of the resulting file
    last = hunks[-1]
    final_has_nl = orig_has_nl
    if not reverse:
        if last["old_start"] + last["old_count"] - 1 >= len(orig_lines):
            final_has_nl = not last["new_eof"]
    else:
        if last["new_start"] + last["new_count"] - 1 >= len(orig_lines):
            final_has_nl = not last["old_eof"]
    result = newline_style.join(work)
    if work and final_has_nl:
        result += newline_style
    if reverse:
        added = sum(len(h["old"]) - h["ctx"] for h in hunks)
        removed = sum(len(h["new"]) - h["ctx"] for h in hunks)
    else:
        added = sum(len(h["new"]) - h["ctx"] for h in hunks)
        removed = sum(len(h["old"]) - h["ctx"] for h in hunks)
    if dry_run:
        if result == original:
            print("DRY RUN: patch would make no changes.")
        else:
            print("DRY RUN: preview of changes (file not modified):")
            a = original.splitlines(keepends=True)
            b = result.splitlines(keepends=True)
            print("".join(difflib.unified_diff(a, b, fromfile=str(p), tofile=str(p) + " (patched)", n=3)), end="")
        print(f"\n{added} line(s) would be added, {removed} line(s) removed. File would have {len(work)} line(s).")
    else:
        write_text_raw(p, result)
        mode = " (reversed)" if reverse else ""
        print(f"Patched `{p}`{mode}: {len(hunks)} hunk(s) applied.")
        print(f"{added} line(s) added, {removed} line(s) removed. File now has {len(work)} line(s).")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
