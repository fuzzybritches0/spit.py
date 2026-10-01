# TASKS-FINISHED.md

Completed work with references, so finished state can be trusted without
re-deriving it. Commit refs are in `~/spit.py` (`git log --oneline`).
Test-count ground truth: see TESTING.md.

## Milestones

### REVERTED (2026-10-01) — the windowed message loading is out of the tree (branch `revert-on-demand-loading`, awaiting the owner's merge)

Cut from `main` `d0a8e30`; `main` untouched, nothing pushed. **What**: the
sliding-window loading of P8 / WP-A…WP-F is reverted in behaviour and in shape —
`ChatView` is a `VerticalScroll` again and `load()` mounts the whole history;
`chat/anchored_scroll.py`, `unit:anchored` (68 checks), `unit:chat_window` (568)
and `doc/UI-ONDEMAND-LOADING.md` are deleted. **Why**: the owner used it and the
app was worse — the wheel froze for as long as a page took to mount and
re-render, the view jumped back down and would not let the reader scroll up, and
nothing paged or pruned while the chat worked, which is when a long tool loop
grows the tree. The owner's words, the four failure modes and the Textual
limits behind them are **DECISIONS 89**; the numbers stay in DECISIONS 76; the
pre-flight list is TRAPS #27; the route forward is **P22** (options, nothing
chosen — naming a front end is the owner's, DECISIONS 77). **What was kept and
why**: P19's `remove_message_at` (the ONE rollback its retry awaits) and the
shared `focus_after_removal`, `mount_message` returning what it mounted,
`is_present`'s two-sided bound, the stale-signal guard, the data-based next-role
question, and all of P12/P13/P14/P19/P0b — later work grew onto those seams,
which is why a mechanical `git revert` of the range could not be done and no one
should try. **Verify**: the differential is the proof — `unit:chat_smoke` t1
compares against the golden generated from `f201700`, the tip BEFORE the whole
experiment, and it passes byte-for-byte on this tree; its t2 is now the
whole-history invariant (`children[i].message is messages[i]`, `is_present` on
both bounds, `mount_message`'s bounds check), 168 → 116. Full suite, every FAIL
0: tools 536 (127/24/30/119/107/32/68/29), arguments 131, chat_smoke 116,
endpoints 547, handoff 60, journal 69, prompt 38, recovery 55, render 278,
run_script 121, sandbox 157, system_note 219, terminal 346.

> **REVERTED 2026-10-01 — DECISIONS 89: the windowed message loading (P8,
> WP-A…WP-F) is OUT of the tree.** `ChatView` is a `VerticalScroll` that mounts
> the whole history again; `chat/anchored_scroll.py`, `unit:anchored` (68),
> `unit:chat_window` (568) and `doc/UI-ONDEMAND-LOADING.md` are deleted. The WP
> entries below stay for their measurements and their instrument lessons — read
> them as the record of a built-and-unshipped feature, NOT as the state of the
> code, and do not "fix" them: the code they describe is gone. Branch
> `revert-on-demand-loading`; the route forward is P22.


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
- **P12: the token counts row and the endpoint's context size** (branch
  `task-token-counts-p12`, `c7e7d74`…`a643666` + the close-out, awaiting the
  owner's merge; `main` untouched). Every chat now shows
  `ctx <used> / <available> · gen <generated> · cached <cached>` on its
  chat-settings row, from the `usage` object the SSE parser used to discard: the
  parse reads usage **wherever a chunk puts it** (no version detection, and the
  empty-`choices` guard removes the latent `IndexError` the modern OpenAI shape
  would have caused), the window size comes from `/props` → `/slots` → the
  endpoint's `context_size` setting, and a server that answers neither shows a
  **dash, never a guessed number** — the denominator is the one place a chat can
  overflow and the user is told about it. The counts live on the `Chat` (a `Work`
  is built per send; `context` is the latest call's, never a sum) and never in
  `messages`, which are POSTed verbatim. DECISIONS 80; new ground-truth row
  `unit:endpoints` 343, the fifth dependency-listed suite. **Open for the owner**:
  the row's rendering at 80 columns (Selects 12/13/13 → 1/1/1, text clipped at
  84–97 of 80; at 120 it fits) — a rendering choice, measurement in the entry.
  Close-out verification: the automated headless suites; no screen here (TRAPS #22).

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

### P12 — token counts: how many are used, and how many exist (branch `task-token-counts-p12`, commits `c7e7d74`…`a643666` + this close-out, awaiting the owner's merge)

**Owner gate.** The owner approved the proposal and gave the `Go!` on 2026-09-22,
with the instruction that the code be implemented step by step, one file per step,
agents chained by fenced handoff messages. That once-per-task `Go!` covered **every**
code step of this entry (DECISIONS 71 (c)); step 6 — this close-out — touches no code
and asks nothing. `main` (`bf55d39`) untouched throughout, nothing pulled, nothing
pushed; the branch is the owner's to merge, as always. Full record: **DECISIONS 80**.

**What landed, step by step** (code commits; each step also left a State doc commit:
`70c0603`, `84cd240`, `19a6c0b`, `b3ee808`, `88309d1`, `a643666`).

- `c7e7d74` planning (on `docs-plan-token-usage-context-size`, the branch this one
  was cut from), `b799526` the entry move — and with it the commit whose copy of
  `endpoints/llamacpp.py` is the suite's pinned differential baseline.
- **Step 1** `a173854` — `endpoints/llamacpp.py`: `extract_fields` is a no-op on
  empty/missing `choices` (the latent `IndexError` that would have killed the stream
  the day a server sent the modern usage-chunk shape); `usage` is read per chunk
  **before** anything touches `choices` and kept on `self.usage` (reset at every
  `stream()` start); `prepare_payload()` sends `stream_options:
  {"include_usage": true}` with one retry **without** the flag on a 4xx (never lose
  a reply over counting); never-raising `get_context_size(endpoint, model=None)`
  with the chain `/props` → `/slots` → `context_size` override → `None`;
  `"context_size"` joins the `construct_payload` skip list.
- **Step 2** `b7d06ac` — `Chat.token_usage = {"context", "generated", "cached"}`
  (`chat.py:40`), fed by `Work.harvest_usage()` right after every `await
  self.endpoint.stream()`, the tool-loop recursion included: `context` = the LATEST
  call's prompt+completion (never summed — the next prompt already contains the
  previous answer and the tool results), `generated` += completion, `cached` =
  latest `cached_tokens` for THAT read. `messages` untouched.
- **Step 3** `304530a` — the endpoint gets `context_size` (`uinteger`, 0 =
  auto-detect, modelled on `timeout`), the honouring logic staying step 1's.
- **Step 4** `756179d` — the counts row: a `Label` **mounted LAST** in
  `ChatSettings.on_mount` (load-bearing: `self.selects` and the file's
  `children[1/3/5]` index by position), text `ctx <used> / <n_ctx> · gen
  <generated> · cached <cached>`, `count_or_dash()` rendering `None` as a dash and
  never a number, `context_sizes` cached per `(endpoint, model)` with the answer
  filed under the pair its probe was STARTED for, `refresh_usage()` the public seam
  called at endpoint/model change and at stream end — through `chat/callback.py`'s
  signal-0 branch, because a sibling never hears the `StreamCallback` (DECISIONS
  80 (e)) — with the `endpoint_list()`-membership guard keeping `get_context_size`
  away from the `{}` the smoke stub answers, and the probe running in its own
  worker `group="context-size", exclusive=True` (measured: `exclusive` without a
  group cancels `update_models()` and its server wait).
- **Step 5** `eef3045` + `76e0dd2` — `spit_app/tests/unit/endpoints/`, **343
  checks**, the fifth dependency-listed suite (TRAPS #19: gates httpx + textual,
  FAIL + remedy, never a silent zero), five check files on one canned
  `http.server` bound to `127.0.0.1` port 0, the differential's OLD side pinned by
  sha from the git object with `baseline_selfcheck()` ahead of every comparison,
  plus `doc/TESTING.md`'s row and its two new differential rules (item 5: pin the
  baseline by sha; item 6: check the instrument by substituting the defect — both
  learned by running, both in DECISIONS-adjacent prose of the step-5 commit).
- **Step 6** this close-out: DECISIONS 80, the PROJECT.md Features row + the
  unified-KV sentence, the P12 flip to DONE in `TASKS-PLANNED.md`, the entry
  deleted from `TASKS-IN-PROGRESS.md` with its banner rewritten to ONE open
  entry. No app code, no test changes.

**Two recoveries mark the chain** (recorded so the numbers above are trusted as
re-measured, not inherited): step 4's session died with the code uncommitted and
its State fields still describing step 3 — the next agent re-measured (six
byte-identical full-suite runs, probes green, golden md5 unmoved), committed it,
and that recovery is what found the 80-column limit below; step 5's session died
while finishing its docs, and the tree at `76e0dd2` was again re-measured (two
byte-identical runs, md5 `ddafccf8f3a6696d149ae33c0a49e5e7`) before its notes
were committed as `a643666`.

**Deviations, collected in one place** (each already in its commit body, stated
loudly there). Step 1: **(D1)** a refusal of `stream_options` is NOT remembered
per endpoint — `Work` deepcopies the endpoint dict per send, so remembering there
dies with the `Work`; cost: a refusing endpoint pays one extra request per send,
never a lost reply. **(D2)** `native_address()` strips the trailing `/v1` only
when present (the old rule of record was a blind `[:-3]`); identical for every
URL the app builds. **(D3)** `get_models`' auth-header lines were extracted to
`auth_headers()` because `get_context_size` needs the same rule; `stream()`'s own
header block was left as HEAD wrote it. Step 4: **(D1)** the refresh is wired in
`chat/callback.py`, not `chat_settings.py` — the step named one file and the
sibling-never-hears-message fact is why it could not be (80 (e)). **(D2)** the
figures render RAW, not in the proposal's `4.7k` form — what the 80-column limit
below costs. **(D3)** `refresh_usage()` also fires on a `model_settings` change
(not part of the cache key): one redraw, no probe. Step 5: **(D1)** NO row was
added to `spit_app/tests/run_tests.sh` — it globs `unit/*` and prints the
`unit:endpoints` row by itself; a hand-written row would print the suite twice.
**(D2)** `t10`/`t11` share `counts_harness.py` — the Work stand-in and the stub
app are the same two objects, and one dependency gate covering both files is
what TRAPS #19 asks for.

