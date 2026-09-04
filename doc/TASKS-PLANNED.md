# TASKS-PLANNED.md

Tasks known to be wanted but not started. Light skeleton per task; the
referenced guides carry the detail. On starting a task: move its entry to
`TASKS-IN-PROGRESS.md`, create a branch first (never touch `main`, never
push), and keep the State field honest so an abandoned task is recoverable.

---

## P0 - Garbled streaming render: tool-call arguments and streamed tool output  [high priority, user-visible bug]

Investigated 2025-09-04; a standalone probe (below) confirmed one bug outright.
User-visible rendering defects; **the LLM's messages are intact** (verified:
the model receives raw accumulated `messages[-1]["content"][0]["text"]` and
raw JSON arguments - all corruption lives in the display pipeline only).

### Symptoms

- **(a) Missing characters** at explicit output points. Most often reported:
  the string `\n~~~~\n` should be on screen but only `~~~~\n` arrives,
  messing up the Markdown layout of the streamed arguments.
- **(b) A stray `}` at the end** of the arguments render, especially (not
  exclusively) when the tool call has no arguments (`{}`).
- **(c) Garbled streamed tool output** when `STREAM_TOOL_RESPONSE` is True
  (`run_command`, `run_script`, `python`), e.g.
  `Running proc[...some output...]...Process ended with~~~~~` - head and tail
  of the wrapper lines truncated, middle scrambled, fence out of place.

### Data-flow map (screen side; verified by reading the code)

1. `endpoints/llamacpp.py` `tool_calls()` accumulates streamed argument
   fragments into `messages[-1]["tool_calls"][i]["function"]["arguments"]`
   and fires `maybe_callback(2)`.
2. `chat/callback.py`: signal 2 -> `Message.process()` -> `Content.process`
   -> `chat/message/content/process/process.py` `Process.process` ->
   `get_content()` -> `process/tool_call.py` `ToolCall.tool_call_arguments()`.
   The formatter re-runs on the growing cumulative string; `Process` then
   re-processes pattern state from its own `self.pos`.
3. Tool response: `tools/run/run.py` `Run.run()` yields `"Running
   process...\n\n"` before and `"\nProcess exited with code N."` after the
   data - these ARE part of the message text, by design the LLM sees them
   too. `spit_app/tool_call.py` appends each chunk to the message and fires
   callback(2) when `STREAM_TOOL_RESPONSE`.
4. Screen-only layers: `Process.tool_start()`/`tool_end()` prepend
   `~~~~~<hint>\n` / append `\n~~~~~` fences, and the whole content passes
   through `pattern_processing.py` + `pattern_methods.py` (the `~` fence
   state machine, `bsize = 8` look-behind window, `skip_add_part`,
   `skip_pp`), writing into Textual `Markdown` streams (`containers/part.py`).

### Bug (b) - CONFIRMED by running the code

`process/tool_call.py` is standalone (no imports) - drive it directly with
system python3:

```python
import sys; sys.path.insert(0, "spit_app/chat/message/content/process")
from tool_call import ToolCall
tc = ToolCall({"name": "noop", "arguments": "{}"})
print(repr(tc.tool_call_arguments()))
# '...#### arguments:\n}'   <-- literal } leaked, no closing fence
```

Trace: the opening `{` sets `key = True`; the closing `}` only gets special
treatment in the branch `(char == "}") and not self.value and not self.key`,
so with `key` still True it falls through to the plain-content branch
(`elif len(self.json) == 1`) and is appended verbatim. Same class of bug also
means the **final value never gets its closing `\n~~~~\n`** - every render
ends with an unbalanced fence count, and `pattern_methods.code_fence`
treats `~~~~` as a code-block toggle, so an ODD number of separators leaves
the last value inside an unclosed block: rendering correctness silently
depends on the parity of the argument count. And a value that itself
contains `~~~~` (e.g. a `~~~~ stderr ~~~~` block quoted into an argument,
verified by the probe) flips the fence parity downstream.

### Suspects for (a) and (c) - ranked, not yet proven

1. `pattern_methods.code_fence`: sets `skip_add_part = 1` unconditionally on
   every fence char - swallows exactly one pending character, which matches
   "the `\n` before `~~~~` is gone". Fence-run detection uses one-char
   look-behind/ahead (`pp_last`/`pp_next`) whose state crosses chunk
   boundaries via `Process.process_content`'s per-call loop.
2. `Process.process_content` bookkeeping: `self.pos = pos + 1` uses the
   leaked loop variable; combined with `bsize = 8` (tail withheld until
   `finish_content`) and `skip_pp` multi-char pattern consumption, chunk
   boundaries can shift the committed prefix. `finish_content` sets
   `self.pos = pos` (off by one from the loop style above, harmless only if
   never followed by another `process_content`).
3. Mixed fence lengths: `tool_start`/`tool_end` use a 5-tilde fence while the
   formatter and tool output emit 4-tilde `~~~~`; `code_block_start_end`
   only closes a block when `code_fences[-1] == pattern` exactly, so a
   4/5-tilde mix can leave the state machine desynchronized across the rest
   of the message.
4. `ToolCall.unescaped()`: `rstrip(r"\\")` + `unesc_pos` accounting on a
   *mutated* (`replace`) copy while the offset indexes the *unmutated*
   `formatted_tool_call` - character loss near backslash-heavy values is
   plausible; also `unesc_tool_call` is rewritten (`[:-1] + r"\n"`) after
   already-written characters.
