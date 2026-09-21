# TASKS-FINISHED.md

Completed work with references, so finished state can be trusted without
re-deriving it. Commit refs are in `~/spit.py` (`git log --oneline`).
Test-count ground truth: see TESTING.md.

## Milestones

- **13 file-tools implemented and tested** (find_files, write_file,
  list_directory, read_files, file_info, search_replace, terminal, lsterm,
  diff, patch, grep, insert_line, delete_lines) - full specs in TOOLS.md.
- **run_command hardening series** (branches `fix-run-command-*`): stdin kept
  (script delivered as file), env + cwd carry-over, trailer fixes, background
  lifecycle (call ends with command; `--die-with-parent`), stderr separation
  with concurrent pipe reads. Merged via `fix-run-command-stderr`.
- **Argument handling**: schema-coercion repair (`7c77787`), UI editor keeps
  argument types (`a200933`), `~`/`$VAR` expansion for PATH_ARGS (`a26477a`).
- **run_command PROMPT rewrite** (`fb15e08`) - HANDOFF task 1: the model is now
  told the real lifecycle/stderr/env semantics; assertion tests added
  (`spit_app/tests/unit/sandbox/test_prompt.py`).
- **Shared test stub adopted everywhere** (`6dcdca9`) - HANDOFF task 2:
  `test_delivery.py` now imports `run_as_file` from `stub_app.py` (3-tuple);
  sandbox suite total held at 103.
- **Test failure counting fixed** (`39ceb2f`).
- **`rename` tool** (branch `rename-tool`, commit `7c1d062`) - planned P2:
  rename/move for files, directories (whole tree) and symlinks; NEVER
  overwrites (target checked with `lexists()`, dangling symlinks count);
  `dry_run` is an identical validation that reports the planned rename
  (not a diff - a rename changes no bytes) - full rationale DECISIONS 60,
  spec TOOLS.md #14; `tests/tools/rename/` 68 checks (18 numbered
  sections, error paths dominate by design).
- **Prompt assembly and the run_script wrapper** (branch
  `fix-prompt-join-and-run-script`: `94b68a9` code, `451a50a` code, `e5e80ed`
  + `850c2d1` + `4907f0f` docs; awaiting the owner's merge, never pushed).
  The model now gets **one block per tool**: `work.py` owns every line break of
  the assembled prompt (DECISIONS 62) - before, 1 of 19 `## <tool>` headings
  started a line, so the tool boundaries it reads were invisible. And
  `run_script` gives the bash wrapper to **bash only**, with `separate_stderr`
  actually reaching `Run` (DECISIONS 63) - before, python3 and perl produced
  nothing but a SyntaxError quoting the trailer, because the wrapper is bash and
  they parse the whole file before running any of it. New suites
  `tests/unit/prompt/` (33 checks) and `tests/unit/run_script/` (83); the
  differentials are recorded in the two commits (10/33 and 25/83 fail against
  the pre-fix code).
- **run_script enforces its `interpreters` setting** (branch
  `fix-run-script-interpreter-allow-list`, `5494c9a` code + `52ca61c` docs) -
  planned P5: the list that only ever filled the `[interpreters]` token is a
  permission now, checked before the `python`->`python3` fallback and before
  `PATH`, with a refusal that names the setting and quotes the list back. The
  same placement closes the `TypeError` a non-string interpreter used to raise
  inside `which()`. DECISIONS 64; 38 new checks (unit:run_script 83 -> 121),
  differential against the previous module: 11 explicit failures - a plain `sh`
  running, twice over - plus section 11's 16 checks never running there at all.
  Awaiting the owner's merge; main untouched, nothing pushed.
- **The `terminal` tool's empty response and its four siblings** (branch
  `task-terminal-empty-output`, six commits; P0b). Five defects, one per commit,
