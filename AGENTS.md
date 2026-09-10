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
| `doc/UI-PROTOCOL.md` | Engine <-> front-end contract (JSONL) — the seam that makes the UI replaceable |
| `doc/UI-ROUTE-RATATUI.md` | Route off Textual to a ratatui front end: gates M0-M5, measurements, fallbacks |
| `doc/DECISIONS.md` | Design decision log — the *why*; append-only |
| `doc/TASKS-IN-PROGRESS.md` | Check first — half-finished work may need recovery; the agents' own crash-recovery file, and agents close their own entries |
| `doc/TASKS-PLANNED.md` | Pick up work here |
| `doc/TASKS-FINISHED.md` | Already done — do not redo or "fix" |

Non-negotiables (details in the docs above):

- **No code change without the owner's `Go!`** — ask once per task, before the
  first edit. A tool's PROMPT text counts as code (the model reads it and
  `tests/unit/prompt/` pins it).
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
