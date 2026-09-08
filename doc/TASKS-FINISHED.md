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
  ratatui capture/geometry list (followup 4), and the owner's
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

