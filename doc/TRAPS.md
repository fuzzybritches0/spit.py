# TRAPS.md - Landmines Already Paid For

Part of the spit.py documentation set (see `PROJECT.md`). Every entry was paid
for with a real bug, a real lost afternoon, or a commit that had to be
amended. Numbered so task entries can point at them. Read fully before your
first code change; re-read the relevant numbers before working in the
matching area.

## The shell wrapper (affects ANY run_command call, not just the app's tool)

1. **`$?` is reset by ANY command.** A `:` no-op between a command and the
   exit-code trailer turned every failure into success. A comment line absorbs
   a trailing backslash and is not a command - that is why `ABSORB` in
   `run/run.py` is a comment. Same trap: the trailer's own default assignments
   must not precede `EXIT_CODE=${?}`.
2. **RESOLVED - a trailer glued to the last line of a command lands inside
   heredoc content.** When the wrapper was `command + "; EXIT_CODE=${?}; ..."`
   this was exactly as bad as it sounds: a command whose last line is a heredoc
   delimiter never ends its here-document, bash reads to end of input, and the
   trailer is written into the file (`git commit -F -` carried it into a real
   commit message once; `python3 - <<'PY'` died on a SyntaxError three lines
   from the end of a script nobody wrote). It has been fixed twice over: the
   trailer now starts a line of its own, bare, with no leading `;` (`68cff03`),
   preceded by the `ABSORB` comment for backslash continuations (`05ffc9a`),
   and `run_command` delivers the script as a file with stdin `DEVNULL`
   (`3fa330a`). Re-measured 2026-09-05 over the real file-delivery path:
   terminated heredocs are byte-exact with no bash warning and no trailer text
   in the file, `git commit` is clean via `-m` with a real newline, via
   `cat > f <<EOF` + `-F f`, and via `-F - <<EOF`, and an export survives a
   trailing comment. `test_trailer.py` pins both halves (t3 heredoc clean, t5
   control asserting the old glue still pollutes). Kept in this list because the
   mechanism is one refactor away from returning and because one case survives:
   **an *unterminated* heredoc still absorbs the wrapper** into the file - that
   is malformed input, and bash says so (`warning: here-document ... delimited
   by end-of-file`), so it fails loudly rather than silently. Prefer
   `write_file`/`search_replace` for file content and `git commit -F file` for
   commit messages - still good practice, no longer a landmine. See DECISIONS
   and CONVENTIONS.

## Process lifecycle (run_command / Run)

3. **`proc.wait()` waits for pipe EOF, not for the command.** Poll
   `proc.returncode` instead.
4. **After killing the process group, wait for the child to be reaped before
   reading `proc.returncode`** - `None < 0` is a `TypeError`; this was a real
   intermittent crash.
5. **Read stdout and stderr CONCURRENTLY.** A pipe holds ~64 KB; a blocked
   writer while you read the other pipe is a deadlock.
6. **Lifecycle tests must use `sandbox=False`** - inside bwrap,
   `--die-with-parent` hides every symptom. The sandbox has its own PID
   namespace, so PIDs are meaningless across two run_command calls.
7. **Backgrounded processes do not outlive a run_command call** (group kill +
   `--die-with-parent`); `setsid cmd &` is the only survivor; persistent work
   belongs in the `terminal` tool. (This is also in the tool's PROMPT now -
   `fb15e08`.)

## Testing

8. **Use distinctive tokens (`mm-one`) in output assertions.** Single letters
   collide with the transport's own "Running process..." / "exited with code"
   text and make tests pass on the wrapper instead of the tool.
9. **Harness `--flag` values are read once: the FIRST occurrence wins.** A
   test must pass the complete arg set on every call; never append an override
   to a shared base string. (`run_tests.sh` wrappers like `dl PATH START END
   PATTERN DRY` exist for this.)
10. **Never commit fixtures; generate them** (`testfile`/`testfile_bytes` in
    `fixtures_common.sh`). A `git format-patch`/`git am` round trip once
    silently rewrote every CRLF fixture to LF - the byte comparisons then
    passed VACUOUSLY; only two hand-typed-count checks noticed. No
    `.gitattributes` (it papers over half the problem and hides it from the
    test code).
11. **Terminator expectations must not come from a file alone**: use
    `assert_cr_lines` / `assert_no_cr` / `assert_last_byte`
    (`test_common.sh`) and keep the `fixtures_selftest` CRLF probe at the top
    of every `create_fixtures.sh`, so a broken generator cannot make both
    sides of a comparison agree again.
12. **A fixture no test reads is deleted, not renamed**; a fixture must be
    named after the test that owns it (`tNN-*`) - two tests once compared
    against another test's expectation and passed.
13. **A differential probe can lie.** Three separate verification scripts fed
    fixtures the wrong source file and still printed a tidy "identical" row.
    Verify the input mapping of any probe before trusting its output.
14. **Green tests do not prove a rename/refactor was content-preserving.**
    Generate both corpora (main vs branch), compare sorted md5 multisets per
    suite; require the diff on `run_tests.sh` to touch only what you intended.
15. **Test numbers are append-only.** Freed numbers (5-9 in patch) stay
    unused; new checks get new numbers so `tNN-*` keeps one meaning forever.

## Design process

16. **Before writing leniency into a parser, MEASURE the reference
    implementations** (`diff -u`, `git diff`, `difflib`, GNU patch) and record
    what each actually emits. An "obvious" compatibility need for bare empty
    lines inside hunks turned out not to exist - and adopting it would have
    broken working patches (DECISIONS 58).
17. **An invented motivating example is a defect.** Proposals must carry
    evidence from a reference implementation or a real failure, never a
    plausible-sounding hypothetical (DECISIONS 58).
18. **Prove behaviour changes by differential over every fixture, not only by
    a green suite**, and assert nothing that applied before applies
    differently. A refusal-that-became-an-application is invisible to the
    suite (see TESTING.md, "Differential verification").

## Python / app environment

19. **System python3 has NO app dependencies** (textual, libtmux...). Scripts
    are stdlib and test directly; modules need the app's runtime. Tests are
    built to run without Textual at all (`stub_app.py`).
20. **Tools are loaded at app startup** - tool code changes need an app
    reload to take effect.
21. **`["string", "array"]` schema types are not decodable everywhere**;
    `arguments.py` repairs the fallout and filesystem arguments must be listed
    in the tool's `PATH_ARGS` (only those get `~`/`$VAR` expansion).