- **The file tools' stdlib shadowing: the interpreter is isolated now** (branch
  `fix-tool-interpreter-path-shadowing`, `4cd6152` code + the docs commit) —
  the reported symptom was a file tool answering with a traceback instead of a
  result and leaving the file unwritten, naming a venv file: `write_file` dying
  in its own `import pathlib` at `site-packages/textual/types.py`. The mechanism
  was neither the tool nor the file: these tools hand their program to python3 on
  **stdin**, which puts the working directory first on `sys.path`, and the working
  directory is state (`cd` carries over from `run_command`), so a call that ended
  inside a python package directory made the *next* file tool import that directory
  instead of the standard library. Which tool died was decided by its own import
  graph, not by the target file — in the same poisoned directory `read_files`
  (imports nothing) answered and `search_replace` (`re → enum → types`) did not.
  `TOOL_PYTHON = ["python3", "-E", "-s", "-P"]` (DECISIONS 78, TRAPS #25) closes
  both doors — `-P` for the start-up directory, `-E` for the `PYTHONPATH` half,
  which was reproduced independently — and deliberately leaves the working
  directory alone, so a relative `path` argument still resolves in the directory
  the last `cd` left. The rejected alternative (load the state only for
  `run_command`/`run_script`/`terminal`) is recorded with its measurements in
  DECISIONS 78: it silences the same crash, re-anchors relative paths to the sandbox
  home — a silent wrong-directory write, worse than the traceback — and leaves
  `sys.path[0]` writable besides. `tests/unit/sandbox/test_python_path.py`, 38
  checks, 29 of them red against the pre-fix interpreter; unit:sandbox 119 → 157,
  every other row byte-for-byte (tools 509, anchored 68, arguments 131, chat_smoke
  168, chat_window 568, prompt 33, render 278, run_script 121, terminal 223), FAIL 0
  throughout. **Left open on purpose, same class**: **P10** (a file-delivered python
  script — `run_script` — gets the shared `sandbox_tmp` as `sys.path[0]`) and **P11**
  (a sandboxed `terminal` pane inherits no carried state while an unsandboxed one
  does). Awaiting the owner's merge; `main` untouched, nothing pushed.
  each carrying its own checks and each **measured against the pre-fix code as
  well as after it**:
  - `e699bb4` — `term_screen()` built the screen into a local and returned
    `self.output`, assigned exactly once, to `""` in `__init__`: every capture of
    a *live* pane returned an empty message container, and a dead one returned
    `"\n\nINFO: Session dead."` with an empty prefix, which is why a dead session
    read as a truncated one. The cache is **per session name in
    `app.tmux[chat_id]["last_screen"]`, not on the object** — `tools/terminal.py`
    builds a new `Terminal` inside `call()`, so an instance attribute is born
    empty every call and could never be "the last screen" across calls, which is
    the only case the dead-pane branch exists to report. DECISIONS 66.
  - `1984851` — every key **chord** was typed as literal text: `_inp.replace(key,
    "")` discards its result (`str` is immutable), so the strip that decides
    key-vs-text did nothing, `len(_inp) <= 1` was false for every chord, and
    `C-c` — advertised by the tool's own PROMPT — arrived as the four characters
    `C - c`; so did `C-a`, `S-Tab`, `M-x`, `C-d`. Bare key names still worked,
    which is why it survived.
  - `c948b3e` — a **fifth defect, found by probing rather than reading**: `lsterm`
    walked `windows.keys()` while its private liveness check deleted the dead
    window it found from that same dict, so the first session to die in a chat
    made the listing raise `RuntimeError: dictionary changed size during
    iteration` — no answer at all, from the tool the PROMPT says to call when you
    are unsure a session is alive. Liveness now exists once, in `run/terminal.py`,
    used by both tools, with the listing snapshotting names first. DECISIONS 67.
  - `b5621fe` — `delay` was read and dropped twice over (`dealy = arguments[...]`
    misspelled the target, and `if arguments["delay"]` read `delay=0` as "no
    delay given"), and `term_new()`'s return was discarded, so a machine without
    bubblewrap got `KeyError: 'chat1'` where it should have got "install
    bubblewrap".
  - `a7eb47a` docs, `8f65e32` a comment with a measurement behind it: the
    discarded `term_screen()` call in `term_send_keys()` looks exactly like the
    bug just removed and is not — deleting it fails two checks, and it is the
    only reason a session killed by its own input still has a screen to report.
  **New coverage**: `tests/unit/terminal/`, 98 checks, real tmux on a **private
  socket** (`libtmux.Server` wrapped to pass `socket_name` — a suite has no
  business creating windows in, or sending input to, the user's server); needs
  libtmux, so `spit_app/tests/create_venv.sh` is documented as the way to get it,
  and a missing dependency FAILs loudly instead of reporting `PASS: 0  FAIL: 0`.
  Ground truth moved only by that new row: `unit:terminal` 98, everything else
  unchanged. Two traps the differential caught in the tests themselves are
  recorded in DECISIONS 67 and TESTING.md — `capture_pane()` returns **lines**
  (`token in lines` is whole-line equality and never matches a token sharing its
  line with a prompt), and a liveness check that *forgets* what it finds dead
  cannot be used to wait for death, because the wait performs the fix and the
  test passes against the broken code.
  **Left, deliberately**: `remain-on-exit` (owner's Go required — see
  TASKS-IN-PROGRESS followup 1), the `time.sleep()` in `call()` (followup 2 —
  **since closed as a false premise**, see the entry below and DECISIONS 68: a
  sync `call()` is dispatched off the event loop, so it never froze the UI), the
  the capture/geometry list (followup 4), and the owner's
  manual check in the running app: a `terminal` call shows its screen in chat,
  `C-c` interrupts a `sleep 60`, and a dead session shows its last screen. Every
  one of those three has an automated analogue. Main untouched, nothing pushed.
- **P0b-followup 2 closed as a false premise: the `terminal` tool's `delay` never
  blocked the event loop** (branch `task-terminal-empty-output`, `d6ddc88` checks +
  `7a3fefc` docs; DECISIONS 68). The entry claimed `tools/terminal.py:call()` sleeps
  `delay` (default 1 s) before capturing and so froze the Textual UI for a second on
  every call, and prescribed `call_async_generator` with `await asyncio.sleep(delay)`.
  What decides is not in the tool: `tool_call.ToolCall.call()` (`d455761`) routes a
  plain function call through `await asyncio.to_thread(...)`, and that is what
  `chat/work.py:118` awaits. Measured over that path — the real `ToolCall` loading the
  real tools directory, a real tmux on a private socket, a 20 ms heartbeat counting
  ticks and the worst gap between them: `delay=1` → 1.05 s wall clock, **53 loop
  ticks, worst gap 22 ms**; `delay=2` → 101 ticks, worst gap 22 ms. The same
  dispatcher with `to_thread` replaced by a direct call — the configuration the
  prescribed fix creates — gives **1 tick and gaps of 1065 ms and 2053 ms**: the
  reported freeze, on the other side of the hop. The rewrite was therefore **not**
  applied, and would have been a pessimization twice over: libtmux spawns the `tmux`
  binary on every round-trip, and one `term_screen()` measured 46 ms, stalling the
  loop by 65 ms when it runs on the loop against 22 ms with the same work off it.
  **New coverage**: `tests/unit/terminal/test_event_loop.py`, 21 checks — section 1
  the shipped path, section 2 the control (an `asyncio` whose `to_thread` runs on the
  caller, so the control is the same dispatcher and the same tool call, not a copy of
  it), section 3 the cost of the tmux round-trips as two medians of three taken in one
  process (an assertion about the hop, not about the machine), section 4 which branch
  of the dispatcher the loaded tools actually land on. `stub_app.py` gained
  `chat.cs("tools")` and `chat.chat_view`, the two inert things the dispatcher asks a
  chat for on its way to a tool. Differential with the hop removed process-wide: 3 of
  the 21 go red (`t1-the-loop-kept-ticking-through-the-delay`,
  `t1-the-loop-never-stalled-for-the-delay`,
  `t3-the-hop-keeps-the-tmux-work-off-the-loop-too`) while the control stays green in
  both configurations — DECISIONS 67's rule, a probe is shown catching the stall
  before it is trusted to report its absence. Ground truth: `unit:terminal` 98 → 119,
  every other row where it was, FAIL 0 everywhere.
  **What survives of the complaint is not blocking**: an in-flight call cannot be
  aborted, because a running thread cannot be interrupted and `delay` is a blind wait
  (enhancement 5, `wait_for`, with enhancement 10 — done together the wait stops being
  a sleep *and* stops holding a thread, and nothing moves onto the loop); and one pool
  thread is held per call for the duration of `delay` (`min(32, cpu+4)` default
  executor) — occupancy, not a frozen UI. Owner confirmed the reading before the docs
  landed. No tool code changed; main untouched, nothing pushed.
- **P8: the chat's widget tree is now a WINDOW over the message data** (the chain
  `task-anchored-scroll-widget` → `task-index-accessor-refactor` →
  `task-sliding-window-core` → `task-scroll-load-prune-triggers` →
  `task-edit-undo-removal-across-window-edges` → `task-window-measurement-numbers-close-p8`,
  all six awaiting the owner's merge; `main` untouched throughout). `ChatView`
  extends the one-shot-anchored `AnchoredScroll`, mounts `messages[lo, hi)` with
  **both ends free**, pages in at a window edge on the scroll trigger and releases
  back to the margin behind it, so **the mounted widget count is a function of the
  viewport and not of the history**: measured 7–15 mounted at every scroll depth of
  a 1,000- and of a 5,000-message chat, against 5,000 messages / 30,000 widgets for
  the whole-history tree, i.e. at 5k **121–127× faster to open, 81–82× faster to
  page down, 11.5× less memory**. The data layer never moved:
  `Chat.messages is ChatView.messages` is an asserted identity and the JSON is
  untouched by a walk. `doc/UI-ONDEMAND-LOADING.md` is the plan with each package's
  deviations from the sketch; `unit:chat_window` is the 568 checks that keep it
  honest and `unit:anchored` the 68 under it; **DECISIONS 76** is the numbers and
  the instrument lessons, and it says out loud what the window does *not* buy (the
  scrollbar now describes the window, `materialize` will still buy the whole
  history, and the front-end question DECISIONS 65 settled is untouched by it —
  this is the Textual-side bridge, and the state extraction any future front end
  would want has a shipped precedent in
  `ChatView.widget/window/materialize`). (65's route was itself retired
  2026-09-20, DECISIONS 77; this sentence predates that and is kept as written.)
  Verification rested on the automated
  headless suites: there is no screen here (TRAPS #22).

### P0b-followup 1 — `remain-on-exit`: a dead session reports its real last screen (branch `task-terminal-empty-output`, commits `d549b61`…`e5b4fba`)

**Owner gate.** The entry carried *"Before you start `remain-on-exit`, come back to
me and wait for my `Go!`"*, and a crashed session had left an implementation in the
working tree without recording a Go — so the tree was unauthorised *and* red
(`unit:terminal` 116/3). It was reverted to HEAD, re-measured from scratch, and the
owner gave the `Go!` for it plus two follow-on items found by that measurement. Every
claim below is from this box (tmux 3.7b, libtmux 0.62, private sockets), not from the
previous session's notes.

**What landed, in three commits.**

- `d549b61` — `term_new()` reported a session whose shell dies during creation as a
  traceback out of `call()`. Measured: `new_window()` raises `TmuxObjectDoesNotExist`
  for a shell that cannot exec *and* for one that execs and exits at once, **at HEAD
  too** — a pre-existing defect, not collateral of the option, which the commit says
  out loud. Now `term_new`'s own error string (the contract `check_bwrap()` set).
- `3f6b279` — **the one that could destroy the user's work**: `libtmux.Server()` takes
  no socket, so every session was created in the user's DEFAULT tmux, and
  `actions.py:action_exit_app` calls `server.kill()` — `tmux kill-server`. Quitting
  spit.py took down the user's sessions. Now `server_socket()` = `spit-<pid>`: one
  server per process, one session per chat. The suite switched from `setdefault` to
  FORCING its socket (with production passing a name, `setdefault` lets production
  win and the suite drives the socket it exists to stay off) and records the request,
  so t10 can pin the production choice without driving it — decision 67's rule applied
  to the harness itself.
- `e5b4fba` — `remain-on-exit` on the window, liveness on `pane_dead`, the real
  dead-session report, and the corpse policy. DECISIONS 69 is the full record.

**Three measurements that changed the design.** (1) The entry's "how to start" does
not work: session-scope `setw` reports `on` and the next window is still destroyed;
libtmux 0.62 has no `Session.set_window_option`. Window scope after creation holds.
(2) tmux writes `Pane is dead (status N, …)` INTO the pane, which scrolls the grid up
one line — a visible-only capture of a corpse loses the first line of everything it
printed, and for a one-line session loses everything, so the report captures 50 lines
of scrollback (which also caps it). (3) Freshness comes from the re-list, not from
`session.refresh()`: membership was correct with no refresh at all, while a cached
`Pane` read `pane_dead='0'` after the shell exited and kept its `pane_id` across a
`respawn-window` that changed the pid. The comment that credited `refresh()` had
mis-attributed the cause and is gone.

**Decisions taken here.** Corpse disposition: **kill-on-report** — a retained window
is destroyed by nothing else, and forgetting a name makes the corpse unreachable
rather than gone (measured: 3 chats + 1 death = 5 windows; reusing the name = 6, one
an abandoned `sandbox_env.sh[dead]`), and since the PROMPT sends the model to `lsterm`
first, `pane_active()` harvests the real screen into the cache *before* forgetting and
destroying. The hazard is measured too: killing the last window takes the session, and
on our socket the server, so `retire()` checks and rebuilds the chat entry keeping the
cache. And the cache now holds **what was reported** (dead screens without the cursor
marker), so a repeat call repeats the exit status instead of appending a second notice.

**Tests.** `unit:terminal` 119 → 173 by addition only: `t9` guard (6 red without it),
`t10` socket (3 red), `test_screen` `t10`-`t13`, `test_lsterm` `t5`, `test_tool_call`
`t11`; 22 of them red against the pre-change backend, 0 with it. The three
`test_lsterm` death-waits moved from `window_exists` to a new non-mutating
`window_dead`, because with `remain-on-exit` "the window is still there" is True
forever — the same question, changed meaning, which is why the assertions were
re-worded rather than the numbers touched. New gotcha found while testing: a
`kill -SEGV $$` in a pane drops a core file in the tmux server's CWD, which is where
the suite runs — the check sets `ulimit -c 0` first.

**Docs synced in `e5b4fba`.** The PROMPT sentence *"when a session dies while not
interacting with it, no output can be recovered"* is false and now says what happens
instead; `TOOLS.md` §7 and §8; `RUNTIME-RUN-COMMAND.md`'s socket, dead-session,
liveness and probe paragraphs; `TESTING.md`'s row, its note and the non-mutating-probe
note; DECISIONS 69. `unit:prompt` 33 still green with the new PROMPT text.

**Manual check the entry asked for** — a session that dies on its own reports its
final screen *and* an exit status: verified by hand and by `t10`/`t11`. Sample report
from the probe: `Session: d1` / `…first line…` / `…last line…` / `Pane is dead
(status 4, Wed Sep 9 …)` / `INFO: Session dead. Exit status: 4.`

**Left for the next agent** — the state layer (registry keyed by `window_id`, one
`list-panes -a` per call instead of 6 `tmux` invocations for 45 ms, `window_name=name`
written into tmux, "no such session" distinct from "session dead"). Measured and
written up in DECISIONS 69(c); enhancement 9 of the followup-4 list. **[DONE — it
landed on this same branch as P0b-followup 1.5, the entry follows below; DECISIONS 70
is its record. Ground truth moved with it: `unit:terminal` 173 → 220.]**

### P0b-followup 1.5 — the `terminal` state layer: ids not objects, one listing per call (branch `task-terminal-empty-output`)

**What landed.** `app.tmux[chat_id]` became `{server, session, stamp, windows:
{name → window_id}, last_screen}` — the registry holds the `window_id` strings tmux
gave, never libtmux objects (69(c) measured a cached object reading `pane_dead '0'`
after its shell was gone). Every question is answered from ONE narrow
`tmux list-panes -a` per call, keyed by `window_id`; objects are built from ids
on demand for capture/send/kill and never read from. `stamp` — the answering
server's own pid and start time, from that same listing — plus the row's
`session_id` is what makes an id count as ours: a restarted tmux numbers from
`$0`/`@0` again, so a stale id can name ANOTHER CHAT's live window; such a name
answers dead from its cache, is never read, typed into, or killed.
`window_name=name` makes tmux say what the registry says. The unnamed window tmux
creates with every session is destroyed once a real window exists, so reporting
the chat's last dead terminal now ends the session and (on our one-session
socket) the server — the ordinary path, with the entry rebuilt keeping its
`Server` object and cache. "No such session" became a distinct answer from
"session dead": a death that never happened used to be reported as one.

**Measurements.** A capture is EXACTLY two `tmux` invocations (`list-panes` +
`capture-pane`), ~16-17 ms, where the object layer paid 6 + 2 `display_message`
(53.4 ms median measured here for the same work); `lsterm` is ONE listing for
any number of windows; `term_input` 5 (was ~10). Cursor parity proven in five
states, and the scripted full scenario (prompt, echo, cursor mid-line, wrapped
200-char line, column 0, screenful, second window, dead report and repeat)
produced byte-identical `repr()` output old vs new — the only permitted
difference the unknown-name answer. The burst that replaced t3's ratio: 5
captures on the loop, 99 ms worst heartbeat gap; the same 5 through the hop,
22 ms. DECISIONS 70 carries both deviations loudly: the t6 re-word (the handoff
authorised only its twin t7; they are the same call) and the t3 burst
re-calibration.

**Tests.** `unit:terminal` 173 → 220 by addition only (`test_screen`
`t14`-`t17`, `t6` +1, `test_tool_call` `t7` +7, `test_event_loop` `t3` +2; two
assertions re-worded in place, numbers append-only). Differential against the
old file: 18 `test_screen` + 2 `test_tool_call` red before, 0 after;
`test_lsterm`/`test_keys`/`test_event_loop` green on both. Full-suite ground
truth: tools 509 and unit 131/33/278/121/119 unmoved, `unit:terminal` 220,
FAIL 0.

### P0 — the garbled streaming render: tool-call arguments and streamed tool output (branch `task-streaming-render-bugs`, commits `69bd1ba`…`c5a5443`, merged)

**Closed 2026-09-10 by the agent that status-checked the task files, on the automated evidence.** The entry carried "the owner's manual checklist in the running app" as its close-out, and that gate was never the owner's to set — DECISIONS 71 is the clarification, TRAPS #22 the trap of inventing it. So state what was and was not done: **the running-app look was never performed** (this sandbox cannot see the app's screen and has no endpoint to drive a streamed reply). What closes the task is what actually verified it — every item of that checklist has an automated analogue in `tests/unit/render/`, and the by-hand list is kept at the end of this entry in case a human ever wants it.

**What was broken** — three symptoms, all inside the display pipeline; the LLM always received intact text and raw JSON arguments. **(a)** characters dropped at explicit output points, most often the `\n` before a `~~~~` separator, which broke the Markdown layout of the streamed arguments. **(b)** a stray `}` at the end of the arguments render — worst for `{}` — and an odd separator count, so rendering correctness silently depended on the parity of the argument count. **(c)** streamed tool output arriving scrambled, head and tail truncated and the fence out of place (`Running proc[...some output...]...Process ended with~~~~~`).

**Three root causes.** (1) `chat/message/content/process/tool_call.py`: the whole-string `unescaped()` post-pass ate fence characters and escaped newlines and mis-detected quote escapes, and the `}` close branch was guarded on `not self.key`, so a closing brace fell through to the plain-content branch and leaked while the last value never received its closing fence. Rewritten as a **per-char JSON scanner** (`69bd1ba`) that emits an even number of separators (N arguments → 2N, `{}` → 0): streaming == whole-string == monotonic per shape, even fence parity asserted per shape. (2) `process/process.py`: `self.pos` indexed the *hint-prefixed* string while `tool_start()` prepended the `~~~~~text\n` prefix only while `pos == 0`, so from the second callback on every chunk was processed starting 12 characters deep and text was lost at every boundary; the hint fences are now computed once and prepended/appended unconditionally (`ba87435`), and the leaked `self.pos = pos + 1` and finish's off-by-one `self.pos = pos` became `end` and `len(content)`. (3) `pattern_methods.code_block_start_end` closed a fence only on **exact equality** and *pushed* every foreign fence run onto `code_fences` permanently, so run.py's `~~~~ stderr ~~~~` inside the `~~~~~hint` block poisoned the stack for the rest of the message; pairing now follows the CommonMark rule — the innermost open fence of the **same character and at least its length** (DECISIONS 59, which also carries why five tildes deliberately out-length the `~~~~` runs of tool output and arguments).

**Coverage — new `spit_app/tests/unit/render/`, 278 checks.** `test_tool_call_format.py` 230: the formatter fed one character at a time *and* in every two-split boundary, golden per shape (`{}`, 1 arg, N args, values containing `~~~~`, `----`, newlines, backslashes, unicode), differential old-vs-new over 35 shapes recorded in `69bd1ba`. `test_render_pipeline.py` 48: exact screen (widget tree + final sources) for plain text, balanced fence blocks, mixed fence lengths, the full `run_command` shape with the STDERR_HEADER inside the hint block, the tool-call render through `Process`, chunk-split invariance at every boundary, and the finish-only re-render path — driven by `stub_textual.py`, which fakes only the widget backbone so the pipeline itself runs for real (TRAPS #19). 16 of these failed before the fixes, with exactly the reported symptoms (`8cadc85` added the `----` shape afterwards; no number reused). The `text_area_tool.py` save path — the whole-string caller that any formatter fix had to keep working — is covered, and the missing-`arguments` `KeyError` crash is fixed.

**Cleared by measurement and deliberately NOT changed** (recorded so nobody re-pays them): the `self.pp.part = ""` reset, the `tool_start()`-twice theory, `skip_add_part`, and the focus-skip catch-up — the finish-only re-render tests (pipeline t8) show the final screen is identical to the fully streamed one.

**Accepted limits (DECISIONS 59).** An argument value with a ≥5-tilde run at column 0 can close its own block early — no fixed-length fence can prevent that; a tool-call stream truncated mid-JSON leaves the last value's fence open.

**The by-hand version, kept in case anyone wants it.** Empty-args call (`lsterm`), `run_command` with stderr (`separate_stderr` default True), a `write_file` whose content contains `~~~~` and one containing `----`, streaming `python`, focus switching mid-stream, re-opening an old chat (the re-render path).

**Verify / measured.** `cd ~/spit.py && bash spit_app/tests/run_tests.sh` on `main`: tools 127/24/30/119/80/32/68/29 and unit 131/33/278/121/119/220, **FAIL 0** everywhere (re-measured 2026-09-10). `unit:render` 278 is this task's row and nothing else moved — a render fix that left every tool-suite count exactly where it was, which is what the entry's Verify asked for. Branch merged into `main`; `main` was never written to directly and nothing was pushed.
**The pipeline map, kept for whoever works here again** (it cost a reading session and it is not written down anywhere else). `endpoints/llamacpp.py:tool_calls()` accumulates streamed argument fragments into `messages[-1]["tool_calls"][i]["function"]["arguments"]` and fires `maybe_callback(2)` → `chat/callback.py` signal 2 → `Message.process()` → `Content.process` → `chat/message/content/process/process.py:Process.process` → `get_content()` → `process/tool_call.py:ToolCall.tool_call_arguments()`: **the formatter re-runs over the whole cumulative string on every callback**, and `Process` re-processes pattern state from its own `self.pos` — which is why a prefix that appears or vanishes between callbacks moves every later boundary. Tool output travels the same path: `tools/run/run.py:Run.run()` yields `"\nExit code N..."` after the data — deliberately part of the message the LLM reads, so they are never removed to fix a screen symptom — and `spit_app/tool_call.py` appends each chunk and fires callback(2) when `STREAM_TOOL_RESPONSE`. On top of that, screen-only: `Process.tool_start()`/`tool_end()` wrap the block in the `~~~~~` fences, and everything passes through `pattern_processing.py` + `pattern_methods.py` (the `~` fence state machine, `bsize = 8` look-behind, `skip_add_part`, `skip_pp`) into Textual `Markdown` streams (`containers/part.py`). Four constraints fall out of the shape and outlive the fix: any formatter change is a change to streaming *and* whole-string output at once, so assert both; the `~~~~` separator is a **shared language** between `tool_call.py` and the fence machine (`patterns` `("~", ..., code_fence)` plus `code_block_start_end` pairing), so emitted fences are never edited in one file alone; `process/text_area_tool.py` (the save path) calls `tool_call_arguments()` once on complete JSON and must keep working; and `callback.py:message_process()` processes only while the message widget has focus, unfocused messages catching up at signal 0 through `finish()` — measured benign for the fence state (pipeline t8, final screen identical to the fully streamed one), but it is where a Textual stream stop/start race would bite first. The original probe (`ToolCall({"name": "noop", "arguments": "{}"}).tool_call_arguments()` returning `'...#### arguments:\n}'` with no closing fence) is now covered by `tests/unit/render/test_tool_call_format.py`; `tool_call.py` imports nothing, so it stays testable with the bare system python3 (TRAPS #19).

### P0b-followup 3 — closed as a **non-issue**: the `Esc` behaviour *is* the terminal, not the tool (owner ruling 2026-09-10; branch left unmerged)

**Nothing was changed and nothing needed changing.** The entry claimed that a lone `Esc` in a pane mangles the next command and asked for a warning sentence in the tool's PROMPT. The owner tested it in their own terminal and ruled: pressing `Esc` swallows the next character there too, tmux does exactly what the terminal does, and in vim `Esc` and `M-Enter` both leave insert mode — so the `terminal` tool, which "does exactly what it should do: it mirrors the terminal behaviour 1:1", is working as designed and the caller gets what a human at that keyboard gets. **DECISIONS 72** is the ruling; **TRAPS #23** is the lesson: before filing pane behaviour, reproduce it in a real terminal, and blame what you measured rather than what sounds right.

**What the investigation did establish, recorded so nobody re-derives it.** A lone `Esc` consumes the next character the pane receives — `echo mm-x` arrives as `cho mm-x` — and it does so after 1.2 s, after 2 s and after 3 s, through libtmux and through the bare `tmux send-keys` CLI alike, in a later send and in a later tool call. The pane answers `bind -v` with `set editing-mode emacs` and `set keyseq-timeout 500`, so the timeout everyone blamed is not the window, and the entry's prescribed remedy — "send `Esc` alone and let the delay elapse" — would not have worked even if the diagnosis had been sound. `Enter` absorbs a pending `Esc`, and so does a sacrificial space; a key chord (`C-a`, `M-x`) leaves nothing pending because a chord is one sequence in one write. None of it needs a fix.

**The branch stays unmerged, deliberately**: `terminal-prompt-esc-limitation` (`f6948ea`, a PROMPT bullet plus 14 checks in `test_tool_call.py`, `unit:terminal` 220 → 234; `4fa008a`, its docs, carrying a decision 72 that this line of history uses for the ruling — revive that branch and its entry becomes 73). No code from it is in `main` or in these docs: `terminal`'s PROMPT is the owner's text unchanged, `term_input()`/`term_send_keys()` are untouched, and `unit:terminal` remains **220**. `test_keys.py` keeps asserting the only claim the tool makes about `Esc` — the key is delivered and its name is not typed.

### The two machine-dependent reds in `unit:terminal`: one missing wait, and two readers of one pane (branch `test-terminal-pane-read-parity`: `b2d0021` the wait, `bd37144` the read, and the docs commit that closes the entry)

**Reported as: 217/3 on the owner's machine, 220/0 on this one** — `t3-typed-the-line`,
`t2-cursor-marker-present`, `t2-screen-is-not-just-the-header`, with the suspicion that
the owner's different venv caused it. **It did not**, and ruling that out is the first
thing worth keeping: `libtmux` is 0.62.0 in both venvs and these suites import no
Textual (TRAPS #19), so `libtmux` and the `tmux` binary are the only things they touch.
The variable is the **shell inside the pane** — `term_new(sandbox=False)` runs
`sandbox_env.sh bash`, which reads the user's `~/.bashrc` — so it was reproduced here by
changing nothing but `HOME`:

| the pane's shell | failing checks | row |
|---|---|---|
| `.bashrc` sleeps 0.4 s, ordinary prompt | `t2` x2 | 218/2 |
| 76-column `PS1`, fast rc | `t3-typed-the-line` | 219/1 |
| both | all three, the owner's names | **217/3** |
| two-line `.bashrc` | none | 220/0 |

**`t2` was a missing synchronisation.** It was the only capture in `test_screen.py`
with no `wait_for_prompt()` before it. Measured mechanism: a pane that has drawn
nothing yet captures as *nothing* — `tmux capture-pane -p` prints its 24 blank rows,
libtmux strips them, `capture_pane()` returns `[]` — so `live_screen()`'s splice loop
has no row to put `█` on and the report stays exactly the 13-character
`Session: <name>\n\n` header. That is why those two fail as a **pair**. The owner added
the one line every other section already had (`b2d0021`).

**`t3` was two readers of one pane.** `live_screen()` captures with
`join_wrapped=True`; `stub_app.screen_of()` — behind ~28 assertions — captured raw.
tmux wraps at the right edge and returns the wrapped rows as separate lines, so a token
straddling the edge is on the pane, inside the tool's report, and invisible to every
test. The failing band is **75-79 prompt columns on an 80-column pane**: 70-74 passes
(the token lands inside one row) and 80+ passes (the prompt itself wraps, so the text
starts fresh on row 1). Side by side on the same pane the raw read lacks `abcdef` and
the joined read has it: **the tool was right throughout**, `run/terminal.py` needed no
change. The neighbour check passing all along — `t3-cursor-was-at-the-front` — was
bash's own `bash: Xabcdef: command not found` carrying the token contiguously, which is
what made this look like one flaky check instead of a reading difference.

**What landed** (`bd37144`): `screen_of()` joins, the two direct `capture_pane()` calls
in `t17` join, and `test_screen` `t18` (3 checks) pins it — a 200-character token, which
wraps at any width this socket can meet (the private socket never has a client, and a
clientless session is tmux's default 80x24, measured), reported whole by the tool, seen
by the harness, **plus a precondition check that the wrap really happened**, because with
no wrap the other two prove nothing (TRAPS #18). The token goes through `echo` rather
than sitting on the command line because the cursor marker *replaces* the character under
it (decision 66) — that token would have tested the splice, not the read.

**Differential** (`main` vs branch, sequential — each file owns one fixed socket name):

```
plain shell                 220/0  ->  223/0    no check changed verdict, 3 added
76-column-prompt shell      219/1  ->  223/0    the red was t3-typed-the-line
the owner's environment     217/3  ->  223/0    all three names gone
new check vs main's stub_app:  92/1  t18-harness-reads-the-pane-as-the-tool-does red
                               alone, its two siblings green on both codes
```

**Accepted, not fixed** — and said plainly because it is the part a future agent could
"helpfully" break: the suite still runs the user's own shell with the user's own rc
files, because handing over a real terminal 1:1 *is* the tool's contract (DECISIONS 72)
and a pinned fake shell would test less. What was wrong was an assertion whose verdict
depended on the width of whoever ran it and on how fast their prompt appeared. The
durable version of that is enhancement 2 (geometry the caller sets) and enhancement 4
(cursor as data, not a character spliced into the text) of the followup-4 list, which
are noted there. Full-suite ground truth: tools 127/24/30/119/80/32/68/29 and unit
131/33/278/121/119 **unmoved**, `unit:terminal` 220 -> 223, FAIL 0 everywhere. Branch
awaiting the owner's merge; `main` untouched, nothing pushed. **DECISIONS 73** is the
record, with the re-measurement recipe (`HOME` at a directory holding a chosen
`.bashrc`) so the class can be re-tested on any machine in one command.


### WP-F (P8 pipeline) — the measurements, the flat count, and P8 closed (branch `task-window-measurement-numbers-close-p8`, awaiting the owner's merge)

Cut from the WP-E tip `074e55d`; the chain is A → B → C → D → E → **F** and `main`
`8819e73` is untouched throughout. **This WP changed no repo code, so no `Go!` was
asked**: the gate the plan hangs on every package is the gate on a *code* change
(DECISIONS 71 (c), TRAPS #22), and WP-F is the measurement pass plus the docs. What
that leaves open is named, not hidden: the measurement probes are in `/tmp` and are
NOT in git — committing them as `spit_app/tests/probes/window/` (the
`alternative-markdown-widget` branch's `tests/probes/markdown/` is the precedent)
would be tests code and needs its own `Go!`. Every number below is reproducible
from the scripts named at the end of this entry.

**The crash it recovered from, because that is the recoverable part.** The session
that held WP-F died on its token limit on 2026-09-19 at 20:53 having written **no
branch, no entry in `TASKS-IN-PROGRESS.md`, and no doc edit** — everything it knew
was fourteen probe scripts and ten logs in `/tmp`. Two things saved it: the probes
carry their reasoning in their header comments (why each instrument exists, which
earlier probe each one answers), and their logs are JSON. Those artefacts were
copied to `/tmp/wp-f-crash/` before anything was re-run, so the recovery is a
second independent measurement rather than a restatement. **The rule this
close-out followed, from WP-C's identical accident: an artefact of a crashed
session is a hypothesis, not a citation** — every figure in DECISIONS 76 and in
this entry was re-measured on this tree, and the two runs are quoted as a range.
**Two figures got through the first pass breaking that rule, and a third pass on
2026-09-20 (`/tmp/wpf-continue-run.sh` → `/tmp/wpf-continue-run.log`) is what
caught them**: the 5k `materialize` row and the extremes of the 5k walk, both of
which the recovery had taken from the crashed artefacts alone because its own 5k
walk was CAPPED at 8,020 notches each way and so never reached the true top or the
open tail. Both were re-run uncapped with the same instruments; where a figure now
reads as a pair of runs, one of them is that third pass. The lesson is the rule's
own, sharpened: **a capped re-measurement is not a re-measurement of what the cap
excludes**, and a range whose two endpoints come from one instrument in one
sitting is one measurement wearing two hats.

**What the numbers say** (headless Textual 8.2.8, (80,24), the app's own
`spit_app/styles.css`, corpus `window_harness.big_fixture(n)` — one-line
alternating messages, **6 widgets per message**; the FULL-MOUNT arm is this same
tree with `INITIAL_WINDOW` past N and the WP-D triggers frozen, i.e. what `main`'s
`load()` does). DECISIONS 76 carries the table and the four instrument lessons;
the two rows worth having here are:

| arm | N | open a chat: `load()` + drain (s) | page-down ms, mid-history | one page of wheel: 8 notches (ms) | RSS at rest (MB) | mounted after `load()` | mounted at every depth (the walk) |
|---|---|---|---|---|---|---|---|
| windowed | 100 | 1.22–1.34 + 0.34–0.63 | 81–83 | 619–622 | 89.7 | 50 of 100 | 13–15 (no walk at 100: the table's page-down depths only) |
| windowed | 1,000 | 0.92–1.41 + 0.37–0.48 | 80–81 | 539–612 | 91.3 | 50 of 1,000 | 7–15 |
| windowed | 5,000 | 0.95–1.47 + 0.36–0.51 | 80–81 | 613–651 | 96.2–96.6 | **50 of 5,000** | **7–15** (40,000 notches) |
| full | 100 | 1.77–2.41 + 0.65–0.92 | 161–162 | 590–694 | 101.3 | 100 of 100 | 100 |
| full | 1,000 | 19.72–31.78 + 8.09–10.75 | 851–1138 | 3880–5049 | 286.0–287.4 | 1,000 of 1,000 | 1,000 |
| full | 5,000 | 115.28–187.02 + 39.6–46.04 | 6504–6673 | 20128–23920 | 1099.3–1105.6 | **5,000 of 5,000** | **5,000** |

i.e. at 5,000 messages: **121–127× faster to open, 81–82× faster to page down,
11.5× less memory, 100× fewer widgets** — and the widget count is the point,
because the other three follow from it. The milliseconds are quoted as a range
between the two runs precisely because they are *not* reproducible (the same
whole-history 5k mount: 115.28 s and 187.02 s); the counts and the RSS are.

**The headline, which is the walk — four uncapped round trips, two per N.** One
real wheel notch per `pilot.pause()`, the sample taken only after `rest()`,
triggers LIVE and their liveness printed on every line. 1k, grid 4, 400 samples
over 8,000 notches: 2026-09-19 (`/tmp/wp-f-crash/wp-f-flat-1000.json`, 299.2 s up
/ 323.2 s down) and 2026-09-20 (`/tmp/wp-f-continue-flat-1000.json`, 307.2 s /
329.6 s). 5k, grid 25, 475 and 426 samples over ~40,000 notches: 2026-09-19
(`/tmp/wp-f-crash/wp-f-flat-5000.json`, 1,365.4 s / 1,461.5 s) and 2026-09-20
(`/tmp/wp-f-continue-flat-5000.json`, cap 40,000, 1,405.1 s / 1,482.7 s). Mounted
**7–15 at both N and in all four runs**, 96.3 % and 99.3 % of the 1k samples and
98.5 % and 99.3 % of the 5k ones in 10–13 — what moves between runs is only how
often the band's edge is touched (13 samples at 15 in one 1k run, 1 in the other),
never where the band is. The two extremes are constants of the design and the
2026-09-20 runs read them again at the same depths and windows: **7 at the true
top** (depth 0, window `[0, 7]`, both N) and **8 at the open tail** (depth 4,997
`[4,992, 5,000]` at 5k, depth 997 `[992, 1,000]` at 1k). `window_consistent()` and
`at_rest` True at **every one of the 1,701 samples of the four walks**. The control
is the same transport with the triggers frozen: 200 notches move neither the window
nor the count (5k: `[4,992, 5,000]` and 8 before and after). RSS grows ~29 MB at 1k
and ~33 MB at 5k across a whole round trip and does not come back — the allocator
holding freed widgets, not the window — so RSS is a band, and 10× under the
full-mount arm anyway.

**What the recovery's first walk cannot be cited for.** Its 5k re-walk ran at grid
250 with a cap of 8,000 notches (`/tmp/wpf-recover-flat-5000.json`, 16 samples,
depths 2,998–4,751) and its 1k at grid 200 (`/tmp/wpf-recover-flat-1000.json`, 10
samples). Neither is part of the band claim: capped at 8,020 notches each way the
5k walk never reached the true top or the open tail, so it never had the chance to
read the 7 or the 8, and until the uncapped run above those two numbers rested on
the crashed session alone. The capped artefacts are kept — byte-identical to the
`/tmp/wp-f-keep-recovery-flat-*.json` copies taken before the re-run — as the record
of what a bounded sitting reaches.

**Two rows the crashed session left unlogged and this WP took.** The window's own
page operation timed at a REAL edge (park at the opposite end under the freeze,
prune, move to the edge, release, call it once): **5 messages paged in 43–67 ms**,
at 1k and at 5k alike, page 5 every time (`_page_count()` = margin 34 rows / mean
7 rows, clamped). That row is **one run** (`/tmp/wpf-recover-edge.log`, four cells
at each N, 61/63/67/65 ms at 1k and 49/46/46/43 ms at 5k) — it is not a range, and
it is quoted as a band of four cells of one sitting, not as two independent runs.
`materialize(3)` from the open window, the explicit API's worst case, is the pair
the third pass was needed for: **1k 15.3 s and 20.4 s, 50 → 997 mounted, 5,982
widgets, RSS 91.4/91.5 → 279.1/279.2 MB (+188 MB); 5k 136.2 s and 151.7 s, 50 →
4,997 mounted, 29,982 widgets, RSS 96.6/96.8 → 1074.7/1080.9 MB (~1 GB, +978/984
MB)** — every cell `at_rest=True` and `consistent=True` with the window open at
`[3, N]`. The counts reproduce exactly and the RSS to 0.6 %; the wall clock is
1.3× apart at 1k and 1.1× at 5k. The window is a policy the triggers keep, not a
limit the widget imposes, and that is the number to know before anything builds
a "jump to the top" out of `materialize`.

**One accepted limit, filed rather than fixed** (WP-B's rule: file what you find,
do not "fix" it on the way past). A burst of N wheel events delivered **between two
frames** queues one `_load_at_edge` per event, and `_page_count()` sizes each page
from the MEAN mounted height, which reads ~0.7 rows for a batch whose regions have
not been laid out yet, so every one of those pages saturates at `INITIAL_WINDOW`:
measured, 10 events in one frame carried the window to (603, 942) with **339
children**, and `at_rest()` reads True in the gaps between the queued callbacks, so
the predicate is not a quiescence oracle for a queued burst. One notch per pause —
what the WP-D suite uses and what this table therefore measures — queues exactly
one, verified at batch sizes 1/2/5/10/40 (0 callbacks still queued when `at_rest`
first read True). Filed as **P9** in `TASKS-PLANNED.md` with the measurements: the
page estimator should not read regions a page operation has not laid out, and the
flatness claim should be re-measured after it does.

**Which verification each claim rests on** (the form the file's protocol asks for).
**Counts and mounted/widget numbers** — two headless runs per cell, reproduced
exactly, and the walk's counts from two uncapped walks per N. **RSS** — the same
two runs, agreeing to 0.6 %, quoted as a pair of values; RSS is per-process, so a
cell measured in a shared process would be inflated and none is. **Milliseconds**
— ranges, never point values, because the box moves and the same cell measured
115.28 s and 187.02 s (1.6×) on one tree; a single millisecond from one run is not
evidence of anything. **Anything about the screen** — nothing: there is no screen in
this environment (TRAPS #22), no frame was looked at by an eye, and the geometry and
frame claims are `unit:chat_window`'s and `unit:anchored`'s, not a sighting. **That
no code changed** — the suite's seventeen rows unmoved, before and after.

**Verified.** `bash spit_app/tests/run_tests.sh` from the repo root, run before
anything was touched (2026-09-20 00:24) and again after the docs landed: **every
row at its TESTING.md value with FAIL 0 — tools 127/24/30/119/80/32/68/29 (509),
anchored 68, arguments 131, chat_smoke 168, chat_window 568, prompt 33, render 278,
run_script 121, sandbox 119, terminal 223.** Nothing moved, which is exactly what a
WP that changes no code has to show: the count-unchanged run is the proof that no
code changed, not a proof of the numbers. The numbers themselves rest on the
headless instruments — there is no screen in this environment (TRAPS #22), so
nothing here was confirmed by eye, and the frame/geometry claims are the
`unit:chat_window` and `unit:anchored` suites' rather than a sighting.

**Probes, if they are ever re-run** (all in `/tmp`, all `~/.venv-spit/bin/python`):
`wp-f-probe-table2.py <windowed|full> <100|1000|5000>` — one cell per process, run
alone, six cells sequentially; `wp-f-probe-edge.py <pageop|materialize> <n>`;
`wp-f-probe-flat.py <n> [grid]` (the crashed session's instrument, overwrites
`/tmp/wp-f-flat-<n>.json` — the originals live in `/tmp/wp-f-crash/`);
`/tmp/wpf-recover-walk.py <n> <grid> <notch-cap>` (the crashed walk's own copy,
changed in two lines only — output path and a cap argument — so the recovery could
not clobber the artefact it was re-measuring; it is the instrument the 2026-09-20
uncapped runs used too, at `grid 25/4 cap 40000`); `/tmp/wpf-continue-run.sh`
(the third pass: both `materialize` cells and both uncapped walks, copying the
recovery's JSONs to `/tmp/wp-f-keep-recovery-flat-*.json` first and restoring them
after, so no prior artefact is overwritten); `wp-f-probe-queued.py` (the burst
hole). **Where each walk JSON lives**: crashed run `/tmp/wp-f-crash/wp-f-flat-*.json`,
recovery's capped runs `/tmp/wpf-recover-flat-*.json` (grid 250/200, cap 8000/6000 —
restore these from `/tmp/wp-f-keep-recovery-flat-*.json` if a re-run overwrites
them), uncapped 2026-09-20 runs `/tmp/wp-f-continue-flat-*.json`. Superseded, kept
for the reasoning in their headers: `calib`, `calib2`, `walk1k`, `burst`, `balloon`,
`wholo`, `table`, `full5k`, `full5k2`, `pagedown`.

No sign-off step participated (DECISIONS 71); the branch awaits the owner's merge,
`main` untouched, nothing pushed. **The P8 pipeline is complete**: A
(`task-anchored-scroll-widget`) → B (`task-index-accessor-refactor`) →
C (`task-sliding-window-core`) → D (`task-scroll-load-prune-triggers`) →
E (`task-edit-undo-removal-across-window-edges`) → F (this branch). The merge is the
owner's and is the only part of finishing that is not the agent's; the followups the
pipeline leaves for whoever next works on the UI are **P9** here and, on the
front-end side, the state extraction a replacement UI would build on — which now
has a shipped precedent in `ChatView.widget/window/materialize`. (As written,
this sentence pointed at a route the owner retired on 2026-09-20; DECISIONS 77.
The seam it named is untouched by that retirement.)


### WP-E (P8 pipeline) — edits, undo and removal across the window edges (branch `task-edit-undo-removal-across-window-edges`, awaiting the owner's merge)

Cut from WP-D's tip `5d36627`; the chain is A → B → C → D → E and `main` `8819e73`
is untouched throughout. **The owner's `Go!` was GIVEN 2026-09-19 together with the
one `Go`-time ruling the WP existed to ask** (DECISIONS 71 (c): once per task, not
asked again): **"refuse in `prune()`"** — `prune()` itself returns while
`view.is_edit` is set, so unloading is disabled at fact 5's own definition rather
than only inherited from the trigger paths, and the per-CHILD pins of fact 5 stay as
they are (the mode is per-VIEW, the pin per-CHILD; with `prune()` refusing there is
no walk left to pin while editing). Accepted cost, measured: a window that grew
during an edit is released only by the first prune after `edit_off` — 19 held, then
19 → 10 — and the mode-off and mode-on runs of the same walk land on the SAME window
once the edit is off. What an edit defers is the release, not the release's size.

**What landed.**

- `chat_view.py` — `page_operations_held()`, the save/restore guard as an async
  context manager for callers OUTSIDE the class (the flag stays the class's
  invariant; an outsider never assigns it). `mount_message()` bounds-checks the
  **data** first, then `index < lo` → `window_start += 1` FIRST and
  `materialize(index, render=False)`, `index >= hi` → `materialize`, in-window →
  the neighbour mount, and it **returns the widget**. The old below-the-top branch
  was wrong in DIRECTION, not just at the gap: an insert at any `index <= lo`
  shifts every mounted widget's data index by +1, so the answer is the mirror of
  the removal's −1 and never a front mount — the front mount that stood there left
  a one-message HOLE even for the ADJACENT index `lo-1` (found by `t21`). The
  in-window branch must NOT delegate: between the caller's insert and the mount,
  `widget(index)` is the message's right-hand neighbour, so `materialize` would
  answer "already mounted" and hand back the wrong widget.
- `chat_view.py` — `focus_after_removal(index, widget_was_removed)`, the ONE rule
  both removal sites answer with. `widget_was_removed` is the first question and it
  is the whole rule: no widget left the tree → nothing the reader can see changed →
  focus stays. Asking the neighbour for every removal reproduces the defect at
  `index == window_hi` (the streaming-error path's shape), where
  `widget(index - 1)` IS the last mounted widget; measured, focus child[1] dragged
  to child[6] about five messages from the reader. Empty data → the text area, or
  the ChatView while the mode is on.
- `undo.py` — the three primitives are DECIDE-FIRST: `_insert` puts the dict in the
  data then takes the guard around `mount_message` + `finish` + `focus`; `_remove`
  asks the WINDOW before it deletes (below → `window_start -= 1`, inside → the
  widget goes under its own lock, above → nothing moves) because
  `del self.messages[index]` used to run first and the accessor then raised,
  leaving the data shorter than the tree with nothing persisted; `_change`'s data
  and undo-entry writes stay window-blind and the widget half runs only if a widget
  exists — and with NO `focus()` when it does not, because a focus there drags the
  reader across the history to a message they were not looking at.
- `chat/message/actions.py` — `maybe_add_message_next` answers from
  `messages[index + 1]["role"]`. The old `require_widget(index+1)` ran from
  `check_action`, which is what `refresh_bindings` runs: with the bottom pruned and
  focus on the last mounted widget the whole binding pass raised IndexError with
  **NO keypress** (`refresh_bindings` fires on every worker-state change). Both add
  sites now take the widget `mount_message` returns (recorded deviation).
- `chat_view_actions.py` — no behaviour code. `show_cots`'s window-only loop is
  COMPLETE, not lossy: the mode is inherited **at mount** (`maybe_mount_content`
  reads `chat_view.is_edit`), verified for the target AND for the gap widgets a
  materialize mounts on the way, and a widget carrying per-widget edit state can
  never be evicted to be missed by `reset_message_edit` because `_prune_pinned`
  pins it. The stale "has to be replayed at mount (WP-E)" comment is replaced by
  that measurement.

**The suite.** `tests/unit/chat_window/test_window_edits.py`, 298 checks (t21–t29),
`unit:chat_window` 270 → **568**. Two of its reds were about the INSTRUMENT and are
worth the words because they are the general form: **the setup's `freeze_triggers`
is part of the state a later row reads** — a row that exercises a trigger path must
`thaw_triggers` and assert the triggers live first, or the harness answers for the
thing under test and a "dropped" green is about nothing (t27-live, t29 both measured
`frozen=True` at every moment, paged staying `[]` for reasons that had nothing to do
with the guard); and **an undo "change" entry holds the PREVIOUS state**, so a setup
that records the CURRENT dict asks `_change` to write the current state over the
current state — "no change", three reds, nothing wrong with the code. Six of the
nine original reds were bad claims/setups of exactly these two kinds and were fixed
by probing the state, not by widening anything.

Full suite from the repo root, re-measured at close-out and run **twice**, both runs
byte-identical, plus every `chat_window` file individually: tools
127/24/30/119/80/32/68/29 (509), anchored 68, arguments 131, **chat_smoke 168** with
`golden.txt` still md5 `8ae9d1186a59627d30d05dee95f0ad95` (the differential is
intact), **chat_window 568**, prompt 33, render 278, run_script 121, sandbox 119,
terminal 223 — **FAIL 0 everywhere**, every row but `unit:chat_window` unmoved.

**What the verification rested on**: the automated headless suites — there is no
screen in this environment, so nothing here was confirmed by eye (TRAPS #22).

**Left for WP-F**, as the plan drew it: the DECISIONS-65-style table at 100/1k/5k
messages, the mounted-count headline and the DECISIONS entry closing P8. **WP-E
files no DECISIONS entry**, as A, B, C and D filed none; the owner's ruling is
recorded here and in `UI-ONDEMAND-LOADING.md`'s WP-E entry, not as a decision of the
agent's.

No sign-off step participated (DECISIONS 71); the branch awaits the owner's merge,
`main` untouched, nothing pushed. **Next in the chain: WP-F** — measurements,
numbers, decision record, close P8 — cut from this tip, its own branch, its own
`Go!`. **[DONE — WP-F was cut from this tip as
`task-window-measurement-numbers-close-p8` and closed the pipeline on 2026-09-20:
the table, the walk, DECISIONS 76 and the P8 close, docs only, no `Go!` asked
because no code changed. Its entry is above this one. Do not start anything from
this paragraph — the pipeline is complete and what is left is P9.]**


### WP-D (P8 pipeline) — the load/prune triggers and scroll UX (branch `task-scroll-load-prune-triggers`, commits `c8aab52`…`5c47bf7` + this close-out, awaiting the owner's merge)

Cut from WP-C's tip `154e4fc`; the owner's `Go!` was given 2026-09-16 before the
first edit, once, when the entry was opened at `f40bce8`. Five commits: `c8aab52`
the harness instruments plus the WP-C files' `freeze_triggers()`, `8a623ac` the
triggers in `chat_view.py`, `2091482` **`prune()` takes the page-op guard** (a real
bug this WP introduced the conditions for and its suite found), `5281fe4` the
trigger suite (172 checks), `5c47bf7` the docs, then this entry. Landed in that
order deliberately: the freeze edits are inert before the code exists, so **no
intermediate commit of the branch carries a red suite**. Two earlier sessions on this
branch died on the token limit; everything below was re-measured on this tree.

**What landed.** `ChatView.watch_scroll_y` is now the thing that pages: `super()`
first (the container decides about the scroll before the window does), sub-row
jitter dropped, then ONE debounce timer re-armed by every scroll (`SCROLL_SETTLE_DELAY`
0.15 s — Textual 8.2.8 has no `scroll_ended` hook at all: `Widget.is_scrolling` is a
0.1 s "ended very recently" window) and a page operation posted through
`call_after_refresh` so a mount never re-enters the layout pass that is reporting the
scroll. Five deviations from the sketch, each measured, each pinned:

- **(a) `load()` and `materialize()` hold the guard too**, by save/restore rather
  than clearing — they are the two entry points that must never be dropped (opening a
  chat; the stream sites addressing the last MESSAGE by data index), and a trigger
  landing in the middle of either would run a second mount batch over the same range.
  A caller that already holds the guard must not have it released under it (`t18`).
- **(b) the page operation prunes INLINE and does not re-arm the settle.** The
  re-arm used to be how a page got its prune; what it also did was chain
  settle → prune → page in → re-arm → settle, and one 30-notch burst unwound **11** of
  those against **1** for the shipped code (`/tmp/wp-d3-probe-design.py`). Only a
  SCROLL arms a settle. The inline prune is what bounds an unbroken burst, because an
  unbroken burst never settles: **15 mounted and flat** with it, **18 → 63** with the
  prune stubbed, past `INITIAL_WINDOW` (`t12`, both arms walked into the same sliding
  state, both with the debounce removed).
- **(c) `_scroll_settled()` re-checks the edges after its prune.** `max_scroll_y` is
  the WINDOW's, so a settled prune can clamp the reader to a mid-history window
  bottom, and at a scroll limit a wheel notch moves nothing and therefore fires no
  watcher at all (measured: 0 watch calls with 240 messages unmounted below). The
  settle is the last event that ever fires in that state — which is the starvation
  `t15` closes, with the defect itself (prune alone) as its control.
- **(d) the edge is decided IN THE CALLBACK, not in the watcher**: child regions are
  one frame stale while a scroll is being reported, so a decision taken at watch time
  is a decision on the previous frame (measured `None` at watch time, `older` once the
  frame lands).
- **(e) `prune()` TAKES the guard instead of only asking for it.** WP-C could ask,
  because prune was then only the second half of an explicit sequence; the settle runs
  it from a `set_timer` callback while the page operation is a `call_after_refresh`
  callback — two asyncio tasks, and prune's removal batch is nothing but await points.
  The overlap is not cosmetic: `_grow_up` **assigns** `lo` absolutely while prune
  **adds** its eviction count to whatever is there when the batch finishes, so a
  page-above landing between the last `child.remove()` and that addition leaves the
  count on the wrong base and the mounted range keeps a **hole** — not a transient,
  because `window_hi` is derived from the child count and every accessor keys off
  `window_start`. Forced at that exact point on the pre-fix tree: **2 runs of 3 ended
  with `window_consistent()` False** (`/tmp/wp-d3-probe-interleave4.py`); the same
  runs with the guard taken drop the page and stay consistent (`/tmp/wp-d3-probe-fix.py`).
  The walk moved to `_release_outside_the_margin()` so the guard covers the whole
  batch; unlike `load()`/`materialize()` prune CLEARS rather than restores, because
  nothing nests inside it — if a page operation is in flight its answer is to do
  nothing.

Follow-bottom is untouched except the one deliberate release inside `load_newer`,
verified both ways as the plan asked: Textual re-arms the anchor whenever the view
sits at `max_scroll_y`, so a reader parked at the bottom of a mid-history window would
be dragged down by any mount below. Release first **only when the page will not reach
the tail** — a page that does reach it IS the tail: not-reach **39 → 39 HELD**,
reach **39 → 383 PULLED** (== the new max, one correction, no intermediate frame), and
an already-released anchor is never released a second time. Thresholds are rows of
REAL child region (`TRIGGER_MARGIN_FACTOR` 1 viewport, strictly below
`PRUNE_MARGIN_FACTOR` 2 — the anti-oscillation fixed point `t19` pins as a parked view
that does not move, settle after settle, at either window edge and at the true top);
page size from the MEAN mounted height, clamped `[1, INITIAL_WINDOW]`. Frozen while
`_window_page_op / is_removing / is_edit / chat.is_working() / not is_mounted`, and
while `content_region.height <= 0` (the hidden-`Chat`-in-`#main` case, TRAPS #24).

**Measured facts worth keeping.** A `scroll_y` correction written with
`DOM.set_reactive` does not invoke watchers (dom.py:249), so the trigger never sees
its own work — measured `load_older(20)` = 1 correction, 0 watch calls, and `load()`'s
follow-bottom writes = 0 watch calls. `scroll_y` is WINDOW-relative: "did the reader
move" is always the top MESSAGE index, never `scroll_y` (measured 352 against 308 rows
of content above the viewport). Settled mid-history window **11–15** children, at the
tail **8** — two constants, asserted separately, never averaged. **66–71 ms** per
headless notch against the 0.15 s wall-clock settle, which is why a burst is not
controllable by timing: 17 settles inside one 200-notch burst, 3 inside a 30-notch
burst taken where every notch mounts, and a chained page-op re-arm turned one 30-notch
burst into 11 settles. Page = 5–6 messages on this fixture (mean 7 rows, margin 34);
travel inside `load()`'s 50 messages ≈ 170 notches.

**Verified — `unit:chat_window` 98 → 270, and the floor that must not move.** 172 new
checks in `test_window_triggers.py`, every zero read against a control (TRAPS #13):
`t10`'s frozen triggers leave the same 200 notches moving nothing; `t12`'s control
stubs the prune alone and the count grows past `INITIAL_WINDOW`; `t15`'s control IS the
defect; `t16`'s control is the same call at the other edge, where it is a page; `t17`'s
controls are the same calls with the freeze lifted; `t20`'s control is the same
`load_older` outside a prune, which pages. Three instrument lessons are written into
the file because each was a bug in an earlier draft rather than a style choice: build
the state and then assert it (`build_an_edge`; `walk_into_the_sliding_region` driven to
the STATE with a ceiling — the fixed-8-burst version asserted `window_start < 940` at a
depth where it reads 953); replace machine-dependent constants with mechanisms and
ratios (`arms == watches`, `settles * 20 <= watches`); sample invariants only at rest,
and spend the arrival sample (`t13`'s tail constant is taken after the burst that
reached the tail — measured arrival 12 mounted then 8, 8, 8, and five more settles
leave (992, 1000)/8 untouched; `t20`'s state moved from `scroll_to(0,0)` to mid-mount,
because at the window top prune's above-side walk is empty — `above=0`,
`evict_above=0`, 383 rows BELOW — so `lo` has no way to move and the check proved
nothing).

Full suite from the repo root, re-measured at close-out: tools
127/24/30/119/80/32/68/29 (509) and unit anchored 68, arguments 131, **chat_smoke
168** with `golden.txt` still md5 `8ae9d1186a59627d30d05dee95f0ad95` (no re-pin: its
fixture chats are ≤ 50 messages, so `load()` mounts exactly what the old loop mounted
and the triggers never fire there), **chat_window 270**, prompt 33, render 278,
run_script 121, sandbox 119, terminal 223 — **FAIL 0 everywhere**, and **three
consecutive full runs byte-identical**, which is what a suite with a wall-clock timer
in it has to show. Two crashes hid inside that row and were found only by running the
files: `test_window_flows.py` called `freeze_triggers` without importing it (NameError,
the whole file dead) and `t13` did `max()` on an empty list; the outer `run_tests.sh`
printed `unit:chat_window: PASS: 54 FAIL: 0` over both. That failure mode of the
runner is now written into TESTING.md.

**What the verification rested on**: the automated headless suites — there is no
screen in this environment, so nothing here was confirmed by eye (TRAPS #22). The
frame instrument (`FrameSpy` on `App._display`) is what stands in for the eye for the
jump-frame claims, and `unit:chat_smoke`'s unchanged golden dump is what shows the
streaming and edit paths still behave as before.

**Left for WP-E / WP-F**, as the plan drew it: `undo._insert/_change/_remove` and
`message/actions.py` across the window edges, focus survival when the focused widget
leaves the window, the `show_cots`/`reset_message_edit` replay on materialize, and the
`is_edit`-disables-unloading `Go`-time decision (E); the 100/1k/5k measurement table,
the mounted-count headline and the DECISIONS entry closing P8 (F). **WP-D files no
DECISIONS entry**, as A, B and C filed none.

No sign-off step participated (DECISIONS 71); the branch awaits the owner's merge,
`main` untouched, nothing pushed. **Next in the chain: WP-E** — edits, undo and
removal across the window edges — cut from this tip, its own branch, its own `Go!`.


### WP-C (P8 pipeline) — the sliding-window core (branch `task-sliding-window-core`, commits `5d92bdf`…`594f3f1` + the docs close-out, awaiting the owner's merge)

Cut from WP-B's tip `52cc686`; the owner's `Go!` was given 2026-09-15 before the
first code change, once, as the entry opened at `5d92bdf` records. Four commits:
`5d92bdf` the in-progress entry, `bd0ece0` the window core (`chat_view.py`),
`f4328c9` the three sharp edges (`chat.py`, `chat_text_area.py`, `callback.py`,
`chat_view_actions.py`), `594f3f1` the suite (`tests/unit/chat_window/`, 98
checks), then the docs close-out (the `TESTING.md` row and the suite's
description, TRAPS #24, the map rows, this entry). **The session that wrote them
crashed between the last commit and the docs commit** — it left `TESTING.md`
dirty and its own entry's State fields saying "Done: nothing yet"; the close-out
was made by the agent that picked it up, and every number below was
**re-measured on this tree**, not copied from the crashed session's notes.

**What landed.** `ChatView` now extends `AnchoredScroll` (the swap WP-A left
deliberately) and the widget tree is a window `messages[lo, hi)` with **both ends
free**:

- `lo` is instance state and keeps WP-B's name (`window_start`, so the accessor
  block needed no edit); **`hi` is derived** — `window_hi = lo + len(children)`,
  with `window` a property over the pair. **Deviation from the sketched
  `window: tuple[int, int]`**: a stored tuple is a second source of truth for the
  one statement the window must keep true (the mounted range is contiguous), and
  deriving `hi` removes the way it could drift.
- `load()` mounts the last `INITIAL_WINDOW` (50, a class constant; a settings
  surface later) and — **deviating from rule 4 as written** — does *not* call
  `scroll_end()`: `scroll_end` funnels through `Widget._scroll_to`, which calls
  `release_anchor()` (P8's own finding), so an explicit call at open would strip
  follow-bottom off every freshly opened chat and change streaming behaviour. The
  `__init__` bottom anchor held through the batched mount *is* the open-at-bottom
  UX, and `t1-open-at-bottom` still pins `scroll_y == max_scroll_y`.
- `_grow_up` is the arm → batch-mount → self-disarm dance, with `lo` moving only
  **after** the batch so the accessors answer for one consistent range
  mid-operation; `_grow_down` / `load_newer` need no compensation (rule 2,
  remount-into-gap is rule 3). One re-entrancy guard (`_window_page_op`) covers
  the three page operations — a trigger firing mid-operation asks for a page the
  running operation is already growing, so it is dropped (WP-D's thresholds are
  what will exercise it).
- `prune()` releases both ends to the margin: eviction is strictly outside
  viewport ± `PRUNE_MARGIN_FACTOR` × viewport height (factor 2 — rule 7 demands
  ≥ 1 as the clamp guard and probe 7 was measured with 2). Evicting above arms the
  one-shot anchor (rule 1: the same event as a mount above, sign flipped);
  evicting below moves and corrects nothing (rule 2). The fact-5 pins — `is_edit`,
  the focused widget (focus can sit inside it), the streaming tail while
  `chat.is_working()` — **bound each walk**, which is incidentally what keeps
  every eviction a strict prefix/suffix and the window contiguous. Two guards the
  plan did not name: a **hidden** chat (`content_region.height <= 0`, and `#main`
  keeps every opened `Chat` mounted, not destroyed) is never a prune target
  because its regions are stale, and `prune()` also yields to `is_removing`.
- `materialize(index, render=True)` grows the window to cover an index and returns
  its widget. The `render=` half is a **deviation from the sketch**: the stream
  sites mount a dict whose content the *stream* owns, so they ask for mount-only,
  while the gap widgets a materialize crosses are history and are always finished
  from their dicts (fact 5). An index outside the data raises `IndexError`, the
  exception `children[index]` raised.
- The three `children[-1]` edges go through it: `action_abort` materializes
  `len(messages)-1` before the teardown, `action_submit` mounts the new user
  message through it instead of a bare `mount` (with the bottom pruned, a bare
  append lands behind the wrong neighbour and breaks the window), `message_start`
  likewise. The ctrl+up/down focus walk became window-tolerant — out of window the
  focus stays put — because those actions are synchronous by design; paging under
  a leaving focus is WP-D's trigger and WP-E's focus-survival decision.
- `mount_message` learned insertion above the top (widget on the front, `lo`
  slides down); `on_remove_message` tolerates a removal **below** the window (the
  streaming-error path removes `messages[-1]`, which may already be evicted — the
  data shifts, so `lo` slides with it) and picks the focus neighbour through the
  accessors.
- `window_consistent()` is now the sliding form: `children[p] is
  messages[lo+p]`'s widget **by dict identity**, inside the data. WP-B's
  arithmetic form is this with `lo` 0 and the tail intact; the identity form is
  what stays true once the bottom is prunable. Quiescence-only for WP-B's recorded
  reason (the stream's data-ahead gap is what `is_present` answers).
- The chat-switch interplay the scope asked about (`side_panel.py:86-88`,
  `handlers.py:27-28`) was **verified and left alone**: opening a chat reuses the
  mounted `Chat`, they are never stacked twice per id, each `ChatView` keeps its
  own window. `t9` pins that as it behaves today.
- The front-end read-list item is noted in `bd0ece0` as asked: this window is the
  same state/view seam a replacement front end would have to extract (messages
  are truth, the widget tree a projection). **No** front-end contract or protocol
  was pre-built — and none is wanted now (DECISIONS 77).

**Left undone on purpose**, at the boundaries the plan drew: the fact-5 superset
"is_edit disables `prune()` entirely" stays a WP-E `Go`-time decision (WP-C pins
per widget, always); `watch_scroll_y` triggers and the settled-scroll prune calls
are WP-D; `undo` / `message/actions.py` across the edges plus focus survival are
WP-E; the 100/1k/5k measurement table, the mounted-count headline and the
DECISIONS entry are WP-F — **this WP files no DECISIONS entry**, as WP-A and WP-B
filed none.

**Verified — `unit:chat_window` 98, and the floor that must not move.** `t1`
opens a generated 1000-message chat: exactly 50 mounted, window `(950, 1000)`, at
the bottom, data complete and list-IDENTICAL, no JSON written; `t1b` is its teeth
(TRAPS #13) — a 120-chat also mounts 50, a number the unwindowed code cannot
produce. `t2` slides: `load_older(25)` → `lo` −25, +25 mounted, tracked anchor
holds, **0 jump frames**, exactly one correction, chat-store md5 and write count
fixed; **`t2c` repeats it with `arm_top_anchor` disarmed and paints the jump**,
which is what makes `t2`'s zeros evidence. `t3` evicts below with `scroll_y`, the
view and the correction counter all unmoved, then remounts into the gap holding.
`t4` prunes at the open state: evicted above back to the margin, `scroll_y`
shifted by EXACTLY the evicted height clamped at the new max, 0 jump frames,
mounted under `INITIAL_WINDOW`, and a second `prune()` changes nothing (steady
state). `t5` the pins: `is_edit` stops the above-walk after evicting the one
unpinned widget above it (a pin bounds the end, it does not freeze the walk), the
streaming tail while `is_working()` blocks the below-walk and the same prune
without the pin evicts, a focused widget below the viewport is unevictable. `t6`
abort-while-scrolled-up: bottom pruned away first, then `action_abort`
materializes the tail by data index, cancels, and removes from **both** sides.
`t7` `materialize` at both edges, same widget when already mounted, `IndexError`
for −1 and for `len(messages)`. `t8` churn 8 × (`load_older(25)` + `prune()`):
mounted count flat and ≤ `INITIAL_WINDOW` at every depth — probe 7's headline at
the `ChatView` level — 0 jump frames and consistency every cycle, store md5 fixed
and zero writes; `lo` monotonicity is **deliberately not asserted** (a prune at a
viewport that never moved legitimately reclaims the page just mounted above the
margin; `lo` only slides when the user scrolls toward it, which is WP-D's
trigger). `t9` the chat-switch interplay, above. The harness (`window_harness.py`)
**imports** the stub app and `FakeWork` from `chat_smoke/smoke_scenario.py`
instead of copying them — a deviation from "each unit suite is self-contained",
chosen so the two stubs cannot drift — and adds the app's own `spit_app/styles.css`
because without it the messages lay out at zero height and every viewport
computation is vacuous: that finding is **TRAPS #24**.

Full suite from the repo root, re-measured at close-out: tools
127/24/30/119/80/32/68/29 (509) and unit anchored 68, arguments 131, **chat_smoke
168**, chat_window 98, prompt 33, render 278, run_script 121, sandbox 119,
terminal 223 — **FAIL 0 everywhere**, i.e. the ground truth moved by exactly the
one new row. `unit:chat_smoke` is 168 with `golden.txt` still md5
`8ae9d1186a59627d30d05dee95f0ad95` (generated from `f201700`, untouched in git
since `d51e42e`) — **no re-pin**: its fixture chats are ≤ 50 messages, so `load()`
mounts exactly what the old loop mounted and the window does not move them, which
is what the entry's Verify demanded. The FAIL-with-remedy path was run by the
suite's author (`HOME=/tmp/fakehome` → `PASS: 0  FAIL: 1` naming
`create_venv.sh`), and the root `run_tests.sh` needed no edit (its `unit/*` loop
auto-discovers any directory with a runner).

No sign-off step participated (DECISIONS 71); branch awaiting the owner's merge,
`main` untouched, nothing pushed. **Next in the chain: WP-D** — load/prune triggers
and scroll UX — cut from this tip, its own branch, its own `Go!`.


### WP-B (P8 pipeline) — the index-accessor refactor, zero behaviour change (branch `task-index-accessor-refactor`, commits `58fa068`…`d51e42e`, awaiting the owner's merge)

Cut from WP-A's tip `f201700`; owner's `Go!` given. The ~30
message-index → `chat_view.children[...]` sites of the coupling table (7 files)
now go through one seam on `ChatView`, with `window_start = 0` hard-wired, so
every accessor is the identity the indexing it replaced:

- `widget(index)` tolerant (None out of window — an update to an unmounted
  message is data-only, the widget rebuilds from the dict on re-entry);
  `require_widget(index)` for the sites that addressed a mounted widget — it
  raises **IndexError**, the exception `children[index]` raised, so no error
  path silently became a no-op; `widget_index(widget)` the reverse map;
  `child_position(index)` for the int `mount(before=)` takes; `last_child()`
  for the deliberately last-**MOUNTED** intents (`focus_this`, `load()`);
  `window_consistent()` the invariant instrument.
- The three `children[-1]` sharp edges now address the **last message by data
  index** (`action_abort`, `action_submit`) or say they mean last-mounted
  (`load()`, `focus_this`). This is the shape WP-C puts a `materialize` behind.
- `undo._remove` asks "is there a mounted widget at this message index" instead
  of comparing a child count with a data index — a child count answers nothing
  once either end can be evicted.
- **Deviation from the sketched API**: the plan's assertion is a *method*, not
  a runtime assert. `len(children) == len(messages) - window_start` holds at
  QUIESCENCE only — streaming appends the dict to `chat.messages` and posts the
  mount afterwards (`work.py`, the endpoints), so mid-stream the data
  legitimately runs ahead of the widget tree (that gap is what `is_present` is
  for). An assert in a mutation path could fire in a working app, which is a
  behaviour change; the invariant is asserted by the suite after every step
  instead, and `require_widget()` is the runtime guard.
- **Filed, not fixed** (the WP hazard): `is_present()` is deliberately narrower
  than `index < len(children)` — the old predicate answered True for a negative
  index and then indexed the LAST child, the wrong widget (unreachable: every
  index is a position in `chat.messages`); `ChatView.mount_message()`'s first
  branch indexes `messages[index]` with `index == len(messages)`, dead code that
  would raise, now commented as filed; `action_add` appends a message and
  undoes/mounts/indexes `messages[0]`, correct only because `check_action`
  requires an empty chat; two chat files (`callback.py`, `message/actions.py`)
  carry no SPDX header.

**Verified — the differential, not the suite.** New suite
`tests/unit/chat_smoke/` (168 checks): `smoke_scenario.py` drives a real `Chat`
headless over a generated fixture (mount, focus, edit_on/off, the message-level
add next/prev, the three stream signals, undo/redo of insert and remove, abort
with a fake worker; a second headed run covers `action_add` on an empty chat)
and dumps plain data per step — roles, per-widget `cnt` keys, rendered `Part`
text, cots visibility, focus, undo list, the chat JSON written so far, scroll
position. It uses no new API, so the same script drives `f201700`; **the tip
reproduces that tree's dump byte-for-byte** (md5 `8ae9d1186a59627d30d05dee95f0ad95`),
committed as `golden.txt` with the regeneration recipe in the test docstring.
The probe was believed only after it was falsified (TRAPS #13): reversing
`load()`'s mount order in a copy of the tree moves the dump.
`test_chat_smoke.py` adds the accessor contract (window_start 0, the invariant
at every step, `widget`/`widget_index`/`last_child`/`child_position` agreeing
with the raw child list, None vs IndexError out of window). Full suite green
before and after: tools 127/24/30/119/80/32/68/29 and unit 68/131/33/278/121/
119/223 unmoved, `unit:chat_smoke: 168` added; the FAIL-with-remedy path was run
(`HOME=/tmp/fakehome` → `PASS: 0  FAIL: 1` naming `create_venv.sh`). No sign-off
step participated (DECISIONS 71); branch awaiting the owner's merge, `main`
untouched, nothing pushed.

### WP-A (P8 pipeline) — the anchored container widget: `AnchoredScroll` (branch `task-anchored-scroll-widget`, commits `377d47d`…`d5f3f79`, awaiting the owner's merge)

**What landed**, four commits on a branch cut from `main` (`8819e73`):
`377d47d` lands the plan docs (the P8 entry, `doc/UI-ONDEMAND-LOADING.md`,
the two map rows) that sat uncommitted in the working tree — the pipeline's
canonical state belongs in git ahead of the implementation; `3ad2982` opened
this WP's in-progress entry; `dd6dac6` the widget; `d5f3f79` the suite.

`spit_app/chat/anchored_scroll.py` — `AnchoredScroll(VerticalScroll)`, the P8
widget implemented from the proven mechanism, not redesigned: `arm_top_anchor()`
(one-shot) + `pin()`/`unpin()` (persistent, re-baselined on every landed
scroll via `watch_scroll_y` → `call_after_refresh`), the direction-agnostic
`scroll_y` correction inside `process_layout` with exactly the
`set_reactive(Widget.scroll_y, …)` + `scroll_target_y` +
`vertical_scrollbar._reactive_position` write Textual's own bottom anchor uses
(`_compositor.py:609-619`), and disarm-if-anchor-gone. **`ChatView` was not
touched** (WP-C changes the base class).

**New suite `tests/unit/anchored/` (68 checks)** — the three throwaway probes
(`probe.py`, `probe6.py`, `probe7.py`) rebuilt as permanent checks, none
weaker than the measurement tables in P8/the plan: the plain-`VerticalScroll`
defect as the control (every painted frame shows the jump); 0 jump frames on
single (15→19) and batched (15→27) mounts above; bottom-anchor coexistence;
user-scroll re-baseline (21 respected, 0 corrections); late growth above
(25→29, no shift); unpin returns the defect; **probe-7 eviction**: evict-above
holds the view and shifts `scroll_y` by exactly the evicted height (30→18 for
12 rows), evict-below produces zero movement *and zero corrections*,
remount-below holds, 20× churn keeps the mounted count flat (worst 13 at
viewport 10 / margin 20 — the window, not the history). The frame-spy
technique is preserved verbatim: wrap `App._display`, one call is one emitted
frame, assert no emitted frame shows the tracked widget at the wrong row.

**Deviations from the planned API** (all additions, none renames; the WP
sketch left the one-shot/pin composition undefined): the two modes share one
anchor slot and are mutually exclusive — `pin()` absorbs an armed one-shot
(same anchor, same baseline: the pin's `placement.region.y − offset` and the
one-shot's `scroll_y + delta` are the same target when captured from the same
state), `arm_top_anchor()` is a no-op while pinned; a removed anchor behaves
per mode (one-shot disarms outright, verified by a follow-up mount moving the
view exactly like the defect control; the pin re-baselines onto the new first
visible child *after* the frame — regions are stale inside a layout pass);
public extras: `is_pinned` and the `corrections` counter (test instrument).
**Consequence for WP-C**: evicting the widget the pin is currently anchored
to is the one prune that moves the view un-compensated for that frame — the
prune policy must re-anchor deliberately (the anchor widget is chosen
viewport-first, so pruning strictly-outside-viewport children never removes
it).

**Verified.** Suite 68/0 stable over three runs; the FAIL-with-remedy path
was actually run (`HOME=/tmp/fakehome` → `PASS: 0  FAIL: 1` naming
`create_venv.sh`, never a silent zero). Full suite green before and after;
ground truth moved only by the new row: tools 127/24/30/119/80/32/68/29 and
unit 131/33/278/121/119/223 unmoved, `unit:anchored: 68` added (`dd6dac6`/`d5f3f79` carry the numbers into TESTING.md, which also
notes PROJECT.md/TRAPS #19's "one venv-dependent suite" statements are now
two). The root `run_tests.sh` needed no edit — its `unit/*` loop
auto-discovers any directory holding a `run_tests.sh`; the "suite row"
requirement is satisfied by the suite's own runner. No sign-off step
participated (DECISIONS 71); branch awaiting the owner's merge, `main`
untouched, nothing pushed.

## Verbatim records kept from the old summary's "Next steps" (they double as
## the conventions their follow-up work must respect)

### 1. DONE — fixtures renamed to `tNN-<what>.txt` (branch `per-test-fixture-names`)

**Why.** Fixture names used to be shared/semantic (`original.txt`,
`exp_insert3.txt`), so a test could compare its output against another test's
fixture and still pass. That exact mistake happened twice in one session (test 18
compared against `exp_insert3.txt`, which belongs to test 1 and contains `NEW`,
not the `X` the test inserted). Per-test names make the mismatch structural, not
just confusing.

**The convention, as now applied to all seven suites.**
- `fixtures/tNN-<short-name>.txt`, `NN` = the number of the test in `run_tests.sh`
  that owns it (`=== 12. Errors ===` → `t12-*`). A `tNN-*` fixture is read by test
  `NN` and by nobody else — that is the point of the whole exercise.
- Scratch files carry the number too: `t01-work.txt`, `t18-work-crlf.txt`,
  `t16-nonl.txt`, `t11-no-such-file` (a path that must **not** exist is a fixture
  too; it is simply never created — same for `t09-no-such-dir`).
- A fixture genuinely used by several tests keeps a neutral name in a shared
  prefix, `fixtures/shared-<name>.txt` (`shared-original.txt`,
  `shared-exp-insert3.txt`, `shared-blank-lines.txt`, `shared-crlf.diff`): content
  is not duplicated, and a `tNN-*` name is never shared.
- `create_fixtures.sh` is in **test order** (not alphabetical) and purely
  declarative: shebang, `source`, `fixtures_selftest`, then `testfile` lines only.
- `grep`'s nested tree keeps its shape under the numbered dir:
  `fixtures/t01-src/app.py`, `fixtures/t01-src/sub/notes.txt`,
  `fixtures/t01-src/blob.bin` (`testfile` already does `mkdir -p`). The tree is one
  fixture owned by test 1; other tests pass the *directory* to the tool, which is
  the only cross-test reference allowed.
- `patch`'s shared corpus lives in `fixtures/corpus/`: `original.txt`,
  `patch.diff`, `expected.txt`, `dup.txt`, `dup_headed.txt` (`dup_tie.txt` was later deleted — no test read it, decision 51)
  (35 references — grouped, not copied per test).
- A test that needs a *derived* expectation generates it inside its own section
  (`sed ... > fixtures/t15-exp-both.txt`), not in the prologue.
- Round-trip tests that `cd "$patch_dir"` still pass the harness an **absolute**
  `$FIXTURES/...` path (`FIXTURES=$PWD/fixtures`, set near the top): a relative
  `fixtures/...` inside that subshell resolves in `spit_app/tests/tools/patch/`.

**Verified.** 415/415 green at the time (24/32/29/30/54/119/127 — `patch` has since been redesigned, see section 3 and the ground-truth table above); every fixture corpus
generated from `main` and from the branch, compared as sorted md5 multisets per
suite → identical; `git diff main..HEAD` on `run_tests.sh` touches fixture paths
and nothing else; suite dirs still hold exactly the three files and no `fixtures/`
survives a run. One commit per suite, smallest first.

**Three deliberate deviations from a pure rename.**
- `insert_line` t11 used `/tmp/no_such_file_il` and `--path /tmp`; they are
  `fixtures/t11-no-such-file` and `--path fixtures`. Nothing a run touches may live
  outside the disposable dir, and this was the only `/tmp` left anywhere.
- `delete_lines` dropped its unused `fixtures/empty.txt` — no test read it (test 16
  truncates its own file with `: >`). It is the one difference between `main`'s
  corpus and the branch's (19 fixtures → 18).
- `patch`'s `t15-exp-both.txt` is now generated inside test 8 rather than in
  the prologue, so the file a test compares against is created by that test.

**Re-check the invariant after editing any suite** — it is cheap and it is the
whole value of the rename: every fixture `create_fixtures.sh` writes must be
referenced by `run_tests.sh`, and no `tNN-*` name may appear outside its own test's
section. Walk both files line by line, tracking the current `echo "=== N.` header;
`grep`'s `t01-src` directory is the only sanctioned exception.

### 2. DONE — `delete_lines`: use the shared line-ending helpers instead of its private copies (branch `delete-lines-shared-line-helpers`)

**Why.** `spit_app/tools/scripts/common/lines.py` is the single definition of the
line-ending primitives (extracted from `patch`, used by `insert_line`).
`delete_lines` carried its own near-duplicates of them.

**The three changes.**
- `spit_app/tools/scripts/delete_lines.py`
  - deleted the private `strip_ending()` and called `strip_newline()` instead —
    they are identical (`"\r\n"`, `"\r"`, `"\n"`, longest first), so behaviour did
    not change;
  - also replaced its `read_lines()` / `write_lines()` bodies with
    `read_text_raw(path).splitlines(keepends=True)` and
    `write_text_raw(path, "".join(lines))` for consistency (the two functions were
    kept, they name the intent).
- `spit_app/tools/delete_lines.py` — `"script": get_script(__file__)` became
  `get_script(__file__, "lines")` (the common script is *prepended*; a tool script
  can never import another tool script).
- `spit_app/tests/tools/delete_lines/setup.json` — `"common":
  "../../../tools/scripts/common/lines.py"` added next to `"script"`. Without it
  the whole suite dies with `ERROR: NameError: name 'strip_newline' is not
  defined`, which is how you notice.

**Verified.** All three changes are in and behaviour is unchanged. `delete_lines`
127/127, `patch` 54/54 (as it then was), `insert_line` 119/119 — all seven suites 415/415, suite
dirs still exactly three files each. Real-path smoke test through
`get_script`/`get_args`: load `spit_app/tools/delete_lines.py` with
`load_module_from_path`, take its `EXEC["script"]`, run it with the `get_args`
head — the assembled script defines `strip_newline` (the common file is prepended),
the tool's own part contains no `strip_ending` and no `open(` at all,
`one\r\nTODO x\r\nthree\r` minus the `TODO` line comes back as `one\r\nthree\r`
(CRLF *and* lone CR survive), `a\nb\nc\nd` minus lines 2-3 comes back as `a\nd`
(still no trailing newline), out-of-range `start_line` still exits 1 naming the
valid range.

The one textual difference between the two implementations is the order the
terminators are tried in: the private copy had `"\r\n", "\n", "\r"`, `strip_newline`
has `"\r\n", "\r", "\n"`. A line can end in both `\n` and `\r` only as CRLF, which
both versions test first, so every other case reaches exactly one branch — hence
byte-identical behaviour, which is the whole point of the dedup.

**The policy was not "improved" while in there, and must not be later either.**
`patch` and `insert_line` normalise to the terminator of the file's first line
break (they must agree, or an insert and its own preview applied by `patch` give
different bytes — see decisions 45 and 46). `delete_lines` deliberately keeps every
remaining line's exact terminator and therefore needs no detection at all: deleting
never rewrites an untouched line. That asymmetry is intentional.

---


### 3. DONE — `patch` redesigned (branch `patch-tool-fixes-2`, commits `ad346c4`…`dd8a50f`)

Five commits, one per step, each leaving **all seven suites green**, each verified
against `main` by differential rather than by the suite alone:

| step | commit | change | patch checks |
|---|---|---|---|
| 1 | `ad346c4` | drop the `^^` trailing-header notation (decision 54) | 54 → 44 |
| 2 | `26e5e0d` | header line counts become advisory (decision 33) | 44 → 55 |
| 3 | `362cfb9` | one positioning rule: apply iff unambiguous (decision 53) | 55 → 57 |
| 4 | `9771729` | match against the pristine file, reject overlaps (55, 56) | 57 → 63 |
| 5 | `dd8a50f` | empty lines separate hunks; blank-line coverage (57, 58) | 63 → 80 |

**Method that mattered more than any individual change.** Every step was proven by
running `main`'s script and the new one over *every* fixture with the same input and
grouping the results, rather than trusting a green suite:

```
main applied        -> new applied, byte-identical   15
main applied        -> new refused (tie / overlap)    2   intended
main refused        -> new applied                    7   intended
main refused (other)-> new refuses identically        6
BOTH APPLIED BUT DIFFERENT BYTES: none
```

That last line is the safety property: the redesign never moves a hunk that used to
be placed and never changes bytes a hunk used to write — it only turns refusals into
applications and one guess into a refusal. The suite alone would not have shown it,
because a refusal that becomes an application is invisible to a test that expected
the refusal.

**Three lessons recorded here because they were paid for.**
- *Numbers are append-only.* Test numbers 5-9 were freed by step 1 and deliberately
  not reused; new tests are 30-39. A `tNN-*` name keeps one meaning across the
  series, which is the whole value of the naming convention (decision 49).
- *A probe can lie.* Three separate differential scripts fed fixtures the wrong
  source file (`t16`/`t18` needed `corpus/dup.txt`, `t27`/`t28` their own files) and
  still printed a tidy "identical" row. Both times the row was re-run against the
  correct source. A differential is only as good as its input mapping.
- *An invented motivating example is a defect.* Step 5 as originally proposed was
  wrong in both direction and evidence (decision 58); it was caught by measuring the
  reference implementations instead of reasoning about them.

**Known edge, deliberately left open** — see *Next steps → 4*.

### exit-reporting — the verdict line reports news; the tool says whether it needs one (branch `alternate-exit-reporting`: `a1563e5`, `a4cf37f`, `ae568a0` + the docs close-out, awaiting the owner's merge)

**What the owner asked for.** Stop the Run class appending `✓ Exit code 0 — command reported no error.` to
every tool result: one paragraph per call saying only what the absence of a failure already says. The
first cut of it (the owner's, uncommitted) gated the line behind the *no-output* condition, which reported
the exit code where nobody needs it and not at all where they do — a failure with output reported no code
(`echo built; exit 3`, the shape of every compiler and test runner), and because the gate began with
`stderr_task`, which is `None` unless `separate_stderr=True`, all 13 script tools lost exit reporting of any
kind. That is the TRAPS #18 class: not a red check, a flipped verdict.

**What shipped.** The line is written when it is news, and how much of it is written is the tool's call, not
`Run`'s — `needs_exit_status_report=True` for `run_command`/`run_script`, whose stdout is somebody else's
text; default `False` for the 13 script tools, whose scripts print their own `ERROR:` verdict. Silence is
covered either way: `or silent` writes the failure line whenever the result would otherwise be empty, and a
success says something only in that same case. The three death sentences sit outside the flag and were
reworded into one family with the exit line; the stderr block moved above the verdict so the verdict is the
last thing read. Full record: **DECISIONS 79**, rule in `RUNTIME-RUN-COMMAND.md`.

**Measured, not assumed.** The flag's premise is that the 13 tools state their own outcome, so it was
counted before it was relied on: **all 36 non-zero exits across all 13 scripts print an `ERROR:` line
first.** It holds inside the scripts and not outside them, which is what `or silent` is for — with the
carve-out absent, a poisoned interpreter, an OOM kill or a future print-less `sys.exit(1)` returned the
empty string, byte for byte, from a `write_file`-shaped call through the real delivery path. The behaviour
was settled by a differential over rc × output × stream-mode with `main` in a throwaway worktree against the
branch, both `separate_stderr` values, plus a case killing the process `Run` exec'd: every failure row
byte-identical to `main`, the success-with-output rows losing exactly the one line, the signal death silent
on `main` and reported here. The worktree was removed afterwards — a second checkout of `main` blocks the
owner's merge — and no commit was made in it.

**The five checks, and what the re-pin changed about them.** They asserted the line this removes, and the
owner re-pinned them to the exact tool result (`out == "read: []\n"`, `out == "hi\n"`,
