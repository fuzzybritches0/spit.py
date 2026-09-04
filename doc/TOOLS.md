# TOOLS.md - Tool Development Guide

Part of the spit.py documentation set (see `PROJECT.md`). This is the reference
for developing, changing, or reviewing tools in `spit_app/tools/`. Read
`CONVENTIONS.md` (module contract, style, git) and `TRAPS.md` before writing
code. The full design-rationale log lives in `DECISIONS.md`.

## Module attributes in use today (ground truth from the current tree)

`call style`: `async` = `call_async_generator()` (script run through `Run`),
`sync` = `call()` (in-process, no sandbox script).

| tool | call style | OUTPUT_TYPE_HINT | PATH_ARGS | other |
|---|---|---|---|---|
| delete_lines | async | text | path | common: lines.py |
| diff | async | text | file1, file2 | |
| file_info | async | (markdown) | path | common: file.py |
| find_files | async | text | path | |
| get_current_weather | sync | json | - | |
| grep | async | text | path | PROMPT_INST, MAX_SECONDS=0 |
| insert_line | async | text | path | common: lines.py |
| list_directory | async | (markdown) | path | common: file.py |
| load_image | sync | - | - | REQUIRES_MULTIMODAL_IMAGE=True |
| lsterm | sync | - | - | tmux backend |
| patch | async | text | path | common: lines.py, PROMPT_INST, MAX_SECONDS=0 |
| python | async | text | - | PROMPT_INST ([modules]/[builtins]/[timeout]/[max_mem_mb]), STREAM_TOOL_RESPONSE |
| read_files | async | text | path | accepts string or list |
| read_url | sync | html | - | PROMPT_INST |
| remove | async | - | path | |
| run_command | async | text | - | wrap_script, PROMPT_INST, STREAM_TOOL_RESPONSE, MAX_SECONDS=0 |
| run_script | async | text | - | PROMPT_INST ([interpreters]), STREAM_TOOL_RESPONSE, MAX_SECONDS=0 |
| search_replace | async | (markdown) | path | PROMPT_INST, MAX_SECONDS=0 |
| set_chat_description | sync | - | - | |
| terminal | sync | text | - | tmux backend, SANDBOX=True |
| websearch | sync | - | - | PROMPT_INST ([max_results], [save_search]) |
| write_file | async | - | path | |

Rules behind the columns:
- `PATH_ARGS` lists every argument holding a filesystem path: only those get
  `~` / `$VAR` expansion (`spit_app/arguments.py`). A path argument missing
  from the list silently stays unexpanded.
- `OUTPUT_TYPE_HINT` ("text", "python", "json", "html", ...) changes only the
  on-screen rendering for the user; the LLM always gets raw output. Set it for
  anything that is not Markdown.
- `PROMPT_INST` carries `[placeholder]` tokens that the app substitutes
  (timeout, interpreters, ...). Never disturb or rename a token, and note that
  `work.py` concatenates PROMPT and PROMPT_INST with **no separator** - PROMPT
  must end in a newline when PROMPT_INST follows.
- `STREAM_TOOL_RESPONSE` tools stream their output into the chat as it arrives.

## Tool file structure and test layout
File-based tools follow this structure:
- `/spit_app/tools/<tool_name>.py` - Main tool definition (DESC, SETTINGS, EXEC, call_async_generator)
- `/spit_app/tools/scripts/<tool_name>.py` - Script executed in sandbox
- `/spit_app/tools/scripts/common/<name>.py` - Shared helpers, prepended to a script by `get_script(__file__, "<name>")` (`file.py` = stat metadata for `file_info`/`list_directory`, `lines.py` = line-ending primitives for `patch`/`insert_line`/`delete_lines`). `setup.json` needs a matching `"common"` entry so the tests prepend the same file.
- Uses existing `Run` class for sandboxed execution
- Returns plain text output

Test suites follow the same layout: `spit_app/tests/tools/<tool_name>/` holds `setup.json`, `run_tests.sh` and `create_fixtures.sh` and nothing else; `spit_app/tests/tools/test_common.sh` holds the assertions (incl. the byte-level ones and `remove_fixtures`), `fixtures_common.sh` the fixture writers, `harness.py` the script runner, and `spit_app/tests/tools/*/fixtures/` is generated, gitignored and disposable.

