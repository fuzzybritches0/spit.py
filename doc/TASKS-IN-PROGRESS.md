# TASKS-IN-PROGRESS.md

Tasks currently under way, with enough state for a different agent (or a
rescheduled one) to pick up exactly where work stopped. A task is only
"finished" when its Verify command passes on a clean tree.

> **Two entries are open. Start with `P0b` — the `terminal` tool.** It is
> broken today, and it is also the harness the UI migration will depend on.
> The streaming-render entry below it is code-complete and merged; only the
> owner's manual checklist in the running app is outstanding.

## P0b - `terminal` returns an empty message container: `term_screen()` throws the screen away  [high priority, user-visible, blocks all interactive work and the UI migration]

Reported by the owner 2026-09-07: a `terminal` call produced an empty message
container. Root cause found by reading the code; the fix is small, the
diagnosis is complete, the *tests* are the work. Started on branch
`task-terminal-empty-output`.

### Root cause (static, certain)

`spit_app/tools/run/terminal.py` `term_screen()` builds the screen into the
**local** `output` and then returns **`self.output`**, which is assigned exactly
once — to `""` in `__init__` — and never written again:

```
$ grep -rn "self\.output" spit_app/tools/run/*.py spit_app/tools/*.py
run/terminal.py:14:   self.output = ""            # the only write, in __init__
run/terminal.py:70:   return f"{self.output}\n\nINFO: Session dead."
run/terminal.py:78:   return f"{self.output}\n\nINFO: Session dead."
run/terminal.py:90:   return self.output          # <-- the screen is `output`, not this
```

So for a **live** pane the tool returns `""`, and `spit_app/tools/terminal.py`
`call()` ends with `return terminal.term_screen(name)` → an empty tool response
→ an empty message container. For a **dead** pane it returns
`"\n\nINFO: Session dead."` with an empty prefix, which is why a dead session
looks like a truncated one. The two dead-pane branches were clearly written
expecting `self.output` to hold the last screen; nothing ever puts it there.

`term_send_keys()` calls `self.term_screen(name)` and discards the result (line
46) — the intent was surely to keep the pre-input screen for the dead-session
message. That is the shape the fix should restore: capture into `self.output`
where it is wanted, and **return the local `output` from `term_screen()`**.