5. Callback/focus gating: `callback.py` `message_process()` only processes
   while the message widget has focus; unfocused messages catch up at signal
   0 via `finish()` - check what the user sees for a message that loses
   focus mid-stream, and whether pattern state (fences!) survives the
   skipped calls identically (it should, since content is cumulative, but
   `pp.part` reset each call + mid-loop `stream.stop()`/remount in
   `code_block_start/end` and `latex_end` is exactly where stop/start
   races of the Textual Markdown stream would bite).

### How to start

1. Re-run the probe above; extend it into a characterization test: feed
   argument JSON 1 char at a time AND in random chunk splits, assert the
   final formatted string equals a golden value per shape (empty `{}`,
   1 arg, N args, value containing `~~~~`/newlines/backslashes, unicode).
   `tool_call.py` needs no Textual - test it in isolation (TRAPS #19).
2. Only then touch the PatternProcessing pipeline; there it needs a fake
   `target`/`Part` (a stub with a collecting `stream`) because
   `pattern_methods` imports Textual containers - stub or run under the
   app's runtime.
3. Manual repro checklist: empty-args tool call (`lsterm`), `run_command`
   with stderr output (`separate_stderr` default True), a `write_file` call
   whose content contains `~~~~` or `----`, streaming `python`, focus
   switching mid-stream, then re-open an old chat (re-render path).

### Gotchas and constraints

- `process/text_area_tool.py` (save path) constructs `ToolCall` and calls
  `tool_call_arguments()` once on the complete JSON - any formatter fix
  must keep that caller working (whole-string behavior, not streaming).
- The `~~~~` separator convention is shared language between this formatter
  and the fence state machine - do not "just change" emitted fences without
  checking `pattern_processing.patterns` (`("~", ..., code_fence)`) and
  `code_block_start_end` pairing.
- Do not remove the `Running process...` / `Process exited with code N.`
  lines from `run.py` to "fix" (c) - they are deliberately in the LLM's
  message; the fix must be in the render pipeline only.
- No test coverage exists anywhere for these UI modules - expect to add the
  first; a pure-python characterization harness fits `tests/unit/` style.
- TRAPS #8 (distinctive tokens), #19 (no Textual in system python), #14
  (prove refactors by byte-level comparison against old output for the
  already-correct shapes before changing behavior).
- **Verify**: full tool suite stays green (UI change must not move any tool
  test counts); new unit suite green; manual checklist above passes in the
  running app.
## P1 - patch: the `is_header_pair` adjacency edge  [open, deliberate]

- **Scope**: `spit_app/tools/scripts/patch.py` (+ its test suite)
- **Status**: left open ON PURPOSE during the patch redesign. Not a forgotten bug.
- **Verify**: `cd ~/spit.py/spit_app/tests/tools/patch && bash run_tests.sh` (80 green);
  a fix adds tests without reusing freed numbers 5-9 (append-only).
- **Gotchas**: TRAPS #13/#15; DECISIONS 37 and the section below.
- **How to start**: read the verbatim record below first; the natural fix is to
  require a genuine file header to be followed by a `@@` hunk header or end of
  input. Prove the change by differential over every fixture (TESTING.md).

### 4. OPEN — the `is_header_pair` adjacency edge in `patch`

`is_header_pair()` decides a `--- old`/`+++ new` **pair** is a file header and skips
it. A *headerless* hunk that removes a line starting with `--` directly above an
added line starting with `++` produces exactly that shape as body content:

```
---x        (removing "--x")
+++y        (adding  "++y")
 keep
```

and the two lines are skipped as if they were a file header. Consequence is a loud
no-match failure, not corruption, and the shape is rare. Left unfixed on purpose so
it is a decision rather than an oversight; if it is ever fixed, the natural fix is to
require that a genuine file header be followed by a `@@` hunk header or end the
input, not merely be a pair.

---

## P2 - New tool: `rename`  [medium priority, not started]
## P3 - New tool: `copy`  [medium priority, not started]
## P4 - New tool: `code_parser`  [low priority, not started]

- **Scope**: new files `spit_app/tools/<name>.py` +
  `spit_app/tools/scripts/<name>.py` + `spit_app/tests/tools/<name>/`
  (exactly three files: `setup.json`, `run_tests.sh`, `create_fixtures.sh`).
- **Verify**: full suite `bash ~/spit.py/spit_app/tests/run_tests.sh` stays green;
  new suite's checks counted in its summary line.
- **Gotchas**: TRAPS #9 (PATH_ARGS), #7/#8 (`git commit -F`, author with
  write_file), #10 (generated fixtures only); follow CONVENTIONS.md module
  contract end to end; both destructive file tools need `dry_run`.
- **Drafted specs (verbatim)**:

## Tools Planned (Not Yet Implemented)

### 1. `rename` (Medium Priority)
**Purpose**: Rename/move files

**Parameters**:
- `old_path` (required): Current file path
- `new_path` (required): New file path
- `dry_run` (optional): Preview without renaming. Default: `False`

**Output**: Success/error message

---

### 2. `copy` (Medium Priority)
**Purpose**: Copy files with options

**Parameters**:
- `source` (required): Source file path
- `destination` (required): Destination path
- `preserve_permissions` (optional): Keep permissions. Default: `False`
- `dry_run` (optional): Preview without copying. Default: `False`

**Output**: Success/error, bytes copied

---

### 3. `code_parser` (Low Priority)
**Purpose**: Parse code structure

**Parameters**:
- `path` (required): File path
- `language` (optional): Language (python, javascript, etc.)

**Output**: Functions, classes, imports, dependencies

---

---

## P5 - Longer-term roadmap (from the repo README, no specs yet)

- More advanced agent capabilities
- GUI/TUI alternative to Textual
- Audio

These are owner-level roadmap items, not pick-up-and-code tasks; do not start
them without explicit instruction.
