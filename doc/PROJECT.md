# PROJECT.md - spit.py: Guide for Future Agents

Start here. This file and its companions were extracted on 2025-09-04 from
`~/TOOL_IMPLEMENTATION_SUMMARY.md` and `~/HANDOFF-run-command-leftovers.md`;
both originals were reviewed section by section, fully absorbed here, and
deleted - these files are now the single source. They guide further
development of the project; everything here reflects the repo at
`~/spit.py`, branch `main`.

## Reading order (the recovery path for a fresh agent)

1. `PROJECT.md` (this file) - what the project is and how it is built.
2. `CONVENTIONS.md` - module contract, coding style, test layout, git rules.
3. `TRAPS.md` - landmines already paid for. Read before touching code.
4. The section guide for your area:
   - `TOOLS.md` - tool development (attribute matrix, structure, full specs)
   - `TESTING.md` - test harness, fixtures, verification methods
   - `RUNTIME-RUN-COMMAND.md` - the run/sandbox/terminal subsystem
5. `TASKS-IN-PROGRESS.md` - is someone's work half-done? Recover it first.
6. `TASKS-PLANNED.md` - pick up work here.
7. `TASKS-FINISHED.md` - what is already done (do not redo or "fix" it).
8. `DECISIONS.md` - the *why* behind behaviour that looks odd. Append-only.

## What spit.py is

A TUI AI assistant (alpha) built with **Textual**, Linux only, licensed
GPL-2.0 (SPDX header line on every source file). It talks to llama.cpp
servers managed locally (optional Vulkan acceleration, model downloads) or to
any OpenAI-compatible `/v1/chat/completions` endpoint. Features: multiple
chats/endpoints/model-settings/system-prompts, tool calling, multimodal
images, Markdown + LaTeX rendering (Kitty/Foot terminals), fully async long
replies, full in-chat history editing. Repo `README.md` has install and usage
instructions (venv, `libcairo2`, `bubblewrap`, `tmux`,
`playwright install chromium-headless-shell`). Tested with Python 3.13.

## Repo layout (the parts that matter for development)

```
main.py                      entry point -> spit_app.app.SpitApp
spit_app/app.py              the Textual app
spit_app/tool_call.py        loads every spit_app/tools/*.py at STARTUP:
                             DESC/SETTINGS required; call or
                             call_async_generator required; optional
                             OUTPUT_TYPE_HINT, PROMPT_INST, Validators,
                             REQUIRES_MULTIMODAL_IMAGE, PATH_ARGS,
                             STREAM_TOOL_RESPONSE
spit_app/arguments.py        coerces argument values to the declared schema
                             types; expands ~ / $VAR for PATH_ARGS only
spit_app/tools/<tool>.py     tool module (contract: CONVENTIONS.md)
spit_app/tools/scripts/      pure-stdlib scripts executed in the sandbox
spit_app/tools/scripts/common/   shared helpers PREPENDED to scripts
                                 (file.py = stat metadata, lines.py =
                                 line-ending primitives)
spit_app/tools/run/run.py    the Run class: sandboxed (bwrap) script/ command
                             execution, trailer, env+cwd carry-over
spit_app/tools/run/common.py kill_process_group, bwrap args
spit_app/tools/run/terminal.py  tmux backend for terminal/lsterm
spit_app/tests/run_tests.sh  runs everything, prints one line per suite
spit_app/tests/tools/        per-tool shell suites (layout: TESTING.md)
spit_app/tests/unit/         arguments + sandbox unit suites (pure python)
```

## How to run things

- All tests: `cd ~/spit.py && bash spit_app/tests/run_tests.sh`
  (expected counts per suite: TESTING.md; all FAIL numbers must be 0)
- One tool suite: `cd ~/spit.py/spit_app/tests/tools/<suite> && bash run_tests.sh`
- Tool *scripts* run with the bare system python3 (pure stdlib) - that is what
  the test harness does. Tool *modules* import `Run`/textual and cannot be
  imported with the system python.

## Environment gotcha (verified, still true)

The app's dependencies (`textual`, `libtmux`, ...) are **NOT installed in the
bare system python3**. The app runs elsewhere (container/venv). Consequences:
- Test scripts in `spit_app/tests/tools/` and `tests/unit/sandbox/` are built
  to need no Textual (sandbox tests drive `Run` through `stub_app.py`).
- To smoke-check a tool module's wiring without deps:
  ```python
  import sys
  from spit_app.tool_call import load_module_from_path
  from pathlib import Path
  m = load_module_from_path('tools.<name>', Path('spit_app/tools/<name>.py'))
  print(m.DESC['function']['name'], m.EXEC['interpreter'], len(m.EXEC['script']))
  ```
- **Tools are loaded at app startup: code changes to tools only take effect
  after the app is reloaded.**

## Ground rules (non-negotiable)

- `~/spit.py` is a git repo. **Never `git pull` or `git push`. Leave `main`
  untouched**: work on a descriptively named branch (list existing branches
  first), one concern per commit, `--ff-only` merge only where the existing
  practice says so. Full rules: CONVENTIONS.md.
- All tool execution is sandboxed with bwrap by default; keep it that way.
- `dry_run` for every destructive operation.
- When in doubt about *why* something is the way it is, grep `DECISIONS.md`
  before changing it.