**Accepted limits** (none to be "fixed" without the owner's word): `token_usage`
is session state — `write_chat_history` still writes only ctime/settings/messages,
so a reloaded chat starts at zeros; an endpoint saved BEFORE `context_size`
existed shows no Context Size field (settings read `endpoints.json` verbatim; the
override is the third rung and is read with `.get()`); and the refusing endpoint's
one extra request per send (D1 of step 1).

**The one open question, left for the owner — the counts row at 80 columns.**
Measured at 80×24 through an app that mounts the repo's own `styles.css`
(TRAPS #24): the three Selects of the settings row are **12/13/13** columns
before P12, **3/3/4** with this Label and a zeroed chat (the 28-column text ends
exactly at column 80), and **1/1/1** with a running chat's figures, whose
39–47-column text ends at 84–97 of the 80 available and is **clipped**; at 120
columns the row fits and the Selects keep 10–14 each. The relief is a rendering
choice — k-abbreviation, CSS leftover width + ellipsis, or a row of its own — and
it is a code change plus a taste call, so nothing was changed for it and this
close-out changes nothing (a k-form invented by an agent is a different lie from
the one `count_or_dash()` refuses). `t11` asserts STRUCTURE, not spelling,
precisely so the owner's answer will not have to keep today's text. DECISIONS 80
(f) carries the same numbers.

**Which verification the close-out rested on, plainly.** The **automated headless
suites**: `unit:endpoints` 343 (this entry's own row), `unit:chat_smoke` 168 with
its golden dump (md5 `8ae9d1186a59627d30d05dee95f0ad95`, unmoved across all six
steps — no re-pin was ever needed), `unit:chat_window` 568, the rest of the suite
green around them. This environment has **no screen**: nothing in P12 was verified
by looking at the running app (TRAPS #22), and no by-hand checklist is a condition
of closing. A by-hand look at the counts row in a real terminal (does it read
well, what should it render at 80 columns) is a **note for whoever next runs the
app**, folded into the open question above. The step-5 entry in the (now-deleted)
in-progress record was right that the `/tmp/p12_*` probes are historical — every
one of their checks is committed in `unit:endpoints`, and `p12_check.py` is a
known-lying differential (TESTING.md item 5 tells why); **do not recreate
`/tmp/p12_old_llamacpp.py`** — the pinned baseline is
`git show b799526:spit_app/endpoints/llamacpp.py` and the suite takes it from the
git object.

**Verified.** Full suite from the repo root at this close-out, run **twice**, the
two runs byte-identical to each other AND to the tree's recorded baseline
`ddafccf8f3a6696d149ae33c0a49e5e7` (stderr empty in every run): tools
127/24/30/119/80/32/68/29 and unit 68/131/168/568/343/33/278/121/157/223,
**FAIL 0 everywhere**. Step 6 adds no checks, so no row may move — none did, which
is itself the proof that the close-out wrote no code.

No sign-off step participated (DECISIONS 71); the branch awaits the owner's merge,
`main` untouched, nothing pushed. There is no handoff after this — step 6 was the
last step, and this entry is the record.

### P15 — the tool header with no tool under it (branch `fix-tool-prompt-header-p15`: `a83c42e` the planning docs, `b969e00` the fix; awaiting the owner's merge)

**Found while planning P13, and it is not P13's work** — filed as its own entry, `Go!`
asked and given separately, because it is a red in `main` that every later close-out in
this area has to read around.

**The red, measured.** At the tip `6bb1b62` ("chat: work: fix no tools selected") the
row is `unit:prompt: PASS: 32  FAIL: 1`, against the **33** `doc/TESTING.md` pins; the
failing check is `t6-mm_tool_without_the_capability_excluded`. Not environmental, and
not a stale expectation either: the same suite run from a clean tree of `6bb1b62^`
reports **PASS: 33  FAIL: 0** (whole tree exported with `git archive`, nothing else
touched). So the tip moved the code away from a rule the suite had already pinned.

**The cause, in one line.** `6bb1b62` moved

```python
prompt = TOOL_PROMPT + "\n\n".join(blocks)
```

*inside* `if self.cs("tools"):`. That changed the header's condition from **"a tool
block was built"** to **"a tool is selected"**, and those are different sets: a selected
tool still drops out of the assembly two lines below, because `req_mm_image()` filters a
multimodal tool out of a chat whose model has no image capability. The header then opens
a section with nothing in it. In the live app the same filter runs in `__init__`
(`tools_descs`) and `prepare_payload` sets `payload["tools"]` only when that list is
non-empty — so the request that went out told the model *"All of your function calls are
rendered in human-readable form for the user to inspect…"* with **no `tools` key in the
payload at all**: instructions to call functions that do not exist in that request. That
is why this is a bug and not a cosmetic prompt-shape preference.

**The fix** (`b969e00`): `blocks = []` hoisted above the `if self.cs("tools"):`, and
`if blocks:` guards the header. The commit that introduced the red was fixing a real
crash — an empty/None selection reaching `tool in self.cs("tools")` — and that guard is
kept exactly as it was; only the header's condition went back to the blocks. Two lines
of change, no new concept.

**Proved by differential, not by the green row** (TRAPS #18: a pinned check sees the one
case it pins). 20 cells of (tool table, selection, capability, user tool settings, chat
prompt) were run through **both** classes. The old side is **pinned by sha** —
`git show 6bb1b62:spit_app/chat/work.py`, exec'd into a module of its own — and *not*
`git show main:`, because the day this fix merges, `main` holds the fix and the old half
of the differential would quietly compare the new code with itself: the
`endpoint_harness.py` lesson, a differential that cannot fail is not evidence. The probe
carries its own self-checks for exactly that ("old side really is 6bb1b62 and NOT the
fixed file", "new side really is the fix", "`TOOL_PROMPT` the same on both sides"), all
three true:

- **15 cells byte-identical**, including the chat-prompt wrapping, the `## tool`
  headings, the `PROMPT_INST` substitution, user-settings precedence, prompts with
  trailing breaks, and a tool whose PROMPT is empty (heading-only block).
- **5 cells moved, and they are exactly the cells where the selection is truthy while
  zero blocks survive** — that set the probe computes a third time, independently of
  both implementations, and asserts against. Nothing with a surviving block changed.
- Among the 5 is a case the pinned test does **not** cover: a chat whose `tools` list
  names a tool that is no longer in the tool table at all also sent the header over
  nothing. The fix catches it; the suite would not have.

**Verified.** Full suite from the repo root after the fix, **stderr empty**: tools
127/24/30/119/80/32/68/29 and unit 68/131/168/568/343/**33**/278/121/157/223, **FAIL 0
everywhere** — every row at the numbers `doc/TESTING.md` already pins, `unit:prompt`
among them again. No check was added, deleted or re-pinned: the row went from 32+1 to 33
because the code moved to the test, which is the only direction that was allowed here
(the check was pinned before the regression existed).

**Left open, deliberately.** The duplication that let this drift in the first place:
`Work.__init__` builds `tools_descs` from the tool table and `Work.prompt()` re-applies
the *same* predicate a second time to build the blocks, so the two can disagree — that
is exactly the seam the header fell through. Unifying them (one pass, both results) is a
behaviour question about the tool table and one commit too big for a two-line fix, so it
is named here instead of being done quietly. `main` untouched, nothing pushed, and no
sign-off participated in closing this (DECISIONS 71).

### P13/WP-A — unpack system notes onto the wire as `user` messages (branch `p13-wp-a-note-unpacking`: `0afaef8` the code+test, then this close-out; awaiting the owner's merge)

**Owner gate.** The `Go!` was GIVEN 2026-09-25 for **WP-A alone**; WP-B/C/D/E have
no `Go!` and none was started. The branch was cut from the docs branch
`docs-p13-owner-rulings-handoff-wp-a` at its tip `1522932` — the entry's explicit
instruction, because that branch carries the owner's rulings (`user` role,
percentage-OR-remaining levels) and `main` still carries the superseded P13 text
(`system` role, 50/80/90%). `main` untouched, nothing pulled, nothing pushed.

**What landed** (`0afaef8`, one concern: the unpacking and the file that pins it).
`endpoints/llamacpp.py` — in `prepare_payload()`'s existing loop, the deepcopy now
starts with `notes = _message.pop("system", [])` (the private key is popped from
the **deepcopy**, never from the app's dict), and after the carrier is appended
each note is unpacked right after it through two new methods on
`LlamaCppEndpoint`:

- `append_note(out, carrier, note)` — carrier role `user` → merge the note text
  into the wire copy's content; carrier `tool`/`assistant` → append one
  `{"role": "user", "content": note["text"]}` item. The comment on it is the
  *why*: a note rides the wire as `user`, never `system` (strict templates —
  Qwen3.x and friends — `raise_exception` on a mid-conversation `system`, owner
  ruling 2026-09-25), and a `user` carrier merges because `user` buys the
  alternation family's rule instead (mistral-instruct, gemma-it raise on two
  consecutive `user` messages) — hazard 1. **Do not "simplify" the merge into
  always-appending**; that reproduces the defect on the alternation templates.
- `merge_into_content(carrier, text)` — onto the LAST `{"type": "text"}` part of a
  list content, a new text part when the list has none (image-only multimodal),
  `\n\n`-append on a plain string; `None`/missing/empty content ends as the text
  itself, never `"None"` and never a leading separator.

Nothing else moved: no Chat, no Work, no UI, no settings surface, no new endpoint
field, no writes into `chat.messages` — its length and order are the index space
the UI addresses (P13's constraint), and the stored dicts keep both their `system`
entry and their own content byte-identical (the deepcopy argument, checked).

**The test.** New file `spit_app/tests/unit/endpoints/test_system_note.py`, owns
**t12** (append-only, TRAPS #15), **51 checks** in the ten groups the entry
prescribed, written first and run red against the unpatched code (19 of the 51
failed before the helper existed). Among them: the merge-count equality carries
the tool-carrier control that makes it fail-able (TRAPS #13); the private-key
absence is asserted on the key SET of every wire message; and the proof proper —
the no-note payload **byte-identical to the pinned baseline `b799526` apart from
`stream_options`** (TRAPS #14, behind `baseline_selfcheck()`, with the control
that one note DOES move it off the baseline, so the byte-identity cannot pass on
a code path that ignores notes). `hook`/`level` are pinned off the wire; the
leading `system` prompt stays at index 0; the `tool_calls` adjacency (hazard 2)
is pinned as a consequence, including a note on an assistant carrying
`tool_calls` landing after the whole message.

**Deviation from the entry's scope note** (stated, not quiet): the entry allowed
"**one** new helper method"; the implementation has **two** — `append_note()` and
its merge split out as `merge_into_content()`, exactly as the entry's own code
sketch showed both. Same concern, same file, WP-D still has one thing to call.

**Verified.** Full `bash spit_app/tests/run_tests.sh` from the repo root: **every
row at the `doc/TESTING.md` numbers except `unit:endpoints` 343 → 394** (= 343 +
51, the five existing files byte-for-byte at 88/132/61/19/43), FAIL 0 everywhere,
exit 0. `chat_smoke`'s `golden.txt` md5 `8ae9d1186a59627d30d05dee95f0ad95`
unmoved — nothing in WP-A can reach the UI, and it did not. `unit:prompt` 33.
`git status` before the docs commit: exactly the two intended paths. The close-out
rested on the automated suites — there is no screen and no live endpoint in this
environment (TRAPS #22), and the byte-identity against `b799526` is the automated
analogue of "no live endpoint sees a format change from this commit".

No sign-off step participated (DECISIONS 71); `main` untouched, nothing pushed.
**Written when this entry closed:** next in P13 was WP-B (the generator and the
hook contract), and nothing beyond WP-A was authorised at that moment. **Superseded
minutes later the same day by the owner's chain instruction** (quoted verbatim in
the "P13/WP-B" entry of `TASKS-IN-PROGRESS.md`): WP-B got its `Go!`, each finisher
writes the next handoff message, WP-B…WP-E all land on `p13-wp-a-note-unpacking`,
and the owner merges that branch to `main` after WP-E — so the merge note above now
means: the whole P13 chain merges as one branch, at the owner's hand, at the end.


### P13/WP-B — the system-note generator and the hook contract (branch `p13-wp-a-note-unpacking`: `a6ec179` the code+test, `7046bcb` the TESTING.md row, then this close-out; awaiting the owner's merge)

**Owner gate.** The `Go!` was GIVEN 2026-09-25 for **WP-B**, together with the
owner's chain instruction (quoted verbatim in the entry this closes): each finisher
writes the next handoff message, everything lands on `p13-wp-a-note-unpacking`,
and the owner merges that branch after WP-E. Worked **on** that branch at its tip
`4638c50` — no new branch, `main` untouched, nothing pulled, nothing pushed. WP-C
is opened by this close-out and nothing in WP-B was started on its behalf.

**What landed** (`a6ec179`, one concern: the generator and the file that pins it).

- `spit_app/chat/system_note.py` — NEW. `class SystemNotes` with `__init__(chat)`
  and `attach()`; a module `HOOKS` list; a module `Note(level, text)` namedtuple;
  `NOTE_KEY = "system"`. `attach()` walks `chat.messages` by index, asks every
  hook at every position, and writes what a hook says **into the message dict at
  that index**, under the private key, as a `{"hook", "level", "text"}` entry —
  exactly the shape `unit:endpoints` t12 (WP-A) unpacks from the other side. The
  messages **list** is never touched: no insert, no append, no copy of the list,
  so its length and its dict identities survive — P13's constraint, and WP-A's
  premise. It imports `namedtuple` and nothing else: no Textual, no httpx, no
  sibling of `chat/` (TRAPS #19), which is what makes the new suite bare-run.
- Nothing else moved. No `Chat`/`Work` wiring (WP-D), no token-status hook and no
  note texts (WP-C), no endpoint file touched, no UI, no settings.

**THE CONTRACT DECIDED (the entry asked for a decision, not a re-litigation).**
`notice(chat, messages, index)` returns **`Note(level, text)` or `None`**; the
generator stamps `hook` itself.

- *Why not bare text:* the stored entry needs a `level`, and WP-C's levels are
  state-machine output, not per-call arguments — a hook picks its level at the
  moment it speaks, so the level has to travel in the return value. A bare-text
  contract would force the generator to invent a level, which is the generator
  speaking for the hook, and would silently store a level no hook chose.
- *Why `hook` is not in the return value:* who spoke is provenance. A hook cannot
  be allowed to say it was somebody else, and it cannot be allowed to be
  anonymous either — the stamp is the hook's `name` if it carries one, else its
  class name, so `notice()` stays the only requirement on a hook (t9).
- *Why that is the narrowest thing that keeps all five invariants true:* (a) and
  (d) are about the walk and the list and do not constrain the return at all; (c)
  needs a silence value, which `None` is; (e) needs nothing swallowed, so the
  refusal of a malformed return is an exception rather than a shrug; and (b) needs
  a key to match "already spoke here" against, which is the stamped name — so the
  level is the only field the hook must supply and the name the only one it must
  not.
- *Idempotence stores nothing on the generator:* `already_spoken()` reads the
  notes standing in the message dict. So (b) holds across `SystemNotes` instances
  (WP-D builds one per chat, requests come and go) **and across a chat reload** —
  notes persist with the chat while `token_usage` does not, which is P13's first
  consequence, and a re-arming hook meeting its own old note leaves it alone (t3).
- *Two consequences pinned rather than left to taste:* the emptiness test is
  `not text`, not a strip (dropping `" "` would be the generator editorialising
  over a hook's words — t4); and a raising hook leaves what it already wrote
  written (no rollback: the note was true when it was written, and the failure
  belongs to the request — t6). A `notice()` return that is neither `None` nor a
  `Note` raises `TypeError` **naming the hook**, because on a module-level `HOOKS`
  list shared by every chat, "not a Note" would send the next agent to the wrong
  file (t8).

**The test** (`spit_app/tests/unit/system_note/`, `run_tests.sh` +
`test_generator.py`, owns **t1–t9**, its own append-only sequence — TRAPS #15; the
`unit:endpoints` numbers are a different sequence and t13 there is WP-D's). Written
first and run against a red — stated as measured, because it was NOT a tidy wall
of reds: with the module absent the file dies at its `import`, and the runner
reports that as `PASS: 0  FAIL: 1` naming the file that never reached its summary
line (re-measured at this commit by moving the module aside). So the red that
proved the checks were real is the mutation list below, not that first run, and
t1's own "imported the repository's own module" could not even be reached until
the module existed. **96 checks**, and every group
verified red by **substituting its defect** rather than assumed
(`git`-restored mutations, one at a time): the walk skipping the tail and asking
only the first hook (t2), dropping the idempotence guard and keying it on
hook+level instead of the hook (t3), writing an empty `system` key on silence and
writing empty text anyway (t4), appending a note as a message (t5, 35 reds),
`except:`-ing the raise (t6), accepting any return / accepting bare text (t8),
dropping the name fallback and ignoring the `name` (t9), and snapshotting `HOOKS`
in `__init__` instead of reading it in `attach()`.

**The venv gate, measured both ways** (TRAPS #19 inverted). The runner has no
preamble at all, and t1 asserts no `textual`/`httpx`/`libtmux` ever lands in
`sys.modules`. With an `import textual` added to the module: on the **bare**
interpreter the file dies, and the runner reports it as `PASS: 0  FAIL: 1` naming
the file that never reached its summary line — so the row cannot read as a silent
zero, which is the failure mode `39ceb2f` fixed for discarded failures and which
the outer `tail -n 1` would otherwise hide (TRAPS #18); under `~/.venv-spit`, where
that import cannot kill the file, the red is
`t1-importing-it-loaded-no-app-dependency` instead. Two small deviations, stated:
the runner differs from the nine bare suites in that it counts a file which died
before printing its summary as **one failure** (a weaker version would report
`PASS: 0  FAIL: 0`, i.e. "measured nothing", from a suite that could not start),
and the generator has two helper methods (`write()`, `already_spoken()`) beside
`attach()` — WP-D still has one thing to call, and the entry's sketch did not
forbid a split.

**Verified.** Full `bash spit_app/tests/run_tests.sh` from the repo root, **exit 0,
stderr empty, every row at the `doc/TESTING.md` numbers plus the one new row**:
tools 127/24/30/119/80/32/68/29 (509), anchored 68, arguments 131, chat_smoke 168,
chat_window 568, endpoints **394** (WP-A's pin, unmoved — the generator was never
wired to it), prompt 33, render 278, run_script 121, sandbox 157, terminal 223,
**system_note 96**; two consecutive full runs byte-identical; `chat_smoke`'s
`golden.txt` md5 `8ae9d1186a59627d30d05dee95f0ad95` unmoved (nothing of WP-B
reaches the UI, and it did not). `git status` before each commit: exactly the
intended paths, `__pycache__` not committed.

**One flake found, in a suite WP-B does not touch — recorded, not fixed.** During
verification `unit:sandbox` reported **156/1** on one full run:
`t3-child-stopped` (`test_lifecycle.py` §3) asks `alive(pid)` once, immediately
after `proc.wait()`, with no ceiling — an orphaned `sleep 30` whose reap has not
happened yet still answers `kill(pid, 0)`, so the check races the kernel. Measured:
2 reds in 15 standalone runs of that file and 1 in 4 full runs under load, 0 in 25
further standalone runs at `7046bcb`, i.e. load-dependent and pre-existing — proven
pre-existing by `git diff --stat 4638c50..HEAD -- spit_app/tests/unit/sandbox
spit_app/tools spit_app/tests/run_tests.sh` being **empty**: the byte-content of
every input of that suite is identical to the parent of this WP. It is the same
class DECISIONS 73 wrote down (synchronise to the state, not to your clock), and
the fix belongs to whoever is `Go!`d for the sandbox suite, not to WP-B — so it is
filed nowhere here (WP-B's scope named its three doc/code targets and this is not
one of them), stated in the close-out and repeated in the WP-C handoff so the owner
can decide. **Every full-suite run quoted above as green is green including that
row.**

No sign-off step participated (DECISIONS 71); `main` untouched, nothing pushed. The
close-out rests on the automated suites — there is no screen here (TRAPS #22) and
nothing of WP-B is wired into the UI, so the automated analogue of "the app is
unchanged" is the unmoved `chat_smoke` golden plus the 17 unmoved rows.

**Written when this entry closed:** next in P13 is **WP-C**, the token-status hook —
the four percentage-OR-remaining levels of the owner's ruling, the four texts
pinned word-for-word, and the 32k announce-order where `info` is shadowed forever.
Its entry is open in `TASKS-IN-PROGRESS.md`; **WP-D and WP-E have no `Go!`** and
WP-C does not authorise them. Handoff: `spit_app/tests/HANDOFF-WP-C.txt`.

### P13/WP-C — the token-status hook: the four levels and their four texts (branch `p13-wp-a-note-unpacking`: `6f1a0ed` the code+test, `ad56e2d` the TESTING.md row, then this close-out; awaiting the owner's merge)

**Owner gate.** The `Go!` was GIVEN 2026-09-25 for **WP-C**, by the owner's chain
instruction arriving through WP-B's handoff message
(`spit_app/tests/HANDOFF-WP-C.txt`). Worked **on** that branch at its tip
`afd9733` — no new branch, `main` untouched, nothing pulled, nothing pushed.
WP-D is opened by this close-out with its own handoff message; WP-E stays
unauthorised until that finisher's message arrives.

**What landed** (`6f1a0ed`, one concern: the hook and the file that pins it).

- `spit_app/chat/token_status.py` — NEW. `class TokenStatus` with
  `name = "token_status"` (the name WP-B's generator stamps and keys its
  once-per-message rule on) and `notice(chat, messages, index)`. The level
  state machine and the four texts, and nothing else: the owner's levels as
  module constants (`32768 / 0.5 / 20000 / 10000`, plus the table's `0.8 /
  0.9`), the three ranks (`info` 1, `warning` 2, `critical` 3, `small_window`
  deliberately not a rank), and the four texts verbatim from the PLANNED
  drafts. It imports `Note`, `NOTE_KEY` and `hook_name` from WP-B's
  `system_note` and nothing else — no Textual, no httpx (TRAPS #19), which is
  what keeps the suite bare-run.
- Nothing wired it: `HOOKS` stays empty, `Chat` and `Work` untouched, no
  endpoint file, no settings, no UI. An unregistered hook changes no behaviour
  and breaks no golden — which is exactly the WP-C posture, and the two
  byte-identical full runs below are the proof it held.
- `spit_app/tests/unit/system_note/test_token_status.py` — NEW file **inside
  WP-B's suite**, owns **t10–t18** (its own append-only sequence, TRAPS #15 —
  t1–t9 stay WP-B's, `unit:endpoints` keeps its separate numbers, t13 there
  stays WP-D's). No new suite directory, no new row: the runner's existing
  glob picked the file up and the existing row moved 96 → **219**.

**THE DECIDE the entry asked for — how the total reaches the hook** (stated in
the handoff as instructed): the hook asks the chat for
**`chat.context_window()`** with `getattr` — callable-or-not, present-or-not —
and treats every non-answer (no attribute, non-callable attribute, `None`,
zero, a negative, a string, a float, a `True`) as *window unknown ⇒ silence*.
Why this shape: the accessor is WP-D's (`Chat.context_window()` over
`ChatSettings.context_sizes[context_key()]`) and WP-C must not build it early;
the duck-typed ask is the narrowest thing that lets the hook be tested against
a stub chat *and* keeps `token_status.py` out of `Chat`'s and Textual's import
graph — the same posture as WP-B's one-attribute `MMChat` (a hook is handed
only what it asks for), and it makes "chat predates WP-D" and "endpoint
reported no window" one rule instead of two. WP-D adds the accessor and wires
the hook with **zero changes to `token_status.py`**.

**The second design decision, taken inside the code but stated in the module's
docstring:** the hook keeps **no state on itself**. Its memory is its own
standing notes — a scan of the message list for entries stamped
`hook == "token_status"` (resolved through `hook_name()`, so the scanner and
the stamp can never disagree). That is WP-B's own principle — *the note IS the
record* — pushed into the hook, and it is what makes the three awkward walks
fall out for free instead of needing bookkeeping: a **reload** (fresh instance,
notes persisted, counts reset — P13's consequence 1) never re-announces an
announced rank; an **abort** (the tail's note removed with the tail —
consequence 3) re-arms the hook exactly as the entry promises; and a verdict
the generator **drops** (the hook already spoke on that message) left no
record, so it is not lost to a remembered-but-unwritten rank — it rides the
next message (pinned by t17). An instance-memory state machine would have had
to re-sync against the history anyway at exactly these three points; deriving
the state from the history instead makes the question not arise, and it also
means a shared instance cannot cross-contaminate two chats.

**The texts, pinned.** Model-facing text is code: the four drafts of
`doc/TASKS-PLANNED.md` (ruling iii — wording delegated, re-pinned when the
owner revisits) sit in the module and are pinned **byte-for-byte** in t16 at
fixtures where `{used}`, `{total}`, `{remaining}` and `{pct}` are pairwise
distinct (111200/200000/88800/56 and neighbours), so a used-vs-remaining or
used-vs-total swap cannot pass; the em-dashes are pinned bytes too. The
"do not call any more tools and do not start new work after the handoff" half
of `critical` — the load-bearing half the owner learned the hard way — is
inside its pin, and P14's fenced-block replacement will re-pin the same way
(ruling iv). One choice made here and pinned rather than left implicit: the
figures are **never clamped** — an overrun (`used > total`, measured by t16)
says 101% and a negative remaining, because the numbers are the server's and
a rounded-down last word is a lie about the same kind the dash rule exists to
prevent.

**The test** — 123 checks, written first against a red; stated as measured,
and the red was again NOT a wall: with the module absent the file dies at its
`import` and the WP-B runner reports `PASS: 96 FAIL: 1` naming it (the "died
before reporting" branch, re-used, not rebuilt). What makes the checks real is
the mutation battery: **fifteen defects substituted one at a time** into
`token_status.py`, each reddening its group and restored from a pristine copy
— `remaining→used` and `used↔total` text swaps (t16), `pct` floor-instead-of-
round and a `max(0, …)` clamp (t16), levels tested in trigger order instead of
highest-first (31 reds incl. the t14 announce-order and every t11 control that
expects the highest verdict), the rank filter dropped (20 reds incl. the
70 000/78 000 non-events of the t12 walk), the tail guard dropped (5 reds),
`small_window` strict-less (`32768` no longer small: 14 reds), `small_window`
repeating (7 reds), and each totality guard dropped in turn (positive-total,
int-only total, callable-accessor, dict-counts, int-only counts, and the
name-key on the rank scan — each reddening exactly its t18 rows). Two
vacuous-subcheck finds during the battery, fixed in the test before the code
was believed: `{"context": True}` as *used* cannot discriminate (1 is below
every trigger either way) so the bool case moved to the **window** side where
accepting it would speak (a window of one token ⇒ instant `critical`), and the
float `used` fixture was moved from 12.5 to 120000.5 for the same reason (a
float that would stay silent below every trigger tests nothing). The TRAPS #19
gate was measured again both ways for the new module: with an `import textual`
added, the bare interpreter run reports `PASS: 96 FAIL: 1` naming the dead
file, and a run under `~/.venv-spit` reddens
`t10-importing-it-loaded-no-app-dependency` instead.

**Verified.** Full `bash spit_app/tests/run_tests.sh` from the repo root,
**exit 0, stderr empty, two consecutive byte-identical runs, every row at the
`doc/TESTING.md` numbers except the one row that had to move**: tools
127/24/30/119/80/32/68/29 (509), anchored 68, arguments 131, chat_smoke 168,
chat_window 568, endpoints **394** (WP-A's pin, unmoved — the hook is not
registered), prompt 33, render 278, run_script 121, sandbox **157** (the
pre-existing `t3-child-stopped` reap flake did not fire in either run — and it
is not WP-C's to fix, per the entry), terminal 223, and **system_note 96 →
219** = 96 + 123, exactly the new checks, `test_generator.py`'s 96 green
alongside every single time (the contract was never bent — a red in that file
is the one thing this handoff forbade and it never appeared). `chat_smoke`'s
`golden.txt` md5 `8ae9d1186a59627d30d05dee95f0ad95` unmoved. `git status`
before each commit: exactly the intended paths. The close-out rests on the
automated suites — there is no screen here (TRAPS #22), and nothing of WP-C
reaches the UI or the wire, so the automated analogue of "the app is
unchanged" is the unmoved golden plus the 17 unmoved rows.

No sign-off step participated (DECISIONS 71); `main` untouched, nothing pushed.

**Written when this entry closed:** next in P13 is **WP-D**, the wiring —
`Chat.__init__` builds the `TokenStatus` and `SystemNotes` (session state,
next to `token_usage`, for the DECISIONS 80 c reason), `Chat.context_window()`
lands (the accessor the hook already asks for), `attach()` goes immediately
before `await self.endpoint.stream()` in `Work.work_stream()`, and
`unit:endpoints` **t13** proves the chain end to end over the canned server.
Its entry is open in `TASKS-IN-PROGRESS.md`; **WP-E has no `Go!`** and WP-D
does not authorise it. Handoff: `spit_app/tests/HANDOFF-WP-D.txt`.

### P13/WP-D — the wiring: `Chat` builds the hook, `Chat.context_window()`, `attach()` before `stream()`, t13 end to end (branch `p13-wp-a-note-unpacking`: `bcdc441` the code+test, `dadc11b` the TESTING.md row, then this close-out; awaiting the owner's merge)

**Owner gate.** The `Go!` was GIVEN 2026-09-25 for **WP-D**, by the owner's chain
instruction arriving through WP-C's handoff message
(`spit_app/tests/HANDOFF-WP-D.txt`). Worked **on** that branch at its tip
`4ee19d0` — no new branch, `main` untouched, nothing pulled, nothing pushed.
WP-E is opened by this close-out with its own handoff message; it is the last
package, and **its finisher writes a close-out, not a handoff** — after WP-E
the branch `p13-wp-a-note-unpacking` awaits the owner's merge.

**What landed** (`bcdc441`, one concern: the wiring and the file that pins it).

- `spit_app/chat/chat.py` — `Chat.__init__` gains `self.system_notes =
  SystemNotes(self)` (per-chat: the generator is bound to its chat's messages)
  and `self.token_status`, next to `self.token_usage` for the DECISIONS 80 c
  reason — a `Work` is built per send, so the note chain must live on the
  `Chat`. `Chat.context_window()` added:
  `self.chat_settings.context_sizes.get(self.chat_settings.context_key())` —
  the counts row's own source, **read as it stands**: no probe, no network on
  the request path (the caller is the hook immediately before
  `endpoint.stream()`, and `get_context_size` is two 3 s GETs); never-asked
  and asked-and-refused are both the dash and answer `None` (DECISIONS 80 b).
  `token_status.py` was **not touched**: it asked for exactly this accessor
  with `getattr` at WP-C, and it needed zero changes — the t10–t18 123 checks
  went on passing, unedited, against the wired `Chat` through the stub.
- `spit_app/chat/work.py` — `self.chat.system_notes.attach()` **immediately
  before** `await self.endpoint.stream()` in `work_stream()`. The position is
  load-bearing and the comment says so: the tool loop re-enters
  `work_stream()`, so the hooks are asked before EVERY request, including the
  ones inside a tool loop where the window actually fills; and a note written
  at that position rides the payload being built next — into the same
  request's `messages`, via WP-A's unpacking. Nothing catches a hook that
  raises (WP-B's invariant e), which is why the hook is total.
- `spit_app/tests/unit/endpoints/test_note_chain.py` — NEW, owns **t13**
  (TRAPS #15: `unit:endpoints` numbers stay append-only; t1–t12 files
  untouched). 48 checks, `unit:endpoints` **394 → 442** — by addition alone,
  the six earlier files green at 88/132/61/19/43/51 every run.

**THE DECIDE the entry asked for — where the hook is registered** (stated in
the handoff as instructed): **the module `HOOKS` list**, not a per-chat
registration. `chat.py` does `TOKEN_STATUS = TokenStatus();
HOOKS.append(TOKEN_STATUS)` once, at its import. The reason is WP-C's own
construction: `TokenStatus` keeps **no state about which chat** — its memory
is its standing notes in whatever messages it is handed — so one instance is
not a compromise but the natural shape ("a shared instance across chats
cannot cross-contaminate them: the memory travels with the messages", WP-C,
`token_status.py`); a per-chat registration would put N entries into the list
every `attach()` asks, N identical verdicts per message, and the generator's
name-keyed idempotence would drop N−1 of them — N times the asking for zero
behaviour, plus one more registration point where `system_note.py` is the one
the contract already declares (its own comment anticipated the hook joining
the module list; WP-C left the list empty only to stay inert). **What it
means for instances:** every chat carries the *same* hook reference
(`chat.token_status is HOOKS[0]`, pinned by t13), a second chat registers no
second entry (pinned), and the generator — the part that is per-chat state —
is per-chat and bound (pinned). There is no chat built "before" the
registration: the hook is appended at the import of the module that defines
`Chat`, and `attach()` reads `HOOKS` per call in any case, which is the
mechanism by which import-time registration reaches every chat.
`system_note.py` and `token_status.py` stay inert on the bare interpreter —
the registration lives in a module they never import (TRAPS #19, gate re-run:
219 unmoved, every run).

**What t13 proves, and where the controls are** (TRAPS #13 — every absence
has the control that puts a note in the same body): under threshold, no note
in the recorded POST body and the app-list carries no private key — control:
the same chat at 60% carries **exactly one** note, `TEXT_INFO` byte-for-byte
with the exact figures, as its own `user` item immediately after the carrier,
`role`+`content` only, no consecutive-`user` pair; a second request at the
same level adds none and the old note still rides in its history position —
control: raise to 85% and the same walk writes the `warning` (the rank machine
on the wire), and back at 60% nothing re-announces (never downgrades, `info`
never twice). The UI's `chat.messages` grows by exactly the streamed replies:
the first five fixture dicts keep their identities, no note ever becomes an
item, and the `ChatView` still projects the same list object. Hazard 1 **on
the wire** (not only in the helper as t12): with a `user` tail the note is
MERGED — the request's message COUNT is the same with the note (3) as without
it, and the control that it is really there is the note text inside the
carrier's own content. `context_window()`: answers `None` while the pair is
unknown and the int once it is; the unknown window answers **silence even
over threshold** and the request lives — control: fill the same chat's cache
and the very next body carries the note; and filling it costs **no probe**
(`window_gets` empty after reset): the accessor reads, it does not ask.

**The fixtures are loaded, not guessed.** The canned scenario is `content` —
a text reply with **no usage chunk** — so `harvest_usage()` never moves a
hand-set fill and every level in the file is exactly the figure set; the
mount's own `ChatSettings` probe (the canned scenario 404s both routes, so it
caches `None` — which is also the unknown-window fixture) is **awaited before**
the test writes the window, so no late probe can clobber it; the stub app is
t11's `StubEndpointApp` extended only with the `slots` dict and `path` a real
`Work` asks — `ChainApp`, nothing else. The window (200000) is chosen in
percentage territory so no remaining-token floor and no `small_window` note
can confound the level checks (WP-C's table).

**Verified red before green, and against substituted defects.** The file ran
against the un-wired tree first: **3/48**, the greens being the checks that
hold vacuously only before the code exists (no note on the wire, no private
key) and every load-bearing check red, ending in `'Chat' object has no
attribute 'context_window'`. Three defects then substituted one at a time
(restored after each): `attach()` moved **after** the stream → **8 reds**
(every position check, every note check — the note arrives one request too
late, which is the defect the load-bearing position exists to prevent); the
accessor **guesses** `or 131072` when unknown → **3 reds** (the accessor
answer and both unknown-window rows — the dash must stay a dash); a
**per-chat registration** (each `Chat` appends its own `TokenStatus`) → **3
reds** (the hooks-list shape, the second-chat row, and the shared-reference
row — the rejected alternative cannot pass the pinned decision). `git status`
before each commit: exactly the intended paths.

**Verified.** Full `bash spit_app/tests/run_tests.sh` from the repo root,
**exit 0, every row at the `doc/TESTING.md` numbers except the one row that
had to move**: tools 127/24/30/119/80/32/68/29 (509), anchored 68, arguments
131, chat_smoke 168, chat_window 568, prompt 33, render 278, run_script 121,
sandbox 157, terminal 223, **system_note 219 unmoved on the bare
interpreter** (test_generator.py's 96 AND test_token_status.py's 123, both
files untouched — the wiring never entered the bare import graph), and
**endpoints 394 → 442** = 394 + 48, exactly the new checks. `chat_smoke`'s
`golden.txt` md5 `8ae9d1186a59627d30d05dee95f0ad95` **unmoved** — the golden
hazard this WP inherited from WP-C: the smoke fixture keeps `token_usage` at
zero and its `context_sizes` never fills (its stub app answers
`endpoint_list()` with `{}`, so no probe ever starts), so
`context_window()` answers `None` there and the wired hook is silent by the
unknown-window rule — and `work_stream()` is not in the smoke script at all
(it drives a `FakeWork`); the silence was proven, and the hook spoke nowhere
it should not have. The pre-existing `unit:sandbox t3-child-stopped` flake
did not fire in any of the ~30 full-suite and per-suite runs of this sitting
(WP-B measured it; not WP-D's, unfixed, booked nowhere). The close-out rests
on the automated suites — there is no screen here (TRAPS #22).

No sign-off step participated (DECISIONS 71); `main` untouched, nothing pushed.

**Written when this entry closed:** next in P13 is **WP-E**, the last package,
docs-only: **DECISIONS 81** (the note-in-the-message-dict contract and why not
an index; once-at-the-tail and the prefix-cache argument; silence when the
window is unknown; the owner's role ruling and the `user`→`user` merge; the
percentage-OR-remaining levels and the rank machine; the strict-template
evidence; the residual abort-then-type limit), cross-linked from DECISIONS 80,
the TESTING.md ground truth (already 442/219 from this WP's row move),
`PROJECT.md`, and the P13 PLANNED entry closed. **Its finisher writes no
handoff** — its close-out says the chain is complete and the branch awaits the
owner's merge. Its entry is open in `TASKS-IN-PROGRESS.md`. Handoff:
`spit_app/tests/HANDOFF-WP-E.txt`.

### P13/WP-E — the docs: DECISIONS 81, the cross-links, PROJECT.md, TESTING.md's post-wiring sentence, P13 closed and its four follow-ups filed (branch `p13-wp-a-note-unpacking`: `67054f2` the docs, then this close-out; the whole branch awaits the owner's merge)

**Owner gate.** The `Go!` was GIVEN 2026-09-25 for **WP-E**, by the owner's chain
instruction arriving through WP-D's handoff message
(`spit_app/tests/HANDOFF-WP-E.txt`). Worked **on** that branch at its tip
`9e13314` — no new branch, `main` untouched, nothing pulled, nothing pushed.
**This is the last package of P13 and its finisher writes no handoff**: the
close-out below is the end of the chain (see "The chain is complete").

**What landed** (one docs commit, one concern: the decision record — **no code,
no test file, no check moved, no row moved**).

- **`doc/DECISIONS.md` — 81 written, and 80 cross-linked to it.** 81 is the WHY
  of the note chain, six parts, each naming where the code or a suite pins it
  (TRAPS #13, the way WP-E's hazard named it: this WP verifies nothing by
  substitution, so its risk was prose drift and every factual sentence points at
  `system_note.py` / `token_status.py` / `chat.py` / `work.py` /
  `llamacpp.py` or at a check by its full name): **(a)** the note lives under
  the private key `system` **inside the message dict**, not as a message,
  because `chat.messages` is the UI's index space (the window projects it by
  dict identity, `StreamCallback`/`RemoveMessage`/`Undo`/`ToolCall` carry those
  indexes) — generator t5/t7, endpoints t12/t13; **(b)** once at the tail and
  the prefix-cache argument, **with WP-A's correction stated as the correction
  it is**: a merge costs one message's tokens, not the prompt — what invalidates
  is rewriting position 0 or moving a note already in the history; **(c)** the
  owner's role ruling (`user`, never `system`) with the strict-template evidence
  (Qwen3.x `raise_exception('System message must be at the beginning.')`, line
  85 of `Qwen3.5-4B.jinja`; llama.cpp #27367/#20733/#18895, QwenLM/Qwen3.8 #244)
  and the `user`→`user` merge rule that keeps the alternation family happy, with
  the grammar argument for why `user` may follow a `tool` run; **(d)** an unknown
  window answers silence — the same dash as DECISIONS 80 b, read and never
  probed on the request path, and silence is the door that keeps a request alive
  because nothing catches a hook on that path; **(e)** the
  percentage-OR-remaining levels with the worked 32k/64k/128k/200k table, the
  machine advancing **by rank and never by trigger order** (the 32k
  announce-order `small_window, warning, critical` with `info` shadowed forever
  is a design rule), `small_window` orthogonal, the memory-is-the-notes argument
  and the ONE registration in the module `HOOKS` at `chat.py` import; **(f)** the
  residual abort-then-type limit — the shape hazard 1 cannot reach, the owner's
  own months of manual practice, and the escape hatch now filed as P16. A
  numbering note is inside it (t12/t13 exist in BOTH suites' sequences; a check
  quoted by full name is `unit:endpoints`'s). 80 gains a cross-link paragraph
  (the same dash, the same `context_sizes[context_key()]` source feeding the
  counts row and the hook) and 81 cites 80 b/c throughout — **both ways**.
- **`doc/PROJECT.md`** — the map gained the note chain in the features paragraph
  (generator → hook → the private key → `prepare_payload()`'s unpacking, the
  `user` role, silence on the dash) and three repo-layout lines
  (`chat/system_note.py`, `chat/token_status.py`, `endpoints/llamacpp.py`), plus
  `system_note` in the `tests/unit/` list. All of it points at DECISIONS 81; a
  map, not an essay.
- **`doc/TESTING.md`** — the one sentence the entry named as history is
  rewritten to read true after WP-D: the system_note section used to end "The
  hook is NOT in `HOOKS` and no `Chat` builds it - registering and wiring it is
  WP-D"; it now says the hook IS registered, once, at `chat.py` import, one
  shared instance whose memory is its own standing notes, the generator per
  chat, and that `unit:endpoints` t13 is the wiring proof — and says why this
  suite stays 219 venv-free anyway (`chat.py` is not in its import graph). The
  rest of the file's post-wiring prose was read and needs nothing else; no row,
  no count, no check moved.
- **`doc/TASKS-PLANNED.md`** — **P13 closed**: the entry became a DONE record
  with the five WP results in five lines and the pointer to this file and
  DECISIONS 81, not a sixth essay. The four follow-ups are filed as real entries
  with their own `Go!`-ahead markers: **P16** `note_mode`
  (`separate`/`merge`/`off` — the kill switch and the abort-then-type escape
  hatch, with the `construct_payload` skip-list trap named), **P17** rendering
  the notes in the UI (invisible today; `chat_smoke`'s golden differential
  named as the thing a render change must re-pin deliberately), **P18** the four
  level numbers as settings (with the defaults-must-be-pinned trap), and **P14**
  the handoff tool, updated for ruling iv — its arrival replaces the
  fenced-block clause of `critical`, a text change and a `t16` re-pin, not a
  mechanism change.

**What was NOT done, on purpose.** No code, no test, no new row, no new suite;
`main` untouched; the P13 mechanism is closed and green and nobody needed to
touch it to make a doc sentence true (where a sentence looked like it wanted
one, the sentence was wrong: the `critical` text says *fenced handoff message*
and that is exactly what is shipped and pinned, and P14's arrival will re-pin
it). The four handoff files under `spit_app/tests/` stay as the chain's history.

**One stale pointer left on purpose, because only code can fix it.** The module
docstring of `token_status.py` and the header comment of
`tests/unit/system_note/test_token_status.py` both say the four texts are "the
drafts of `doc/TASKS-PLANNED.md`" — and the P13 entry those sentences point at
is now the closed one, which no longer carries the drafts (DECISIONS 81 and the
pinned tests are where the wording lives now). Both sentences are inside code,
and WP-E was docs-only with no `Go!` for a code change (DECISIONS 71), so they
were left exactly as written rather than edited quietly: the reference still
resolves in git history, and the next agent who is `Go!`d on either file should
re-point it at DECISIONS 81 / t16 in passing. Nothing in the closed entry
contradicts them — the texts they describe are the shipped ones, byte for byte.

**Corrected at the final read-back, in this close-out's own commit.** DECISIONS
81 first cited two hook checks as `t11-silence-when-the-window-is-unknown` and
`t11-silence-when-the-chat-has-no-accessor` — those are the *function* names in
`test_token_status.py`, not the names the suite prints. 81's own rule (a check
quoted by its full name is quoted as the suite reports it) is what caught it, so
the citation now names `t11-an-unknown-window-writes-nothing`,
`t11-a-chat-without-context_window-writes-nothing` and their two
`t11-CONTROL-…speaks` controls. Every other check name and every sha in 81 was
then checked against the four test files and `git cat-file`: all real. One docs
commit holds the decision record; this correction rides the close-out commit
rather than quietly rewriting it.

**Verified.** Full `bash spit_app/tests/run_tests.sh` from the repo root, run
**five times** across the sitting — twice on the working tree before the docs
commit, once after it, twice after the close — and **all five byte-identical to
each other**, exit 0, stderr
empty, **every row at
the `doc/TESTING.md` numbers** — tools 127/24/30/119/80/32/68/29 (509), anchored
68, arguments 131, chat_smoke 168, chat_window 568, endpoints 442, prompt 33,
render 278, run_script 121, sandbox 157, system_note 219, terminal 223, FAIL 0
everywhere — which is the whole Verify of a WP that changes no code: the
count-unchanged run is the proof no code changed. `chat_smoke`'s `golden.txt`
md5 `8ae9d1186a59627d30d05dee95f0ad95` **unmoved**. `git status` before the
docs commit: exactly the four `doc/` files; the commit's diff touches `doc/`
only. The pre-existing `unit:sandbox` `t3-child-stopped` flake (WP-B measured
it) **did not fire in either run** — it is not P13's, it was not touched, and
nothing is booked for it here. The close-out rests on the automated suites:
there is no screen in this environment (TRAPS #22), and nothing of WP-E is
runnable anyway — it is prose.

No sign-off step participated (DECISIONS 71); `main` untouched, nothing pushed.

**THE P13 CHAIN IS COMPLETE.** **WP-A, WP-B, WP-C, WP-D and WP-E are all closed**
in this file — the unpacking (`0afaef8`), the generator (`a6ec179`), the hook
(`6f1a0ed`), the wiring (`bcdc441`), the decision record (this WP-E) — with the
`unit:endpoints` row at **442** and `unit:system_note` at **219** and every
other row where P12 left it. **No handoff message is written after this one**:
the chain ends with this close-out because there is no next package — WP-F does
not exist and inventing one would be the invention TRAPS #22 warns about. What
remains of P13 is the follow-ups' own work, and each is filed with its own
`Go!` ahead of it (P14 the handoff tool, P16 `note_mode`, P17 the notes in the
UI, P18 the level numbers as settings). **`p13-wp-a-note-unpacking` now awaits
the owner's merge** — the only part of finishing that is not the agent's
(DECISIONS 71 a). Nothing here merges, pushes or pulls; `main` is untouched and
carries none of P13 until the owner's hand does.


### P14 — the `handoff` tool: the owner's manual loop becomes one tool call (branch `task-handoff-tool-p14`: `ff0a4b8` the entry opened, `961eac1` the tool and its suite, `6a994f7` the `critical` note re-worded with its `t16` re-pin, `8a8f904` the decision record, then this close-out; the branch awaits the owner's merge)

**Owner gate.** The `Go!` was GIVEN **2026-09-26** for this task and it covered
every code step of it (DECISIONS 71 (c)); nothing here re-asks it. The branch was
cut from `main` at `98631e6` — P13 merged — so P14 stands on the shipped note
mechanism and not on P13's unmerged docs branch. `main` untouched throughout,
nothing pulled, nothing pushed; the branch is the owner's to merge.

**What landed, commit by commit.**

- `ff0a4b8` — docs only: the working entry in `TASKS-IN-PROGRESS.md` with the
  State fields and the hazards measured **before** the first line of code (the
  canned server must answer `GET /models`, or a `ChatSettings` `update_models`
  worker on every chat mount loops 60 × 10 s; `/props` and `/slots` must answer
  404, so the window is unknown, the token-status hook is silent, and every POST
  the suite asserts on is note-free), and P14's flip to STARTED in
  `TASKS-PLANNED.md`.
- `961eac1` — `spit_app/tools/handoff.py` (129 lines) and
  `spit_app/tests/unit/handoff/`, **60 checks**, the **sixth dependency-listed
  suite** (TRAPS #19: the gate probes `textual, httpx, libtmux, ddgs,
  playwright`, because the code under test reaches `ToolCall`, which loads the
  whole tool tree). `async def call`, deliberately: `tool_call.py` awaits a
  coroutine `call` on the app's own loop instead of pushing widget work through
  `asyncio.to_thread` (the `set_chat_description` precedent). The `TOOLS.md`
  matrix reads `sync` for it, and that is right in the column's own terms — the
  column says *in-process `call()`, no sandbox script*; whether that `call` is a
  coroutine is the other axis, and the comment above the function in `handoff.py`
  is where this is written down.
- `6a994f7` — `chat/token_status.py`'s `TEXT_CRITICAL` re-worded to call the
  tool, and `unit:system_note` **t16 re-pinned in the same commit**, byte for
  byte against the rendered template. The generator, the rank machine, the
  private key and the unpacking are untouched: **DECISIONS 81 stands as the
  record of the mechanism**, exactly as ruling iv predicted (a text change plus
  its re-pin, not a mechanism change).
- `8a8f904` — **DECISIONS 82** (the argues: the `action_submit` reuse against a
  second write path, whole-`csettings` inheritance with `desc` excepted, the
  flag set LAST on `chat._work`, the two owned consequences, the suite's
  real/stub split, the three measured harness lessons), the `handoff` spec as
  `TOOLS.md` **#15** plus its matrix row, `TESTING.md`'s `unit:handoff` **60**
  row with "five suites" → "**six**" and the gate explained, and `PROJECT.md`'s
  map sentence.
- this close-out — docs, no code.

**The mechanic** (the short form; DECISIONS 82 and `TOOLS.md` #15 carry the
argues). The tool writes the new chat's JSON in `Manage.save_managed`'s shape
with the calling chat's whole `csettings` deep-copied and a fresh id in
`Manage`'s scheme plus the bump-loop `Manage` never needed (two handoffs in one
clock tick); `SidePanel.option_list()` makes the sidebar entry exist; the real
`Chat` is mounted, the others hidden, the new row `highlighted`, the new chat
focused; the text area is set and `ChatTextArea.action_submit()` is awaited —
**the human ctrl+enter path**, so the user-message dict, the undo `insert`, the
mount through the sliding window, `write_chat_history()` and the started `Work`
are the ones a human typing the same message would leave; and LAST, only after
all of that succeeded, `chat._work.exit_after_busy = True` — the flag
`action_abort` already sets and the one `work.py` checks after every tool call.
A refusal (blank or non-string `message`, unwritable file) returns before any of
it: nothing created, no flag, the working chat keeps working. `t7` pins the
refusal with its control.

**Two corrections of the brief, made while planning and shipped as planned** —
both recorded in the (now closed) entry and in 82, because both are the kind of
slip that fails silently:

- the flag lives on **`chat._work`, not `chat.work`**: `chat.work` is the Textual
  `Worker` wrapped around the `Work`, and a flag set on the Worker is read by
  nobody; `work.py`'s per-tool-call check (`if self.exit_after_busy: return
  None`) is on the `Work`.
- **`desc` is not inherited verbatim**: the new chat reads
  `"Handoff: <old desc>"` unless the optional `description` argument says
  otherwise (t1 pins the default and the whole-block inheritance, t8 pins the
  override and its junk-value control). Verbatim inheritance would put two
  identical rows in the sidebar — the one thing the owner's manual loop never
  suffered.

**The consequences this design OWNS** (DECISIONS 82 (d) — each is a decision and
each is pinned; none is a hole to be filled quietly later):

- **a sibling tool call in the same assistant reply is SKIPPED.** `handoff` ends
  the stream by returning inside `work_stream`'s per-tool loop, so a second call
  in the one turn never runs. Work-loop **t15** pins it: two calls asked,
  exactly one new chat, one tool result, and the second message never reached any
  wire — with the control that the first one did. The `DESC`/PROMPT line *"Call
  it alone"* is load-bearing, not decoration.
- **"this chat ends" is its work stream, not the widget.** The old `Chat` stays
  mounted, readable and usable, exactly as after an abort; its tmux sessions stay
  alive with it, which is terminal-harness **item 12**'s territory and not this
  tool's. Ripping the widget out was never in the contract.
- **a chat without `handoff` in its selected tools cannot hand off.** Existing
  chats gain no tool retroactively; the owner enables it per chat. That is
  precisely why the fenced-block wording survives inside `critical` as the
  fallback instead of being deleted.

**The note re-pin (ruling iv, arrived).** `TEXT_CRITICAL` now sends the model to
the tool — *"Hand the work off NOW: call the `handoff` tool with your handoff
message…"* — and the fenced block is what it writes *when no handoff tool is
available*. The load-bearing stop-clause, *"Do not call any more tools and do not
start new work after the handoff — the chat dies inside this reply"*, is
byte-identical inside the new wording, and `unit:system_note` stayed at **219**
in count with the `t16` strings moved in the same commit as the text: the text
came to the pin, the pin did not come to the code (TRAPS #18).

**Verified.** Full `bash spit_app/tests/run_tests.sh` from the repo root at this
tip, run **five times** for the close-out — three before its own edits, twice
after them — **byte-identical across all five** (the md5 of the captured stdout
of every run: `5a7e48a4270a10f3a47d1fd3a89921a6`), **exit 0**, stderr empty,
**every row at the `doc/TESTING.md` numbers** — tools 127/24/30/119/80/32/68/29
(509), anchored 68, arguments 131, chat_smoke 168, chat_window 568, endpoints
442, **handoff 60** (this entry's own row), prompt 33, render 278, run_script
121, sandbox 157, system_note **219**, terminal 223, FAIL 0 everywhere.
`unit:prompt` reads its pinned **33** because the new `DESC`/PROMPT are not in
the stub table that suite drives — the row neither moves nor lies.
`chat_smoke`'s `golden.txt` md5 `8ae9d1186a59627d30d05dee95f0ad95` **unmoved**:
the handoff tool is not selected by the smoke chat, so nothing on that wire
changed. The close-out adds no checks and touches no code, so the
count-unchanged run is itself the proof of that.

**Corrected by the runs taken after the close-out commit: stderr is not always
clean.** The five runs above had stderr empty, and nine further runs were then
taken at the same tree for the record — **fourteen in all, every one of them
exit 0 with stdout byte-identical** — but **two of the fourteen printed a
traceback**: the canned
server's `do_GET` 404 branch (`handoff_harness.py:209`) dies on
`BrokenPipeError` when the client is gone before the 404 body lands — the
`update_models` / `/props` / `/slots` probe path, which hangs up because the
answer is a 404 or the worker is being torn down. The `do_POST` handler already
catches `(BrokenPipeError, ConnectionResetError)` for exactly this reason, with
the comment saying the recording already happened; the GET path simply never got
the same guard, and Python's `socketserver` prints the traceback and carries on.
**Nothing is measured wrong** — no check moved, the suite still reports 60/0, and
the full suite still exits 0 — but the claim "stderr empty" is true of the five
close-out runs and not of every run, so it is stated that way here. **Not fixed
here**: it is a one-line guard in a test file, a code change, and DECISIONS 71
keeps a `Go!` in front of those; whoever next is `Go!`d on this suite (or on any
red in it) should wrap the `do_GET` `_send` in the same `except
(BrokenPipeError, ConnectionResetError): pass` the POST path has and say so in
the commit. Recorded rather than quietly patched, so that the next agent reading
a stderr wall out of a green suite knows what it is before spending an afternoon
on it.

**Which verification the close-out rested on, plainly.** The **automated headless
suites**, and only those. `unit:handoff` drives the real `Chat` (window, undo,
stream callbacks), the real `SidePanel` `OptionList`, the real `Work` and the
real `ToolCall` over a canned 127.0.0.1 SSE server: *"sent"* is proven by the
POST the server records and by the streamed reply landing in the new chat, and
*"ends"* by the **absence** of the next request — the one assertion a tool that
merely sets a flag cannot satisfy. This environment has **no screen** (TRAPS #22),
so nothing here was confirmed by watching a new chat appear in the running app; a
by-hand look at a real handoff (does the sidebar row read well, does the
foreground switch feel right, does the reply stream into the mounted window) is a
**note for whoever next runs the app**, never a condition of closing.

**No handoff is written after this one.** P14 was one package, not a chain: the
work is done, the entry is closed, and what the branch needs next is not another
agent but the owner's hand. **`task-handoff-tool-p14` now awaits the OWNER'S
MERGE** — the only part of finishing that is not the agent's (DECISIONS 71 a). No
sign-off step participated; nothing merged, pushed or pulled; `main` is at
`98631e6` and carries none of P14 until the owner's hand does. What P14 leaves
for later work is already filed, each with its own `Go!` ahead of it — P16
`note_mode`, P17 the notes in the UI, P18 the level numbers as settings — and
the tmux teardown a closed chat still does not get belongs to terminal-harness
**item 12**, not to P14.

### P0b-followup 4 — the `terminal` tool as a UI-under-test harness: items 1-12 shipped (branch `task-terminal-harness-p0bf4`: `8f3a038` the entry opened with the baseline and the machine facts, `85d33e2` the backend in `run/terminal.py`, `dc23995` the tool's arguments in `tools/terminal.py`, `d1a5688` the abort flag in `chat/chat.py`, `c3f69a1` the teardown in `manage/chat/chat.py`, `5368883` the 123-check suite, `cef8169` DECISIONS 83 + TOOLS.md #7 + the TESTING.md row + the owner's ruling in PROJECT.md/AGENTS.md, then this close-out; the branch awaits the owner's merge)

**WHAT WAS ASKED AND WHAT THE OWNER RULED.** The list is the one written during P0b:
twelve things a pane must be able to report before the `terminal` tool is a harness
for a program under test rather than a convenience (items 8, 9, 10 and 12 had
landed partly in earlier followups and are marked where they are done, never where
they are open). The branch was cut from `main` `c023a16` under the owner's ruling of
2026-09-28, quoted verbatim in DECISIONS 83 and now in `PROJECT.md`/`AGENTS.md`:
*"You may work now independently without asking the user for any permission. One
thing remains the same: only the user may merge your work into main."* No `Go!` was
asked for anything on this branch; nothing was merged, pushed or pulled; `main` is
untouched and carries none of it until the owner's hand does.

**WHAT SHIPPED** — every item that was open, in the two layers the list implies
(the backend in `spit_app/tools/run/terminal.py`, the caller-visible arguments in
`spit_app/tools/terminal.py`):

1. `command` (argv), `env`, `cwd` at creation — "start the UI under test" is the
   primitive and interactive bash is its default; creation-only, and naming an
   existing session together with them is refused rather than typed into it.
2. `cols`/`rows` at creation and `resize` on a live session, both-or-neither;
   measured per WINDOW on a clientless session, which is what turns DECISIONS 73's
   "a capture's width must not belong to the machine" from a guard into an argument.
3. `capture` = `text` | `styled` (`-e`) | `bytes` (`-e -C`), with the grid limit
   stated in the DESC, the PROMPT, TOOLS.md and DECISIONS 83 (b).
4. The cursor as data — `cursor_x`/`cursor_y` in `screen_json`, `marker=False` to
   drop the `█` splice that overwrites the character under it.
5. `wait_for` (regex) / `wait_stable` (ms) / `wait_timeout` (default 15 s), which
   REPLACE `delay`; six kinds, and a timeout that answers with a WARNING instead of
   silence.
6. `send_bytes`, raw through `send-keys -l --`, byte-exact; NUL refused.
7. `history` (capped at 500) and `diff` with a text-only baseline.
8/11. `format="json"` — `state`/`cols`/`rows`/`pane_pid`/`command`/`cursor_x`/
   `cursor_y`/`screen[]` live, `exit_status`/`signal`/`dead_time` dead, and
   `{session, state: "absent"}` for a name the chat never had.
10. The cancellable wait, completed: `Chat.action_abort` stamps the `abort` flag the
    poll reads, the flag is consumed, and `call()` clears it at the start.
12. `close_chat` — a deleted or archived chat's session dies with it, called from
    `manage/chat/chat.py:delete()` after the file is gone (which covers `archive()`
    too), killing the session and never the Server.

**GROUND TRUTH AT THE CLOSE.** Full suite from the repo root, exit 0, twice with the
PASS/FAIL rows identical: tools 127/24/30/119/80/32/68/29 (509), `unit:anchored` 68,
`unit:arguments` 131, `unit:chat_smoke` 168, `unit:chat_window` 568,
`unit:endpoints` 442, `unit:handoff` 60, `unit:prompt` 33, `unit:render` 278,
`unit:run_script` 121, `unit:sandbox` 157, `unit:system_note` 219, and
**`unit:terminal` 223 → 346** — the whole rise is the new `test_harness.py` (123
checks) and nothing else moved; the five existing files of that suite were not
touched. `chat_smoke`'s golden `golden.txt` md5
`8ae9d1186a59627d30d05dee95f0ad95` unmoved (the `action_abort` change is a no-op on
the stub app that golden drives, which is what its `getattr` guard is for). The
suite keeps the terminal directory's two properties: a private socket, and at exit
stale socket FILES with **no running server** (`tmux -L spit-unit-terminal-harness
ls` fails after a run; `pgrep tmux` finds nothing).

**WHICH VERIFICATION THE CLOSE-OUT RESTED ON, plainly.** The automated suites only —
this environment has no screen (TRAPS #22), so nothing was confirmed by watching a
terminal in the running app. Within those, the evidence is of three kinds: the green
run; the **substituted defects** (forcing the tool's capture mode to `text` reddens
exactly the two tool-level capture checks; forcing the backend's mode reddens `t3`'s
four; `close_chat` reduced to its pop reddens three of `t9`; a disabled abort check
reddens three of `t6`), so no green in the new file is one that cannot fail; and the
**byte-for-byte default path** — `t3` asserts `term_screen(name)` equals
`term_screen(name, mode="text")`, and `test_screen`'s 93 checks passed untouched
through a refactor of the same function, which is TRAPS #14 done in the only way
that counts.

**THE LIMITS, stated plainly, because three of them are things the list asked for
that this did not deliver.**

- **The graphics byte stream is NOT assertable and no recorder ships.** Every
  capture mode reads the pane's GRID: a Kitty/Sixel sequence is consumed by tmux and
  comes back as its placeholder, never as its bytes — item 3's original hope ("this
  is how the Kitty/Sixel path gets asserted") is not reachable through
  `capture-pane`. `pipe-pane` would reach it and was **rejected**: it opens a file
  the tmux server keeps writing to, from a process that outlives the pane, into a
  path the model itself can read and grow, with no lifetime the tool layer controls
  and no cap. That belongs in its own task with its own file discipline.
  DECISIONS 83 (b); the code comment in `capture_pane_of` points at the same entry.
- **An argv that exits before tmux answers cannot be retained at all** —
  `command=["true"]` makes `new_window()` raise (`no such window: @1`, measured), so
  `term_new` reports its error string and registers nothing. "A dead pane reports its
  exit code" is therefore pinned with a command that prints, waits a beat and exits
  7. A harness that wants to assert on an instant exit asserts on the error string.
- **libtmux's key layer does not mangle ESC** — the claim written from the first
  probe did not reproduce (its routes delivered the ESC payloads byte-exact on this
  tmux 3.7c / libtmux 0.62 pair). What it cannot carry is a payload that BEGINS WITH
  A FLAG: `-l …`, `-t …`, `-- …` arrive as `b''`. `send_bytes` stays on tmux's own
  argv with `--` for the reason that reproduces, and the suite pins both halves.
- **`cwd` is a path as the PANE's filesystem sees it**, not as the carried shell
  state sees it; its relationship to `run_command`'s carried `cd` is P11's open
  question and this task did not touch it.
- **A `wait_for` is cancellable; nothing else is.** A program already running in a
  pane is stopped by what you type into it, not by a tool call.
- **The PROMPT keeps the owner's now-half-false sentence** ("The terminal is 24x80
  characters with no scroll-back") — true as a default, false as a limit — because
  the PROMPT is the owner's text and the rule that it is what the model reads
  outlived the `Go!`; the two new blocks state the capability next to it and
  `doc/TOOLS.md` #7, the spec, drops the two false claims outright. DECISIONS 83 (i)
  records the choice, so nobody reads the PROMPT as the last word on what the tool
  can do.
- **The manage `delete()` call site is pinned by no test**: no suite here constructs
  that widget. `close_chat`'s behaviour and its stranger-id no-op are pinned (t9);
  the id shape at the call site (`chat-<uuid>`, not the bare manage uuid) is carried
  by the comment and by this note. Getting it wrong would be silent, which is exactly
  why it is written down twice.

**WHAT THIS LEAVES OPEN** in the list: nothing that is not filed. Item 9's "fail
loudly beyond 'no such session'" remains the choice it was; item 12's remaining
exposure (a chat whose windows outlived it because the app was killed rather than
quit) is the socket's own teardown, unchanged by this. The stale socket FILES this
task's probes left under `/tmp/tmux-1000/spit-probe-*` are removed; the suites'
own `/tmp/tmux-1000/spit-unit-terminal-*` files stay, as they always have, and are
harmless.

**No handoff is written after this one.** The entry is closed, the branch is
complete, and what it needs next is not another agent but the owner's hand:
**`task-terminal-harness-p0bf4` awaits the OWNER'S MERGE** — the only part of
finishing that is not the agent's (DECISIONS 71 a, unchanged by the 2026-09-28
ruling).

### P19/WP-1 — the new-chat sequence extracted from `handoff` into `chat/handoff.py` (branch `task-recovery-handoff-helper-p19wp1`: `99e1338` the entry moved into TASKS-IN-PROGRESS with its State fields, `738b788` the refactor, `6ad4a7c` the state record; the branch awaits the owner's merge)

**What it is**: the first of P19's four packages, and deliberately the only
code change of it — a **behaviour-free refactor**. `tools/handoff.py:call`
built the next chat itself: id, chat file, sidebar, mount, foreground, focus,
`text_area.text`, `await action_submit()`. That sequence is now one module-level
function in `spit_app/chat/handoff.py`, because WP-4's failure-recovery chat
must be opened by the **same** code and not by a copy of it that can drift
(DECISIONS 82 a: the message enters through the human submit path, so the file
on disk, the undo history and the widget tree are what a human typing the same
message would leave).

**The split, and why it falls there**:

- `spit_app/chat/handoff.py`: `new_chat_id(app)` (the `Manage` id scheme plus
  the bump-loop, moved whole) and `async create_and_submit(app, settings,
  message) -> str|None`. It takes settings already built and returns the id, or
  **None when the chat file could not be written** — the only step that can
  fail. It knows nothing about ending a chat, and that is the point: nothing in
  it can set a flag.
- `spit_app/tools/handoff.py` keeps everything that belongs to the *tool*:
  `DESC`/`PROMPT`/`SETTINGS`, the deepcopy of `csettings` and the `"Handoff: …"`
  desc rule (82 b — the inheritance decision), the success string, the refusal
  of a blank message, and **`chat._work.exit_after_busy = True` as the last
  statement of a successful call** (82 c — a handoff that failed halfway must
  leave the working chat working, and the flag line being last *is* the
  guarantee, so it did not travel into the helper).

**Verification it rests on** — TRAPS #18, the suite and not the argument that
the move was faithful: the full suite was run from the repo root **before** any
code changed (the baseline: tools 509, anchored 68, arguments 131, chat_smoke
168, chat_window 568, endpoints 442, handoff 60, prompt 33, render 278,
run_script 121, sandbox 157, system_note 219, terminal 346, FAIL 0 everywhere —
exactly `doc/TESTING.md`) and **after**: every row byte-for-byte the same,
`unit:handoff` still **60 / 0**, and `git show --stat` on the code commit is the
two files. No test needed a seam and no check moved: `t1`-`t9` drive the real
tool and `t10`-`t15` the real `Work` + `ToolCall` over the canned server, so
what they pin through the move is the chat file's shape, the sidebar's
highlight and display state, the undo record, the POST the new chat makes, the
streamed reply that lands in it, and — for the flag — the **absence** of a
second request from the old chat.

**Limits accepted**: none new. This WP changed no behaviour, so there is nothing
to accept; `P19` stays open in `TASKS-IN-PROGRESS.md` with WP-2 (typed endpoint
failures, the retry loop, the slot leak, the dead `endpoint == -1`), WP-3
(`journal`) and WP-4 (wire the recovery, `DECISIONS 84`) left, and the entry
carries what the reading for WP-2 measured — including the two `unit:endpoints`
t6 checks that today's error contract pins and that WP-2 must re-pin in place.

### P19 — failure recovery: an endpoint failure must not need a human (branch `task-endpoint-retry-p19wp2`, cut from `task-recovery-handoff-helper-p19wp1` @ `85e012a`: WP-1 `738b788` on that parent branch, WP-2 `44b8739`, `2728272`, `391bb3a`, `020f502`, `b4b4759`, `f67bc04`, WP-3 `dd351a2`, `5967054`, WP-4 `1e4d132`, `5c6853a`, `8fef3fb`, then the two WP-4 docs commits `a2d033d` (DECISIONS 86) and `9514ada` (the `unit:recovery` row and its spec), then this close-out; **the branch awaits the OWNER'S MERGE**)

**What this is**: the owner's brief in full — an endpoint failure must
not halt a working agent and must not need a human. (1) retry the
request with a delay; (2) when the retries are exhausted, open a new
chat exactly like the `handoff` tool does, the current chat's settings
cloned, a recovery message as its first message; (3) a `journal` tool
the agent uses while still alive, whose entries become that recovery
message. Four packages, and the entry closes as a whole — that was
P19's rule from the start, no WP moves to this file on its own merits —
so this is the entry's only close-out; WP-1 carries its own entry above
because it was cut and closed as a separate branch-level package. The
decisions taken live in **DECISIONS 84** (WP-2: a failure carries its
status, the retry wraps only the request, the rollback keeps the
queue's order; per-endpoint `retry_attempts`/`retry_delay`; auto-submit
when the probe answers and a draft when it does not; the modal stays
for a deterministic 4xx while transient and exhausted failures become
an in-chat notice), **85** (WP-3: the journal is an in-process tool,
its cap a ceiling on the READ only, read from the app not the module)
and **86** (WP-4: the recovery is a message in a new chat, the notice
a message in the old one, the chain one deep).

**What shipped**:

- **WP-1** (`738b788`, see the entry above): the new-chat sequence
  extracted from `tools/handoff.py` into `chat/handoff.py` —
  `new_chat_id` and `async create_and_submit(app, settings, message) ->
  str|None` — so WP-4's recovery chat opens through the **same** code
  and not a copy that can drift.
- **WP-2** (the six commits): typed failures carrying
  `status_code`/`retryable` in `endpoints/llamacpp.py`
  (`EndpointFailure` and five named subclasses, the `str()` sentences
  byte-identical to what the app always showed), the retry loop around
  `attach() + endpoint.stream()` **and nothing wider**, the rollback
  through the widget's own queue, the stale-signal guard,
  `Work.retrying`, and the prompt-cache slot returned on every way out.
  `unit:endpoints` 442 → **512**.
- **WP-3** (`dd351a2`, `5967054`): `tools/journal.py` — one append-only
  file per chat, multi-line timestamped entries, `entry` writes and no
  `entry` reads, the read capped by `journal_max_chars` at an ENTRY
  boundary with the newest entry whole — and the "journal now /
  journal before the handoff" clause in the two note texts with their
  `t16` re-pin. New `unit:journal` **69**, `unit:prompt` 33 → **38**,
  `unit:system_note` **219** by the re-pin alone.
- **WP-4** (`1e4d132`, `5c6853a`, `8fef3fb`): new `chat/recovery.py` —
  the brief built from what the app itself witnesses (chat id, the
  transcript path, the error, the attempts made, the last N messages,
  the token counts) with the journal appended when there is one; the
  one probe (`get_models` at `timeout=3`, answering `[]` on any
  failure) deciding auto-submit versus draft per 84 b; the cloned
  `csettings` with `recovered_from` and the **chain depth capped at 1**
  — a recovery chat that fails again reports, it does not recover; and
  the in-chat notice of 84 c in the dead chat. `create_and_submit`
  gains the `submit: bool = True` draft switch; `Work.report_failure`
  becomes async and takes the attempt number, splitting off
  `report_modal` for the deterministic 4xx; `DeterministicFailure`
  joins `tests/unit/prompt/stub_modules.py` because `work.py` imports
  it at module level. New `unit:recovery` **55**
  (`tests/unit/recovery/`, built on `unit:handoff`'s harness), the
  absence-of-a-second-recovery-chat and draft-not-submitted checks
  included. Recovery is **not** behind the `handoff` tool (DECISIONS
  82 d), so the path bypasses `ToolCall` deliberately.

**Verified** — the FULL suite from the repo root at this tree
(`bash spit_app/tests/run_tests.sh`, log `/tmp/p19wp4-run1.log`):
tools 509 (127/24/30/119/80/32/68/29), anchored 68, arguments 131,
`chat_smoke` 168, `chat_window` 568, endpoints **512**, handoff 60,
journal 69, **recovery 55** (the new row), prompt 38, render 278,
run_script 121, sandbox 157, system_note 219, terminal 346, FAIL 0
everywhere, `SUITE-EXIT:0`. `chat_smoke`'s golden md5
`8ae9d1186a59627d30d05dee95f0df0ad95` verified unmoved; no stray
`core.N`, no fixtures left behind. The `unit:chat_window`
`t11-a-second-scroll-settles-too` load flake filed in the entry's
State hazards did **not** fire in this run.

**Things the recovery work learned that the code does not show**:

- The recovery's new chat FILE is its first act and the in-chat NOTICE
  is its last: a test that asserts on the world the moment the file
  appears reads a recovery that has not finished. The harness gates on
  `recovery_reported(pilot)` for exactly this reason.
- `Work.report_failure` sends the corpse back through the awaited
  `roll_back_attempt` **before** the recovery appends the notice,
  because the removal's index is `len(messages)-1`: a removal posted
  after the append would take the NOTICE back and leave the corpse
  standing in the dead chat (DECISIONS 86 f).
- `unit:endpoints` stays at **512** only because `can_recover(app)` —
  which requires `app.settings.path["chats"]` — answers False **before
  any probe** for those bare `StubSettings` apps. That gate is
  load-bearing for the suites; do not remove or reorder it.
- A suite built on `unit:handoff`'s harness must redirect
  `handoff_harness.FIXTURES`/`DATA` **module globals** to its own
  fixtures — `StubSettings` builds its `path` from them and
  `ToolCall.__init__` wants `custom_tools` before a subclass can
  intervene.
- The recovery suite's server subclass answers **503 on POST replies
  while `/models` still answers 200** — the probe answered, the
  request refused — and `server.stop()` mid-case is the DRAFT branch:
  the brief is on the wire in one and nowhere on it in the other, the
  same marker evidencing both.
- Carried forward from the deleted entry because it outlives P19: the
  outer `spit_app/tests/run_tests.sh` pipes every suite through
  `| tail -n 1` **and the pipeline swallows the suites' exit status** —
  a crashing suite reports `PASS: 0 FAIL: 0` and the run still ends
  `SUITE-EXIT:0`. Read each suite's own output, never only the row;
  and the full suite does not survive backgrounding inside
  `run_command` — run it in a `terminal` session through `tee`.

**What this leaves**: nothing half-done. `task-endpoint-retry-p19wp2`
**awaits the OWNER'S MERGE** (DECISIONS 71 a) — the only part of
finishing that is not the agent's. Nothing was pushed, `main` is
untouched at `edba920`. The P19 entry is deleted from
`TASKS-IN-PROGRESS.md` and **no entry is open**.

### P1 — the `---`/`+++` pair above a headerless hunk (branch `fix-patch-header-pair-adjacency-p1`: `a1f1032` code + tests + PROMPT sentence, then the docs commit)

**What this was**: the edge `DECISIONS 37` left open on purpose (planned P1,
"open, deliberate"): `is_header_pair()` skipped any `--- old` over `+++ new`
outside a hunk, and a headerless hunk whose first two body lines remove a
`--…` line and add a `++…` line completes exactly that pair — `---x` over
`+++y` — so those two lines were skipped as a file header and the hunk lost
its edit.

**What measuring it found, before any code** (the entry's own premise was
wrong, and the direction of the error matters): the entry says "Consequence is
a loud no-match failure". It is not. On file `--x\nkeep\nmore` the patch
`---x / +++y / ␠keep / ␠more` ran on `main` with **rc 0** and printed
`Patched …: 1 hunk(s) applied. 0 line(s) added, 0 line(s) removed.` The pair
was dropped, the hunk that remained was pure context, context matches, and the
tool reported success for a patch whose whole content it had thrown away — a
silent no-op with a success line on it. The reference implementations were
measured too (TRAPS #16/#17): GNU patch 2.8 answers `Only garbage was found in
the patch input` for that input *and* for the t11 shape (`--- work.txt /
+++ work.txt / <headerless body>`), and `git apply` answers `No valid patches in
input`: **neither supports headerless hunks at all**, so there was no reference
behaviour to copy and the disambiguation rule was this tool's to choose inside
decision 34's decision that headers are optional per hunk.

**What shipped**: the file decides. A pair with **no body run under it** —
end of input, a blank line, or a `@@` header next — is a header whoever the
file is (this is the half of the entry's suggested rule that was right, and it
is why `diff`/`git`/`difflib` output never takes this path at all). For a pair
over a body run both readings are built and each asks the file whether it
places a hunk — the side a hunk must find is the old side forward and the new
side in reverse, the same swap `sides()` performs, so `reverse` needs no
separate rule. Body open, header closed → **content**, and the model's edit is
applied; header open, body closed → **header** (t11, unchanged); **both open →
refused**, atomically, naming the remedy:

`ERROR: The `---`/`+++` pair at lines 1-2 is a file header or the first two
body lines of the hunk under it, and the file matches both readings. Write the
hunk's `@@ -start +start @@` header between them to say which it is.`

A run of pure context is *not* an open header reading, because it places no
edit anywhere — which is why the shape from the measurement above is fixed
rather than merely made loud. Full why in **DECISIONS 87**.

**What was measured and NOT taken**: the entry's own fix — "require that a
genuine file header be followed by a `@@` hunk header or end of the input".
It is one line and it breaks `t11`, which is a file header followed by
neither, applies today, and is exactly the shape decision 34 exists to accept:
under that rule its pair becomes body, its old block opens with a line
`-- work.txt` no file contains, and a patch that applies today is refused.
TRAPS #18 calls that an applied→refused nobody asked for; the rule above keeps
it green and still closes the hole.

**Proved by differential, not by the suite** (58 rows: every
source/patch pair `run_tests.sh` uses — mapping read out of the suite and
printed before the run, TRAPS #13 — plus 20 synthetic pair shapes forward and
in reverse): **41 applied→applied**, 37 byte-identical and the 4 others
changing bytes *because the fix applied the edit `main` dropped* (`--x`
present with a context-only run, its CRLF and unterminated variants, and that
patch reversed); **3 applied→refused**, the three genuinely ambiguous shapes,
intended and named — one of them a real-looking `--- original.txt /
+++ expected.txt` header on a file that happens to hold a line
`-- original.txt` above the block, which now needs its `@@` line (pinned
both ways as t44: refused as written, applying once the header is there);
**14 refused→refused**, two of them with the line numbers in the message
shifted by one because the pair is now content — same verdict, same class. No
applied→applied row moved bytes that had no reason to.

**Ground truth at the close**: `patch` **107** (was 80; t40–t45, and **14 of
the 27 new checks are red against `main`'s script**, so no green here is one
that could not fail — TRAPS #13), every other row at the `doc/TESTING.md`
numbers, `unit:prompt` **38** unmoved (the PROMPT gained one sentence about the
pair rule; `t8` counts one `## ` heading per tool and requires a PROMPT of every
module, and neither moved), full suite `SUITE-EXIT:0` with stderr empty,
`chat_smoke`'s golden md5 `8ae9d1186a59627d30d05dee95f0ad95` unmoved.

**Files**: `spit_app/tools/scripts/patch.py` (the reading functions and the
file read moved above the parse loop, because a pair's meaning is only
decidable against the file — nothing there can fail on a missing file, which
is refused at the top), `spit_app/tools/patch.py` (one PROMPT sentence),
`spit_app/tests/tools/patch/{run_tests.sh,create_fixtures.sh}` (t40–t45,
append-only numbers, no freed number reused).

**Process note**: the entry never sat in `TASKS-IN-PROGRESS.md` — it opened,
measured, shipped and closed inside one sitting, so the crash-recovery record is
this entry plus the journal file the agent wrote as it went. Where a task spans
sittings the protocol still applies (entry moved in, State fields kept current).

**What this leaves**: nothing half-done in P1. `fix-patch-header-pair-adjacency-p1`
**awaits the OWNER'S MERGE** (DECISIONS 71 a) — the only part of finishing that
is not the agent's. Nothing was pushed; `main` untouched.

### Token counts stuck at zero — the harvest call P19/WP-2 left behind (branch `fix-token-harvest-call-site`: `17615f6` the line + t15 + its fixtures, `8ea5442` the docs, `ff7737a` the dead import t15 never called)

**What the owner reported**: since `task-endpoint-retry-p19wp2` was merged, the
three numbers on the chat-settings row — the token count, the generation count,
the cached count — stay at `0` through a whole progressing chat, and the model
stopped being told about its token consumption through `system_note.py`.

**The finding (investigated first, no code touched until it was written down)**:
one missing line. `Work.harvest_usage()` is intact and correct and has **no
caller** — `391bb3a` moved the request out of `work_stream()` into the new
`stream_attempts()` loop and carried the `attach()` line and the `return None`
across but not the harvest that used to sit between the await and the `except`.
So `chat.token_usage` never leaves `Chat.__init__`'s three zeros and every
consumer renders them: the counts row (`usage_text`, refreshed faithfully on
signal 0 — it redraws zeros because that is what it is told), `TokenStatus`
(`used = 0` is below every percentage and every remaining-token floor, so it
answers silence forever and no note ever reaches the wire — which is the
`system_note` symptom, and why nothing in `system_note.py` or `token_status.py`
was wrong), and `recovery.recovery_brief()`, which tells a successor chat "Token
counts when it died: context 0, generated 0, cached 0". `endpoints/llamacpp.py`
still parses and keeps the usage object: the figures arrived and were thrown
away. Proven read-only before the fix, with a real headless `Chat` and a real
`Work` over the canned server — `endpoint.usage` full, `chat.token_usage` at
zeros, no note on the next request; the same chat after one hand-called harvest
moves to `121000/1000/90000` and the very next request carries the `info` note.

**What shipped**: the line, back where it was — after the await, inside the
`try`, before the success path's `return None` (the position is the decision:
only a landed reply is counted, `stream()` resets `usage` at its own start so a
dead attempt cannot leave a figure, the tool-loop recursion re-passes it, and it
runs before the signal-0 redraw of the row). Plus `test_harvest_wiring.py`,
**t15, 35 checks**, pinning the JOIN rather than the method: a real
`Work.work_stream()` over the canned server, and the counts, the row and the
recorded POST bodies read off it. Three canned scenarios were added for it to
`post_reply` — `bigusage`, `usage-then-error`, `flaky-503-usage` — and
deliberately **not** to `SHAPES`, which is t2/t3/t4's differential table.
`counts_harness.Reply`'s docstring now says out loud that it copies the flow and
where the real one is tested.

**Why the suite could not see it, which is the part that was written down twice
(TRAPS #26, DECISIONS 88)**: `t10` drives the method on a `SimpleNamespace`,
`t11` drives a `FakeEndpoint` through a hand-written `Reply.one()` that copies
the two statements, `t13` runs the real worker against a scenario with **no
usage chunk** and hand-sets the fill, `t14` runs the real worker and never reads
`token_usage`. `unit:endpoints` was at **512 green** the whole time.

**Ground truth at the close**: `unit:endpoints` 512 → **547** (t15's 35 by
addition alone, every other file at its own number), every other row at the
`doc/TESTING.md` numbers, `chat_smoke`'s golden md5
`8ae9d1186a59627d30d05dee95f0ad95` unmoved, full suite `SUITE-EXIT:0` with
stderr empty. The new file was verified red four ways — no line at all (14 of 35
red), the harvest ahead of `stream()` (15), in a `finally` (the corpse check),
in the retry branch too (the same check) — so no green in it is one that could
not fail (TRAPS #13).

**Corrected by the runs taken after the close-out: stderr is not always clean,
and it is not this branch.** The sentence above — "stderr empty" — is true of the
run it was taken from and of most runs, and the same over-claim was made and
corrected in the P14 entry three days earlier. Measured 2026-09-30 in a second
sitting, after `ff7737a`: **20 consecutive `unit:recovery` runs on this branch →
1 run with a stderr traceback**; the **same 20 runs in a clean worktree of
`main` → 1 run** with the same traceback, from
`unit/handoff/handoff_harness.py`'s `do_GET` 404 branch (`BrokenPipeError`, the
client already hung up; stdlib `socketserver` prints it and carries on). Same
rate on both sides, same frame, and this branch never opens that file: it is
pre-existing and environmental, and nothing in the counts moves with it — the
full suite is `SUITE-EXIT:0` and every row at its number either way. It is filed
as **P20** with the one-line guard its own `do_POST` already carries, so the
next agent neither re-derives it nor mistakes it for whatever they just changed.

**Ground truth, re-taken at this branch's final tip (`ff7737a`)**: full suite
`SUITE-EXIT:0`, every row at its `doc/TESTING.md` number — tools
127/24/30/119/107/32/68/29, anchored 68, arguments 131, chat_smoke 168,
chat_window 568, **endpoints 547**, handoff 60, journal 69, prompt 38, recovery
55, render 278, run_script 121, sandbox 157, system_note 219, terminal 346,
FAIL 0 everywhere — and `chat_smoke`'s `golden.txt` md5
`8ae9d1186a59627d30d05dee95f0ad95` unmoved. The per-file split of the endpoints
row was re-counted file by file at this tip: **88 / 132 / 62 / 19 / 43 / 51 / 48
/ 69 / 35 = 547**, which is the list `doc/TESTING.md` pins, so the row is 547
because its files are those nine numbers and not because a total was typed.

**Process note**: this entry is the record of a task that spanned two sittings,
which is the case the crash-recovery files exist for, so it says plainly how it
was picked up. The first sitting diagnosed, fixed, tested and closed it and died
of token exhaustion **with the tree dirty** — one uncommitted line, the removal
of `fixture_chat` from an import that file never used, and a half-formed plan to
fold it into `17615f6` with `git commit --fixup` and an autosquash rebase. The
second sitting found that state in `git status` and the reasoning in the dead
agent's last trace. Two things came of it:

- The tidy-up became **`ff7737a`, its own commit**, not a rewrite. The autosquash
  instinct was wrong: `17615f6` is cited by SHA in this entry's own heading and in
  `8ea5442`'s message, so rewriting it would have left two citations pointing at
  commits that no longer exist. **Once a doc names a SHA, that commit is fixed; a
  correction lands on top.** Now a rule in `doc/CONVENTIONS.md`.
- The claim in the paragraph above, "closed inside one sitting", was true when
  written and is false now, so it is replaced rather than kept. A close-out that
  cannot survive the next `git status` is not a record.

**What this leaves**: nothing half-done. `fix-token-harvest-call-site` **awaits
the OWNER'S MERGE** (DECISIONS 71 a) — the only part of finishing that is not the
agent's. Nothing was pushed; `main` untouched. The one thing this task found and
did not fix is **P20** (the canned servers' `do_GET` traceback), which is not its
concern and is not a red.
