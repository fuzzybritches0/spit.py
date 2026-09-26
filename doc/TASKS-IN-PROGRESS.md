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

> **ONE entry is open** in this file: the `terminal`-tool harness list
> (followup 4) below. Nothing else is half-done, and no branch is waiting on an
> agent.

> **P13 CLOSED COMPLETE 2026-09-25** — **WP-A, WP-B, WP-C, WP-D and WP-E are all
> closed** in `TASKS-FINISHED.md`, and **the chain ends with WP-E: no handoff
> message was written after it, because there is no next package** (WP-F does not
> exist). The five packages: the unpacking `0afaef8` (WP-A), the generator
> `a6ec179` (WP-B), the token-status hook `6f1a0ed` (WP-C), the wiring `bcdc441`
> + the TESTING.md row `dadc11b` (WP-D), and WP-E's docs commit (DECISIONS 81
> with DECISIONS 80 cross-linked both ways, `PROJECT.md`'s note chain,
> `TESTING.md`'s post-wiring sentence, the P13 entry closed in
> `TASKS-PLANNED.md` and its follow-ups filed as **P14** (the handoff tool, whose
> arrival re-pins the `critical` text's fenced-block clause), **P16**
> (`note_mode` `separate`/`merge`/`off`), **P17** (the notes rendered in the UI),
> **P18** (the level numbers as settings) — each of those a task of its own with
> its own `Go!` ahead of it, none of them P13's unfinished work. Ground truth at
> the close: `unit:endpoints` **442**, `unit:system_note` **219**, every other row
> where P12 left it, `chat_smoke`'s golden md5
> `8ae9d1186a59627d30d05dee95f0ad95` unmoved, full suite exit 0 twice
> byte-identical. **`p13-wp-a-note-unpacking` awaits the OWNER'S MERGE** — the
> only part of finishing that is not the agent's (DECISIONS 71 a); nothing was
> pushed and `main` is untouched. Do not start anything from this banner: P13's
> mechanism is shipped and pinned, and the WHY is DECISIONS 81.
> **P13/WP-D closed 2026-09-25** on `p13-wp-a-note-unpacking` (`bcdc441` the
> code+test, `dadc11b` the `unit:endpoints` TESTING.md row 394 → 442, then
> this close-out): `Chat.__init__` builds `SystemNotes(self)` and the hook
> reference next to `token_usage`; the token-status hook is registered **once
> in the module `HOOKS` list at `chat.py` import — one shared stateless
> instance** (the WP-D decision: the hook keeps no state about WHICH chat, so
> sharing is its natural shape; a per-chat registration would ask N identical
> hooks per message for zero behaviour; pinned by t13, and the rejected
> alternative reddens it); `Chat.context_window()` reads
> `ChatSettings.context_sizes[context_key()]` as it stands — no network on
> the request path, the dash answers `None` — and `token_status.py` needed
> **zero changes**, exactly as WP-C's `getattr` ask promised;
> `Work.work_stream()` calls `self.chat.system_notes.attach()` immediately
> before `await self.endpoint.stream()`, so every request — including the
> ones inside a tool loop — asks the hooks first. `unit:endpoints` **442**
> (the new `test_note_chain.py`, t13, 48 checks: silence under threshold with
> the over-50% control, the note byte-for-byte in the right wire position,
> same level adds none with the higher-level control, the merged `user`
> carrier with the same message count, the UI list growing by replies only,
> the unknown-window dash silent with its control, no probe on the request
> path, the registration shape); `unit:system_note` **219 unmoved on the bare
> interpreter**, `chat_smoke`'s golden md5 `8ae9d1186a59627d30d05dee95f0ad95`
> unmoved (the wired hook is silent there by the unknown-window rule), full
> suite exit 0 with every other row unmoved. Resolution in
> `TASKS-FINISHED.md`.
> **P13/WP-C closed 2026-09-25** on `p13-wp-a-note-unpacking` (`6f1a0ed` the
> code+test, `ad56e2d` the `unit:system_note` TESTING.md row 96 → 219, then
> this close-out): new `spit_app/chat/token_status.py` — `TokenStatus`, the
> token-status hook, `name = "token_status"` — the owner's
> percentage-OR-remaining levels as module constants, the machine advancing
> **by rank** (the 32k announce-order `small_window, warning, critical` with
> `info` shadowed forever, pinned as a walk), the four model-facing texts
> pinned byte-for-byte at all-distinct figures with the figures never
> clamped, and **no state on the instance** — the hook's memory is its own
> standing notes, so reload, abort and the generator's drop rule need no
> resync (a verdict dropped off the tail rides the next message, pinned). It
> asks the total through `chat.context_window()` with `getattr` — unknown
> window or unknown counts are silence, the door that keeps a request alive —
> and that accessor is **WP-D's** to add. 123 new checks (`test_token_status.py`,
> t10–t18 in WP-B's suite, bare `python3`, the TRAPS #19 gate re-run over the
> new module and measured both ways), fifteen substituted defects each
> reddening its group; `test_generator.py`'s 96 green throughout (the contract
> unbent); full suite exit 0, every other row unmoved, `chat_smoke`'s golden
> md5 unchanged. **WP-E has no `Go!`**: it arrives with WP-D's handoff
> message, and its finisher writes a close-out, not a handoff.
> **P13/WP-B closed 2026-09-25** on `p13-wp-a-note-unpacking` (`a6ec179` the
> code+test, `7046bcb` the `unit:system_note` TESTING.md row, then this close-out):
> new `spit_app/chat/system_note.py` — `SystemNotes(chat).attach()`, the module
> `HOOKS` list, `Note(level, text)` — writes a hook's note **into the message dict**
> under the private key `system` as `{"hook", "level", "text"}`, so the messages
> list never grows; the contract pinned there is that a hook is anything with
> `notice(chat, messages, index)` returning **`Note(level, text)` or `None`** (the
> level travels in the return because WP-C's levels are state-machine output;
> `hook` is stamped by the generator, from the hook's `name` else its class name),
> and idempotence keys on that name against the notes already standing, so it holds
> across instances and across a reload. New ground-truth row
> **`unit:system_note` 96** (t1–t9, bare `python3`, no venv preamble — the absence
> is the gate, TRAPS #19 inverted); full suite exit 0 with every other row unmoved
> and `chat_smoke`'s golden md5 unchanged; resolution in `TASKS-FINISHED.md`, which
> also records the one pre-existing flake it found (`unit:sandbox`
> `t3-child-stopped`, a reap race at a byte-identical tree — not P13's, not fixed
> here). **WP-D and WP-E have no `Go!`**: each arrives with the previous
> finisher's message.
> **P13/WP-A closed 2026-09-25** on `p13-wp-a-note-unpacking` (cut from the
> `docs-p13-owner-rulings-handoff-wp-a` tip `1522932`, `0afaef8` the code+test, then this
> close-out): `prepare_payload()` now pops the private key `system` from the deepcopy and
> unpacks each note right after its carrier — MERGED into the content when the carrier is
> `user`, its own `{"role": "user", ...}` item when it is `tool`/`assistant`, never a
> `system` item, never a second consecutive `user`. `unit:endpoints` 343 → **394** with
> the new `test_system_note.py` (t12, 51 checks); resolution in `TASKS-FINISHED.md`.
> **How P13 chained (history now — the chain ran and ended)**: the owner's
> instruction of 2026-09-25 (quoted verbatim in the WP-B entry) gave the `Go!` for
> **WP-B** and told each finisher to write the next handoff message, so WP-C, WP-D
> and WP-E ran **on top of this branch** as each previous WP's finisher opened its
> entry — no new branches. **All five packages closed on 2026-09-25**, WP-E
> writing no handoff, and the owner merges `p13-wp-a-note-unpacking` to `main`
> when the owner chooses. The owner rulings every package built on (`user` role,
> percentage-OR-remaining levels) ride on that branch and are recorded in
> DECISIONS 81. The older sentences in the paragraphs above ("WP-E has no `Go!`",
> "WP-D and WP-E have no `Go!`") are what was true when each finisher wrote
> them; they are history, not open work.
> **P15 closed and merged 2026-09-25** (`b969e00`, close-out `d160c2e`): `unit:prompt`
> reads its pinned **33** on `main` again, so a full-suite run from `main` has no
> pre-existing red to explain. **P13's owner rulings are on the unmerged docs branch
> `docs-p13-owner-rulings-handoff-wp-a`** — the role is `user`, the levels are
> percentage-OR-remaining; `main` still carries the older P13 text, which is why WP-A
> was cut from that branch and not from `main`.
> **P12 — token counts — closed on 2026-09-24** on `task-token-counts-p12`
> (`c7e7d74` planning, `b799526` the entry move, then the six steps
> `a173854`, `b7d06ac`, `304530a`, `756179d`, `eef3045` + the docs after each,
> tip `a643666` + the close-out): usage is read from wherever a chunk puts it,
> the window size comes from `/props` → `/slots` → the endpoint's
> `context_size` or a dash, the counts ride on the `Chat` (never `Work`, never
> `messages`), and `spit_app/tests/unit/endpoints/` — **343 checks**, the fifth
> dependency-listed suite — is part of the ground truth in `doc/TESTING.md`.
> Resolution in `TASKS-FINISHED.md`, which also carries the two recoveries this
> chain needed and the deviations of steps 1, 4 and 5 in one place. The one
> thing P12 leaves for the owner is the counts row's 80-column rendering — a
> code change and a taste call, so it waits for the owner's word, with the
> measurement attached so it can be decided without re-measuring.
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
