# TESTING.md - Test Infrastructure and Verification Methods

Part of the spit.py documentation set (see `PROJECT.md`).

## Running tests

- Everything: `cd ~/spit.py && bash spit_app/tests/run_tests.sh`
  (prints one line per suite: `<suite>: PASS: n  FAIL: 0`)
- One tool suite: `cd ~/spit.py/spit_app/tests/tools/<suite> && bash run_tests.sh`
- One unit file: `cd ~/spit.py/spit_app/tests/unit/<suite> && python3 test_x.py`
  (each test file runs directly; its directory is on `sys.path`)

**The outer runner's one line per suite is `| tail -n 1`, and that hides a crashing
file.** A file that dies mid-run prints its traceback and no `PASS:` line, so the
suite's row simply counts the files that survived: the run of 2026-09-17 printed
`unit:chat_window: PASS: 54 FAIL: 0` while **two of its three files were dead** (a
missing import in one, `max()` on an empty list in another) - FAIL 0, and the
tracebacks only visible because stderr went to the terminal and not into the row. So
read the table above as a FLOOR and compare every row with it: a count that goes
down without tests being deleted is a crash (TRAPS #18), never a rounding. When a
suite has more than one file, run the files (or redirect the whole output somewhere
and read it) instead of trusting the row.

Tests run WITHOUT the app and without Textual. Tool *scripts* are pure
stdlib; the sandbox unit tests drive `Run` through `stub_app.py`
(StubApp/StubChat/StubMain - the three things the app would provide).

## Ground truth - expected counts (all zero failures)

| suite | checks |
|---|---|
| delete_lines | 127 |
| insert_line | 119 |
| patch | 107 |
| read_files | 32 |
| grep | 30 |
| search_replace | 29 |
| rename | 68 |
| diff | 24 |
| tools total | 509 |
| unit:anchored | 68 |
| unit:arguments | 131 |
| unit:chat_smoke | 168 |
| unit:chat_window | 568 |
| unit:endpoints | 547 |
| unit:handoff | 60 |
| unit:journal | 69 |
| unit:recovery | 55 |
| unit:prompt | 38 |
| unit:render | 278 |
| unit:run_script | 121 |
| unit:sandbox | 157 |
| unit:system_note | 219 |
| unit:terminal | 346 |

## The test venv (six suites need it)

`unit:terminal` drives a **real tmux** through `libtmux`; `unit:anchored`,
`unit:chat_smoke` and `unit:chat_window` drive a **real headless Textual**
(`App.run_test` - frame and geometry accuracy cannot be checked against a stub).
`unit:endpoints` needs **httpx** - the module under test,
`spit_app/endpoints/llamacpp.py`, imports it, and the bare system python3 does
not have it (measured: `ModuleNotFoundError: No module named 'httpx'`) - and
**Textual** too, because its counts-row file drives `chat_settings` headless.
`unit:handoff` (P14) drives the real `Chat`, `SidePanel`, `Work` and `ToolCall`
headless over a canned 127.0.0.1 SSE server - and its gate probes
`textual, httpx, libtmux, ddgs, playwright`, because `ToolCall` loads the whole
tool tree and that tree imports all of it (TRAPS #19: the dependency is what
the code UNDER TEST imports, not what the test file happens to import).
The bare system python3 has no app dependencies (TRAPS #19), so all six need a
venv. Build it once:

```
bash spit_app/tests/create_venv.sh        # -> ~/.venv-spit, everything in requirements.txt
```

The `unset PIP_USER PIP_BREAK_SYSTEM_PACKAGES` inside that script is not
decoration: this environment exports both so installs work against the system
interpreter, and a virtualenv refuses a `--user` install outright, so without
them the very first install fails and pip leaves an empty venv.

The suite picks its interpreter in a fixed order -- `$SPIT_TEST_PYTHON`, then
`~/.venv-spit/bin/python3`, then `python3` if it imports libtmux -- and **a
missing dependency is a FAIL, not a skip**. A suite that prints
`PASS: 0  FAIL: 0` because it could not start is indistinguishable from one that
ran and passed, which is the mistake `39ceb2f` fixed for discarded failures; this
row goes red and names the command that fixes it. Every suite here still passes
on a machine with the venv and no app runtime.

(`unit:chat_window` was re-measured 2026-09-17 at **270** - the WP-D file
`test_window_triggers.py` (172 checks) added to WP-C's 98 by addition alone, the two
WP-C files changed only by a `freeze_triggers()` call each, every other row
byte-for-byte where WP-C left it, and three consecutive full runs byte-identical.)

(`unit:chat_window` is **568** since WP-E: the new file `test_window_edits.py`
(298 checks) added by addition alone - the three WP-C/WP-D files untouched, every
other row byte-for-byte (tools 509, anchored 68, arguments 131, chat_smoke 168,
prompt 33, render 278, run_script 121, sandbox 119, terminal 223 as it then stood), two consecutive
full runs identical, and the chat_smoke `golden.txt` md5
`8ae9d1186a59627d30d05dee95f0ad95` unmoved: the WP-B differential is intact.)

(The sandbox row was re-measured 2026-09-04 at 119 - `test_prompt.py` and
the failure-counting fix raised it; the table lagged. Counts only ever go
up, per the rule above.)

(It is **157** since `fix-tool-interpreter-path-shadowing`: one new file,
`test_python_path.py`, 38 checks, by addition alone - every other row
byte-for-byte where it was (tools 509, anchored 68, arguments 131, chat_smoke
168, chat_window 568, prompt 33, render 278, run_script 121, terminal 223 as it then
stood — it is 346 since P0b-followup 4, see the `unit:terminal` note below).
29 of the 38 are red against the pre-fix interpreter, which is the point of the
file: the first section is the control that shows a `types.py` in the working
directory really does poison a stdlib-only script, so the checks after it cannot
pass on a fixture that cannot fail. Its section 4 is the check that keeps the
*semantics* honest - a relative `path` must still edit the file in the carried
cwd and not the same-named one in the sandbox home - because the alternative
fix that was rejected moves the tool rather than closing the door (DECISIONS 78,
TRAPS #25).)

(`unit:terminal` was re-measured at 119 when `test_event_loop.py` landed on the
`task-terminal-empty-output` branch: 98 → 119 by addition alone, every other row
byte-for-byte where it was. It is 173 now, from the same branch: 119 → 129 for the
`term_new` guard (`t9`, 6 of them red without the guard), → 136 for the private tmux
socket (`t10`, 3 red without it), → 173 for `remain-on-exit` and the dead-session
report (`test_screen` `t10`-`t13`, `test_lsterm` `t5`, `test_tool_call` `t11`; 22 of
the whole set red against the pre-change backend). No existing check was deleted or
re-numbered; the only existing assertions that changed are the three `test_lsterm`
death-waits, re-pointed from `window_exists()` to `window_dead()` because
`remain-on-exit` makes "the window is still there" true for a dead session — a
question that now means something different, not a check that was wrong.)

(`unit:terminal` is 220 with the tmux state layer (DECISIONS 70), same branch,
same rule: 173 → 220, every other row unmoved. +37 `test_screen` `t14`-`t17`
(id registry and tmux-side window names; the last terminal reported taking the
session and the server down; the cost of a call counted in `tmux` invocations —
2 for a capture, 1 for a listing — and the stale-id alias guard, both guards of
it), +7 `test_tool_call` `t7`, +2 `test_event_loop` `t3`, +1 in `test_screen`
`t6`. Against the pre-layer backend 18 of `test_screen` and 2 of
`test_tool_call` go red — `t6` (3), `t14` (4), `t15` (1: the stray window still
holds the session open), `t16` (6), `t17`'s stamp half (4) — while
`t17`'s alias half is green on BOTH codes (copying another chat's registry ENTRY
is caught even by the old membership check — it pins the guard's intent, it does
not discriminate the codes), and `test_lsterm`, `test_keys` and
`test_event_loop` stay green on both (t3's checks measure the dispatcher's hop,
which both codes have; they go red only under section 2's control).
`t3`'s ratio check became a BURST comparison (5 captures on the loop against 5
through the hop, same 0.5 margin): at ~16 ms per capture the single-call gap it
compared had nothing left to separate — the check got weaker-looking precisely
because the tool got faster, and the burst measures the hop's real job. The two
re-worded assertions (`t6`, `t7` — one each, numbers and check-counts kept)
are the deliberate behaviour changes DECISIONS 70 records: "no such session" is
now a distinct answer from "session dead".)

(`unit:terminal` is 223 after the two machine-dependent reds the owner reported
(217/3 there, 220/0 here). +3 `test_screen` `t18`, and no check changed verdict:
`main` vs branch on this box 220/0 -> 223/0. The two reds were never the tmux
backend — one capture with no `wait_for_prompt()` in front of it, and a harness
reading the pane with different capture flags than `live_screen()` uses. The
whole diagnosis, including the four-way `HOME` decomposition that reproduced the
owner's exact three check names, is DECISIONS 73 and the `TASKS-FINISHED.md`
entry for branch `test-terminal-pane-read-parity`.)

(It is **346** since P0b-followup 4 (`task-terminal-harness-p0bf4`): the new file
`test_harness.py`, **123 checks**, added by addition alone — the five existing files
untouched, every other row where the table says it is, `chat_smoke`'s golden md5
`8ae9d1186a59627d30d05dee95f0ad95` unmoved, the full suite exit 0. Its sections are
the item numbers of the harness list in the task docs: `command`/`env`/`cwd` and the
argv that exits too fast to be retained, geometry at creation and `resize` (per
WINDOW, measured), the three capture modes and the grid limit that no mode escapes,
the cursor as data versus the `█` splice, scrollback and the diff's baseline rules,
`wait_for` in all six kinds with the abort stamped from another thread, `send_bytes`
byte-exact against libtmux's key layer losing a leading-dash payload, `screen_json`
live/dead/absent, `close_chat` with the sessions counted **relative** (every section
shares one private socket, so tmux holds the earlier sections' sessions too — an
absolute count is a property of the file's order), the tool's own argument wiring,
and one real bwrap launch guarded by `shutil.which`. It keeps the directory's two
properties: a private socket, and at exit stale socket FILES with **no running
server** (`tmux -L spit-unit-terminal-harness ls` fails after a run). Every group was
verified red by substituting its defect — DECISIONS 83 (h) lists which mutation
reddened which checks, including the two harness-side reds it found in this file.)

`unit:prompt` is new: `tests/unit/prompt/` drives the real
`Work.prompt()` with httpx/Textual stubbed out (`stub_modules.py`, TRAPS #19),
so the one string the model reads about its tools is covered without the app.
It is **38** since P19/WP-3 (was 33): `t8` walks `spit_app/tools/` and needs no
edit when a tool arrives - it requires a `PROMPT` of every module and counts one
`## ` heading per tool - and the +5 is `t9`, the group that says *what* arrived
(`## journal` is its own heading at the start of a line, its block is not glued
to the next tool, and it tells the model to journal before a handoff, in the
fields a record of work has). A new tool moving this row by ADDED checks and not
by a red is the point: the count going up is the expected outcome of adding a
tool, and a red would mean the new tool broke the assembly.
`unit:run_script` (121) covers a tool *module* two ways - a spy `Run`
(`stub_run.py`) for the call it makes, and the real bash/python3/perl for the
payload it builds, because a wrong payload is a parse failure and only the real
interpreter sees one. Its two perl checks report a verdict (`absent` / `ran` /
`refused`) against the machine they run on, so the count holds wherever it runs
while a perl that is installed and broken still fails. `stub_run.build()` takes
`allowed=`, the `interpreters` setting to run the call under, which is how the
allow-list sections (9-11) test both narrowing and widening; note that a call
naming an interpreter outside the default list now has to widen it first just to
reach the payload question - the tests obey the rule they check.

A count going down without you deleting tests is a bug (see TRAPS #18: the
runner once discarded failures - fixed in `39ceb2f`). New checks only ever
raise a suite's count. Numbers inside a suite are append-only (TRAPS #15).

## Tool suite anatomy

`spit_app/tests/tools/<suite>/` contains **exactly three files** (invariant
to re-check after any edit):

- `setup.json` - `{"script": "<relative path to tool script>", "common":
  "<path>" (if the tool uses get_script with a common), "args": [...]}`
- `run_tests.sh` - runs checks through the shared `harness.py`; ends by
  creating fixtures, running checks, removing fixtures (exit trap;
  `KEEP_FIXTURES=1` keeps them for inspection)
- `create_fixtures.sh` - purely declarative: shebang, source,
  `fixtures_selftest`, then `testfile` lines **in test order** and nothing
  else; a derived expectation is generated inside the test that uses it.

Shared machinery (one level up): `harness.py` (prepends a `get_args`-style
head + the optional `common` script, pipes the whole thing into the bare
python3 - exactly how `Run` delivers it), `test_common.sh` (assertions incl.
byte-level `assert_cr_lines`/`assert_no_cr`/`assert_last_byte`, and
`remove_fixtures`), `fixtures_common.sh` (`testfile`/`testfile_bytes` writers,
`printf '%b'` escapes: `\n \r \t \0nnn`; double a literal backslash).

`fixtures/` is generated, gitignored, disposable. Naming: `tNN-<short-name>`
owned by test NN and by nobody else (must-not-exist paths count as fixtures -
they are simply never created); `shared-<name>` for genuinely shared content;
`corpus/<name>` for patch's multi-file corpus; grep's nested tree is one
`tNN-src` fixture. Round-trip tests that `cd` elsewhere must still pass the
harness **absolute** fixture paths.

## Writing checks

- Pass the complete arg set on every harness call - repeated `--flag` values
  silently use the FIRST (TRAPS #9). Wrap in a helper function per suite.
- Assert on distinctive tokens, not single letters (TRAPS #8).
- Terminator expectations need the byte-level assertions, never file
  comparison alone (TRAPS #11).
- Anything documented as "pasteable into patch" needs a round-trip test:
  extract the preview diff (awk `^--- ` to the summary line), apply it via
  the patch harness, compare with the file the tool itself wrote. (This is
  how missing `\ No newline at end of file` markers were caught.)

## Unit suites

- `tests/unit/chat_smoke/` - the WP-B differential (168 checks) for the
  `ChatView` index-accessor seam. `smoke_scenario.py` drives a real `Chat`
  headless over a generated fixture chat - mount, focus, `edit_on/off`, the
  message-level add/remove actions, the three stream signals, undo/redo of
  insert and remove, abort with a fake worker, plus a second headed run for
  `action_add` (reachable only with an empty chat) - and dumps plain data per
  step. It uses no new API so it can drive the pre-refactor tree too; the
  golden dump was generated from `f201700` by the recipe in
  `test_chat_smoke.py`, which adds the accessor contract (window_start 0, the
  `len(children) == len(messages) - window_start` invariant at every step, the
  forward/reverse maps agreeing with the raw child list, None from `widget()`
  and IndexError from `require_widget()` out of window). The app is a stub (in-
  memory `read_json`/`write_json`, `endpoint_list*`, a fake `#side-panel`), not
  `SpitApp` - the real app starts the llama.cpp server and reads the user's own
  settings and chats, which would make the dump machine-dependent. Venv-
  dependent, FAIL-with-remedy like `unit:anchored` (TRAPS #19).
- `tests/unit/anchored/` - the `AnchoredScroll` container (68 checks), the P8
  probes (`/tmp/anchor-probe/`, see `TASKS-PLANNED.md` P8 and
  `UI-ONDEMAND-LOADING.md` WP-A) rebuilt as permanent checks. Runs a **real
  headless Textual** (`App.run_test`, the venv - TRAPS #19), so no stubbing:
  the instrument is a spy on `App._display` - one call is one emitted frame -
  which is what turns "the correction lands in the same frame" into an
  assertion (`0 jump frames` == no emitted frame shows the tracked widget at
  the wrong screen row). `test_oneshot.py`: the plain-`VerticalScroll` defect
  as the control (every painted frame shows the jump), single + batched
  mounts above, bottom-anchor (`Widget.anchor`) coexistence, manual scroll /
  follow-bottom after a correction, disarm-if-anchor-gone. `test_pin.py`: the
  persistent pin - user-scroll re-baseline, mount above, late growth above,
  unpin returns the defect, anchor-removed re-baselines without a phantom
  correction. `test_eviction.py`: the sliding window - evict-above holds the
  view and shifts `scroll_y` by exactly the evicted height, evict-below moves
  nothing and corrects nothing, remount-below holds, 20x churn keeps the
  mounted count flat (worst 13 at viewport 10 / margin 20 - the window, not
  the history). The shared harness is `anchored_app.py` (not `test_*` on
  purpose, the `stub_app.py` precedent).
- `tests/unit/chat_window/` - the WP-C **sliding window** (98 checks): a real
  headless `Chat` over a **generated** 1000-message fixture, asserting the window
  and never the data (`Chat.messages is ChatView.messages` is a check). `t1` open:
  exactly `INITIAL_WINDOW` (50) mounted, window `(950, 1000)`, at the bottom, no
  JSON written; `t1b` gives it teeth (a 120-message chat also mounts 50 - without
  windowing the number is unreachable). `t2` slide: `load_older(25)` moves `lo` by
  −25, the tracked anchor holds, **0 jump frames**, exactly one correction; **`t2c`
  is its control** - the same operation with `arm_top_anchor` disarmed paints the
  jump and leaves `scroll_y` alone, which is what makes `t2`'s zeros evidence
  rather than an accident (TRAPS #13). `t3` evict-below moves neither `scroll_y`
  nor the correction counter, and `load_newer` remounts into the gap holding (rules
  2-3). `t4` `prune()` at the open state evicts above back to the margin with
  `scroll_y` shifting by exactly the evicted height clamped at the new max, 0 jump
  frames, and a second `prune()` is a no-op (steady state). `t5` the fact-5 pins
  bound each walk (an `is_edit` widget stops the above-walk after the one unpinned
  widget above it; the streaming tail while `is_working()`, and a focused widget
  below the viewport, block the below-walk). `t6` abort-while-scrolled-up
  materializes the tail and removes it from **both** sides. `t7` `materialize()` at
  both edges, `IndexError` for −1 and for `len(messages)`. `t8` 8× churn: mounted
  count flat and ≤ `INITIAL_WINDOW` at every depth, 0 jump frames, chat-JSON md5
  fixed and zero writes. `t9` the chat-switch interplay pinned as it works today:
  every opened `Chat` stays mounted in `#main` (hidden, never stacked twice), each
  `ChatView` keeps its own window, and a **hidden** chat is never a prune target.
  Two harness facts worth knowing before writing another UI suite here: the stub app
  and `FakeWork` are **imported from `chat_smoke/smoke_scenario.py`** rather than
  copied, so the two suites' stubs cannot drift (cross-suite import is new, and the
  close-out says so), and `WindowApp` adds the app's own `spit_app/styles.css`
  because **without the stylesheet the messages lay out at zero height and every
  viewport computation goes vacuous** - TRAPS #24.
- `tests/unit/chat_window/test_window_triggers.py` - the **WP-D scroll triggers**
  (172 checks, so `unit:chat_window` is 98 + 172 = 270): a real wheel notch
  (`window_harness.wheel_event`, forwarded with `app.screen._forward_event`) drives
  `watch_scroll_y`, never a `scroll_to`. `t10` the headline - 200 notches up through
  the 1k fixture page history in **and** prune the bottom, mounted count flat, 0 jump
  frames per settle, with the frozen-triggers control that makes the flatness
  evidence (TRAPS #13); `t11` the debounce as a mechanism (`arms == watches`) and as
  a ratio, not as a constant; `t12` the prune **behind every load**, both arms walked
  into the same sliding state and both with the settle taken away, so the only prune
  left is the one each page operation runs (15 mounted, flat; control with the prune
  stubbed: 18 → 63, past `INITIAL_WINDOW`); `t13` the walk back down, driven to the
  STATE with a ceiling rather than for a fixed number of bursts; `t14` the
  follow-bottom release measured three ways; `t15` the parked-at-the-window-bottom
  starvation the settle's edge re-check exists to close, with the defect itself as
  the control; `t16` the true ends; `t17` the freezes (`is_edit`, a working chat, a
  page operation in flight); `t18` the guard save/restore on `materialize()`; `t19`
  the anti-oscillation fixed point; `t20` **`prune()` takes the page-op guard** -
  asked from inside the removal batch, which is where the settled `set_timer` task
  and the `call_after_refresh` page operation interleave, and the one check that
  pins a real code bug (without the guard the two `window_start` writes - `_grow_up`
  assigning absolutely, prune adding the eviction count - corrupt the mounted range:
  2 of 3 forced runs inconsistent). The two WP-C files now call
  **`freeze_triggers(view)`** after their `load()`: the triggers are live on every
  `ChatView`, so a setup `scroll_to` would page and prune on its own account and
  rewrite the page-operation arithmetic those checks measure (the combined walk is
  `t10`'s subject).

  Two instruments were added to `window_harness.py` for this file, and both are the
  same lesson `unit:terminal` wrote down - **wait for the widget's state, not for
  your own clock**. `SCROLL_SETTLE_DELAY` is a 0.15 s **wall-clock** timer while a
  headless notch costs a frame plus the pump (measured 66-71 ms), so burst timing is
  not a thing a suite can control: a 200-notch burst fired **17 settles** and a
  30-notch burst taken where every notch mounts fired **3**. `freeze_settle` /
  `thaw_settle` therefore remove the debounce so "this burst never settles" is a fact
  about the widget (that is `t12`'s premise, asserted as
  `t12-the-burst-really-never-settled`), and `rest(pilot, view)` / `at_rest(view)`
  wait for quiescence before any invariant is sampled, because
  `window_consistent()` is an invariant of QUIESCENCE - sampled mid-page-operation
  it read False 231 times in four walks and **zero** times sampled at rest, with
  nothing wrong either time.
- `tests/unit/chat_window/test_window_edits.py` - the **WP-E edits/undo/focus across
  the window edges** (298 checks, so `unit:chat_window` is 98 + 172 + 298 = 568):
  `t21` `mount_message` at every index class (the insert-below-the-top branch is
  `window_start += 1` + a `materialize`, never a front mount - the pre-WP-E front
  mount left a one-message HOLE even for the adjacent index; the in-window branch
  is the neighbour mount and is pinned as NOT delegable, because between the insert
  and the mount `widget(index)` is the right-hand neighbour); `t22` the crash with
  no keypress - `check_action("add_message_next")` asked a widget for the next
  message's role and raised out of `refresh_bindings` with the bottom pruned; it
  answers from the data now, and the row asks the same question pruned and mounted
  in both answer directions. `t23`/`t24` the undo insert/remove primitives at every
  edge class and through the real `append_undo` + `action_undo`/`action_redo` path
  (the chat is WRITTEN now - a DELTA, never absolute - and a below-window removal
  tracks the reader as a WIDGET, since lo sliding renumbers every index); `t25`
  `_change` data-first with the entry holding the PREVIOUS state (the setup lesson:
  an entry built from the CURRENT dict writes the current state over the current
  state - "no change", three reds, nothing wrong with the code); `t26` the ONE
  focus rule both removal sites use, with the `widget_was_removed` question pinned
  (a bare `widget(index) or widget(index-1)` drags focus for the streaming-error
  path's removal at `index == window_hi`); `t27` the owner's ruling - `prune()`
  REFUSES while `is_edit`, held live through `action_edit_on`, released by the first
  settle after `edit_off`, measured by **lo** because a settled settle is prune PLUS
  the edge re-check and the parked reader gets a page back below; `t28` the mode is
  inherited AT MOUNT (target and gap widgets), so `show_cots`/`reset_message_edit`
  need no replay code; `t29` the undo primitives hold the page-op guard and give
  back what they found. Two instrument lessons from this file, both reds that
  blamed the code and were about the harness: **the setup's `freeze_triggers` is
  part of the state a later row reads** - a row exercising a trigger path must
  `thaw_triggers` and assert the triggers LIVE first, or the harness answers for
  the thing under test and a "dropped" green is about nothing (t27-live, t29) - and
  **an undo "change" entry holds the PREVIOUS state** (t25).
- `tests/unit/arguments/` - schema coercion, paths, pipeline (131 checks).
- `tests/unit/terminal/` - the tmux backend and the two tools on it, against a
  **real tmux on a private socket** (`libtmux.Server` is wrapped to pass
  `socket_name`, so a user's own server never gets a window created in it or
  input sent to it). `stub_app.py` supplies the three things `Terminal` asks the
  app for and nothing else, plus `wait_for`-style polling — every timing
  expectation is a poll with a ceiling, never a fixed sleep. Three traps it had to
  step around: `capture_pane()` returns **lines**, so `token in lines` asks
  whether a line *equals* the token and silently never matches a token sharing
  its line with a prompt (`screen_of()` joins first); `pane_active()`
  **forgets** a dead window as a side effect, so a test that waits for death by
  polling it has cleaned the registry the code under test needs dirty —
  `window_dead()` is the non-mutating probe for "has the process exited"; and the
  harness must capture with the **same flags as `live_screen()`**, `join_wrapped`
  included — tmux hands a wrapped line back as two rows, so a token that crossed
  the right edge is on the pane, inside the tool's own report, and in nothing the
  tests can see (measured: an 80-column pane with a `PS1` of 75-79 columns made
  `test_keys` t3 red for its whole 15 s ceiling on one machine and green on
  another; DECISIONS 73). The general form of both, and the reason they are in
  this file rather than in a comment: **assert on what the tool is able to report,
  and wait for the pane's state, not for your own clock.** The pane's shell is the
  user's own bash with the user's own rc files in a window whose width is tmux's
  default, so neither how fast the prompt appears nor how wide it is belongs to the
  code under test — which is also how `t2` came to assert on a brand-new window
  before its shell had drawn anything: an undrawn pane captures as *nothing* (tmux
  prints the blank rows, libtmux strips them, `capture_pane()` returns `[]`), so
  `live_screen()` has no row for the cursor marker and the report is the header
  alone. `t18` is the guard for the flags and it says its own precondition — that a
  wrap really happened — because without one its assertions would prove nothing.
  `window_exists()` still exists but it asks a different question now — "does tmux
  still hold the window" — and since the windows are made with `remain-on-exit` the
  two answers differ for every dead session, so picking the wrong one is no longer
  merely untidy, it waits forever. Both were found by running the
  suite against the unfixed code and watching it pass when it should have failed.
  Reading the registry and reading tmux are two different questions since the state
  layer: `window_id_of()`/`registered_window_id()` read the registry (which window_id
  a name was given — ids now, and `window_id_of` also accepts the object-shaped
  registry so the harness still fits the code under a differential), while
  `tmux_panes()` (one libtmux `Server.panes` = one `list-panes -a`),
  `tmux_window_names()`, `session_window_ids()`, `tmux_session_ids()` and
  `registered_ids_are_all_the_windows()` ask tmux, independently of the tool — a
  test that believed the tool's own snapshot would be testing the tool's own
  snapshot. `counted_tmux_invocations()` records EVERY `tmux` process libtmux
  starts (all seven of the modules that imported `tmux_cmd` into their own
  namespace are wrapped — wrapping one counts nothing) and stores the SUBCOMMAND,
  not `args[0]`, which is the `-L<socket>` flag on every single call; that is what
  lets `test_screen` t16 pin "a capture is 2 invocations, a listing is 1" instead
  of hoping nobody quietly adds a round-trip back.
  `test_event_loop.py` (23 checks, the row's 98 → 119) is the one file that
  drives the *dispatcher* — the real `tool_call.ToolCall.call()`, the thing
  `chat/work.py` awaits — rather than calling `call()` directly, because the
  property it pins belongs to the dispatcher's `asyncio.to_thread` hop: a
  `delay=1` call costs the event loop a 22 ms worst gap, not a second. It carries
  the control that produces the freeze on demand (the hop removed), and its
  section 3 compares two gaps measured in the same process (medians of three), so
  the assertion is about the hop and not about how fast tmux is on the box.
- `tests/unit/terminal/test_harness.py` (123 checks, the row's 223 → 346) is the
  harness list of the task docs turned into checks: sections 1-12 are its item numbers
  (start a program under test with `command`/`env`/`cwd`; set and resize the geometry;
  the three capture modes and what none of them can see; the cursor as data; scrollback
  and the diff baseline; `wait_for` in its six kinds and the abort that ends it;
  `send_bytes` byte-for-byte against libtmux's key layer as the control; `screen_json`;
  `close_chat`; the tool's own argument wiring; one real bwrap launch). Two things it
  adds to the directory's own lessons, both because a check of its own was red for the
  wrong reason first: a session started with `command` has no shell to read what is
  typed (the tty echoes it as literal text, so a `printf` "sent" to a `sleep 60` pane
  never runs), and sessions are counted **relative**, through a surviving chat's server
  object, because every section shares one private socket and an absolute session count
  is a property of the file's order.
- `tests/unit/sandbox/` - script wrapper and delivery: trailer, state
  (env/cwd carry-over), streams (stderr separation), lifecycle (background -
  MUST use sandbox=False, TRAPS #6), delivery, prompt (asserts the
  run_command PROMPT tells the model the truth), and `test_python_path.py`
  (the `TOOL_PYTHON` isolation: a poisoned cwd and a poisoned `PYTHONPATH`
  from the state, driven through `sandbox_env.sh` with the program on stdin
  exactly as the file tools deliver it, plus the control that the bare
  interpreter dies there). Runner globs `test_*.py`
  and sums `PASS: n  FAIL: n` lines; `stub_app.py` deliberately does not
  match the glob - renaming it would make the runner treat it as a suite.
  Lifecycle/delivery/streams drive everything through the shared
  `run_as_file(...)` -> `(output, leftovers, elapsed)`.

- `tests/unit/system_note/` - the P13 system notes (**219** checks = WP-B's 96
  plus WP-C's 123, by addition alone): the **generator** `spit_app/chat/system_note.py`
  (the hook contract and its five invariants) and the **token-status hook**
  `spit_app/chat/token_status.py`, on plain dicts and stub chats - no Textual,
  no endpoint, no network.
  `test_generator.py` owns **t1-t9** and `test_token_status.py` owns **t10-t18**
  (append-only within the suite; the
  `unit:endpoints` numbers are a separate sequence, and t13 there belongs to
  WP-D). `t1` is the gate with TRAPS #19 **inverted**: the runner has no venv
  preamble because the module imports nothing of the app's runtime (`spit_app/chat/`
  is a namespace package), and t1 asserts no `textual`/`httpx`/`libtmux` landed in
  `sys.modules` - so a module that later grows such an import reddens here instead
  of quietly becoming venv-bound. Measured both ways: with an `import textual` added
  to the module, the bare run reports `PASS: 0  FAIL: 1` naming the file that died,
  and a run under `~/.venv-spit` (where the import cannot kill the file) reddens
  `t1-importing-it-loaded-no-app-dependency`. The five invariants are t2-t6 -
  asked at every index; at most once per hook per message (idempotence over N walks
  *and* over a reloaded chat, because the standing note is itself the record);
  silence (`None`, or empty text) writes nothing, asserted on the key SET of every
  message; the `messages` LIST untouched - object identity, length, per-message
  `id()`, and every other key byte-identical - which is P13's whole constraint; a
  raising hook propagates, unwrapped, with no rollback of what was already written.
  `t7` pins the stored entry (`{"hook", "level", "text"}` dicts - not namedtuples,
  which would persist as JSON lists - under the private key `system`) that
  `unit:endpoints` t12 unpacks from the wire side; `t8` refuses a `notice()` return
  that is neither `None` nor a `Note`, naming the hook; `t9` the name that stamps
  `hook` and keys the once-per-message rule. Every group was verified red by
  substituting its defect (skipping the tail, dropping the idempotence guard,
  writing an empty `system` key, appending a note as a message, `except:`-ing the
  raise, accepting a bare string, ignoring the `name`), so no green in this suite is
  one that cannot fail (TRAPS #13/#14).
  `test_token_status.py` (t10-t18, 123 checks, P13/WP-C) pins the hook itself:
  the t10 gate re-runs the TRAPS #19 probe over `token_status.py` (re-measured
  both ways - bare interpreter dies, under the venv the dependency check
  reddens); silence below every trigger, at zero usage, with no counts and with
  an unknown window, each with the control that makes the same hook speak;
  tail-only (a note mid-chat is the cached-prompt defect); the rank machine on
  a 128k walk whose fill drops back; the owner's percentage-OR-remaining table
  at its exact tokens - the 20 000/10 000 floors governing 64k, the 80%/90%
  governing 128k and 200k, the 32k announce-order pinned as
  `small_window, warning, critical` with `info` shadowed forever, and
  `small_window` once, at 0% fill, never at `total` one over, winning its
  message with the fill-rank pending for the next; the four model-facing texts
  pinned **byte-for-byte** at fixtures where used/total/remaining/pct are all
  distinct (a swap cannot pass; the figures are never clamped - an overrun
  says 101% and a negative remaining, because they are the server's numbers);
  WP-B's drop rule met by a hook whose memory is its own standing notes (a
  verdict dropped off the tail rides the next message; the hook keeps no
  state on itself, so reload, abort and a dropped note all need no resync);
  and totality - rubbish counts and rubbish windows (None, prose, lists,
  floats, bools, a non-callable accessor) answer silence and keep the request
  alive, since WP-D attaches right before `endpoint.stream()` and nothing
  there catches. Fifteen defects substituted, each reddening its group (text
  swaps, pct floor-instead-of-round, a clamp, levels in trigger order, no
  rank filter, no tail guard, the small-window boundary strict-less and
  repeating, every totality guard), so again no green here is one that
  cannot fail (TRAPS #13/#14). The hook IS registered now: `chat.py` appends ONE
  `TokenStatus` to the module `HOOKS` at its import and every `Chat` carries that
  same reference - the hook keeps no state about WHICH chat, so sharing is its
  natural shape (DECISIONS 81 e) - while the generator is per chat. Nothing in
  this suite depends on that: `chat.py` is not in the bare interpreter's import
  graph, which is why the row stays 219 venv-free, and the wiring is proved
  where the app is real, by `unit:endpoints` t13.

- `tests/unit/journal/` - the P19/WP-3 **journal** tool (**69** checks, t1-t8),
  on the **bare python3 with no venv preamble and that absence is the gate**
  (TRAPS #19 inverted, the `unit:system_note` precedent): measured, loading
  `spit_app/tools/journal.py` puts no `textual`/`httpx`/`libtmux`/`ddgs`/
  `playwright` in `sys.modules`, so `t1` asserts that stays true and a future
  app import reddens HERE instead of quietly making the row venv-bound. The tool
  is loaded by `load_module_from_path` from the real tool tree (the function
  `load_tools` uses), driven with a two-field stub app - `settings.path["data"]`
  and `settings.tool_settings`, and that small surface IS the point of building
  it in-process - and its data home is the generated, disposable
  `./fixtures/journal-data` (`KEEP_FIXTURES=1` to inspect; the journal dir itself
  is NOT pre-made, so a refusal to create it cannot hide behind the setup).
  What it pins: `entry` WRITES one timestamped MULTI-LINE entry into
  `journal/<chat-id>.txt` and the answer is checked against the file's bytes
  (t2); no `entry`, a `None` entry and a blank one all READ (t3); the read cap
  cuts at an **entry boundary** and a cap smaller than the newest entry shows
  that entry WHOLE, while the journal file itself stays uncapped (t4);
  `journal_max_chars` is a setting, with blank / string / zero / negative / bool
  / float all answering the default and a small legal value still cutting as the
  control (t5); append-only, fields are ONE entry, and a body line opening with
  `[` is body not a second entry (t6); one file per chat, so what one chat wrote
  is neither readable nor writable through another (t7); and every refusal - a
  chat id outside `chat-<chars>` including `a\b`, a non-text `entry`, a journal
  path that is a file - writes NOTHING and has the control that the good value
  writes (t8). Two real defects the new checks caught in the first draft, both
  recorded in DECISIONS 85: the cap read back out of the module `SETTINGS` dict
  (process state - one chat's 300 became the next chat's) and the `..`-style
  id check that a whitelist replaces. `run_tests.sh` is executable, and the row
  that shows a shell `Permission denied` instead of a `PASS:` line is the outer
  runner's `| tail -n 1` hazard (TRAPS #18) wearing a different hat.
- `tests/unit/recovery/` - the P19/WP-4 **failure recovery** (**55** checks,
  t1-t6). It IMPORTS `tests/unit/handoff/handoff_harness.py` rather than
  rebuilding it - the real `Chat`, `SidePanel`, `Work` and `ToolCall`, the
  sidebar-mounted fixture, `until`, `quiesce`, `new_id_from`, the counters - and
  adds the two things a recovery needs and a handoff never meets: a canned server
  that answers every request for a reply with 503 while `GET /models` keeps
  answering 200 (`RecoveryServer`: that split IS DECISIONS 84 b - the probe
  answered, the request did not), and an app with the `data` directory the journal
  lives in. `handoff_harness`'s module-level `FIXTURES`/`DATA` are pointed at this
  suite's own generated `./fixtures/recovery-data`, because `StubSettings.__init__`
  builds `path` from those globals and `ToolCall.__init__` wants `custom_tools`
  before any subclass could intervene. The dependency gate is `unit:handoff`'s
  verbatim (`textual, httpx, libtmux, ddgs, playwright`) - the same reason: it is
  what the code under test reaches through `ToolCall`, TRAPS #19.
  Every failure is driven the way a human drives it (`text_area.text`, then
  `action_submit()`), so no check hands `recover()` a convenient object, and
  `retry_attempts` is 1 with no delay because the retry counts are
  `unit:endpoints` t14's subject - this suite waits for the RECOVERY. What it
  pins: the continuation chat's file with its settings differing from the dead
  chat's in EXACTLY `desc` and `recovered_from` (a set of key names, so any other
  drift is named); the brief as its first message, carrying the dead chat's id,
  `chats/<id>.json`, the failure's class and text, the token line, the quoted
  turns with a long one cut and marked, and "Continue the work."; the brief
  RECORDED on the wire as a POST body with the refused request recorded beside it
  as the control; `app.exception` None (no modal) in every branch; the dead chat's
  notice naming the new chat. **The absence of a second recovery chat is not
  proved by timing**: t1's continuation chat is submitted into the same refusing
  server, so it fails for real and reaches the recovery itself, and t2 waits for
  THAT failure's notice before it counts the chat files (TRAPS #13). Depth 1 from
  the start (a chat PRE-STAMPED with `recovered_from`) creates no file at all. The
  DRAFT branch runs with the canned server STOPPED - the chat file exists, its
  `messages` are `[]`, its text area holds the brief and NO POST carries it, the
  control being t1 where the same marker reaches the wire. The journal is written
  by the REAL `journal` tool and asserted inside the brief, with the control that
  a chat which kept none gets one plain sentence and not `read_journal`'s
  writer-facing prose (DECISIONS 86 e). And the notice keeps the sliding window:
  `window_consistent()` holds with the notice having its own widget at the tail
  (DECISIONS 86 a). `recovery_reported(pilot)` waits for the notice because the
  new chat's FILE is the recovery's first act - asserting on the world the moment
  a file appears reads a recovery that has not finished.
- `tests/unit/endpoints/` - the P12 **token counts and context sizes** suite
  (343 checks; 442 since P13/WP-A's `test_system_note.py` brought 51 and
  P13/WP-D's `test_note_chain.py` brought 48, both by addition alone; **512**
  since P19/WP-2 - the new `test_retry.py` brought t14's **69** by addition
  alone, and `test_requests.py` moved 61 → **62**: t6's re-pin re-worded two
  checks with the behaviour and ADDED one control, numbers kept and the count
  not down. **547** since the harvest regression of 2026-09-30 - the new
  `test_harvest_wiring.py` brought t15's **35** by addition alone and no other
  file moved; the row had been green at 512 the whole time the chat's three
  counts sat at zero, which is the hole that file exists to make impossible
  (TRAPS #26, DECISIONS 88).
  Per file now **88/132/62/19/43/51/48/69/35** = 547):
  `endpoints/llamacpp.py`, `Work.harvest_usage()` and the
  chat-settings counts row, driven against a **canned stdlib `http.server`**
  bound to `127.0.0.1` port 0 - no live model, no port but loopback, no user
  data dir, no tool import. `run_tests.sh` gates **httpx and textual** (both
  probes in one `import`, FAIL-with-remedy and `PASS: 0  FAIL: 1` when either is
  missing, never a silent zero - TRAPS #19), globs `test_*.py` and sums the
  `PASS:` lines. Files: `test_payload.py` (t1 payload, t5 skip list, t8
  `native_address`, t9 auth header, 88), `test_stream_parse.py` (t2 every stream
  shape old-vs-new, t3 the empty-`choices` chunk that used to kill the stream,
  t4 the usage object, 132), `test_requests.py` (t6 the one-retry rule around
  `stream_options`, t7 the `/props` → `/slots` → override chain - both read the
  server's **recorded request lines**, because those behaviours *are* request
  counts and request order, **62** since t6's P19/WP-2 re-pin), `test_harvest_usage.py` (t10, driven with a
  `SimpleNamespace` because the harvest reads `self.endpoint.usage` and
  `self.chat.token_usage` and nothing else - 19), `test_counts_row.py` (t11, the
  counts row in a real headless widget tree, 43), `test_system_note.py` (t12,
  P13/WP-A: the private key `system` unpacks onto the wire as `user` notes after
  their carriers - merge onto a `user` carrier, never a second consecutive
  `user`, never a mid-conversation `system` - and the proof that a no-note
  payload is byte-identical to the pinned baseline `b799526` apart from
  `stream_options`, 51), `test_note_chain.py` (t13, P13/WP-D: **the wiring end
  to end** - a real headless `Chat` (the stub app extended with the `slots` and
  `path` a real `Work` asks) and a real `Work.work_stream()` against the canned
  server, whose RECORDED POST bodies are the wire: silence under threshold with
  the over-50% control speaking, the info note byte-for-byte as its own `user`
  item right after its carrier, a second request at the same level adding none
  with the higher-level control (the rank machine on the wire, and never
  downgrading back), the UI's `chat.messages` growing by streamed replies only,
  the `user`-carrier note MERGED so the request's message COUNT is the same
  with the note as without it (hazard 1 proven on the wire, not only in the
  helper), `context_window()` answering the int or the dash with the dash
  meaning silence and filling the cache costing no probe - no network on the
  request path - and the registration pinned as ONE `token_status` entry in the
  module `HOOKS` at `chat.py` import, one shared hook instance across chats,
  the generator per chat. The fixture's canned scenario carries NO usage chunk
  so `harvest_usage()` never moves a hand-set fill, and the mount's own probe
  is awaited before the test writes the window, so nothing can clobber it;
  verified red before the wiring and against substituted defects - attach after
  the stream, a guessed denominator, a per-chat registration, 48),
  `test_retry.py` (t14, the retry loop over request counts, 69) and
  `test_harvest_wiring.py` (**t15, 35** - THE HARVEST IS WIRED, the file the
  regression of 2026-09-30 left behind): a real `Work.work_stream()` against the
  canned server, and the counts, the row and the NEXT request's note read from
  it - the landed reply moves all three figures and the row shows them, the
  CONTROL of a reply with no usage chunk leaves all three exactly where they
  were, three corpses of an in-stream death are asked for and counted NONE (the
  shape that reddens a harvest in a `finally`, or ahead of the `try`, or in the
  retry branch), a retry's success is counted once, `context` FALLS on a smaller
  second reply while `generated` adds it, and the fill a reply earned is the
  figure the next request's `info` note quotes byte for byte. Three canned
  scenarios were added for it to `post_reply` and NOT to `SHAPES`, which is
  t2/t3/t4's differential table: `bigusage`, `usage-then-error`,
  `flaky-503-usage`. Verified red four ways - see DECISIONS 88). Shared code
  lives in `endpoint_harness.py` and `counts_harness.py`, deliberately **not**
  `test_*`:
  the runner's glob would turn a harness into a suite file (the `stub_app.py` /
  `window_harness.py` precedent), and `counts_harness.py` imports
  `chat_smoke/smoke_scenario.py`'s `SmokeApp` and overrides `endpoint_list()` -
  the stub answers `{}`, which is the *guard* path of `refresh_usage()`, so a
  suite built on it could never see a single context-size probe.
  Every differential file prints its INPUT MAPPING before it runs (TRAPS #13),
  and every comparison against the pre-step-1 code is preceded by
  `baseline_selfcheck()` - see "Differential verification" below.

## Differential verification (for changes to established behaviour)

A green suite cannot see a refusal that became an application, or a rename
that silently changed fixture bytes. The method that governs behaviour
changes (proven on the patch redesign):

1. Run the OLD script and the NEW script over **every** fixture with the same
   input; group results by (old verdict, new verdict).
2. Assert: every "applied -> applied" pair is **byte-identical**; each
   "refused -> applied" and "applied -> refused" case is intended and named.
3. Check the probe's own input mapping before believing it (TRAPS #13).
4. For pure renames/refactors: md5-multiset comparison of generated corpora
   per suite + `git diff main..HEAD` touching only the intended paths
   (TRAPS #14).

5. **Pin the OLD side by SHA, and prove it is old.** A differential whose
   baseline is derived at run time from `HEAD` silently becomes a comparison of
   the new code with itself the moment the change is committed - and it still
   prints tidy greens. Measured on this repo: the step-1 probe
   (`/tmp/p12_check.py`) took its OLD side from `git show HEAD:...` and rewrote
   `/tmp/p12_old_llamacpp.py` on every run. Correct while step 1 was
   uncommitted; re-run after the commit it printed `PASS: 47  FAIL: 3`, the
   three reds being exactly the checks that ask the old side to BE old, while
   its "identical to old" reconstruction pairs stayed green **vacuously**. So
   `unit:endpoints` execs `git show b799526:spit_app/endpoints/llamacpp.py`
   (md5 `38858cde93e6066ce24e39a908cd0a6a` - `a173854^`, the parent of the
   commit that changed the file, byte-identical to `main`'s copy) into a module
   of its own - from the git object, not a temp file, so nothing can be
   overwritten between runs - and every file that compares against it first
   runs `baseline_selfcheck()`: the pinned bytes, the parent-of-step-1
   relationship, "not the current file", and four facts that only the old file
   fails (no `stream_options`, no `get_context_size` / `native_address` /
   `auth_headers`, `extract_fields` raises `IndexError` on `"choices": []`). A
   differential that cannot fail is not evidence.

6. **Check the instrument by substituting the defect.** Breaking the mechanism
   on purpose is what turns a green row into a claim: writing the context-size
   answer under the *currently selected* pair instead of the pair the probe was
   started for left every in-flight-cancellation check green (the exclusive
   worker group cancels the probe, so the answer never arrives to be filed
   anywhere) and reddened only the arrangement where the switch starts no
   worker and the late answer does arrive. See `test_counts_row.py`
   `t11_no_bleeding`, which carries both arrangements for exactly that reason.
