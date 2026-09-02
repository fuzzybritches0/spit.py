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

    def new_hunk(old_start, new_start, headed=True):
        return {
            "old_start": old_start,
            "new_start": new_start,
            "old": [],
            "new": [],
            "ctx": 0,
            "old_eof": False,
            "new_eof": False,
            "last": None,
            "headed": headed,
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
                # body lines with no header: the body alone has to place the hunk
                cur = new_hunk(1, 1, headed=False)
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
    original = read_text_raw(p)
    newline_style = detect_newline(original)
    orig_lines = original.splitlines()

    def find_all(lines_, block):
        # all 0-based positions where `block` appears in `lines_`
        n, m = len(lines_), len(block)
        if m > n:
            return []
        return [i for i in range(n - m + 1) if lines_[i:i + m] == block]

    def at_lines(positions):
        return ", ".join(f"line {pos_ + 1}" for pos_ in positions)

    def resolve_position(i, h, hint, positions):
        if len(positions) == 1:
            return positions[0]
        if not h["headed"]:
            err(f"Hunk {i} is ambiguous — its body matches the file at {at_lines(positions)} "
                f"and it has no header to choose between them. Add context lines, or a "
                f"`@@ -start +start @@` header naming the line you mean.")
        nearest = [pos_ for pos_ in positions if abs(pos_ - hint) == min(abs(x - hint) for x in positions)]
        if len(nearest) > 1:
            err(f"Hunk {i} is ambiguous — {at_lines(nearest)} match the file and are all the same "
                f"distance from header line {hint + 1}, so the header does not pick one. Add context "
                f"lines, or point the header at the line you mean.")
        return nearest[0]

    def sides(h):
        if reverse:
            return h["new"], h["old"], h["new_start"], h["old_eof"]
        return h["old"], h["new"], h["old_start"], h["new_eof"]

    def reject_overlaps(placed):
        deepest = None
        for item in sorted(placed, key=lambda item: (item["start"], item["hunk"])):
            if deepest is not None and item["start"] < deepest["end"]:
                err(f"Hunk {item['hunk']} overlaps hunk {deepest['hunk']} (lines "
                    f"{item['start'] + 1}-{item['end']} and {deepest['start'] + 1}-{deepest['end']}) "
                    f"— hunks must describe different parts of the file.")
            if deepest is None or item["end"] > deepest["end"]:
                deepest = item

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

    # Every hunk is placed against the untouched file, because a hunk's own
    # lines describe the file as it originally is. An earlier hunk's edit can
    # therefore neither create nor destroy a later hunk's match, the headers
    # need no running offset to be reinterpreted, and hunks that claim the
    # same lines become visible instead of quietly overwriting each other.
    placed = []
    for i, h in enumerate(hunks, 1):
        look_for, replacement, header_line, eof = sides(h)
        hint = header_line - 1
        if not look_for:
            # a pure insertion has no old lines to anchor on: only a header can place it
            if not h["headed"]:
                err(f"Hunk {i} is ambiguous — it only inserts lines, so its position has to "
                    f"come from a `@@ -start +start @@` header.")
            start = max(0, min(hint, len(orig_lines)))
        else:
            positions = find_all(orig_lines, look_for)
            if not positions:
                print(f"ERROR: Hunk {i} does not match the file.")
                probe = max(0, min(hint, len(orig_lines) - 1)) if orig_lines else 0
                print(describe_mismatch(look_for, probe, orig_lines))
                sys.exit(1)
            start = resolve_position(i, h, hint, positions)
        placed.append({"start": start, "end": start + len(look_for), "hunk": i,
                       "replacement": replacement, "eof": eof})

    reject_overlaps(placed)
    # Bottom-up application leaves every span above untouched, so the positions
    # resolved against the original stay valid. Two hunks inserting at the same
    # line keep the order they have in the patch: the first one ends up on top.
    work = list(orig_lines)
    for item in sorted(placed, key=lambda item: (-item["start"], -item["hunk"])):
        work[item["start"]:item["end"]] = item["replacement"]

    # The trailing newline follows the hunk that reaches the end of the file
    # and its `\ No newline at end of file` marker, if it carries one.
    deepest = max(placed, key=lambda item: item["end"])
    final_has_nl = orig_has_nl
    if deepest["end"] == len(orig_lines):
        final_has_nl = not deepest["eof"]
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
