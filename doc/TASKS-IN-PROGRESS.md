# TASKS-IN-PROGRESS.md

Tasks currently under way, with enough state for a different agent (or a
rescheduled one) to pick up exactly where work stopped. A task is only
"finished" when its Verify command passes on a clean tree.

## Currently: none.

Repo state as of 2025-09-04: `main` == `origin/main` (nothing unpushed),
working tree clean, all suites green per TESTING.md counts. The two leftover
tasks from `HANDOFF-run-command-leftovers.md` were completed in `fb15e08`
(run_command PROMPT rewrite + `test_prompt.py`) and `6dcdca9` (shared
`stub_app` adopted by `test_delivery.py`); the follow-up fix `39ceb2f`
corrected failure counting. See TASKS-FINISHED.md.

## Protocol when starting a task from TASKS-PLANNED.md

1. `git branch -a` (avoid name collisions), create a descriptively named
   branch. Never work on `main`, never push.
2. Move the entry here and keep these fields current AS YOU WORK - they are
   the crash-recovery record:
   - **Branch**: name + last commit sha on it
   - **Scope**: files touched so far
   - **Done**: what is complete and verified
   - **Left**: the precise next step, small enough to finish in one sitting
   - **State hazards**: half-finished edits, fixtures left over
     (`KEEP_FIXTURES`), uncommitted changes, suites currently red
   - **Verify**: command + expected result that closes the task
3. Commit early and often on the branch (one concern per commit) so the
   recovery point is a commit, not an uncommitted working tree.
4. On completion: run the FULL suite from the repo root, confirm ground-truth
   counts only went up by your new checks, move the entry to
   TASKS-FINISHED.md with the resolution (branch, commits, outcome), delete
   this entry.
