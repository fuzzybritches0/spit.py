# CONVENTIONS.md - How Code, Tests, and Commits Are Written Here

Part of the spit.py documentation set (see `PROJECT.md`).

## Coding style

- Prefer **code-as-doc**: descriptive method names, simple constructs,
  obvious flow. Simplicity beats ingeniousness; easy-to-read code is
  documentation that never goes stale.
- Docstrings and comments are **not forbidden** - the preference is to avoid
  them, but when the situation calls for one (a non-obvious invariant, a trap
  the code cannot express), use it. A real example in the repo: the comment in
  `run_command.py` explaining that `work.py` concatenates PROMPT and
  PROMPT_INST without a separator. A future agent should not refuse a needed
  comment because of an over-styled reading of this rule.
- Every source file starts with `# SPDX-License-Identifier: GPL-2.0`.
- Tool scripts (`spit_app/tools/scripts/`) are **pure stdlib, self-contained,
  import nothing from the app**. Shared code between scripts is *prepended*
  via `get_script(__file__, "<common>")` - a script can never import another
  script. Existing commons: `file.py` (stat metadata for file_info /
  list_directory), `lines.py` (line-ending primitives for patch /
  insert_line / delete_lines). If you add a common, add the matching
  `"common"` key to the tool's test `setup.json` or the suite dies on
  `NameError`.

## Tool module contract (`spit_app/tools/<tool>.py`)

Loaded dynamically at app startup by `tool_call.load_tools()`. Required:

- `NAME = __file__.split("/")[-1][:-3]`
- `DESC` - OpenAI function schema (`type: function`, name, description,
  JSON-schema parameters with `required`). The `description` strings are
  what the model reads: be terse and say what actually happens.
- `SETTINGS` - user-editable settings, at minimum `prompt` (from `PROMPT`)
  and `sandbox`; `load_user_settings(app, NAME, SETTINGS)` must be called at
  the start of the call so user overrides apply.
- Either `call(app, arguments, chat_id)` (sync, in-process - terminal tools
  and network tools) or `async def call_async_generator(app, arguments,
  chat_id)` (the norm: build `args + EXEC["script"]`, construct `Run(...)`,
  `async for line in run.run(): yield line`).

Optional (picked up by `load_tools` if present):
`OUTPUT_TYPE_HINT` (screen rendering only: "text"/"python"/"json"/"html";
set it for anything non-Markdown), `PROMPT_INST` (instruction string with
`[placeholder]` tokens the app substitutes - never break a token; PROMPT must
end with `\n` when PROMPT_INST follows), `Validators`,
`REQUIRES_MULTIMODAL_IMAGE`, `PATH_ARGS` (every filesystem-path argument -
only those get `~`/`$VAR` expansion), `STREAM_TOOL_RESPONSE`.

`EXEC = {"script": get_script(__file__[, "<common>"]), "interpreter":
"python3"}` for script tools. `get_args(arguments, {defaults})` renders the
argument block prepended to the script.

## Schema gotchas

- `"type": ["string", "array"]` is not decodable by every endpoint.
  `spit_app/arguments.py` repairs the fallout, but list-capable arguments must
  still be tested and any path arguments listed in `PATH_ARGS`.
- Integers: the tools accept numeric strings and error cleanly otherwise; keep
  that leniency in new tools.

## Test conventions (summary - details in TESTING.md)

- Per-tool suite dir holds **exactly three files**: `setup.json`,
  `run_tests.sh`, `create_fixtures.sh`. Fixtures are generated, never
  committed, removed on exit (`KEEP_FIXTURES=1` keeps them).
- Fixture naming: `tNN-<short-name>` owned by test N; `shared-<name>` for
  multi-test content; `corpus/<name>` for patch's corpus. Test numbers are
  **append-only** - freed numbers are never reused.
- Nothing any test touches lives outside `./fixtures/` (no `/tmp`).

## Git conventions

- Repo `~/spit.py`; **never `git pull` / `git push`; leave `main` untouched**
  (branches are reviewed and merged by the owner; your main then gets updated
  externally).
- `git branch -a` first - branch names exist for every past fix; pick a
  descriptive, non-colliding name (style: `fix-<tool>-<concern>`,
  `<tool>-<concern>`).
- One concern per commit. Imperative subject like the existing ones
  (`patch: ignore header line counts`). Body explains *why*, including the
  measurement that forced the decision where there is one.
- **Commit messages via `git commit -F /tmp/msg.txt`, never a heredoc** - the
  sandbox shell wrapper appends its trailer to the last line and pollutes
  heredocs (this actually happened; the commit had to be amended).
- Clean `__pycache__` before `git add -A` (gitignored anyway, but keep the
  tree honest).
- Author file content with `write_file`/`search_replace`, not shell heredocs
  (same trailer-pollution trap).
