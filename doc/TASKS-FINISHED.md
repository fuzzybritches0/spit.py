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

