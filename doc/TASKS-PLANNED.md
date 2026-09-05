# TASKS-PLANNED.md

Tasks known to be wanted but not started. Light skeleton per task; the
referenced guides carry the detail. On starting a task: move its entry to
`TASKS-IN-PROGRESS.md`, create a branch first (never touch `main`, never
push), and keep the State field honest so an abandoned task is recoverable.

---

## P0 - MOVED to TASKS-IN-PROGRESS.md  [high priority, user-visible bug]

Started on branch `task-streaming-render-bugs`; the full entry (symptoms,
data-flow map, probe, suspects, constraints) and its live State fields are in
`TASKS-IN-PROGRESS.md`.

---

## P1 - patch: the `is_header_pair` adjacency edge  [open, deliberate]

- **Scope**: `spit_app/tools/scripts/patch.py` (+ its test suite)
- **Status**: left open ON PURPOSE during the patch redesign. Not a forgotten bug.
- **Verify**: `cd ~/spit.py/spit_app/tests/tools/patch && bash run_tests.sh` (80 green);
  a fix adds tests without reusing freed numbers 5-9 (append-only).
- **Gotchas**: TRAPS #13/#15; DECISIONS 37 and the section below.
- **How to start**: read the verbatim record below first; the natural fix is to
  require a genuine file header to be followed by a `@@` hunk header or end of
  input. Prove the change by differential over every fixture (TESTING.md).

### 4. OPEN — the `is_header_pair` adjacency edge in `patch`

`is_header_pair()` decides a `--- old`/`+++ new` **pair** is a file header and skips
it. A *headerless* hunk that removes a line starting with `--` directly above an
added line starting with `++` produces exactly that shape as body content:

```
---x        (removing "--x")
+++y        (adding  "++y")
 keep
```

and the two lines are skipped as if they were a file header. Consequence is a loud
no-match failure, not corruption, and the shape is rare. Left unfixed on purpose so
it is a decision rather than an oversight; if it is ever fixed, the natural fix is to
require that a genuine file header be followed by a `@@` hunk header or end the
input, not merely be a pair.

---

## P2 - DONE - `rename` implemented  [medium priority]

Branch `rename-tool`, commit `7c1d062` (docs in the follow-up commit);
resolution in `TASKS-FINISHED.md`, spec in TOOLS.md #14, policy
rationale DECISIONS 60. The drafted spec below (verbatim) stays here.

## P3 - New tool: `copy`  [medium priority, not started]
## P4 - New tool: `code_parser`  [low priority, not started]

- **Scope**: new files `spit_app/tools/<name>.py` +
  `spit_app/tools/scripts/<name>.py` + `spit_app/tests/tools/<name>/`
  (exactly three files: `setup.json`, `run_tests.sh`, `create_fixtures.sh`).
- **Verify**: full suite `bash ~/spit.py/spit_app/tests/run_tests.sh` stays green;
  new suite's checks counted in its summary line.
- **Gotchas**: TRAPS #9 (PATH_ARGS), #7/#8 (`git commit -F`, author with
  write_file), #10 (generated fixtures only); follow CONVENTIONS.md module
  contract end to end; both destructive file tools need `dry_run`.
- **Drafted specs (verbatim)**:

## Tools Planned (Not Yet Implemented)

### 1. `rename` (Medium Priority)
**Purpose**: Rename/move files

**Parameters**:
- `old_path` (required): Current file path
- `new_path` (required): New file path
- `dry_run` (optional): Preview without renaming. Default: `False`

**Output**: Success/error message

---

### 2. `copy` (Medium Priority)
**Purpose**: Copy files with options

**Parameters**:
- `source` (required): Source file path
- `destination` (required): Destination path
- `preserve_permissions` (optional): Keep permissions. Default: `False`
- `dry_run` (optional): Preview without copying. Default: `False`

**Output**: Success/error, bytes copied

---

### 3. `code_parser` (Low Priority)
**Purpose**: Parse code structure

**Parameters**:
- `path` (required): File path
- `language` (optional): Language (python, javascript, etc.)

**Output**: Functions, classes, imports, dependencies

---

---

## P5 - Longer-term roadmap (from the repo README, no specs yet)

- More advanced agent capabilities
- GUI/TUI alternative to Textual
- Audio

These are owner-level roadmap items, not pick-up-and-code tasks; do not start
them without explicit instruction.
