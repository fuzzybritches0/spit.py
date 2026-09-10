# TASKS-IN-PROGRESS.md

Nothing in this file is finished. An entry leaves it only by the protocol at the
bottom: the work verified, the FULL suite re-run, and the entry moved to
`TASKS-FINISHED.md` with its resolution.

> **Three entries are open**: two `terminal` followups — all on this branch's
> tail — and the streaming-render checklist. The empty-response
> defect that used to head this file is **fixed and committed on this branch**
> (`e699bb4`…`8f65e32`, six commits, 98 new checks) — the full record is in
> `TASKS-FINISHED.md`, "the `terminal` tool's empty response and its four
> siblings". What is left of it is here as followups 3 and 4 — the numbering is
> kept so that anything pointing at a followup by number stays true:
> one PROMPT question for the owner, and the capture/geometry list the ratatui
> harness will need. **Followup 1 — `remain-on-exit` — is DONE** (`d549b61`…`e5b4fba`,
> `unit:terminal` 119 → 173, DECISIONS 69): a dead session now reports its real final
> screen and its exit status, and the sessions run on a tmux socket of spit.py's own
> instead of the user's. Its entry is in `TASKS-FINISHED.md`, together with the one
> piece of follow-up work its measurement uncovered — the state layer (registry keyed
> by `window_id`, ONE `list-panes -a` per call instead of 6 `tmux` invocations,
> `window_name=name` written into tmux, "no such session" distinct from "session
> dead") — which is **now done too**, as P0b-followup 1.5 on this branch
> (`unit:terminal` 173 → 220, DECISIONS 70, its entry directly below followup 1 in
> `TASKS-FINISHED.md`). **Followup 2 — the `time.sleep()` in the tool's
> `call()`, said to block the UI event loop — closed as a false premise** and moved
> to `TASKS-FINISHED.md` (`d6ddc88` checks, `7a3fefc` docs, DECISIONS 68):
> `tool_call.ToolCall.call()` dispatches a sync `call()` through
> `asyncio.to_thread`, so that sleep never ran on the loop at all. The
> streaming-render entry is code-complete and merged; only the owner's manual
> checklist in the running app is outstanding — **nobody else should sign it off**.
>
> **Re-checked 2026-09-10 against `main` (`9c254e8`), the source and a full run
> of `bash spit_app/tests/run_tests.sh`** (14 rows, FAIL 0: tools
> 127/24/30/119/80/32/68/29, unit 131/33/278/121/119/220 — exactly the
> ground truth in `TESTING.md`): **all three entries below are still open and
> none of them may be closed from here.** Not finished, with the evidence:
> **P0** — the code is merged and `unit:render` is 278 green, but its `Left`
> item is the owner's manual check in the running app, which no commit, no
> `DECISIONS` entry and no line of `TASKS-FINISHED.md` records as done; **the
> entry moves only on that sign-off**. **Followup 3** — `terminal`'s PROMPT
> (`spit_app/tools/terminal.py`) still carries no `Esc` sentence, so the
> question is still unanswered. **Followup 4** — the tool still takes only
> `name`/`input`/`delay`: no `command`/`env`/`cwd`, no `cols`/`rows`/`resize`,
> no `styled`/`bytes` capture, no cursor fields, no `wait_for`, no
> `send_bytes`, no diff capture, no `format="json"`; items 1-7 and 11 are
> untouched in the code and 8, 9, 10, 12 are partial as marked in the list.

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

**Status 2026-09-10: unanswered.** `spit_app/tools/terminal.py` PROMPT still
lists `Escape/Esc` among the supported keys and says nothing about the merge,
and `unit:prompt` (33) is green with that text — i.e. nothing has been decided
either way. An agent must not answer this by editing the PROMPT: it is the
owner's call, and the answer changes a model-facing string.

---

## P0b-followup 4 - what the `terminal` tool still needs *for* the ratatui migration  [enhancement list, picked up piece by piece]

The list below was written during P0b and is **verbatim from it**; four items
have moved since — 8, 9, 10 and 12 — and each is marked **where it is marked
done, never where it is still open**. Nothing else has been done, re-checked
against the source 2026-09-10: `spit_app/tools/terminal.py` still accepts
exactly `name`, `input` and `delay`, so items 1-7 and 11 have no code behind
them at all.

**Already done while fixing P0b** (so do not re-do them): the *single
implementation* half of item 9 — `pane_active()` now exists once in
`run/terminal.py` and `lsterm` uses it (`c948b3e`); the *namespaced windows* half
of item 9 has its foundation now (followup 1.5: tmux itself names the windows,
the registry resolves by its own names, and an unresolved name answers "no such
session") — whether the tool should fail *loudly* beyond that answer is still an
open choice. Item 8 (process state as first-class output) is mostly done: a dead
pane reports its REAL final screen and its exit code (followup 1), every field
the snapshot needs already includes `pane_pid`/`pane_current_command`/geometry,
and the state layer those come from — DECISIONS 69's recommendation and the
one `list-panes -a` per call — **landed as followup 1.5**; `pane_dead_signal`
and `pane_dead_time` (tmux >= 3.3) are two more tokens away in that format
line. What is left of item 8 is surfacing them as fields on a LIVE
screen — a formatting job now, not a plumbing one.

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
    `kill_process_group` and the abort path — TRAPS #4). **Half settled**:
    DECISIONS 68 measured the shipped path and the loop is not blocked (a sync
    `call()` goes through `asyncio.to_thread`), so do not "fix" that half
    again; what is left is the abortable in-flight call, which lands with
    item 5 (`wait_for` replaces the blind `delay`).
11. **Structured output option** (`format="json"`: rows, cursor, attrs, bytes,
    process state) so tests assert on data instead of parsing prose.
12. **Sandbox stays on by default** (and lifecycle tests use `sandbox=False`,
    TRAPS #6), and teardown is guaranteed: a `kill` that takes the process group
    and auto-cleanup when the chat closes. During this evaluation the only way
    to clean up orphaned sessions was `tmux kill-server`, which is not
    acceptable in a shared tmux. **Partly landed since**: the sessions now run
    on a tmux socket of spit.py's own, `spit-<pid>`, so `kill-server` can never
    reach the user's server (`3f6b279`, DECISIONS 69 a), a reported corpse is
    destroyed at the moment it is reported (`retire()`, `e5b4fba`), and the app
    kills its own server at exit. What is left is teardown when a single **chat**
    closes — `actions.py:action_exit_app` is still the only thing that frees
    anything, so a closed chat's windows outlive the chat.


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

- **Branch**: `task-streaming-render-bugs` (tip `c5a5443`), **merged into
  `main`** - the five commits below are in `main` now, so reading the fixed
  files off `main` shows the fix. Commits on it, in order:
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
  - `8cadc85` render: cover the `----` argument shape the checklist names
    (new `t6-dash-*` checks; no numbers reused)
  - `c5a5443` docs: TESTING ground-truth row unit:render 278 +
    sandbox re-measurement 119, DECISIONS 59 (fence language, pairing
    rule, accepted limits), this entry brought current. *(This was the
    "(pending commit)" of the last edit of this list; it is committed and
    merged.)*
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
  re-measured 2026-09-10 on `main`: tools 127/24/30/119/80/32/68/29 and
  unit 131/33/278/121/119/220, all FAIL 0 (the ground-truth table is
  TESTING.md; the `unit:render` 278 row is this task's, and no other count
  may move). The suite is the whole automated close-out; what Verify cannot
  reach is the manual checklist (owner-side) in Left - and until the owner
  signs that off, this entry is NOT finished, however green the suite is.

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