Inside `fixtures/` every file is named after the test that owns it — `tNN-<short-name>.txt`, scratch and must-not-exist paths included — with `shared-<name>` for what several tests read and `corpus/<name>` for `patch`'s shared corpus (decision 49). `create_fixtures.sh` lists them in test order.

Terminal tools (`terminal`, `lsterm`) have a different structure:
- `/spit_app/tools/<tool_name>.py` - Main tool definition (DESC, SETTINGS, call)
- No `scripts/` subdirectory — directly uses the `Run` class's tmux methods (`term_new`, `term_input`, `term_screen`)
- Sessions persist across tool calls via `libtmux` (one tmux session per chat conversation)

---

## Tool Comparison Matrix

| Tool | Single File | Directory | Recursive | JSON Output | Markdown | Dry Run | Line Numbers |
|------|-------------|-----------|-----------|-------------|----------|---------|--------------|
| `file_info` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `list_directory` | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| `find_files` | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| `grep` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅¹ |
| `read_files` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅² |
| `write_file` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `search_replace` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅¹ |
| `diff` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅¹ |
| `patch` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| `insert_line` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| `delete_lines` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| `rename` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| `copy` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

¹ Line numbers are inherent to the output format (`file:line:`, match counts, diff hunk headers) — not a toggle.
² Opt-in via `show_line_numbers=true` (default `false`), `cat -n` style.

---

## Implemented tool specs (verbatim reference)

Full per-tool specs extracted from `~/TOOL_IMPLEMENTATION_SUMMARY.md` on
2025-09-04; they document behaviour the tests assert. Where a spec and the code
disagree, the code plus its test suite are right - and fix the discrepancy as
its own commit.

### 1. `find_files`
**Purpose**: Find files matching patterns in directories

**Parameters**:
- `path` (required): Directory to search
- `pattern` (optional): Glob pattern (e.g., `*.py`, `**/*.txt`). Default: `*`
- `recursive` (optional): Search subdirectories. Default: `True`
- `max_results` (optional): Maximum results. Default: `100`

**Output**: `Found N file(s):` header followed by indented file paths; directories are listed with a trailing `/`

**Example**:
```
find_files(path="/home/kurt", pattern="*.py", recursive=True)
```

---

### 2. `write_file` (Extended)
**Purpose**: Save text to file (overwrite or append)

**Parameters**:
- `path` (required): File path
- `content` (required): Text content
- `append` (optional): Append instead of overwrite. Default: `False`
- `create_dirs` (optional): Create parent directories. Default: `True`
- `prepend_newline` (optional): Add `\n` before content when appending. Default: `True`

**Output**: Success/error message

**Example**:
```
write_file(path="/home/kurt/file.txt", content="Line 1\n", append=True)
```

---

### 3. `list_directory` (Enhanced)
**Purpose**: Get directory contents with metadata including file sizes, owner/group, type (file/dir/link/block/char/fifo/socket), and modification times. Useful for exploring file systems and identifying special files like device nodes and symlinks.

**Parameters**:
- `path` (required): Directory path to list
- `recursive` (optional): Include subdirectories. Default: `False`
- `show_hidden` (optional): Include hidden files (starting with `.`). Default: `False`
- `max_results` (optional): Only show 'max_results' results. Min: 1, Max: 10000, Default: `100`

**Output**: Markdown table with Name/Path, Size, Type, Owner, Modified

**Features**:
- Human-readable sizes (B, KB, MB, GB, TB)
- Owner:Group display (e.g., `kurt:kurt`)
- File type detection: `file`, `dir`, `link`, `block`, `char`, `fifo`, `socket`
- Symlink detection with full target path (`file @ -> /full/path`)
- Broken symlink detection (`-> broken`)
- Truncation warning when results exceed max_results

**Example**:
```
list_directory(path="/home/kurt/spit.py", recursive=False, show_hidden=True)
```

---

### 4. `read_files` (Renamed from `read_file`)
**Purpose**: Read one or more text files

