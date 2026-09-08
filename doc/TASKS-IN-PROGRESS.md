> **Five entries are open**: four `terminal` followups — all on this branch's
> tail — and the streaming-render checklist. The empty-response
> defect that used to head this file is **fixed and committed on this branch**
> (`e699bb4`…`8f65e32`, six commits, 98 new checks) — the full record is in
> `TASKS-FINISHED.md`, "the `terminal` tool's empty response and its four
> siblings". What is left of it is here as followups 1-4: `remain-on-exit`
> (designed, measured, **not started** — it waits for the owner's explicit Go),
> the blocking `time.sleep()` in the tool's `call()`, one PROMPT question for the
> owner, and the capture/geometry list the ratatui harness will need. The
> streaming-render entry is code-complete and merged; only the owner's manual
> checklist in the running app is outstanding — **nobody else should sign it off**.

## Machine state these entries assume (none of it is in git)

- **The test venv**: `bash spit_app/tests/create_venv.sh` → `~/.venv-spit`
  (all of `requirements.txt`). `unit:terminal` needs libtmux and reports
  `PASS: 0  FAIL: 1` with the remedy when it cannot import it — never a silent
  zero. `doc/TESTING.md`, "The test venv". Note the `unset PIP_USER
  PIP_BREAK_SYSTEM_PACKAGES` inside that script: this environment exports both
  and a virtualenv refuses a `--user` install outright.
- **Never drive a shared tmux.** `tests/unit/terminal/stub_app.py` wraps
  `libtmux.Server` to pass `socket_name`, so the suite runs on its own server and
  may `kill-server` freely. A run leaves stale socket *files* under
  `/tmp/tmux-1000/spit-unit-terminal-*` and **no running server**; removing the
  files is safe, and any new terminal test must keep both properties.

## P0b-followup 1 - `remain-on-exit`: let a dead session report its real last screen  [**awaiting the owner's Go — do not start without it**]

Owner instruction 2026-09-07: *"Make `remain-on-exit` its own commit… Before you
start `remain-on-exit`, come back to me and wait for my `Go!`"*. The session
ended before the Go arrived. **It is not started and nothing in the tree
implements it.** Get the Go, or a clear no, before touching code.

**What it buys.** The dead-session path reports the last screen *we* captured
(decision 66 context: the cache lives in `app.tmux[chat_id]`), because with tmux
defaults the window is destroyed when its shell exits — measured: capture fails,
and if it was the last window the whole server goes (`no server running on
/tmp/tmux-1000/…`). With `remain-on-exit on` the pane survives its process, so
the report can carry the pane's **actual final screen** plus its **exit code**,
and `capture-pane -S -N` reaches past the visible 24 lines. Measured on tmux
3.7b: `dead=1 status=0`, `CCC-DIED-NOW` still on the screen, history recovered
from `-S -50`, and tmux appends its own `Pane is dead (status 0, …)` line — which
is what a test should assert the exit code from, not the tool's prose.

This is the direct answer to enhancement 8 below ("a crashed UI and an empty UI
look identical") and it is the cheapest of them, which is why it is first.

**The cost, and it is a real one.** `remain-on-exit` keeps the window in
`session.windows`, so the membership test in `run/terminal.py:pane_active()`
would call a dead pane **live**. Liveness therefore moves to `pane_dead`:

- `pane_active()` — one function, shared by `terminal` and `lsterm` since
  `c948b3e`, so there is exactly one place to change (deliberate: this decision
  was split out of the bug fix partly because it lands cleanly on a single
  implementation).
- the documented contract that **names are reusable after death** and that
  `lsterm` "lists only live sessions" (TOOLS.md 7/8, RUNTIME-RUN-COMMAND.md) —
  both rest on the membership test and must be restated in terms of `pane_dead`.
- `term_send_keys()` on a dead-but-retained pane: measured, tmux accepts the
  send and delivers nothing, so the tool must refuse explicitly instead of
  reporting success.

**How to start.** Set it on the **session before `new_window()`**
(`setw -t <session> remain-on-exit on`): set after creation it races the first
shell exit — in the probe that raced, the content was already gone. Then flip
liveness to `pane_dead`, add `pane_dead_status` to the dead report, and keep the
`app.tmux[chat_id]["last_screen"]` cache as the fallback for panes that died
before the option existed and for the window-destroyed path.

**Verify**: full suite unchanged (…/119 + `unit:terminal` at its current count)
plus the new checks green; new `tNN-*` numbers only (append-only). Manual: a
session that dies on its own reports its final screen **and** an exit status.

---

## P0b-followup 2 - the tool's `time.sleep()` blocks the UI event loop  [medium, known, deliberately left]

`spit_app/tools/terminal.py:call()` is synchronous and sleeps for `delay`
(default 1 s) before capturing: a 1-second freeze of the Textual UI on every
`terminal` call, on an app whose complaint list starts with "the UI is
sluggish". Recorded in the original P0b entry as *out of scope for the fix and
fatal for the migration*; the fix went in without touching it, so this is the
debt, still unpaid.

Fix shape: `call_async_generator` (the tool contract supports it — CONVENTIONS)
with `await asyncio.sleep(delay)`, so the wait yields to the event loop. Pairs
naturally with enhancement 5 (`wait_for` instead of blind sleeps) — do them
together and the streaming tests stop needing sleeps at all.

**Verify**: full suite unchanged; a check that the call no longer blocks
(measure the event loop, not the wall clock) — and note `tests/unit/terminal/`
drives `call()` directly, so it will not see an event-loop regression on its own.

---

## P0b-followup 3 - open question for the owner: the `Esc` limitation belongs in the PROMPT  [small, owner decision]

Measured while writing `test_keys.py`: bash reads a lone `Esc` and then **merges
the next character into it as Alt-`<char>`**. `Esc` followed immediately by
`echo mm-after-esc` reached the prompt as `cho mm-after-esc` — the `e` was
consumed by the escape sequence. This is terminal semantics (readline's
`keyseq-timeout`), **not** a spit.py defect, and the test deliberately asserts
only that the key is delivered and its name is not typed.

But a model reading today's PROMPT is told `["Esc", "Escape", …]` sequences are
fine and gets a mangled command, with no hint why. **Question for the owner**:
add one sentence to `terminal`'s PROMPT (something like: *a lone `Esc` merges
with the character that follows it; send `Esc` alone and wait, or use the pane's
own key names*)? Decision only, because PROMPT text is what the model reads and
TRAPS/RUNTIME-RUN-COMMAND require code and PROMPT to stay in sync — and
`tests/unit/prompt/` pins PROMPT strings.

---

## P0b-followup 4 - what the `terminal` tool still needs *for* the ratatui migration  [enhancement list, picked up piece by piece]

The list below was written during P0b and is **verbatim from it**; two items have
moved since, and they are marked. Nothing else has been done.

**Already done while fixing P0b** (so do not re-do them): the *single
implementation* half of item 9 — `pane_active()` now exists once in
`run/terminal.py` and `lsterm` uses it (`c948b3e`); the *namespaced
windows / fail loudly on an unresolved name* half is still open. Item 8
(process state as first-class output) is half-done: a dead pane now reports
the last cached screen instead of one bare sentence (P0b), but there is
still no `pane_pid` / exit code — see followup 1.

Once `spit-tui` exists (the Rust front end planned in
`doc/UI-ROUTE-RATATUI.md` and the engine <-> front-end protocol in
`doc/UI-PROTOCOL.md` — both merged into this branch at `51faf79`, so they are
**here**, read them here), this tool stops being a convenience and becomes **the only harness that can see the
real binary running in a real pty** — ratatui's `TestBackend` covers widgets,
the `terminal` tool covers the end-to-end app. Design it for that job now:

1. **`command`, not hardcoded `bash`.** Launch arbitrary argv in the pane
   (`command=["./spit-tui"]`, plus `env={}`, `cwd=`) — "start the UI under test"
   is the primitive; interactive bash is a special case of it.
2. **Geometry you control.** `cols`/`rows` at creation and a `resize` action.
   Re-wrap-on-resize is load-bearing in the new architecture (measured: 746 ms
   to re-wrap 2,000 messages), and it cannot be tested at 24x80 only. During
   this evaluation I had to nest a private tmux server to get 120x40 and
   150x35.
3. **Capture modes: text | styled | bytes.** Today only plain text. `styled`
   (`capture-pane -e`) is how markdown/heading/highlight/border styling gets
   asserted. `bytes` (raw pane output) is how the **Kitty/Sixel graphics path
   gets asserted** — LaTeX and image rendering could not be verified at all in
   this environment because there is no way to see the escape sequences, and
   that is the single biggest unproven risk in the migration.
4. **Cursor as data, not decoration.** Report `cursor_x`/`cursor_y` as fields
   instead of splicing a `█` into the text (which corrupts the line and breaks
   under double-width characters); keep the marker as an option.
5. **`wait_for` instead of `delay`.** Wait until a regex matches the pane or the
   screen is stable for N ms, with a timeout — blind sleeps make streaming tests
   flaky, and streaming (token deltas, follow-bottom, abort) is the main thing
   the new UI must get right.
6. **`send_bytes` / raw mode**, so a test can inject SGR mouse sequences and
   bracketed paste. That is exactly how pyratatui's mouse and paste defects were
   proven (4 injected sequences → 0 delivered; a pasted Enter arriving as
   `Ctrl+J` wipes the line), and the new front end's input layer must be tested
   against the same sequences.
7. **Scrollback and diffs**: `capture(since=-N)` and "changed lines since last
   capture". With no scrollback and full-screen captures, an agent burns context
   re-reading the same 24 lines; a diff capture makes long-session work cheap.
8. **Process state as first-class output**: `pane_pid`,
   `pane_current_command`, exited-with-code. Today a dead pane is one sentence
   with no content, so a crashed UI and an empty UI look identical.
9. **Namespaced sessions.** One tmux session per chat is right, but windows are
   addressed by bare `name`, and a call naming a session that does not exist can
   land on an already-running window instead of failing (this bit me live: the
   first call of a session named `prt` reached a different, already-attached
   pane). Prefix windows by `chat_id`, name the tmux window, and fail loudly on
   a name that does not resolve — `lsterm` should list the same names, and its
   private `pane_active()` (which mutates state as a side effect of *listing*)
   should be the one implementation in `Terminal`.
10. **Non-blocking and cancellable**: the wait must not block the UI loop; an
    in-flight `terminal` call should be abortable (the engine already has
    `kill_process_group` and the abort path — TRAPS #4).
11. **Structured output option** (`format="json"`: rows, cursor, attrs, bytes,
    process state) so tests assert on data instead of parsing prose.
12. **Sandbox stays on by default** (and lifecycle tests use `sandbox=False`,
    TRAPS #6), and teardown is guaranteed: a `kill` that takes the process group
    and auto-cleanup when the chat closes. During this evaluation the only way
    to clean up orphaned sessions was `tmux kill-server`, which is not
    acceptable in a shared tmux.


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
