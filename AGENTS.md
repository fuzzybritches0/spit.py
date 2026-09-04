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
| `doc/DECISIONS.md` | Design decision log — the *why*; append-only |
| `doc/TASKS-IN-PROGRESS.md` | Check first — half-finished work may need recovery |
| `doc/TASKS-PLANNED.md` | Pick up work here |
| `doc/TASKS-FINISHED.md` | Already done — do not redo or "fix" |

Non-negotiables (details in the docs above):

- **Never `git pull` or `git push`. Leave `main` untouched.** Work on a
  descriptively named branch; commit with `git commit -F file` (no heredocs).
- Read `doc/TRAPS.md` before your first code change.
- Run the full test suite (`bash spit_app/tests/run_tests.sh`) before and
  after changes; expected counts and rules in `doc/TESTING.md`.
- `dry_run` for every destructive operation; sandbox stays on by default.
