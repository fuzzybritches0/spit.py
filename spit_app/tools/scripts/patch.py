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
    if not content.strip():
        err("Diff is empty or contains no hunks.")
    lines = content.splitlines()
    # A header is matched in full (with or without the optional counts, which
    # `diff` omits when a count is 1) but only the two start line numbers are
    # captured: the counts are derived from the body and never trusted.
    hunk_re = re.compile(r"^@@ -(?P<old_start>\d+)(?:,\d+)? \+(?P<new_start>\d+)(?:,\d+)? @@")

    # A real file header always comes as a `--- old` line directly followed
    # by a `+++ new` line. A body line whose text starts with `--`/`++` renders
    # as `---…`/`+++…` too, so pairing is how a header is recognised but it is
    # not how a header is PROVED: the first two lines of a headerless hunk that
    # removes a `--…` line and adds a `++…` line complete a pair exactly as a
    # header does, and they are content. `pair_is_body()` asks the file.
    def is_header_pair(arr, i):
        if arr[i][:3] == "---":
            return i + 1 < len(arr) and arr[i + 1][:3] == "+++"
        if arr[i][:3] == "+++":
            return i > 0 and arr[i - 1][:3] == "---"
        return False

    def body_run(arr, i):
        end = i
        while end < len(arr) and arr[end][:1] in (" ", "-", "+"):
            end += 1
        return arr[i:end]

    def findable_side(block):
        # the lines a hunk has to find in the file to be placed: the old side
        # going forward, the new side in reverse -- the swap `sides()` performs.
        if reverse:
            return [line[1:] for line in block if line[0] in " +"]
        return [line[1:] for line in block if line[0] in " -"]

    def has_changes(block):
        # a run of pure context places an edit nowhere, so it is not evidence for
        # the header reading against the body reading of the pair above it.
        return any(line[0] in "-+" for line in block)

    def places_a_hunk(block):
        # A hunk with nothing to find is placed by a `@@` header or not at all
        # (decision 35), so an empty block places nothing and cannot argue for a
        # reading of the pair above it.
        return bool(block) and bool(find_all(orig_lines, block))

    def pair_is_body(arr, i):
        # `---x` over `+++y`, with a body run under them: the file header of the
        # hunk below, or that hunk's own first two lines. A pair with no body run
        # under it -- end of input, a blank line, or a `@@` header next -- is a
        # header whoever the file is, which is why every real diff is untouched
        # by this: `diff`/`git` always write the `@@` line.
        if arr[i][:3] != "---":
            return False
        run = body_run(arr, i + 2)
        if not run:
            return False
        as_body = places_a_hunk(findable_side(arr[i:i + 2] + run))
        as_header = has_changes(run) and places_a_hunk(findable_side(run))
        if as_body and as_header:
            err(f"The `---`/`+++` pair at lines {i + 1}-{i + 2} is a file header or the first two "
                f"body lines of the hunk under it, and the file matches both readings. Write the "
                f"hunk's `@@ -start +start @@` header between them to say which it is.")
        # A body reading that places a real edit wins over a header reading that
        # places none: a patch whose only content is context is not what a patch
        # is for, and the silent no-op it produced was the whole of the defect.
        return as_body

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

    # The file is read before the patch is parsed because the pair above a
    # headerless hunk is only decidable against it. Nothing here can fail on a
    # missing file: that is refused at the top.
    original = read_text_raw(p)
    newline_style = detect_newline(original)
    orig_lines = original.splitlines()

    def find_all(lines_, block):
        # all 0-based positions where `block` appears in `lines_`
        n, m = len(lines_), len(block)
        if m > n:
            return []
        return [i for i in range(n - m + 1) if lines_[i:i + m] == block]

    hunks = []
    cur = None
    for idx, line in enumerate(lines):
        m = hunk_re.match(line)
        if m:
            cur = new_hunk(int(m["old_start"]), int(m["new_start"]))
            hunks.append(cur)
            continue
        if not line:
            # An empty line separates hunks: it belongs to none of them, so the
            # body run below it starts a new hunk. A blank line *inside* a hunk
            # is never empty -- context is " ", added is "+", removed is "-".
            cur = None
            continue
        if line[:1] in (" ", "-", "+"):
            if cur is None:
                if is_header_pair(lines, idx) and not pair_is_body(lines, idx):
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

    def shown(text):
        if text is None:
            return "<past end of file>"
        return "a BLANK line" if text == "" else "`" + text + "`"

    def describe_mismatch(exp, start, work):
        # first position within the expected block that differs from the file,
        # so the error names the real culprit line instead of always line 1.
        for k, want in enumerate(exp):
            at = start + k
            have = work[at] if 0 <= at < len(work) else None
            if have != want:
                advice = ""
                if have == "" or want == "":
                    advice = (" -- a blank line inside a hunk is ` ` for context or `+`/`-` for an "
                              "added/removed line; a truly empty line only separates hunks")
                return f"line {at + 1}: expected {shown(want)}, found {shown(have)}{advice}"
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