**Parameters**:
- `path` (required): A file path or list of file paths
- `encoding` (optional): File encoding. Default: `utf-8`
- `show_line_numbers` (optional): Prefix each line with a 1-based line number (cat -n style). Default: `False`

**Output**: 
- Single file: Direct content with file info
- Multiple files: Structured output with separators and summary
- With `show_line_numbers=True`: every content line is prefixed with a right-aligned 1-based number and a tab (applied per file in multi-file mode)

**Features**:
- Backward compatible: accepts both string and array for `path`; `show_line_numbers` defaults to `False` so existing output is byte-identical
- Optional `cat -n` style line numbering (1-based, right-aligned, tab-separated, width scales with digit count) — the reliable line-number view for tools that target lines by number (`insert_line` / `delete_lines`)
- Numbering uses `splitlines()`, so LF, CRLF and lone-CR files count lines uniformly; no phantom trailing line for files ending in a newline
- Display caveat: `splitlines()` strips line endings, so a CRLF file is *displayed* with LF endings in numbered mode (display only — the file itself is never modified)
- Error handling: FileNotFoundError, PermissionError, UnicodeDecodeError
- Summary: Shows total files processed and success count

**Example**:
```
read_files(path=["/home/kurt/file1.txt", "/home/kurt/file2.txt"], encoding="utf-8")
read_files(path="/home/kurt/file.txt", show_line_numbers=True)
```

---

### 5. `file_info` (NEW - Recently Implemented)
**Purpose**: Get detailed metadata for a single file or directory

**Parameters**:
- `path` (required): File or directory path
- `format` (optional): Output format - `'text'` or `'json'`. Default: `'text'`

**Output**: 
- Text format: Human-readable key-value pairs
- JSON format: Structured JSON object

**Features**:
- Comprehensive metadata: size, permissions, owner, group, timestamps
- File type detection: file, directory, block_device, char_device, fifo, socket, symlink
- Inode number and hard link count
- Symlink status with target path
- Boolean flags: is_file, is_directory, is_block_device, is_char_device, is_fifo, is_socket
- Human-readable size formatting
- Both text and JSON output options

**Example**:
```
file_info(path="main.py", format="text")
file_info(path="/home/kurt", format="json")
```

**Example Output (text)**:
```
File: spit.py/main.py
Exists: Yes
Type: file
Size: 119.0 B (119 bytes)
Permissions: rwxr-xr-x (755)
Owner: kurt:kurt
Modified: 2026-05-22 17:36:04
Inode: 40114263
Hard Links: 1
Is Symlink: No
Is File: 1
Is Directory: 0
```

**Example Output (JSON)**:
```json
{
  "path": "spit.py/main.py",
  "type": "file",
  "size_human": "119.0 B",
  "permissions": "rwxr-xr-x",
  "permissions_octal": "755",
  "owner": "kurt",
  "group": "kurt",
  "is_file": 1,
  "is_directory": 0
}
```

---

### 6. `search_replace` (NEW - Recently Implemented)
**Purpose**: Find and replace text in files

**Parameters**:
- `path` (required): File path
- `find` (required): Text or regex pattern to find
- `replace` (required): Replacement text
- `use_regex` (optional): Treat find as regex. Default: `False`
- `max_replacements` (optional): Limit replacements. Default: `0` (all)
- `dry_run` (optional): Don't change file, only report match count. Default: `False`

**Output**:
- Applied: `Replaced N of M match(es) in \`path\`.`
- No matches: `No matches found for \`find\` in \`path\`.` (exit 0)
- `dry_run`: `DRY RUN: Found N match(es) for \`find\` in \`path\`.` + `Would replace M with \`replace\`. File not modified.`

**Features**:
- Plain text or regex pattern matching
- Maximum replacements limit to control changes
- Handles UnicodeDecodeError for binary files
- Handles PermissionError for read/write operations
- Shows total matches found and replacements made
- No preview mode (removed to save tokens — LLMs handle single/multi-line replacement reliably)

**Example**:
```
search_replace(path="/home/kurt/file.txt", find="old_text", replace="new_text", use_regex=False)
search_replace(path="/home/kurt/file.txt", find="TODO", replace="DONE", dry_run=True)
```

**Example Output**:
```
Replaced 3 of 3 match(es) in `/home/kurt/file.txt`.
```

