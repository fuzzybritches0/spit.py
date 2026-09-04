# TASKS-IN-PROGRESS.md

Tasks currently under way, with enough state for a different agent (or a
rescheduled one) to pick up exactly where work stopped. A task is only
"finished" when its Verify command passes on a clean tree.

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

### State (kept current while working - crash-recovery record)

- **Branch**: `task-streaming-render-bugs` (existed at `af9a328` = main tip,
  created empty by the planning agent; now carries this task). Last commit:
  docs(tasks) move-in entry.
- **Scope**: files touched so far: `doc/TASKS-IN-PROGRESS.md`,
  `doc/TASKS-PLANNED.md` only. No code touched yet.
- **Done**:
  - All docs read (AGENTS, PROJECT, CONVENTIONS, TRAPS, TESTING, DECISIONS,
    TASKS-*).
  - Baseline full suite green on main: delete_lines 127, diff 24, grep 30,
    insert_line 119, patch 80, read_files 32, search_replace 29,
    unit:arguments 131, unit:sandbox **119** (TESTING.md table still says
    103 - counts only went up, table is stale, not a regression).
  - Probe re-run, confirmed: `{}` renders `...#### arguments:\n}` (stray
    `}` leak); 2-arg render ends `...d` with 3 `~~~~` fences (odd - missing
    trailing `\n~~~~\n`); value containing `~~~~` verified.
  - Data flow read end to end (llamacpp -> callback -> Message -> Content ->
    Process -> PatternProcessing/pattern_methods -> Part/Code streams) plus
    `run.py` wrapper text (`STDERR_HEADER = "~~~~ stderr ~~~~"`).
  - Additional confirmed-by-reasoning suspects (each needs a test first):
    - `unescaped()` per-char repair (`last_char == "\\" and char == "\n"`)
      cannot tell a JSON-escape repair from a formatter-emitted real fence
      newline preceded by a value ending in a backslash - it eats the
      fence's leading `\n`. This IS symptom (a) (value ending `\\` in JSON
      + emitted `\n~~~~`).
    - formatter quote detection tests only `last_char == "\\"` (one
      backslash), so a value ending `"...\\"` in JSON (odd-backslash
      ambiguity) closes the string wrongly -> `}` arrives with `value`
      still True -> appended verbatim (another stray-} path).
    - `Process.process_content` sets `self.pp.part = ""` at the START of
      every call - wipes a pending `"~~~~"` that `code_block_start` left in
      `part` awaiting the closing fence (loss depends on chunk arrival =
      symptom (c)). Same reset at start of `finish_content`.
    - `tool_start()` gates on `self.pos == 0`, but `pos` stays 0 while
      content is shorter than bsize=8 - a second early callback prepends
      `~~~~~hint\n` AGAIN (5-tilde fence twice, parity flip).
    - 4-vs-5-tilde mix: inside a `~~~~~hint` block a `~~~~ stderr ~~~~`
      run neither closes (not equal to `~~~~~`) nor pushes-and-closes;
      `code_block_start_end` else-branch pushes it onto `code_fences`
      forever -> `tool_end`'s `\n~~~~~` closes the wrong entry (matches
      the `...with~~~~~` example).
- **Left** (next step, small): create `spit_app/tests/unit/render/` unit
  suite: `stub_textual.py` (sys.modules injection for textual, textual.widgets,
  textual.containers, textual.message, textual_image.widget, markdown_it,
  cairosvg, ziamath, PIL - LaTeX is imported by pattern_methods so these
  stubs are required even without latex in fixtures), `test_tool_call_format.py`
  (golden values + chunk-split invariance, imports tool_call.py directly,
  needs NO stub), `test_render_pipeline.py` (drive Process with fake
  target/Part; invariance across chunk splits for: tool_call render,
  tool-role content with output_type_hint incl. tool_start-once and mixed
  4/5 fences; run.py wrapper text + `~~~~ stderr ~~~~`). Tests must be RED
  on current code for the exact defects above (characterize-as-failing),
  then fixes in separate commits. Planned fix design (formatter rewrite):
  per-char JSON string scanner with proper escape-pair state integrated in
  the accumulate loop (replaces the whole-string `unescaped()` post-pass);
  close-branch drops `not self.key`; top-level close emits `\n~~~~\n` iff
  content was rendered since the last emitted fence; `{}` renders header
  only. Public API of ToolCall must not change (text_area_tool.py calls it
  once on complete JSON).
- **State hazards**: nothing half-finished; tree clean; no fixtures left
  over. Suites all green. Do NOT trust the 4/5-tilde analysis for the fix
  shape until the pipeline test reproduces it.
- **Verify**: `cd ~/spit.py && bash spit_app/tests/run_tests.sh` - all tool
  suites at ground-truth counts (127/24/30/119/80/32/29), unit:arguments
  131, unit:sandbox 119, new unit:render suite all green; manual checklist
  above in the running app (owner-side).

## Protocol when starting a task from TASKS-PLANNED.md

1. `git branch -a` (avoid name collisions), create a descriptively named
   branch. Never work on `main`, never push.
2. Move the entry here and keep these fields current AS YOU WORK - they are
   the crash-recovery record:
   - **Branch**: name + last commit sha on it
   - **Scope**: files touched so far
   - **Done**: what is complete and verified
   - **Left**: the precise next step, small enough to finish in one sitting
   - **State hazards**: half-finished edits, fixtures left over
     (`KEEP_FIXTURES`), uncommitted changes, suites currently red
   - **Verify**: command + expected result that closes the task
3. Commit early and often on the branch (one concern per commit) so the
   recovery point is a commit, not an uncommitted working tree.
4. On completion: run the FULL suite from the repo root, confirm ground-truth
   counts only went up by your new checks, move the entry to
   TASKS-FINISHED.md with the resolution (branch, commits, outcome), delete
   this entry.
