# RUNTIME-RUN-COMMAND.md - The Run / Sandbox / Terminal Subsystem

Part of the spit.py documentation set (see `PROJECT.md`). This area had the
densest bug history in the project; the traps numbered 1-7 in `TRAPS.md` all
live here. Files: `spit_app/tools/run/run.py` (Run, wrap_script, get_script,
get_args), `run/common.py` (kill_process_group, bwrap args),
`run/terminal.py` (tmux backend), `run/sandbox_env.sh`.

## How a script tool executes

1. Module builds `script = get_args(arguments, defaults) + EXEC["script"]`
   (`EXEC["script"]` = optional common file prepended + tool script, both
   pure stdlib).
2. `Run(app, chat_id, interpreter, script, sandbox, timeout)` writes the
   script to a **file** and runs it through that file (not `python3 -c`) so
   the command keeps its stdin.
3. Inside or outside bwrap according to the user-editable `sandbox` setting
   (default True; the settings UI says DANGER on disabling). bwrap args
   include `--die-with-parent` and bind `sandbox_env.sh` as
   `~/.sandbox_env.sh`.
4. A **trailer** appended to the command captures the real exit code and the
   exported environment. The trailer is fragile - see TRAPS #1.

## run_command semantics (the model is told these; keep code and PROMPT in sync)

- Backgrounded processes do **not** outlive the call: the process group is
  killed when the command ends; inside the sandbox `--die-with-parent` tears
  everything down. `setsid cmd &` escapes the group and survives. Persistent
  work belongs in the `terminal` tool.
- stderr is reported in a `~~~~ stderr ~~~~` block AFTER the output, only when
  there is stderr; `separate_stderr=false` interleaves both streams (the
  implementation reads both pipes concurrently - TRAPS #5).
- `export` and `cd` carry over to the next call via `~/.sandbox_env` (the
  exported env is stored as literal `export NAME=value` lines; a STATE_EXCLUDE
  regex keeps noise out) and `~/.sandbox_cwd`. Both streams must be drained at
  once; poll `proc.returncode`, never rely on `proc.wait()`.
- Timeout: `MAX_SECONDS = 0` means no timeout; the `[timeout]` token in
  `PROMPT_INST` is substituted by the app - never remove or rename it.
- `run_script` wraps the same machinery for named interpreters
  (`[interpreters]` token); `python.py` is the restricted-builtin variant.

## terminal / lsterm

- `libtmux`; **one tmux session per chat conversation**, one window per named
  terminal running bash (bwrap-sandboxed by default).
- Screen capture: 24x80, **no scrollback**; cursor rendered as `█`. A dead
  session reports `INFO: Session dead.` and is auto-cleaned, so names are
  reusable; `lsterm` lists only live sessions.
- Output that scrolls off is lost; long-lived/verbose processes must redirect
  (`> log 2>&1`) and a session dying unattended recovers nothing.
- These tools bypass `scripts/`: they call the Run class's tmux methods
  (`term_new`, `term_input`, `term_screen`) directly from a sync `call()`.

## Where the knowledge lives

- Behaviour specs: `spit_app/tests/unit/sandbox/test_trailer.py`,
  `test_state.py`, `test_streams.py`, `test_lifecycle.py`,
  `test_delivery.py`, `test_prompt.py` (PROMPT assertions) - 103 checks, all
  no-Textual via `stub_app.run_as_file(script, home, root, timeout, **kw)`
  returning `(output, leftovers, elapsed)`.
- Commit history worth reading: `fix-run-command-*` branches merged in
  `3767dac` + `fb15e08` + `d2121b1` + `3fa330a` + `05ffc9a`/`68cff03`.
- The old `HANDOFF-run-command-leftovers.md` (deleted after absorption; see
  PROJECT.md) raised the PROMPT rewrite and the
  stub de-duplication; BOTH are done (TASKS-FINISHED.md), but its "Traps
  already paid for" section survives here in TRAPS.md.
