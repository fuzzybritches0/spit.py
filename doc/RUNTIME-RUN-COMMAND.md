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
  (`[interpreters]` token, and the list is **enforced** - nothing outside it
  reaches `PATH`; bash alone gets the wrapper, decision 63 and decision 64);
  `python.py` is the restricted-builtin variant.

## terminal / lsterm

- `libtmux`; **one tmux session per chat conversation**, one window per named
  terminal running bash (bwrap-sandboxed by default).
- The tmux server is one of spit.py's own: `run/terminal.py:server_socket()` is
  `spit-<pid>` and every `libtmux.Server(socket_name=…)` is built with it. A bare
  `libtmux.Server()` means the user's DEFAULT socket, and `actions.py:action_exit_app`
  calls `server.kill()`, which is `tmux kill-server` — so before this, quitting the app
  took down every session of the user's tmux. One server per process, one session per
  chat inside it. The suite forces its own socket over this and records the request
  (`stub_app.requested_sockets`), because pinning a choice the harness overrides needs
  the record, not the socket.
- Screen capture: 24x80, **no scrollback**; cursor rendered as `█`. The last
  screen of each name is cached in `app.tmux[chat_id]["last_screen"][name]` —
  on the app, not on the `Terminal`, because `tools/terminal.py` builds a new
  `Terminal` per call and an instance attribute cannot remember anything across
  calls (decision 66). The cache holds **what the tool last reported** for that
  name: for a live screen the rendered capture with the cursor marker, for a dead
  one the dead report including its `Exit status: N`, so a repeat call says exactly
  the same thing. `lsterm` lists only live sessions, from `live_window_names()`, which
  snapshots the names before checking any of them: the liveness check deletes a
  dead window from the dict being walked, and doing that mid-iteration is the
  `RuntimeError` that used to kill the listing (decision 67).
- Liveness lives in ONE function, `run/terminal.py:pane_active()` — `lsterm`
  had a private copy and it is the thing that mutates. It asks the pane's
  `pane_dead`, not whether tmux still holds the window: `remain-on-exit` means a
  dead session keeps its window, so membership now answers "is there still a
  corpse". Discovering a death there also harvests the real screen into the cache
  and destroys the window (`retire()`), because `lsterm` is often the only thing
  that ever sees a death — the model is told to call it first. Tests that wait for
  a session to die without cleaning up behind them use a non-mutating probe
  (`stub_app.py:window_dead`); `window_exists` is now a different question and is
  only for asking whether tmux still has the window. Either way a mutating probe in
  the setup performs the fix and the test passes against broken code (decision 67).
  Since the state layer (decision 70) the question is asked against ONE
  `tmux list-panes -a` snapshot per call, never against a cached libtmux object —
  a cached `Pane` was measured reading `pane_dead '0'` after its shell was gone.
  The registry holds `name → window_id` strings plus the server identity (pid,
  start time) the ids belong to; an id counts as ours only when the snapshot's
  stamp matches the chat's AND its row names the chat's own session, because a
  restarted tmux numbers from `$0`/`@0` again and a stale id can then name
  another chat's live window. `retire()` kills only what a fresh listing says is
  ours, then re-lists: killing the last window destroys the session, and on our
  own socket the last real window is now the ordinary last window (the unnamed
  window tmux creates with every session is destroyed once a registered one
  exists), so the chat's entry is rebuilt — keeping the `Server` object
  (`actions.py` indexes `chat["server"]` unguarded at exit, and the same object
  revives tmux on its socket) and the screen cache.
- Cost, and it is half the reason for the snapshot: `term_screen()` is exactly
  TWO `tmux` invocations (`list-panes -a` + `capture-pane`, ~16 ms median here)
  where the object layer paid six plus two `display_message` cursor reads
  (~53 ms median measured on this box for the same work); `lsterm` over three or
  four windows is ONE `list-panes`, and `term_input` five invocations. The
  narrow 13-token format (with `pane_current_command` LAST and a maxsplit parse,
  because a process name can contain anything) costs ~9 ms where libtmux's own
  ~125-field listing costs ~12 ms for the same rows. `pane_snapshot()` treats
  tmux's "no server running"/"error connecting to" as the ANSWER (empty —
  everything ours is gone) and any OTHER complaint as a RAISE: reading a tmux
  error as "all dead" would forget every live session in the chat and destroy
  their windows.
- Output that scrolls off a live session is lost, so long-lived/verbose processes must
  redirect (`> log 2>&1`). A session dying unattended is no longer one of them: its
  report carries the pane's actual final screen (last 50 lines) and its exit status.
- These tools bypass `scripts/`: they call the Run class's tmux methods
  (`term_new`, `term_input`, `term_screen`) directly from a sync `call()`.
- A sync `call()` does not run on the UI's event loop:
  `tool_call.ToolCall.call()` dispatches it through `await asyncio.to_thread(...)`
  (`d455761`), which is why `delay` (default 1 s) costs the loop a 22 ms worst gap
  and not the second it is often blamed for. Keep it that way: libtmux spawns the
  `tmux` binary on every round-trip — a plain `term_screen()` is ~16 ms here
  (re-measured for decision 70; it was ~46-53 ms before the snapshot layer, and
  the older claim of ~46 ms predates this box) and, run on the loop, stalls it by
  about its own duration — so a generator-form `call()` would put the tmux I/O on
  the UI thread while the sleep it meant to rescue was already off it. One cheap
  capture is a small stall; a BURST of them is not: five captures back to back on
  the loop measured a 99 ms worst heartbeat gap against 22 ms through the hop,
  which is what `test_event_loop.py` t3 now pins (a single ~16 ms capture made the
  original single-call ratio too tight to mean anything). DECISIONS 68, pinned by
  `tests/unit/terminal/test_event_loop.py`.

## Where the knowledge lives

- Behaviour specs: `spit_app/tests/unit/sandbox/test_trailer.py`,
  `test_state.py`, `test_streams.py`, `test_lifecycle.py`,
  `test_delivery.py`, `test_prompt.py` (PROMPT assertions) - 119 checks, all
  no-Textual via `stub_app.run_as_file(script, home, root, timeout, **kw)`
  returning `(output, leftovers, elapsed)`.
- Terminal behaviour specs: `spit_app/tests/unit/terminal/` - 220 checks against
  a **real tmux on a private socket**. `test_screen.py` the capture and the
  cross-call cache and (t14-t17) the state layer itself — id registry, tmux-side
  window names, the cost of a call counted in `tmux` invocations, the dead
  last-terminal teardown, the stale-id alias guard — `test_keys.py` keys versus
  literal text (with a control showing literal bytes do NOT interrupt),
  `test_lsterm.py` the listing surviving dead sessions, `test_tool_call.py`
  `delay` and the errors `call()` must report rather than raise,
  `test_event_loop.py` the dispatcher's `to_thread` hop and the event loop's
  heartbeat through a call and through a burst of captures (with the control
  that reproduces the freeze on demand). Needs libtmux, so it needs the test venv:
  `bash spit_app/tests/create_venv.sh` (TRAPS #19, TESTING.md).
- Commit history worth reading: `fix-run-command-*` branches merged in
  `3767dac` + `fb15e08` + `d2121b1` + `3fa330a` + `05ffc9a`/`68cff03`.
- The old `HANDOFF-run-command-leftovers.md` (deleted after absorption; see
  PROJECT.md) raised the PROMPT rewrite and the
  stub de-duplication; BOTH are done (TASKS-FINISHED.md), but its "Traps
  already paid for" section survives here in TRAPS.md.