**Verify the live copy first (TRAPS #19).** The app runs outside this
interpreter, and in the session where this was diagnosed, some `terminal` calls
*did* return real screens while the code in this tree can only return `""`. So
before anything else: confirm the running copy is this file
(`git log -1 --format=%H -- spit_app/tools/run/terminal.py`, compare against the
checkout the app imports), then reproduce with
`terminal(name="probe", input=["echo one two three", "Enter"])`.

### Second real defect, same tool: every key combination is sent as literal text

`term_input()` strips the key/modifier names out of `_inp` to decide whether the
argument is a bare key or a chord — and throws the result away, because `str`
is immutable and the return value is discarded:

```python
_inp = inp
for key in KEYS:      _inp.replace(key, "")    # no-op, five times over
for mod in MODS:      _inp.replace(mod, "")    # no-op
if len(_inp) <= 1:
    return self.term_send_keys(name, inp, False)   # never taken for "C-c"
return self.term_send_keys(name, inp, True)        # literal text "C-c"
```

`"C-c"` is 3 characters, so the `<= 1` branch is unreachable for a chord and
Ctrl-C — the thing the tool's own PROMPT advertises (`Send a signal ["C-c"]`) —
is typed into the pane as the four characters `C-c`. Everything in `KEYS` still
works (it returns earlier), which is why the bug is invisible until you need an
interrupt. Note the corollary: `S-Tab`, `M-x`, `C-a`, `C-q` are all broken, and
`tui-textarea`-style editors driven through this tool cannot be interrupted.
Empirically confirm before fixing (send `C-c` to `sleep 60` and check whether it
dies), then fix by comparing the *returned* string, and add a check that a chord
reaches the pane as a control character, not as text.

### Third and fourth defects (small, same file, fix in the same sweep)

- `tools/terminal.py`: `dealy = arguments["delay"]` — misspelled target, so the
  caller's `delay` is silently ignored and `time.sleep(delay)` always sleeps 1.
  Also `if "delay" in arguments and arguments["delay"]` means `delay=0` is
  ignored too. (Both are silent-wrong-argument bugs: TRAPS #9's cousin.)
- `tools/terminal.py`: `terminal.term_new(name)`'s return value is discarded.
  `term_new` returns `check_bwrap(...)`'s error string when bwrap is unusable,
  **and returns without creating anything** — `call()` then indexes
  `app.tmux[chat_id]["windows"]`, which was never populated, and raises
  `KeyError` instead of reporting "bwrap missing". Return the error.
  Relatedly, `Terminal.pane_active()` and `lsterm.pane_active()` index
  `self.tmux[self.chat_id]` with no guard for a chat that has no tmux entry.
- `time.sleep(delay)` sits in a synchronous `call()`, i.e. it blocks the UI
  event loop for the whole wait — a 1-second freeze per `terminal` call, on an
  app whose complaint list starts with "the UI is sluggish". Out of scope for
  the fix, fatal for the migration (see Enhancements).

### No coverage exists

No test suite anywhere mentions `libtmux`, `term_screen` or `term_new` — the
`terminal` and `lsterm` tools are the only user-facing tools in the repo with
zero checks, which is precisely how a `return self.output` survives. The fix
must arrive with `spit_app/tests/unit/terminal/` (pure python, real tmux, no
Textual — same pattern as `tests/unit/sandbox/stub_app.py` driving `Run`):
live capture returns the pane's text and the cursor marker; a dead pane returns
the last screen plus `INFO: Session dead.`; `delay` is honoured; `C-c`
interrupts; missing bwrap is reported and not a `KeyError`. Lifecycle checks
MUST use `sandbox=False` (TRAPS #6).

### Done / Left / Verify

- **Branch**: `task-terminal-empty-output`. Commits, in order:
  - `e699bb4` terminal: return the captured screen, and keep it per chat
    (+ `tests/unit/terminal/`: `stub_app.py`, `run_tests.sh`, `test_screen.py`,
    and `tests/create_venv.sh`)
  - `1984851` terminal: send a key chord as a key, not as literal text
    (+ `test_keys.py`, 30 checks)
  - `c948b3e` lsterm: list the sessions without dying on one that died
    (+ `test_lsterm.py`, 21 checks) — a **fifth defect**, found by probing
    rather than by reading: the listing raised `RuntimeError` on any dead
    session. DECISIONS 67.
  - `b5621fe` terminal: honour delay, and report a session that could not start
    (+ `test_tool_call.py`, 14 checks)
- **Scope**: `spit_app/tools/run/terminal.py`, `spit_app/tools/terminal.py`,
  `spit_app/tools/lsterm.py`, `spit_app/tests/unit/terminal/` (4 files +
  stub + runner), `spit_app/tests/create_venv.sh`, docs.
- **Done** — all four reported symptoms fixed and **measured**, each against
  the pre-fix code as well as after it:
  - Empty response: `term_screen()` returns the local it built, and the last
    screen is cached in `app.tmux[chat_id]["last_screen"][name]` — *not* on the
    instance, because a `Terminal` is built per call, so `self.output` could
    never be "the last screen" across calls. DECISIONS 66.
  - Chords: assigning the result of the strip (`key_body = key_body.replace(...)`)
    makes `C-c` a signal. Proved by effects, since a control char is invisible:
    `pane_current_command` leaves `sleep`, bash's Ctrl-A puts an X at the front
    of a line, `C-d` ends the shell — **plus a control** (t5) showing the same
    bytes as text do *not* interrupt, so the suite cannot pass on a pane where
    nothing kills anything.
  - `delay`: the `dealy` typo and the truthiness test on `delay=0` both fixed.
  - Missing bwrap: `term_new()`'s error is returned; the unreachable-by-accident
    `windows = ...` line that raised the `KeyError` is gone.
  - Dead pane: reports the cached screen verbatim + `INFO: Session dead.`, with
    an explicit "closed before anything was captured" instead of a blank prefix.
  - Coverage gap closed: `unit:terminal` 98 checks, real tmux on a **private
    socket** (`libtmux.Server` wrapped to pass `socket_name`) — a test suite has
    no business creating windows in the user's server.
- **Left**:
  1. **`remain-on-exit`** — measured and ready, **awaiting the owner's Go** as
     its own commit. Today a dead window's content is gone with it (verified:
     server exits, `no server running`), so the cached screen is all a dead
     session can say. With `remain-on-exit on` the pane survives: content
     capturable, `#{pane_dead}` and `#{pane_dead_status}` give the exit code,
     and history reaches past the visible 24 lines. The cost is that
     `pane_active()`'s membership test would call a dead pane **live**, so
     liveness moves to `pane_dead` — which the fix now does in one function
     (DECISIONS 67), and `lsterm`'s "names are reusable after death" rule has to
     move with it.
  2. `time.sleep(delay)` still blocks the UI event loop (entry above: out of
     scope for the fix, fatal for the ratatui migration → enhancement 10).
  3. Owner-side manual check in the running app: a `terminal` call shows its
     screen in chat, `C-c` interrupts a `sleep 60`, and a dead session shows its
     last screen. Automated analogues exist for all three.
- **State hazards**: none. Tree clean at every commit; no fixtures used; no
  suite red. The venv at `~/.venv-spit` is machine state, not repo state — see
  TESTING.md if `unit:terminal` reports FAIL 1 on a fresh machine.
- **Verify**: `cd ~/spit.py && bash spit_app/tests/run_tests.sh` —
  127/24/30/119/80/32/68/29 + 131/33/278/121/119 **unchanged** and
  `unit:terminal: PASS: 98 FAIL: 0`.

### Enhancements this tool needs *for* the ratatui migration

Once `spit-tui` exists (the Rust front end planned in
`doc/UI-ROUTE-RATATUI.md`, on branch `task-ui-route-ratatui-json` — that
file is not on this branch yet), this
tool stops being a convenience and becomes **the only harness that can see the
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