**Example Output (dry_run)**:
```
DRY RUN: Found 3 match(es) for `old_text` in `/home/kurt/file.txt`.
Would replace 3 with `new_text`. File not modified.
```

---

### 7. `terminal` (NEW - Recently Implemented)
**Purpose**: Control persistent interactive terminal sessions with a 24×80 character window. Best for long-running processes, interactive CLIs, REPLs, TUI applications, and background services.

**Parameters**:
- `name` (required): The terminal session name. A new name creates a new session; an existing name sends input to that session.
- `input` (optional): An array of string-of-characters and/or key names to send to the terminal.
- `delay` (optional): Seconds to wait before capturing the screen after sending input. Default: `1`

**Output**: The current 24×80 terminal screen with cursor position indicated by `█`. If the session has died: `INFO: Session dead.`

**Architecture**:
- Uses `libtmux` to create persistent tmux sessions (one tmux session per chat conversation)
- Each terminal is a tmux window running a bash shell
- Sandboxed by default with `bwrap` (bubblewrap) for security
- Screen captured via `capture_pane()`; cursor position shown via `display_message()`
- No scrollback — only the current 24 lines are captured

**Supported Keys**:
`Up`, `Down`, `Left`, `Right`, `Space`, `Tab`, `Delete`, `End`, `Enter`, `Escape`/`Esc`, `F1`–`F12`, `Home`, `Insert`, `PageDown`/`PgDn`, `PageUp`/`PgUp`
Modifier prefixes: `C-` (Ctrl), `S-` (Shift), `M-` (Alt)

