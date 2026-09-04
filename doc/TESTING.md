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
| diff | 24 |
| tools total | 441 |
| unit:arguments | 131 |
| unit:sandbox | 103 |

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
