# AGENTS.md

Before doing anything in this repository, read **`doc/PROJECT.md`** — it is
the entry point to the project documentation and carries the reading order.

Quick map:

| File | What it is |
|---|---|
| `doc/PROJECT.md` | Start here: overview, repo layout, test commands, ground rules |
| `doc/CONVENTIONS.md` | Tool module contract, coding style, git workflow |
| `doc/TRAPS.md` | Landmines already paid for — read before touching code |
| `doc/TOOLS.md` | Tool development guide (attributes, structure, full specs) |
| `doc/TESTING.md` | Test infrastructure, fixtures, verification methods |
| `doc/RUNTIME-RUN-COMMAND.md` | The run/sandbox/terminal subsystem |
| `doc/DECISIONS.md` 76 + 89 | The windowed message loading of 2026-09: built, measured, and **REVERTED 2026-10-01** (89). Its doc is deleted; the numbers and the four ways it failed the user are the record. The chat view is P8 again, and the route question is P22 |
| `doc/DECISIONS.md` | Design decision log — the *why*; append-only |
| `doc/TASKS-IN-PROGRESS.md` | Check first — half-finished work may need recovery; the agents' own crash-recovery file, and agents close their own entries |
| `doc/TASKS-PLANNED.md` | Pick up work here |
| `doc/TASKS-FINISHED.md` | Already done — do not redo or "fix" |

Non-negotiables (details in the docs above):

- **No `Go!` is needed to change code.** Owner's ruling of 2026-09-28, verbatim:
  *"You may work now independently without asking the user for any permission.
  One thing remains the same: only the user may merge your work into main."* So
  nothing is asked before an edit — a tool's PROMPT text included, since it is
  still code (the model reads it, and `tests/unit/prompt/` pins the prompt
  machinery). **Only the merge is the owner's** (DECISIONS 71 a, as amended
  by 83).
- **Never `git pull` or `git push`. Leave `main` untouched.** Work on a
  descriptively named branch; commit with `git commit -F file` (house
  style; the heredoc-pollution reason it used to give is fixed — TRAPS #2).
- Read `doc/TRAPS.md` before your first code change.
- **There is no owner sign-off of finished work.** The docs and the task files
  are the agent's own working material; close your own tasks when the entry's
  `Verify` is met and move them to `doc/TASKS-FINISHED.md`. Only the merge is
  the owner's (DECISIONS 71).
- Run the full test suite (`bash spit_app/tests/run_tests.sh`) before and
  after changes; expected counts and rules in `doc/TESTING.md`.
- `dry_run` for every destructive operation; sandbox stays on by default.
