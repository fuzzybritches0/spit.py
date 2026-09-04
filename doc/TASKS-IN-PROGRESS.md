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

- **Branch**: `task-streaming-render-bugs`. Commits on it, in order:
  - `f72dcd1` docs(tasks): start P0 on its branch (this entry moved here)
  - `69bd1ba` tool_call: rewrite the arguments formatter as a per-char
    JSON scanner (+ `tests/unit/render/test_tool_call_format.py`, 230
    checks; differential old-vs-new over 35 shapes recorded in the
    message)
  - `ba87435` process: stop the fence drift and fence poisoning that
    garble streams (+ `tests/unit/render/test_render_pipeline.py`;
    process.py hint fences become stable prefix/suffix attributes,
    pattern_methods pairs fences by same-char + at-least-length;
    suspects cleared by measurement and NOT changed: pp.part reset,
    tool_start-twice, skip_add_part - recorded in the commit message)
  - (pending commit) docs: TESTING ground-truth row unit:render 278 +
    sandbox re-measurement 119, DECISIONS 59 (fence language, pairing
    rule, accepted limits), `----` argument shape added to the suite.
- **Scope**: `spit_app/chat/message/content/process/tool_call.py`
  (rewritten), `process.py`, `pattern_methods.py`, new
  `spit_app/tests/unit/render/` (run_tests.sh, stub_textual.py,
  test_tool_call_format.py, test_render_pipeline.py), docs as above.
- **Done**:
  - All symptoms (a), (b), (c) have failing-first characterization tests
    and fixes; unit:render 278 green (formatter 230 + pipeline 48).
  - (a) was the whole-string `unescaped()` post-pass eating fence and
    escaped newlines and mis-detecting quote escapes - gone with the
    per-char scanner; streaming == whole-string == monotonic per shape.
  - (b) stray `}`: the rewrite's close branch has no `not self.key`
    guard; the trailing fence is emitted at the top-level close; `{}`
    renders the header only; even fence parity asserted per shape.
  - (c) two root causes fixed and measured (see ba87435): self.pos
    indexing a string whose `~~~~~text\n` prefix vanished after the
    first callback (per-boundary text loss), and code_block_start_end
    pushing foreign fence runs onto code_fences forever (STDERR_HEADER
    inside the hint block poisoned the stack). Chunk-split invariance
    asserted at every two-split boundary for the run_command shape.
  - text_area_tool.py save path kept working (format suite t6);
    missing-"arguments" KeyError crash fixed (t7).
  - Focus-skip catch-up (suspect 5) verified benign via finish-only
    re-render tests (pipeline t8) - final screen identical to
    fully-streamed.
- **Left**: owner-side MANUAL checklist in the running app (needs the
  app runtime; system python3 has no Textual, TRAPS #19): empty-args
  call (`lsterm`), `run_command` with stderr, `write_file` content
  containing `~~~~`/`----`, streaming `python`, focus switching
  mid-stream, re-open an old chat. Every item has an automated analogue
  in tests/unit/render; this item is the human confirmation. On its
  pass: move this entry to TASKS-FINISHED.md.
- **State hazards**: none. Tree clean at every commit; no fixtures used;
  no suite red. KNOWN ACCEPTED LIMITS (DECISIONS 59): argument values
  with >=5-tilde runs at column 0 can close their own block early;
  JSON truncated mid-stream leaves the last value fence open.
- **Verify**: `cd ~/spit.py && bash spit_app/tests/run_tests.sh` -
  127/24/30/119/80/32/29 + 131/278/119, all FAIL 0 (the tool-suite
  counts must not move); manual checklist (owner-side) as in Left.

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