**Features**:
- Persistent sessions that survive across tool calls within a chat
- Auto-creates a new session if the name does not already exist
- Cursor position rendered with `█` in the screen capture
- Sandbox support (bwrap) for security; can be disabled (at the user's own risk)
- Dead session detection with automatic cleanup

**Limitations**:
- 24×80 character window with **no scrollback**
- Output that scrolls off the screen is lost
- When a session dies while not being actively interacted with, no output can be recovered
- For verbose or long-lived processes, redirect output to a file (`> log.txt 2>&1`)
- Not ideal for one-shot file operations — prefer dedicated file and command tools

**Example**:
```
terminal(name="dev", input=["npm run dev > dev.log 2>&1 &", "Enter"])
terminal(name="dev", delay=3)                    # screen snapshot
terminal(name="dev", input=["C-c"])              # send Ctrl+C
terminal(name="dev", input=["exit", "Enter"])    # close session
```

---

### 8. `lsterm` (NEW - Recently Implemented)
**Purpose**: List all currently live terminal sessions for the current chat.

**Parameters**: None

**Output**: List of active session names, or `No active sessions found!`

**Architecture**:
- Uses `libtmux` to verify which tmux windows are still alive
- Dead sessions are automatically removed from the internal tracking
- Session names can be freely reused after the session dies

**Features**:
- Shows only live sessions (dead sessions are auto-cleaned)
- Prevents accidentally reusing a name that still has a live session
- Useful for checking whether a session has died after a long period of inactivity or due to system failure / user actions

**Example**:
```
lsterm()
```

**Example Output**:
```
# Currently active sessions:

- `dev`
- `test`
```

or:
```
No active sessions found!
```

---

### 9. `diff` (NEW - Recently Implemented)
**Purpose**: Compare two files and show differences

**Parameters**:
- `file1` (required): First file path
- `file2` (required): Second file path
- `context` (optional): Context lines. Default: `3`
- `output_format` (optional): `unified`, `context`, `side_by_side`. Default: `unified`

**Output**: 
- `unified`: Standard unified diff with hunk headers and line numbers, in a code block
- `context`: Context diff format, in a code block
- `side_by_side`: Aligned two-column view (old vs new) with line numbers and `[added]`/`[removed]`/`[changed]` markers, in a code block
- Identical files: `Files `<file1>` and `<file2>` are identical.`
- Summary line after the diff: lines added, removed, changed

**Features**:
- Uses `difflib` (stdlib) — no external dependencies
- Files read with UTF-8; `splitlines(keepends=True)` passed to difflib so content lines keep their line endings (difflib appends line terminators only to headers)
- Error handling: missing file, not-a-file, invalid `output_format`, UnicodeDecodeError
- `json.dumps` used for path arguments (handles quotes in paths)
- Non-zero exit code on errors

**Example**:
```
diff(file1="/home/kurt/a.txt", file2="/home/kurt/b.txt", context=3, output_format="unified")
```

**Example Output (unified)**:
```
--- a.txt
+++ b.txt
@@ -1,5 +1,6 @@
 Line one
-Line two
+Line two CHANGED
 Line three
 Line four
 Line five
+Line six

Summary: 1 line(s) added, 0 line(s) removed, 1 line(s) changed.
```

---

### 10. `patch` (REWRITTEN — branch `patch-tool-fixes-2`, decisions 53-58)
**Purpose**: Apply unified diff patches to a file

**Parameters**:
- `path` (required): File to patch
- `diff` (required): Diff content (unified format) or path to a diff file
- `reverse` (optional): Reverse the patch (apply new -> old). Default: `False`
- `dry_run` (optional): Preview without applying. Default: `False`

**The one rule the whole tool follows**: *the hunk body is the ground truth; the header is a position hint whose only job is to break ties. A hunk applies if and only if its target position can be determined without guessing.* Everything below is a consequence of that, and it is deliberately strict about location and loose about bookkeeping — the two things an LLM is respectively good and bad at.

**Output**:
- `dry_run`: `DRY RUN: preview of changes (file not modified):` + unified diff of the would-be change, then `N line(s) would be added, M line(s) removed. File would have X line(s).`
- Applied: `Patched `<path>`` (+ ` (reversed)` if reverse) `: N hunk(s) applied.` then `A line(s) added, R line(s) removed. File now has X line(s).`
- No-op: `DRY RUN: patch would make no changes.`
- Errors: `ERROR: <reason>`, non-zero exit, file left unmodified — any failing hunk rejects the whole patch (atomic)

**Placement**:
- **Header line counts are IGNORED.** They are still matched by the regex (so both `-N` and `-N,M` spellings, including the abbreviated `@@ -2 +2 @@`, parse) but never captured: the body already states how many lines it has, so demanding the number asks the model to do arithmetic for information that carries no signal, and punishes it for getting it wrong. This was the single largest source of refusals. It also unlocks the insertion header an LLM naturally writes: `@@ -3 +3,2 @@` (claims 1 old line, body has none) inserts before line 3, byte-identical to the canonical `@@ -3,0 +3,1 @@`.
- **Exactly one match of the body → applied there**, whatever the header says (so a shifted file with a stale header still works).
- **Several matches → the header's start line picks the nearest.** If the body matches at the header's own position, that is distance 0 and therefore uniquely nearest.
- **A tie is refused, never guessed.** Equidistant candidates used to silently take the earlier match and report success; now:
  `ERROR: Hunk 1 is ambiguous — line 1, line 3 match the file and are all the same distance from header line 2, so the header does not pick one. Add context lines, or point the header at the line you mean.`
- **Headers are optional per hunk and may be mixed.** The old all-or-nothing rule ("either every hunk has a header or none of them do") turned harmless variation into a hard error: a patch with one headerless hunk and one headed hunk, each matching uniquely, was refused.
- A **headerless** hunk has nothing to break a tie, so its body must match in exactly one place. A hunk that **only inserts** lines has no old lines to anchor on and therefore needs a header.
- **Every hunk is matched against the file as it is before the patch**, then the resolved spans are applied bottom-up. A hunk's own lines describe the pre-patch file — that is what a unified diff means — so an earlier hunk's edit can neither create nor destroy a later hunk's match, and the header start lines mean what they say with no running offset to reinterpret them.
- **Overlapping hunks are rejected**: `ERROR: Hunk 2 overlaps hunk 1 (lines 3-5 and 1-3) — hunks must describe different parts of the file.` Before this guard, `patch(1)`-style sequential application accepted such a patch with rc 0 and returned a plausible-looking union of the two hunks, with nothing to indicate they had both claimed line 3.

**Syntax accepted**:
- **Empty lines separate hunks — any number of them.** An empty line belongs to no hunk, so the body run below it starts a new one. The old parser dropped empty lines before parsing, which made them invisible rather than separating: two headerless hunks split by a blank line were merged into one and refused.
- A blank line *inside* a hunk is ` ` (single space) for context, `+` for an added blank, `-` for a removed blank — verified against `diff -u`, `git diff` and `difflib`, which all encode it exactly that way and never emit a truly empty line inside a hunk. GNU patch does tolerate a bare empty line, but only because it consumes exactly `old_count` body lines and so always knows where the hunk ends; since the counts are deliberately not trusted here, the same trick would mean guessing, and the visible price of that tolerance is `Hunk #1 succeeded at 1 with fuzz 2`.
- `--- old` / `+++ new` file headers are recognised as a *pair*, so a body line whose text merely starts with `--`/`++` (removing `--x` renders as `---x`) is not mistaken for a header.
- Abbreviated headers (`@@ -1 +1 @@`) and function-context suffixes (`@@ -1,5 +1,5 @@ def foo():`) are accepted. Markdown code fences around the patch are stripped, so output pasted straight from the `diff` tool works. `diff` accepts either patch content or a path to a patch file (auto-detected).
- **The `^^ -1,4 +1,4 ^^` trailing-header notation is gone**, along with its right-to-left pre-pass. It existed so a model could write the counts *after* the body; with the counts ignored there is nothing to get right afterwards, and in practice no model ever used it.

**Bytes preserved**:
- The target's dominant line terminator (LF, CRLF or lone CR, from the first line break) is detected on read and reused on write via `newline=''`, so patching one line of a CRLF file does not rewrite the whole file to LF. Shares its rule with `insert_line` through `common/lines.py` (decision 46).
- `\ No newline at end of file` markers are honoured, one per affected last line as real `diff`/`git diff` emit them, so `reverse` round-trips byte-exactly.
- The trailing newline of the result follows the **resolved span that reaches the end of the file** and its marker — not `hunks[-1]`, which was only ever "the hunk at EOF" when the patch happened to list hunks in file order.

**Diagnostics**: on a failed match the error names the first line within the hunk that actually differs (`line N: expected \`x\`, found \`y\``), not just the hunk's first line, and a blank is spelled out rather than printed as an empty gap:

```
ERROR: Hunk 1 does not match the file.
line 2: expected `beta`, found a BLANK line -- a blank line inside a hunk is ` `
for context or `+`/`-` for an added/removed line; a truly empty line only
separates hunks
```

**Examples**:
```
patch(path="/home/kurt/file.txt", diff="/home/kurt/file.patch")
patch(path="/home/kurt/file.txt", diff="@@ -1,3 +1,3 @@\n Line one\n-old\n+new\n Line three\n")
patch(path="/home/kurt/file.txt", diff="file.patch", reverse=True)
```

**Example Output**:
```
Reading diff from file `patch.diff`.
Patched `/home/kurt/work.txt`: 2 hunk(s) applied.
4 line(s) added, 3 line(s) removed. File now has 21 line(s).
```

**Example Output (dry_run)**:
```
DRY RUN: preview of changes (file not modified):
--- work.txt
+++ work.txt (patched)
@@ -1,10 +1,9 @@
 Line one
-Line two
+Line two CHANGED
 Line three

4 line(s) would be added, 3 line(s) removed. File would have 21 line(s).
```

---

### 11. `grep` (NEW - Recently Implemented)
**Purpose**: Search file contents for regex patterns

**Parameters**:
- `path` (required): Directory to search (a single file is also accepted)
- `pattern` (required): Regex pattern to search
- `file_pattern` (optional): File name filter (e.g., `*.py`). Default: `*`
- `recursive` (optional): Search subdirectories. Default: `True`
- `context` (optional): Lines before/after match. Default: `0`
- `max_results` (optional): Maximum number of results. Default: `100`

**Output**:
- Header: `Found N match(es) for `pattern` in `path`:`
- Matches in a code block as `file:line: content` (plain text, file:line:content format)
- Context lines (when `context > 0`) as `file-line-content` (dash separator, grep `-C` style)
- No matches: `No matches found for `pattern` in `path`.` (exit 0)
- Notes after the code block: truncation warning when `max_results` is hit, and count of skipped binary/unreadable files

**Features**:
- Regex patterns via `re` (stdlib), matched per line (`regex.search` on each line)
- File discovery via glob `file_pattern`; results sorted for deterministic output
- Context ranges merged when overlapping or adjacent (no duplicate context lines)
- Binary/unreadable files (`UnicodeDecodeError`, `OSError`) skipped, count noted at the end
- Truncation at `max_results` matches with a warning line
- Lenient `path`: a single file path is accepted and searched on its own
- Exit code 0 also for no matches (consistent with `diff`); non-zero only on errors (missing path, not file/dir, invalid regex)
- Timeout setting (default 0 = no timeout), same as `search_replace`

**Example**:
```
grep(path="/home/kurt/spit.py", pattern="def main", file_pattern="*.py", context=2)
```

**Example Output**:
```
Found 3 match(es) for `grep_me` in `test-grep`:

```
test-grep/app.py-5-    print("hello world")
test-grep/app.py:6:     grep_me("once")
test-grep/app.py:7:     grep_me("twice")
test-grep/app.py-8-
test-grep/app.py-9-class GrepMe:
test-grep/app.py:10:     def grep_me(self):
test-grep/app.py-11-        pass
```
Skipped 1 binary/unreadable file(s).
```

### 12. `insert_line` (NEW - Recently Implemented)
**Purpose**: Insert line(s) at a specific position in a file

**Parameters**:
- `path` (required): File path
- `content` (required): Content to insert (may span multiple lines)
- `line_number` (optional): Line to insert before (1 = beginning). Default: `1`
- `after_line` (optional): Insert after this line number (0 = beginning). Mutually exclusive with `line_number`. Default: `None`
- `dry_run` (optional): Preview without applying. Default: `False`

**Output**:
- Applied: `Inserted N line(s) into `path` <where>.` then `File now has M line(s).` — `<where>` is `at the beginning`, `at the end`, or `before line X`
- `dry_run`: `DRY RUN: preview of changes (file not modified):` + unified diff (via `difflib`) in a code block, then `N line(s) would be inserted <where>. File would have M line(s).`

**Features**:
- Multi-line content: `content.splitlines()` — each line becomes an inserted line; a trailing `\n` in content does not create a phantom empty line
- `line_number` is the 1-based line to insert *before* (`1` = beginning); appending at the end is `line_number = n+1` / `after_line = n`
- `after_line` is an equivalent "insert after line Y" mode (`0` = beginning); providing both with a non-default `line_number` is an error (ambiguity)
- Lenient integer coercion: numeric strings (`"5"`) accepted; non-integers → clean `ERROR: ... must be an integer`
- Trailing-newline state of the original file is preserved (no trailing newline is added to files that didn't have one; an empty file gets one once content is inserted)
- **Line endings are the file's own**: read and write use `newline=''`, the terminator of the file's first line break (`\n`, `\r\n` or lone `\r`) is detected and reused for the joined result, the inserted line and the trailing newline — inserting `MID` into `one\r\ntwo\r\n` yields `one\r\nMID\r\ntwo\r\n`. Mixed endings are normalised to that terminator, which is `patch`'s rule as well, so both tools produce the same bytes for the same edit
- `dry_run` renders the exact unified diff that would be applied — pasteable straight into the `patch` tool (fences auto-stripped), **including `\ No newline at end of file` markers**, so a file without a trailing newline round-trips byte-exactly (verified by round-trip tests: middle/beginning/end inserts, with and without trailing newline, blank lines, empty file, multi-line content)
- Error handling: missing file, not-a-file, out-of-range position (range stated in the message), empty content, non-integer position; non-zero exit on error, file left unmodified on error
- Pure stdlib — no external dependencies

**Example**:
```
insert_line(path="/home/kurt/file.txt", content="NEW", line_number=3)
insert_line(path="/home/kurt/file.txt", content="A1\nA2", after_line=2, dry_run=True)
```

**Example Output**:
```
Inserted 3 line(s) into `/home/kurt/file.txt` before line 3.
File now has 8 line(s).
```

**Example Output (dry_run)**:
```
DRY RUN: preview of changes (file not modified):
```
--- work.txt
+++ work.txt (inserted)
@@ -1,5 +1,7 @@
 Line one
 Line two
+A1
+A2
 Line three
 Line four
 Line five
```

2 line(s) would be inserted before line 3. File would have 7 line(s).
```

---

### 13. `delete_lines` (NEW - Recently Implemented)
**Purpose**: Delete lines from a file by line number range and/or by regex pattern

**Parameters**:
- `path` (required): File path
- `start_line` (optional): First line to delete (1-based, inclusive). Alone it deletes just that line. Default: `None`
- `end_line` (optional): Last line to delete (1-based, inclusive). Defaults to `start_line`. Requires `start_line`. Default: `None`
- `pattern` (optional): Regex deleted from every line it matches (matched per line, anchored with `^`/`$` like `grep`). With a line range only matching lines inside the range are deleted. Default: `None`
- `dry_run` (optional): Preview without deleting. Default: `False`

**Output**:
- Applied: `Deleted N line(s) from \`path\` (SCOPE).` then `File now has M line(s).` — `SCOPE` is `line 5`, `lines 3-7`, `matching \`TODO\`` or `lines 2-9 matching \`TODO\``
- No match: `No lines matched \`pattern\` in \`path\`.` (exit 0, file untouched)
- `dry_run`: `DRY RUN: preview of changes (file not modified):` + unified diff (via `difflib`) in a code block, then `N line(s) would be deleted (SCOPE). File would have M line(s).`
- Errors: `ERROR: <reason>` with a non-zero exit and the file left unmodified

**Features**:
- Range and pattern **compose**: the range selects the region, the pattern selects the lines inside it; pattern alone means the whole file; at least one of them is required
- `end_line` is inclusive and defaults to `start_line`, so `start_line=5` alone deletes only line 5
- Regex per line (`re.search`), terminator stripped first so `^`/`$` anchor to the line content; `re.error` is a clean `ERROR: Invalid regex pattern ...`
- **Per-line terminators are preserved untouched**: the file is read `splitlines(keepends=True)` and the kept lines are joined verbatim, so LF, CRLF and lone-CR files stay as they are and the trailing-newline state survives (no dominant-terminator detection needed — a delete only removes whole lines, it never has to synthesise an ending)
- **Uses the shared line-ending primitives**: `strip_newline()`, `read_text_raw()` and `write_text_raw()` come from `scripts/common/lines.py`, prepended by `get_script(__file__, "lines")` — the script has no private copies and opens no file of its own (decision 52)
- Deleting the last line of a file without a trailing newline leaves the previous line's terminator behind (`a\nb` → delete line 2 → `a\n`) — POSIX line semantics, same as `sed '2d'`
- Blank lines are ordinary lines (`^$` matches them)
- Deleting every line leaves an empty file (exit 0, `File now has 0 line(s).`)
- `dry_run` renders a real unified diff **including hand-written `\ No newline at end of file` markers** (`difflib` never emits them), so the preview is pasteable straight into `patch` and round-trips byte-exactly — tested for blank-line, no-trailing-newline, CRLF, whole-file and scattered-pattern shapes
- Validation: missing file, not-a-file, nothing to delete, `end_line` without `start_line`, `end_line` before `start_line`, out of range (valid range stated in the message), empty pattern, invalid regex, non-integer line numbers (numeric strings accepted)
- Pure stdlib — no external dependencies

**Example**:
```
delete_lines(path="/home/kurt/file.txt", start_line=12, end_line=14)
delete_lines(path="/home/kurt/notes.txt", pattern="^\\s*#")
delete_lines(path="/home/kurt/app.py", start_line=100, end_line=120, pattern="TODO", dry_run=True)
```

**Example Output**:
```
Deleted 2 line(s) from `demo.txt` (matching `TODO`).
File now has 5 line(s).
```

**Example Output (dry_run)**:
```
DRY RUN: preview of changes (file not modified):
```
--- demo.txt
+++ demo.txt (deleted)
@@ -1,7 +1,5 @@
 Header
 import os
 
-TODO: drop this
 keep me
-TODO: drop that
 footer
```

2 line(s) would be deleted (matching `TODO`). File would have 5 line(s).
```

---
