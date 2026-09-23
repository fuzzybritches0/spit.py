# TASKS-IN-PROGRESS.md

This file is the agents' own crash-recovery record. An entry exists so that, if
a session dies, the next agent picks the work up from the **State** fields
instead of re-deriving it — nothing here is for the owner's review, and the
whole `doc/` set exists to support the agent's work. Nothing in this file is
finished. Whoever holds an entry closes it, alone, when its **Verify** is met:
run the FULL suite from the repo root, confirm the ground-truth counts moved
only by the checks the task added, write the resolution into
`TASKS-FINISHED.md`, delete the entry here. No owner sign-off enters into that
(DECISIONS 71, TRAPS #22) — the owner's gate is the `Go!` asked **before**
changing code, and the merge of the branch, which is the only part of finishing
that is not the agent's.

> **TWO entries are open** in this file: the `terminal`-tool harness list,
> followup 4, and **P12 - token counts** (started 2026-09-22 on
> `task-token-counts-p12`, owner's `Go!` given, six-step handoff chain — see
> its entry and its State below). **P12 is at step 5 of 6**: steps 1-4 are
> committed (`a173854`, `b7d06ac`, `304530a`, `756179d`), and step 4 needed a
> recovery on 2026-09-23 — the session that wrote it died with the code
> uncommitted and its State fields still describing step 3, so the next agent
> re-measured it rather than trusting the notes (six byte-identical full-suite
> runs, probes green, golden md5 unmoved) and committed it. That recovery also
> found an **80-column layout limit** in the new counts row, filed for the owner
> in the step-4 block; the chain's next step is the committed test suite.
> **exit-reporting closed on 2026-09-21** on `alternate-exit-reporting`
> (`a1563e5`, `a4cf37f`, `ae568a0` + the docs after it): the verdict-line rule in
> `run/run.py`, per-tool via `needs_exit_status_report`, the five re-pinned checks
> green and `unit:sandbox` back at its 157. Resolution in `TASKS-FINISHED.md`;
> the three things it left unpinned are filed in `TASKS-PLANNED.md`.
> The on-demand-loading pipeline is **closed end to end** — WP-A…WP-F are all in
> `TASKS-FINISHED.md` on six branches awaiting the owner's merge, and P8 is marked
> DONE in `TASKS-PLANNED.md`. WP-F closed 2026-09-20 on
> `task-window-measurement-numbers-close-p8` (`18a84c4` P9 filed, `0568ce6`
> DECISIONS 76 with the numbers, `a13d0e2` P8 closed, `b47f728` the fallback-ladder
> rung 0, then this close): it changed **no repo code**, so it asked no `Go!`
> (DECISIONS 71 (c)), and what it left behind is **P9**, a code hole with its own
> `Go!` ahead of it — not an unfinished package.
> **The `/tmp` state WP-F depended on is not in git and the entry above is gone,
> so it is stated once here**: the crashed session's artefacts live in
> `/tmp/wp-f-crash/` and must never be re-run over; the recovery's capped walk
> JSONs `/tmp/wpf-recover-flat-*.json` must keep their content (grid 250/cap 8000
> and grid 200/cap 6000 — `/tmp/wp-f-keep-recovery-flat-*.json` are the copies to
> restore from); the uncapped 2026-09-20 runs are `/tmp/wp-f-continue-flat-*.json`.
> All of it, and the recipe for re-running any cell, is in the WP-F entry of
> `TASKS-FINISHED.md`.
> **WP-E of the on-demand-loading pipeline closed 2026-09-19**: the window-aware
> `mount_message` (returns the widget; bounds-checks the DATA before touching the
> window; `window_start += 1` for an insert below the top — the front mount that
> stood there was wrong in DIRECTION and left a one-message HOLE even for the
> adjacent index), the three DECIDE-FIRST undo primitives under the new
> `page_operations_held()` guard, the ONE focus rule both removal sites share
> (`widget_was_removed` asked before the neighbour question), `check_action`
> answering `add_message_next` from the DATA (it used to raise IndexError out of
> `refresh_bindings` with the bottom pruned — a crash with NO keypress), and
> `prune()` **refusing while `is_edit`** per the owner's ruling of 2026-09-19
> ("refuse in `prune()`", the accepted cost measured at 19 held → 19 → 10 on the
> first prune after edit_off). `unit:chat_window` 270 → **568** with the new
> `test_window_edits.py` (298 checks, t21–t29), full suite FAIL 0, two consecutive
> byte-identical runs, `chat_smoke`'s golden md5 unchanged. The close-out rests on
> the automated headless suites — there is no screen here (TRAPS #22). The
> resolution is in `TASKS-FINISHED.md`, including the two instrument lessons its
> own reds taught: the setup's `freeze_triggers` is part of the state a later row
> reads, and an undo "change" entry holds the PREVIOUS state. **WP-F was cut from
> this tip and closed the pipeline on 2026-09-20**
> (`task-window-measurement-numbers-close-p8`): the 100/1k/5k table, the walk,
> DECISIONS 76 and the P8 close — no repo code touched, so no `Go!` was asked
> (DECISIONS 71 (c)).
> **WP-D of the on-demand-loading pipeline closed 2026-09-17**: the scroll triggers,
> the `prune()`-takes-the-guard fix and the 172-check trigger suite are on
> `task-scroll-load-prune-triggers` (`c8aab52`, `8a623ac`, `2091482`, `5281fe4`,
> `5c47bf7`), `unit:chat_window` 98 → 270, full suite FAIL 0 with three consecutive
> byte-identical runs and `chat_smoke`'s golden md5 unchanged. The resolution is in
> `TASKS-FINISHED.md`, including the one real bug this WP found (the settled-scroll
> `set_timer` prune interleaving with the `call_after_refresh` page operation, which
> corrupted the mounted range 2 runs of 3 when forced at the hazard point) and the
> wall-clock numbers behind every timing claim (0.15 s settle against 66-71 ms per
> headless notch — 17 settles inside one 200-notch burst, which is why the suite waits
> for the widget's state instead of for its clock).
> **WP-C of the on-demand-loading pipeline closed 2026-09-15**: the window core
> and its 98-check suite are on `task-sliding-window-core` (`bd0ece0`,
> `f4328c9`, `594f3f1`), and the session that wrote them crashed mid-close-out —
> `doc/TESTING.md` left uncommitted and this file's own State fields still saying
> "Done: nothing yet". The next agent re-measured the full suite rather than
> trusting those notes (FAIL 0, `unit:chat_window` 98 new, `chat_smoke` 168 with
> its golden md5 unchanged), and the resolution is in `TASKS-FINISHED.md`. WP-A,
> WP-B, WP-C, WP-D and WP-E are all closed there, on branches awaiting the owner's
> merge (the chain is `task-anchored-scroll-widget` → `task-index-accessor-refactor`
> → `task-sliding-window-core` → `task-scroll-load-prune-triggers` →
> `task-edit-undo-removal-across-window-edges`, `main` untouched throughout);
> **WP-F closed the pipeline on 2026-09-20**
> (`task-window-measurement-numbers-close-p8`, cut from the WP-E tip) — the
> measurements, DECISIONS 76 and the P8 close, docs only, and it is in
> `TASKS-FINISHED.md` with the other five. Nothing in that pipeline is left to
> start; what it left behind is **P9** in `TASKS-PLANNED.md`, a page-SIZING hole
> that needs its own `Go!` because it is a code change. The followup
> *numbers* stay in the headings so that cross-references by number remain true
> even though 1, 1.5, 2 and 3 are gone — **followup 3 closed as a non-issue on
> 2026-09-10 by the owner's ruling**: a lone `Esc` swallowing the next character
> is how a terminal works, tmux does the same thing as the owner's own terminal,
> and the `terminal` tool's job is to hand the caller a terminal 1:1, so there
> is nothing to fix and nothing to explain away in the PROMPT. DECISIONS 72 and
> TRAPS #23; the branch that had been cut for it,
> `terminal-prompt-esc-limitation` (`f6948ea`, `4fa008a`), is **left unmerged on
> purpose**. Reopening that question is re-litigating the owner's ruling, so do
> not: **a pane that behaves like a terminal is not a defect**. What remains:
> **P0b** and its four siblings
> (`e699bb4`…`8f65e32`, 98 checks), **followup 1** `remain-on-exit`
> (`d549b61`…`e5b4fba`, DECISIONS 69), **followup 1.5** the state layer
> (`8cfd14a`, DECISIONS 70) and **followup 2**, closed as a false premise
> (DECISIONS 68), are all recorded in `TASKS-FINISHED.md`, and `main`
> (`9c254e8`) carries all of it. **P0, the garbled streaming render, left this
> file on 2026-09-10**: its commits are merged, `unit:render` is 278 green, and
> the suite measured tools 127/24/30/119/80/32/68/29 + unit
> 131/33/278/121/119/220, FAIL 0 — which is exactly its Verify. The one thing
> that had kept it open was a human checklist nobody had asked for; the
> resolution (root causes, coverage, the two accepted limits, and that
> checklist kept in case anyone still wants to run it by hand) is in
> `TASKS-FINISHED.md`.

## Machine state these entries assume (none of it is in git)

- **The test venv**: `bash spit_app/tests/create_venv.sh` → `~/.venv-spit`
  (all of `requirements.txt`). `unit:terminal` needs libtmux and reports
  `PASS: 0  FAIL: 1` with the remedy when it cannot import it — never a silent
  zero. `doc/TESTING.md`, "The test venv". Note the `unset PIP_USER
  PIP_BREAK_SYSTEM_PACKAGES` inside that script: this environment exports both
  and a virtualenv refuses a `--user` install outright.
- **Never drive a shared tmux.** `tests/unit/terminal/stub_app.py` wraps
  `libtmux.Server` to pass `socket_name`, so the suite runs on its own server and
  may `kill-server` freely. A run leaves stale socket *files* under
  `/tmp/tmux-1000/spit-unit-terminal-*` and **no running server**; removing the
  files is safe, and any new terminal test must keep both properties.

## P0b-followup 4 - what the `terminal` tool still needs as a UI-under-test harness  [enhancement list, picked up piece by piece]

The list below was written during P0b and is **verbatim from it except for the
framing**, which named a migration plan the owner retired on 2026-09-20
(DECISIONS 77). The items and their measurements survive that retirement
untouched: none of them is about one toolkit, they are about what a pane can
report. Four items have moved since — 8, 9, 10 and 12 — and each is marked
**where it is marked done, never where it is still open**. Nothing else has been done, re-checked
against the source 2026-09-10: `spit_app/tools/terminal.py` still accepts
exactly `name`, `input` and `delay`, so items 1-7 and 11 have no code behind
them at all.

**Already done while fixing P0b** (so do not re-do them): the *single
implementation* half of item 9 — `pane_active()` now exists once in
`run/terminal.py` and `lsterm` uses it (`c948b3e`); the *namespaced windows* half
of item 9 has its foundation now (followup 1.5: tmux itself names the windows,
the registry resolves by its own names, and an unresolved name answers "no such
session") — whether the tool should fail *loudly* beyond that answer is still an
open choice. Item 8 (process state as first-class output) is mostly done: a dead
pane reports its REAL final screen and its exit code (followup 1), every field
the snapshot needs already includes `pane_pid`/`pane_current_command`/geometry,
and the state layer those come from — DECISIONS 69's recommendation and the
one `list-panes -a` per call — **landed as followup 1.5**; `pane_dead_signal`
and `pane_dead_time` (tmux >= 3.3) are two more tokens away in that format
line. What is left of item 8 is surfacing them as fields on a LIVE
screen — a formatting job now, not a plumbing one.

Any front end that is not the Textual one running in-process arrives as **a
program in a real pty**, and for that job this tool stops being a convenience
and becomes **the only harness that can see it**: a front end's own widget-level
test backend covers its widgets, the `terminal` tool covers the end-to-end app —
does it start, stream, scroll, paste, and die cleanly. The `App.run_test` suites
drive Textual in-process and cannot reach a program that is not Textual, so
this tool is the only way to assert on that end-to-end behaviour. Design it for
that job:

1. **`command`, not hardcoded `bash`.** Launch arbitrary argv in the pane
   (`command=["python3", "main.py"]`, plus `env={}`, `cwd=`) — "start the UI
   under test" is the primitive; interactive bash is a special case of it.
2. **Geometry you control.** `cols`/`rows` at creation and a `resize` action.
   Re-wrap-on-resize is load-bearing for anything that re-wraps its history when
   the pane changes width (measured: 746 ms to re-wrap 2,000 messages), and it
   cannot be tested at 24x80 only. During
   this evaluation I had to nest a private tmux server to get 120x40 and
   150x35.
3. **Capture modes: text | styled | bytes.** Today only plain text. `styled`
   (`capture-pane -e`) is how markdown/heading/highlight/border styling gets
   asserted. `bytes` (raw pane output) is how the **Kitty/Sixel graphics path
   gets asserted** — LaTeX and image rendering could not be verified at all in
   this environment because there is no way to see the escape sequences, and
   that is the single biggest unproven risk in the graphics path.
4. **Cursor as data, not decoration.** Report `cursor_x`/`cursor_y` as fields
   instead of splicing a `█` into the text (which corrupts the line and breaks
   under double-width characters); keep the marker as an option.
5. **`wait_for` instead of `delay`.** Wait until a regex matches the pane or the
   screen is stable for N ms, with a timeout — blind sleeps make streaming tests
   flaky, and streaming (token deltas, follow-bottom, abort) is the main thing
   any UI under test must get right.
6. **`send_bytes` / raw mode**, so a test can inject SGR mouse sequences and
   bracketed paste. That is exactly how a candidate front end's mouse and paste
   defects were proven in 2026-09 (4 injected sequences → 0 delivered; a pasted
   Enter arriving as `Ctrl+J` wipes the line — those measurements belong to the
   evaluation retired in DECISIONS 77; the check they justify does not), and any
   front end's input layer must be tested against the same sequences.
7. **Scrollback and diffs**: `capture(since=-N)` and "changed lines since last
   capture". With no scrollback and full-screen captures, an agent burns context
   re-reading the same 24 lines; a diff capture makes long-session work cheap.
8. **Process state as first-class output**: `pane_pid`,
   `pane_current_command`, exited-with-code. Today a dead pane is one sentence
   with no content, so a crashed UI and an empty UI look identical.
9. **Namespaced sessions.** One tmux session per chat is right, but windows are
   addressed by bare `name`, and a call naming a session that does not exist can
   land on an already-running window instead of failing (this bit me live: the
   first call of a session named `prt` reached a different, already-attached
   pane). Prefix windows by `chat_id`, name the tmux window, and fail loudly on
   a name that does not resolve — `lsterm` should list the same names, and its
   private `pane_active()` (which mutates state as a side effect of *listing*)
   should be the one implementation in `Terminal`.
10. **Non-blocking and cancellable**: the wait must not block the UI loop; an
    in-flight `terminal` call should be abortable (the engine already has
    `kill_process_group` and the abort path — TRAPS #4). **Half settled**:
    DECISIONS 68 measured the shipped path and the loop is not blocked (a sync
    `call()` goes through `asyncio.to_thread`), so do not "fix" that half
    again; what is left is the abortable in-flight call, which lands with
    item 5 (`wait_for` replaces the blind `delay`).
11. **Structured output option** (`format="json"`: rows, cursor, attrs, bytes,
    process state) so tests assert on data instead of parsing prose.
12. **Sandbox stays on by default** (and lifecycle tests use `sandbox=False`,
    TRAPS #6), and teardown is guaranteed: a `kill` that takes the process group
    and auto-cleanup when the chat closes. During this evaluation the only way
    to clean up orphaned sessions was `tmux kill-server`, which is not
    acceptable in a shared tmux. **Partly landed since**: the sessions now run
    on a tmux socket of spit.py's own, `spit-<pid>`, so `kill-server` can never
    reach the user's server (`3f6b279`, DECISIONS 69 a), a reported corpse is
    destroyed at the moment it is reported (`retire()`, `e5b4fba`), and the app
    kills its own server at exit. What is left is teardown when a single **chat**
    closes — `actions.py:action_exit_app` is still the only thing that frees
    anything, so a closed chat's windows outlive the chat.

**Why items 2 and 4 are not cosmetics** (learned 2026-09-11, closing the owner's
217/3 against this box's 220/0 — DECISIONS 73 and the `TASKS-FINISHED.md` entry for
branch `test-terminal-pane-read-parity`): a suite that cannot set the pane's geometry
and splices the cursor into the text is a suite whose verdict belongs to the machine.
Two of those three reds were exactly that. A token that crossed the right edge of an
80-column pane was on the pane, inside the tool's own report, and invisible to the
harness's read (fixed by reading with the tool's capture flags, `join_wrapped`
included, plus a `t18` guard whose own check says a wrap really happened); and a
capture taken before the shell had drawn anything read as an empty pane, because tmux
prints the blank rows and libtmux strips them (fixed by waiting for the prompt). Both
classes are guarded now; neither class is *impossible* now. Item 2 — `cols`/`rows` at
creation — is what pins the width an assertion depends on instead of inheriting tmux's
default for a clientless session, and item 4 — cursor as data — removes the splice that
overwrites the character under the cursor, which is why `t18` has to send its wrapped
token through `echo` rather than leave it on the command line. The one thing NOT to do
is "fix" the class by pinning the prompt or substituting a tame shell: DECISIONS 72 is
that the pane is the user's terminal, warts included, and the fix belongs in how the
pane is read and synchronised.


### State (crash-recovery record)

- **Branch**: none started. Everything marked landed above is on `main` via
  `task-terminal-empty-output`; this entry has no working branch of its own.
- **Scope** (when it starts): `spit_app/tools/terminal.py` (DESC + PROMPT),
  `spit_app/tools/run/terminal.py` (the state layer every item reads from),
  `spit_app/tools/lsterm.py`, and `tests/unit/terminal/` (220 checks, real tmux
  on a private socket through `stub_app.py`).
- **Done**: items 8, 9, 10 and 12, as marked where each is marked — nothing else.
- **Left**: pick ONE item, give it its own branch and its own `Go!`. The natural
  first pair is items 5 + 10 (`wait_for` replaces the blind `delay`, which is
  also what makes an in-flight call abortable — DECISIONS 68 says the loop is
  already free, so this is about cancellation and flaky sleeps, not about
  freezing the UI); the natural single starter is item 1 (`command=` + `env=` +
  `cwd=`), which is self-contained and is the one item every later
  UI-under-test harness needs regardless of what that UI turns out to be.
- **State hazards**: none. `tests/unit/terminal/` leaves stale socket *files*
  under `/tmp/tmux-1000/spit-unit-terminal-*` with no server behind them —
  safe to remove, and any new test must keep that property.
- **Verify**: full suite from the repo root. `unit:terminal` goes up by the new
  checks and nothing else moves. The rendered screen is the contract: prove any
  capture-formatting change **byte-for-byte** against the current output before
  changing behaviour (TRAPS #14), and keep the sandbox on by default (TRAPS #6)
  with `sandbox=False` only inside lifecycle tests.

## P12 - Token counts: how many are used, and how many exist  [owner's `Go!` given 2026-09-22; six-step handoff chain]

**`Go!` record**: the owner approved the proposal on 2026-09-22 and instructed
that the code be implemented step by step, one file per step, agents chained by
fenced handoff messages. The once-per-task `Go!` for **every** code step of this
entry is that instruction: do not re-ask, and do not invent further gates
(TRAPS #22).

- **The gap** (verified in the code). `endpoints/llamacpp.py` `stream()` parses every
  SSE chunk through `extract_fields()`, which reads **only** `choices[0].delta`
  (content / reasoning / tool_calls); everything else in every chunk is discarded, and
  nothing ever asks the server for its context size. Both numbers the owner wants —
  how full the window is, and what the chat has cost — are in the response today and
  thrown away.
- **Server-side facts** (verified 2026-09-22 against llama.cpp master source and
  `tools/server/README.md`; symbol names are the stable handle, line numbers drift):
  - The `usage` object (`usage_json_oaicompat()` in `server-task.cpp`):
    `prompt_tokens`, `completion_tokens`, `total_tokens`,
    `prompt_tokens_details.cached_tokens`. `prompt_tokens` is `slot.task->n_tokens()`
    (`server-context.cpp`) — the **whole prompt of that request, cache-reused tokens
    included**, i.e. exactly "context occupied", and correct even with
    `save_cache_prompt` in play.
  - The `timings` object attaches to the **last** streamed chunk unconditionally
    (`to_json_oaicompat_chat_stream()`, `deltas.back()["timings"] = ...`):
    `prompt_n`, `cache_n`, `predicted_n`; the README's own rule for context occupancy
    is `prompt_n + cache_n + predicted_n`. llama.cpp-only, and speculative decoding
    skews `timings` but not `usage`.
  - **Three stream shapes exist, so parse per chunk and detect no versions.** llama.cpp
    before PR #15444 (Aug 2025) put `usage` on the final `finish_reason` chunk,
    `choices` non-empty, sent whether requested or not (issue #12102). llama.cpp since
    #15444, and OpenAI itself, send `usage` **only** when the request carries
    `stream_options: {"include_usage": true}` (parsed via `server-schema.cpp`), and
    then as an extra final chunk with `"choices": []`.
- **The latent crash the first commit must fix**: `extract_fields()` does
  `delta["choices"][0]["delta"]` and `work_stream()` re-raises everything outside its
  timeout family — so an OpenAI-style empty-`choices` usage chunk today would kill the
  stream with an `IndexError`. The enabling guard: read `delta.get("usage")` **before**
  touching `choices`, and make `extract_fields` a no-op when `choices` is empty. That
  one rule is correct for all three shapes with no version detection.
- **Tokens used — the proposal**:
  - `prepare_payload()`: `payload["stream_options"] = {"include_usage": True}`. If some
    exotic endpoint 4xxs on the unknown field, retry once without the flag and remember
    that per endpoint (old llama.cpp ignores unknown fields *and* sends `usage` anyway).
  - `stream()`: take `usage` from any chunk that carries it.
  - Accumulate on the **`Chat`**, **never in `messages`** (they are POSTed verbatim) and
    **not on `Work`** (a new `Work` is constructed per send — `chat_text_area.py:45`,
    `chat_view_actions.py:50` — so it cannot hold anything across replies):
    `context` = latest call's `prompt + completion` (the window fill; each recursive
    tool-loop call refreshes it, since its prompt already contains the previous answer
    and the tool results), `generated` = sum of `completion_tokens` across the chat,
    `cached` = latest `prompt_tokens_details.cached_tokens` as best-effort bonus.
  - `timings` may be read the same way as a llama.cpp-only cross-check, never as the
    contract.
- **Maximum available — the proposal**:
  - New `async def get_context_size(endpoint, model)` beside `get_models()` in
    `endpoints/llamacpp.py`: `GET {address}/props` →
    `default_generation_settings.n_ctx`; router/multi-model mode takes `?model=<id>`.
    `{address}` is the endpoint URL minus the trailing `/v1` — the same rule `work.py`
    and `ManageCache` already use for the native `/slots/...` calls. The local managed
    server needs no special case: `app.get_endpoint("0")` already hands back
    `server.endpoint` (`app.py:143`).
  - Fallback chain: `/props` → `/slots[0].n_ctx` → a per-endpoint override field
    `context_size` (`uinteger`, 0 = auto-detect; precedent: the local server's
    `ctx-size`) → `None`, and the UI shows a dash rather than a lie.
    `/v1/models` `meta.n_ctx_train` is the *trained* context — informational only, not
    the server's limit; non-llama stacks that expose `max_model_len`/`context_length`
    in `/v1/models` may be taken as hints.
  - **Integration landmine**: `construct_payload(payload, self.endpoint)` forwards every
    endpoint setting not on its skip list to the server. `context_size` **must** join
    that list (`["name", "endpoint_url", "key", "reasoning_key", "save_cache_prompt",
    "parallel", ...]`) or it will be POSTed as an inference param.
  - Cache per `(endpoint, model)`; refresh where the value can actually change: managed
    server start (`handlers.py` / the llamacpp Apply button), model load
    (`work.py:maybe_load_model`), endpoint/model change in `ChatSettings`.
- **UI**: one `Label` in the per-chat `ChatSettings` row
  (`ctx 4.7k / 8.1k · gen 612 · cached 3.1k`), fed through the existing
  `chat_view.callback` signal path (or read at signal 0, stream end). Nothing in the
  message stream itself — a status row costs zero tokens.
- **Semantics to document, not fix**: with unified KV (new llama.cpp default; the app
  exposes `kv-unified`) `n_ctx` is the total shared across parallel slots; older
  servers divided it per slot (total = parallel × n_ctx). Report what the server
  reports, and say so in the docs.
- **Not proposed**: client-side tokenization (tiktoken or similar) — the app does not
  own GGUF vocabularies, the server is the only true counter. If a before-send budget
  check is ever wanted, `POST {address}/tokenize` is llama.cpp's own exact tokenizer.
- **Verify**: new unit section driving `LlamaCppEndpoint` and `get_context_size` against
  a canned-SSE stdlib HTTP server on 127.0.0.1 (no live model), append-only numbers
  (TRAPS #15): payload carries `stream_options`; `usage` extracted from **both** the
  empty-`choices` shape and the old `finish_reason`-chunk shape; empty `choices` no
  longer raises; `/props` parsed, override fallback honoured, absent answers `None`;
  `context_size` never appears in the outgoing payload (TRAPS #13 — the control asserts
  it *does* leak without the skip-list entry). Differential (TRAPS #18): replay every
  recorded response fixture with the flag on and off, assert byte-identical
  content/reasoning/tool_calls reconstruction. Full suite: only the new checks move.
- **Gotchas**: TRAPS #19 — `endpoints/llamacpp.py` imports `httpx`, so this suite is a
  **fifth dependency-listed suite** (after terminal/anchored/chat_smoke/chat_window):
  it must run under the test venv and report the remedy when the import fails, never a
  silent zero. Do not touch `messages`. A DECISIONS entry lands with the implementation
  recording the read-anywhere parse and the override fallback.

### Step chain (file by file, handoff discipline)

One file (or one clearly-stated concern) per step. Each step's agent finishes by
updating this entry's **State** and writing the **next fenced handoff message**
for the next agent, naming the next step; the chain ends at step 6, whose agent
closes the entry — after that there is no handoff, the resolution is the record.
Deviating from a step is allowed only where the code disagrees with the plan, and
must be stated **loudly** in the commit body, in the State fields, and in the next
handoff (precedent: DECISIONS 70 "Deviations from the handoff, stated loudly").

1. `spit_app/endpoints/llamacpp.py` — the enabling guard (`extract_fields` a no-op on
   empty/missing `choices`; `delta.get("usage")` read **before** `choices`;
   `self.usage` reset at each `stream()` start and set wherever it arrives),
   `stream_options: {"include_usage": true}` in `prepare_payload()` with one retry
   **without** the flag on a refusal (never lose a reply over counting), new
   `get_context_size(endpoint, model=None)` with the fallback chain above
   (`{address}` = endpoint URL minus trailing `/v1`; never raises, `None` = unknown,
   same shape as `get_models()`), and `"context_size"` added to the
   `construct_payload` skip list. Full suite green; `chat_smoke`'s golden md5
   unchanged.
2. `spit_app/chat/work.py` (+ `token_usage` init on `Chat` in `spit_app/chat/chat.py`) —
   harvest `self.endpoint.usage` after every `await self.endpoint.stream()` (the
   tool-loop recursion included; skip harvest on error paths) into
   `chat.token_usage = {"context": 0, "generated": 0, "cached": 0}` — on the **Chat**,
   not `Work`: `Work` is constructed per send (`chat_text_area.py:45`,
   `chat_view_actions.py:50`). `context` = latest `prompt_tokens + completion_tokens`;
   `generated` += `completion_tokens`; `cached` = latest
   `prompt_tokens_details.cached_tokens` best-effort. `messages` untouched.
3. `spit_app/manage/endpoint/endpoint.py` — add `context_size` to `NEW` (`uinteger`,
   default 0 = auto-detect, description says so; model it on `timeout`). The honouring
   logic is step 1's; prove it here, do not re-implement it.
4. `spit_app/chat/chat_settings.py` — a `Label` on the chat-settings row showing
   `ctx <used> / <n_ctx> · gen <generated> · cached <cached>`; `n_ctx` via
   `get_context_size(self.app.get_endpoint(cs("endpoint")), cs("model"))` cached per
   `(endpoint, model)`; refreshed at stream end (signal 0 on the `StreamCallback`
   path) and on endpoint/model change; a `None` renders as a dash, never as a number.
5. `spit_app/tests/unit/endpoints/` (+ row in `spit_app/tests/run_tests.sh`, ground-truth
   row in `doc/TESTING.md`) — canned-SSE stdlib HTTP server on 127.0.0.1 and canned
   `/props`/`/slots` payloads, no live model; every check in the **Verify** bullet
   above; append-only numbering (TRAPS #15); the skip-list check carries its
   fail-able control (TRAPS #13); differential on/off byte-identical replay (TRAPS
   #18). Fifth dependency-listed suite (TRAPS #19): runs under `~/.venv-spit`, reports
   FAIL with the remedy on a missing import, never a silent zero.
6. Close-out — full suite green with only this entry's checks moved; differential
   recorded; a new DECISIONS entry (read-anywhere parse; `n_ctx` fallback and
   override; `token_usage` on `Chat` not `Work`, the per-send construction being the
   reason; the skip-list entry); doc updates where the mechanism must be written down;
   then move this entry to `TASKS-FINISHED.md` with the resolution (branch, commits,
   which verification the close-out rested on). No sign-off step (DECISIONS 71,
   TRAPS #22). The branch is the owner's to merge, as always.

### State (crash-recovery record)

- **Branch**: `task-token-counts-p12`, cut from `docs-plan-token-usage-context-size`
  (`c7e7d74`, the planning landing). Last code commit on it: `756179d` (step 4).
  **Working tree clean** — the session that wrote step 4 died with it uncommitted
  and its State fields still describing the tree at step 3; the recovery of
  2026-09-23 re-measured it, committed it as `756179d`, and this doc commit is
  what it left in place of the handoff that was never written.
- **Scope** (so far): `spit_app/endpoints/llamacpp.py` (step 1),
  `spit_app/chat/work.py` + `spit_app/chat/chat.py` (step 2),
  `spit_app/manage/endpoint/endpoint.py` (step 3),
  `spit_app/chat/chat_settings.py` + `spit_app/chat/callback.py` (step 4 — TWO
  files, which is deviation D1 in the step-4 block). Rest of the chain: see the
  step list — one file per step, in order.
- **Done**: planning (`c7e7d74`), the entry move (`b799526`), **step 1**
  (`a173854`), **step 2** (`b7d06ac`), **step 3** (`304530a`) and **step 4**
  (`756179d`, recovered and re-verified) — see the four blocks below.

  **Step 1** (`a173854`): `extract_fields` is a no-op on empty/missing `choices`;
  `delta.get("usage")` is read in the chunk loop *before* anything touches choices
  and kept on `self.usage` (init'd in `__init__`, reset at the start of every
  `stream()`, stored only when the chunk carries a non-empty one);
  `prepare_payload()` sends `stream_options: {"include_usage": true}`; a **4xx**
  refusal with the flag set retries **once** without it (5xx not retried; a refusal
  that survives raises the same `Endpoint returned N: ...` `RuntimeError`, so
  `work_stream`'s error path is unchanged); new never-raising
  `get_context_size(endpoint, model=None)` with the chain `/props` →
  `default_generation_settings.n_ctx` (sends `?model=<id>` when a model is given) →
  first `/slots` `n_ctx` → `context_size` override > 0 → `None`; `"context_size"`
  added to the `construct_payload` skip list. Full suite: every row at its
  TESTING.md value, FAIL 0, byte-identical to the pre-change run; `chat_smoke`'s
  golden md5 unchanged (`8ae9d1186a59627d30d05dee95f0ad95`).
  **Deviations, stated loudly** (also in the commit body): **(D1)** the proposal's
  "remember that per endpoint" is NOT implemented — `Work` deepcopies the endpoint
  dict per send (`work.py:22`), so remembering there dies with the `Work` and
  remembering properly means mutating shared settings from a request path (not this
  file). Cost: an endpoint that refuses the flag pays one extra request per send,
  never a lost reply. **(D2)** `native_address()` strips the trailing `/v1` only
  when present (the rule of record is a blind `[:-3]`); identical for every URL the
  app builds, no mangling when a URL lacks the suffix. **(D3)** `get_models`'
  three Authorization-header lines were extracted to `auth_headers()` (identical
  semantics) because `get_context_size` needs the same rule; `stream()`'s own
  header block was deliberately left as HEAD wrote it.

  **Step 2** (`b7d06ac`): `Chat.__init__` carries
  `self.token_usage = {"context": 0, "generated": 0, "cached": 0}` (a plain dict
  beside `self.work = None` (`chat.py:34`), at `chat.py:40` — not a Textual var), and
  `Work.harvest_usage()` (`work.py:114`) is called immediately after the one
  `await self.endpoint.stream()` and still inside its `try` (`work.py:151`), so an
  escaping exception skips it. One point only: the tool-loop recursion
  (`work.py:165`) re-enters the same statement. Semantics: `if not usage: return`
  first (silence changes nothing — it never zeroes the accumulated numbers);
  `context` = the LATEST call's `prompt_tokens + completion_tokens` (window fill,
  refreshed by every call of a tool loop, never summed); `generated` +=
  `completion_tokens`; `cached` = the latest `prompt_tokens_details.cached_tokens`,
  and an absent one reads 0 for THAT read rather than keeping the previous call's
  figure. Every key read with `.get()`. `messages` untouched. **No deviation from
  the handoff.** Accepted limit, in the commit body: `token_usage` is session state
  — `write_chat_history` (`chat.py:106-111`) still writes only
  ctime/settings/messages, so a reloaded chat starts at zeros; it is NOT added to
  the saved chat file without the owner's word.

  **Step 3** (`304530a`): `NEW` gained, after `timeout` and before `reasoning_key`
  (mount order is `NEW`'s dict order; nothing else reordered),
  `"context_size": {"stype": "uinteger", "empty": False, "desc": "Context Size
  (0 = auto-detect)", "value": 0}` — modelled on `timeout` (same `uinteger`, same
  `"empty": False`, which `manage/validation.py:27`/`:152` turn into `is_not_empty`,
  so it cannot be saved blank; the desc carries the `N (0 = meaning)` phrasing), and
  deliberately NOT on `parallel`, which omits `"empty"`. No logic; `llamacpp.py`
  untouched. **No deviation from the handoff.** Measurements after the edit
  (throwaway `/tmp/p12_step3_probe.py`, PASS 10 FAIL 0 — step 5 replaces it):
  `get_context_size(ep, "m")` on `http://127.0.0.1:1/v1` (BOTH HTTP rungs refused)
  with `context_size` 8192 → **8192** (the override rung answered);
  `prepare_payload()` keys → exactly `model/messages/stream/stream_options/timeout`,
  `context_size` **absent**; the TRAPS #13 control — the same endpoint plus
  `n_ctx_control` 4242, NOT on the skip list → **does** appear (4242) while
  `context_size` still does not; and the three no-value paths (0, blanked-to-`None`
  the way `store_values` leaves it, key absent entirely) all answer `None` without
  raising. Probe detail worth keeping: `NEW` carries no `"value"` for the settings
  without a default, but `construct_payload` (`llamacpp.py:149`) and `auth_headers`
  (`:29`) index it, so a test endpoint must be built as a SAVED one (`setdefault`).
  Accepted limit, in the commit body: an endpoint stored BEFORE this change keeps
  only its own keys (`settings` reads `endpoints.json` verbatim, `Manage.load()`
  deepcopies, `manage.py:37`) so it shows no Context Size field, even after an
  edit+save; harmless (the override is the last of three rungs and is read with
  `.get()`), and NOT to be "fixed" by merging `NEW` into loaded endpoints in
  `settings.py` without the owner's word.

  **Step 4** (`756179d`, **recovered 2026-09-23**): the counts row is a `Label`
  (`ChatSettings.usage_label`) mounted LAST in `on_mount` — a position that is
  load-bearing, because `self.selects` and every `children[1/3/5]` in this file
  index BY POSITION: mounted before the Selects it shifts all three and
  `unit:chat_smoke` dies inside its own harness (`'Label' object has no attribute
  'set_options'`), which the outer runner's `| tail -n 1` reports as
  `PASS: 0  FAIL: 0`. Text `ctx <used> / <n_ctx> · gen <generated> · cached
  <cached>`; `count_or_dash()` renders `None` as `—`, never as a number, and 0 as
  0. `context_sizes` caches the window size per `(endpoint, model)` — absent key
  "never asked", stored `None` "asked and the server would not say" — with
  `"none"`/NULL models normalised to `None` so a router server is never asked
  `?model=none`, and each answer stored under the pair its probe was STARTED for,
  never under whatever is selected when it lands. `refresh_usage()` is the public
  seam: called from `on_select_changed` (endpoint/model change, including the
  model `update_models()` picks programmatically, which announces itself the same
  way) and from the signal-0 branch of `ChatView.on_stream_callback`; both carry
  the `endpoint_list()`-membership guard, which is what keeps `get_context_size()`
  away from the `{}` the smoke stub answers with. The probe runs in
  `@work(group="context-size", exclusive=True, exit_on_error=False)`: a worker
  because it is two GETs of `timeout=3` (~6 s on an endpoint answering neither
  `/props` nor `/slots`, which would freeze the UI at the end of every reply), and
  in its OWN group because `exclusive=True` without a group cancels every other
  worker of that node — `update_models()` and its 60-try server wait included
  (measured on a bare widget: default group → `a-CANCELLED`, own group → runs to
  completion). The harvest-before-signal ordering is VERIFIED, not assumed: signal
  0 is posted as stream()'s last act and the harvest runs the moment the await
  returns, so the row shows this reply's numbers; the probe proves the instrument
  can see staleness by deferring the harvest past the signal.
  **Deviations, stated loudly** (also in the commit body): **(D1)** the refresh is
  wired in `chat/callback.py`, NOT in `chat_settings.py` — the step named one
  file and hazard (a) below is why it could not be: an `on_stream_callback` on
  `ChatSettings` is never delivered (a sibling of the `ChatView`, and a Textual
  Message bubbles to ANCESTORS only), so the call sits in the one branch that
  already knows "signal 0, this reply is over"; a handler on `Chat` was rejected
  because it also fires for signals 1 and 2 — once per streamed chunk — for a call
  needed once per reply. **(D2)** the figures render RAW, not in the proposal's
  `4.7k` form, which is what the 80-column limit below costs. **(D3)**
  `refresh_usage()` also fires on a `model_settings` change (not in the cache
  key): one redraw, no probe, accepted.
  **Verified by the recovery** — probes green on the tree as it landed:
  `/tmp/p12_step4_label_probe.py` (A the row moves through the real seam and NOT
  with the seam unwired — the control; B a real harvest renders `ctx 4311 / — ·
  gen 211 · cached 3050` and the second reply is not one-reply-stale; C a dead
  endpoint with no override is a dash and never `0 / 0`; D one probe per pair,
  four more refreshes cost zero, a new model costs exactly one, step 3's
  `context_size` override renders; E a 0.5 s probe neither delays the refresh nor
  stalls the message loop; F endpoint change through the real `on_select_changed`;
  G the three Selects still sit at children[1/3/5] and the Label is the last
  child), `/tmp/p12_step4_mount_probe.py` (the row is filled at MOUNT with no
  reply ever sent, at a cost of exactly one probe, plus the staleness control),
  `/tmp/p12_step4_exclusive_probe.py` (the worker-group measurement above),
  `/tmp/p12_step4_probe.py` (the signal-0 receivers). Six byte-identical full-suite
  runs of this tree (md5 `478ed3aff02c64dd6934ccbd1acb23fc`): the crashed
  session's pre-step baseline and its two runs, and three taken after the
  recovery — every row at its TESTING.md value, FAIL 0, `chat_smoke`'s golden md5
  unmoved.
  **LIMIT FOUND BY THE RECOVERY, FILED FOR THE OWNER** (measured through
  `WindowApp`, which mounts the repo's own `spit_app/styles.css` — TRAPS #24; the
  row is `height: 1`, so the question is horizontal): the Label takes its natural
  width and the three Selects give way. At 80×24 the Selects are **12/13/13**
  columns at HEAD, **3/3/4** with this Label and a zeroed chat (the 28-column text
  ends exactly at column 80), and **1/1/1** with a running chat's figures, whose
  39–47-column text then ends at 84–97 of the 80 available and is **clipped**. At
  120 columns the row fits and the Selects keep 10–14 each. No suite can see this
  (`chat_smoke`'s dump reads the message list, `chat_window`'s checks are about the
  window), so the row is unasserted territory. The relief is a rendering choice —
  the k-abbreviated form the proposal showed, or CSS giving the Label the leftover
  width and ellipsizing it, or a row of its own — and it is the owner's, so nothing
  was changed for it. Probes: `/tmp/p12_recover_layout_probe2.py` (after) and
  `/tmp/p12_recover_layout_before.py` (HEAD — pass it the tree to measure).
- **Left**: **step 5** — `spit_app/tests/unit/endpoints/` (+ a row in
  `spit_app/tests/run_tests.sh`, + the ground-truth row in `doc/TESTING.md`):
  canned-SSE stdlib HTTP server on 127.0.0.1 and canned `/props`/`/slots`
  payloads, no live model; every check of the **Verify** bullet above; append-only
  numbering (TRAPS #15); the skip-list check with its fail-able control (TRAPS
  #13); the differential on/off byte-identical replay (TRAPS #18); fifth
  dependency-listed suite (TRAPS #19) — `~/.venv-spit`, FAIL-with-remedy on a
  missing import, never a silent zero. The full handoff for it is fenced below.
  Nothing else of P12 is left before step 6 except that one **owner question**:
  what the counts row renders at 80 columns (see LIMIT in the step-4 block). It
  is a code change (`chat_settings.py` and/or `styles.css`) AND a taste call, so
  it waits for the owner's word; it does not block step 5 or step 6, and it must
  not be "fixed" by guessing — a k-form invented by an agent is a different lie
  from the one `count_or_dash()` refuses.
- **State hazards**: none in the repo — tree clean at `756179d` + this doc commit,
  full suite green with every row at its TESTING.md value (tools
  127/24/30/119/80/32/68/29, unit 68/131/168/568/33/278/121/157/223) and
  `chat_smoke`'s golden md5 unmoved (`8ae9d1186a59627d30d05dee95f0ad95`).
  In `/tmp`, deliberately NOT committed (the committed suite is step 5) and safe
  to delete: `p12_check.py`, `p12_old_llamacpp.py`, `p12_step2_probe.py`,
  `p12_step3_probe.py` (steps 1-3), `p12_step4_probe.py`,
  `p12_step4_exclusive_probe.py`, `p12_step4_label_probe.py`,
  `p12_step4_mount_probe.py` (step 4 — all four green on the tree as committed),
  `p12_recover_layout_probe.py`, `p12_recover_layout_probe2.py`,
  `p12_recover_layout_before.py` (the 80-column finding) and `p12_rec_full_{1,2}.txt`
  (the recovery's suite rows). All run with
  `PYTHONPATH=~/spit.py ~/.venv-spit/bin/python`; none is read by anything in the
  repo, and step 5 replaces them with committed checks. TWO recovery artefacts to
  know about so nobody chases them: (a) `/tmp/p12_step4_seam_probe.py` was written
  BEFORE step 4 existed in the file — it monkey-patches `refresh_usage` onto
  `ChatSettings` and expects six children — so it now reports four reds that are
  expectations of the old tree, not defects (the doubled refresh is the probe's
  own `Chat` handler plus the wired `ChatView` one; harmless, because
  `refresh_usage` is a redraw); the label probe supersedes it. (b)
  `/tmp/spit-head-p12/` is a throwaway `git archive` copy of `19a6c0b` used for the
  before-picture of the settings row — remove it freely.
- **Verify**: each step: full suite from the repo root, counts unmoved except by this
  entry's own new checks (step 5). Final: the entry's **Verify** bullet, then close
  per step 6.

### Handoff for step 5 (written by the step-4 recovery, 2026-09-23)

```
P12 step 5: build spit_app/tests/unit/endpoints/ — the committed suite for
steps 1-4 — plus its row in spit_app/tests/run_tests.sh and its ground-truth row
in doc/TESTING.md. Canned-SSE stdlib HTTP server on 127.0.0.1 + canned /props and
/slots bodies: no live model, nothing beyond localhost. Append-only test numbers
(TRAPS #15). Checks the entry's Verify bullet asks for, and the four the steps
earned on the way:
  * prepare_payload() carries stream_options {"include_usage": true};
  * usage is taken from BOTH stream shapes — the final chunk with "choices": []
    (OpenAI, llama.cpp since #15444) and the finish_reason chunk with choices
    non-empty (old llama.cpp);
  * an empty-choices chunk does NOT raise (the latent IndexError step 1 removed —
    write this one against the old extract_fields first and watch it go red);
  * a 4xx refusal retries once WITHOUT the flag and a 5xx does not;
  * get_context_size: /props default_generation_settings.n_ctx, ?model=<id> when
    a model is given, then /slots[0].n_ctx, then the context_size override, then
    None; never raises on a dead address, a 404, or garbage JSON;
  * context_size NEVER appears in the outgoing payload, with the TRAPS #13
    control that a setting NOT on the skip list DOES leak;
  * Work.harvest_usage: context is the latest call's prompt+completion (never
    summed), generated accumulates, cached is the latest details or 0, silence
    zeroes nothing, an error path counts nothing, messages untouched;
  * the row (chat_settings): dash-not-number for None, one probe per
    (endpoint, model), raw figures, and the three Selects still at children[1/3/5].
Differential (TRAPS #18): replay every recorded SSE fixture with the flag on and
off and assert byte-identical content/reasoning/tool_calls reconstruction — and
verify the probe's own input mapping FIRST (TRAPS #13: three historical probes fed
fixtures to the wrong file and still printed "identical").
Shapes to steal rather than re-derive: /tmp/p12_check.py (the stream),
/tmp/p12_step3_probe.py (payload + skip-list control), /tmp/p12_step2_probe.py
(the harvest), /tmp/p12_step4_label_probe.py (the row, and StubEndpointApp — the
smoke stub's endpoint_list()/get_endpoint() answer {}, which is the GUARD path and
can never start a probe). A test endpoint must be built as a SAVED one: every
field needs {"value": ...} because construct_payload and auth_headers index it.
Do not touch messages. Do not "fix" the 80-column row: that is the owner's call,
filed in the step-4 block. Fifth dependency-listed suite (TRAPS #19): the runner
row must FAIL with the remedy when the import is missing, never PASS 0 FAIL 0.
Full suite after it: every existing row where TESTING.md says it is, this suite's
count new, FAIL 0 everywhere, chat_smoke golden md5
8ae9d1186a59627d30d05dee95f0ad95 unmoved. Then step 6 closes the entry.
```

## Protocol when starting a task from TASKS-PLANNED.md

1. `git branch -a` (avoid name collisions), create a descriptively named
   branch. Never work on `main`, never push. Ask for the owner's `Go!` before
   the first **code** change; an entry that is waiting on that `Go!` still
   lives here, with **Left** saying exactly that.
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
   this entry. **That decision is yours to make — there is no sign-off step.**
   Do not leave a finished entry here because a human "should look at it": put
   the by-hand check inside the finished entry if it is still worth doing, and
   say in the resolution which verification the close-out rested on. If an
   item cannot be performed in this environment at all, it was never a
   verification, and saying so out loud is better than an entry that can never
   close (TRAPS #22).
5. An abandoned entry keeps its State fields honest — that is the entire point
   of the file: **Left** is one sitting's next step, **State hazards** names
   what is red, half-edited or left in `/tmp`, and the recovery point is a
   commit, never an uncommitted tree.
