# TESTING.md - Test Infrastructure and Verification Methods

Part of the spit.py documentation set (see `PROJECT.md`).

## Running tests

- Everything: `cd ~/spit.py && bash spit_app/tests/run_tests.sh`
  (prints one line per suite: `<suite>: PASS: n  FAIL: 0`)
- One tool suite: `cd ~/spit.py/spit_app/tests/tools/<suite> && bash run_tests.sh`
- One unit file: `cd ~/spit.py/spit_app/tests/unit/<suite> && python3 test_x.py`
  (each test file runs directly; its directory is on `sys.path`)

Tests run WITHOUT the app and without Textual. Tool *scripts* are pure
stdlib; the sandbox unit tests drive `Run` through `stub_app.py`
(StubApp/StubChat/StubMain - the three things the app would provide).

## Ground truth - expected counts (all zero failures)

| suite | checks |
|---|---|
| delete_lines | 127 |
| insert_line | 119 |
| patch | 80 |
| read_files | 32 |
| grep | 30 |
| search_replace | 29 |
| rename | 68 |
| diff | 24 |
| tools total | 509 |
| unit:arguments | 131 |
| unit:prompt | 33 |
| unit:render | 278 |
| unit:run_script | 121 |
| unit:sandbox | 119 |
| unit:terminal | 119 |

## The test venv (unit:terminal needs it)

`unit:terminal` drives a **real tmux** through `libtmux`, and the bare system
python3 has no app dependencies (TRAPS #19), so it needs a venv. Build it once:

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

(The sandbox row was re-measured 2026-09-04 at 119 - `test_prompt.py` and
the failure-counting fix raised it; the table lagged. Counts only ever go
up, per the rule above.)

(`unit:terminal` was re-measured at 119 when `test_event_loop.py` landed on the
`task-terminal-empty-output` branch: 98 → 119 by addition alone, every other row
byte-for-byte where it was.)

`unit:prompt` (33) is new: `tests/unit/prompt/` drives the real
`Work.prompt()` with httpx/Textual stubbed out (`stub_modules.py`, TRAPS #19),
so the one string the model reads about its tools is covered without the app.
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

- `tests/unit/arguments/` - schema coercion, paths, pipeline (131 checks).
- `tests/unit/terminal/` - the tmux backend and the two tools on it, against a
  **real tmux on a private socket** (`libtmux.Server` is wrapped to pass
  `socket_name`, so a user's own server never gets a window created in it or
  input sent to it). `stub_app.py` supplies the three things `Terminal` asks the
  app for and nothing else, plus `wait_for`-style polling — every timing
  expectation is a poll with a ceiling, never a fixed sleep. Two traps it had to
  step around: `capture_pane()` returns **lines**, so `token in lines` asks
  whether a line *equals* the token and silently never matches a token sharing
  its line with a prompt (`screen_of()` joins first); and `pane_active()`
  **forgets** a dead window as a side effect, so a test that waits for death by
  polling it has cleaned the registry the code under test needs dirty —
  `window_exists()` is the non-mutating probe. Both were found by running the
  suite against the unfixed code and watching it pass when it should have failed.
  `test_event_loop.py` (21 checks, the row's 98 → 119) is the one file that
  drives the *dispatcher* — the real `tool_call.ToolCall.call()`, the thing
  `chat/work.py` awaits — rather than calling `call()` directly, because the
  property it pins belongs to the dispatcher's `asyncio.to_thread` hop: a
  `delay=1` call costs the event loop a 22 ms worst gap, not a second. It carries
  the control that produces the freeze on demand (the hop removed), and its
  section 3 compares two gaps measured in the same process (medians of three), so
  the assertion is about the hop and not about how fast tmux is on the box.
- `tests/unit/sandbox/` - script wrapper and delivery: trailer, state
  (env/cwd carry-over), streams (stderr separation), lifecycle (background -
  MUST use sandbox=False, TRAPS #6), delivery, prompt (asserts the
  run_command PROMPT tells the model the truth). Runner globs `test_*.py`
  and sums `PASS: n  FAIL: n` lines; `stub_app.py` deliberately does not
  match the glob - renaming it would make the runner treat it as a suite.
  Lifecycle/delivery/streams drive everything through the shared
  `run_as_file(...)` -> `(output, leftovers, elapsed)`.

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
