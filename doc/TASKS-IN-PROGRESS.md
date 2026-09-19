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

> **TWO entries are open** while WP-E is in flight: the ratatui enhancement list,
> followup 4, and **WP-E of the on-demand-loading pipeline**. **WP-E's `Go!` was
> GIVEN by the owner on 2026-09-19 together with its ruling — "`refuse in
> prune()`": `prune()` itself returns while the view's `is_edit` is set** — so the
> next agent may edit code. Its branch is cut, its measurements are recorded in
> its entry below, and NO code has been edited yet. Back to ONE entry when WP-E
> closes.
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
> WP-B, WP-C and WP-D are all closed there, on branches awaiting the owner's merge
> (the chain is `task-anchored-scroll-widget` → `task-index-accessor-refactor` →
> `task-sliding-window-core` → `task-scroll-load-prune-triggers`, `main` untouched
> throughout); **WP-E and WP-F are not started** — each takes its own branch cut from
> the chain tip and its own `Go!` (`doc/UI-ONDEMAND-LOADING.md`). The followup
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

## WP-E — edits, undo and removal across the window edges  [`Go!` GIVEN 2026-09-19 — code not started]

The fifth work package of `doc/UI-ONDEMAND-LOADING.md` (the sliding window):
`undo._insert/_change/_remove`, the message-level add/remove flows and the focus
that has to survive them, all of which still assume the widget tree is the whole
history. Scope, Accept and the coupling-table row (`chat/message/actions.py`
87/89, 123/125/127, 138 = "the index-editing flows — WP-E") are in that file.

### State (crash-recovery record)

- **Branch**: `task-edit-undo-removal-across-window-edges`, cut from the chain tip
  `5d36627` (= `task-scroll-load-prune-triggers`, itself unmerged; the chain is
  A → B → C → D → E, `main` `8819e73` untouched). Last commit: `git log -1` on it —
  DOCS ONLY so far (this entry plus the ruling), i.e. **no code commit exists**.
- **Scope**: NOTHING edited. Planned: `spit_app/chat/undo.py`,
  `spit_app/chat/chat_view.py` (`mount_message`, `on_remove_message`, possibly
  `prune`), `spit_app/chat/message/actions.py`,
  `spit_app/chat/chat_view_actions.py` (`show_cots`/`reset_message_edit`, only if a
  materialized widget turns out NOT to inherit the mode), plus NEW
  `spit_app/tests/unit/chat_window/test_window_edits.py` (t21 onward — TRAPS #15).
- **Done**: measurement only; no claim below is inherited. The baseline suite run
  HERE at `5d36627` is byte-identical to the `TESTING.md` table (tools
  127/24/30/119/80/32/68/29 = 509, anchored 68, arguments 131, chat_smoke 168,
  chat_window 270, prompt 33, render 278, run_script 121, sandbox 119, terminal
  223, FAIL 0 everywhere; `/tmp/wp-e-baseline-mine-1.log`), and `chat_smoke`'s
  golden md5 is `8ae9d1186a59627d30d05dee95f0ad95`. Every defect below was
  re-measured on THIS box with the WP-E probes
  (`/tmp/wp-e-probe-{undo,actions,actions2,undopath,mountmsg,focus,isedit}.py`),
  each of which asserts its own input mapping — child0 really is `messages[lo]` —
  before it prints a row (TRAPS #13).
- **Measured, on this tree** (headless, `~/.venv-spit`, 1k/200-message fixtures,
  `(80,24)`):
  - `undo._insert(msg, 3)` at the open window `(950,1000)`: `child_position(3)` is
    None → `mount(before=None)` **appends at the TAIL**, then `require_widget(3)`
    raises IndexError; after-state `window=(950,1001) children=51 child0_index=951
    consistent=False`, `len(messages)` 1000→1001, `write_chat_history()` never
    reached (writes 2→2). Data changed, widget mounted behind the wrong neighbour,
    `lo` never slid, store untouched.
  - `undo._remove(3)`: `del self.messages[index]` runs FIRST (200→199), then the
    accessor raises → `consistent=False`, lo unchanged, no write.
    `undo._change(3)` (driven with a real undo entry, so the list assignment is
    valid) replaces `messages[3]` and overwrites `undo_list[undo_index]`, THEN
    raises — the entry is consumed, `undo_index` is never decremented, and nothing
    is persisted.
  - In-window `_insert`/`_remove`/`_change` all stay consistent: the defect is
    purely at the edges. `_insert(index == window_hi)` with the bottom pruned works
    BY LUCK (child_position == len(children) → the append IS the right neighbour);
    `_insert(hi+3)` raises and leaves `consistent=False`.
  - `mount_message`'s `index < window_start` branch is wrong in **direction**, not
    just at the gap: inserting at any `index <= lo` shifts every mounted widget's
    data index by +1, so the answer is `window_start += 1` (or a materialize) —
    never a front mount. Measured `mount_message(3)` at `(150,157)` →
    `window=(149,157)`, children[0] projects index 3, consistent False;
    **`mount_message(lo-1)` — the adjacent case — is ALSO inconsistent** (children[1]
    projects lo+1: a one-message hole); `index > hi` mounts at the end and is
    inconsistent too.
  - **A crash reachable with NO keypress**: `Message.maybe_add_message_next`
    (`message/actions.py:138`) does `require_widget(index+1)`; with the bottom
    pruned and focus on the last mounted widget (hi=157, `widget(158)=None`)
    `check_action("add_message_next")` **raises IndexError** out of the binding
    machinery — and `check_action` is what `refresh_bindings` runs. The question is
    about the DATA (`messages[index+1]["role"]`), not about a widget.
  - Focus: prune can never evict focus (`_prune_pinned` covers `is_edit`,
    `focused_widget`/`focused_message`/`has_focus_within`, the streaming tail), so
    the focused widget only leaves the window by REMOVAL. With focus mid-window
    (child[1]) and `RemoveMessage(len(messages)-1)` landing BELOW the window,
    `on_remove_message`'s `self.widget(index) or self.last_child()` moves focus to
    child[6] — the window tail, ~5 messages away from where the reader was.
    `undo._remove` of the window-TOP widget and of a pruned-to-7 window both
    survive (Textual moves focus itself, `focused_widget` stays mounted,
    `view.focus()` is fine), so the surviving decisions are the below-the-window
    removal and "no mounted neighbour → focus the ChatView".
  - `is_edit` (the `Go`-time question): `_triggers_frozen()` already refuses paging
    AND pruning while `is_edit`, and `_prune_pinned` already refuses per widget —
    and `prune()` has exactly TWO callers in the app (`chat_view.py:558`, `:583`),
    both inside that already-frozen trigger path (`grep -n '\.prune()' spit_app` =
    those two). An explicit `prune()` is nevertheless mode-blind: a grown window
    `(938,957)`/19 → **evicted to `(947,957)`/10 with `is_edit=True`, identical to
    `is_edit=False`**; the same grown window with ONE widget carrying `is_edit=1`
    evicts nothing (19 → 19, and the pin bounds the whole walk). (The "40 notches
    with the mode on" row only proves the freeze against `t17`'s control: at that
    particular parked state the same 40 notches do nothing with the mode OFF too.)
  - Cost of a far materialize, for the Accept sentence: `materialize(3)` from the
    open window `(950,1000)` mounts **997 widgets in ~23.5 s headless**,
    `consistent=True`, **0 bad frames**, and the reader does not move (still on
    997); `_insert`'s following `focus()` takes it to top=3; the next `prune()` →
    `(3,10)`/7.
  - **The mode IS inherited at mount, so `show_cots`/`reset_message_edit` need no
    replay code** (`/tmp/wp-e-probe-inherit.py`, a fixture carrying `reasoning` in
    every 10th message, each of those an assistant turn): materializing the SAME
    index below the window with `is_edit=False` yields the target's
    `cnt["reasoning"].display=False`, and with `is_edit=True` it yields
    `display=True` — that is `Message.maybe_mount_content` reading
    `chat_view.is_edit`, exactly as the plan's fact 6 predicted. A widget mounted
    BEFORE the mode was turned on flips False→True on `action_edit_on()` and back
    on `action_edit_off()`. And a widget carrying per-widget `is_edit=1` SURVIVES a
    prune (7 → 7), which is what makes `reset_message_edit`'s window-only loop
    sound: an edited widget is never unmounted, so there is no edit state out there
    to reset. (The gap widget that probe sampled landed on a user message, so the
    gap-widget case is NOT covered by that row and gets its own check in the
    suite.) WP-E's only code debt in `chat_view_actions.py` is therefore the stale
    comment saying this state "has to be replayed at mount (WP-E)": it already is.
- **THE `Go!` WAS GIVEN, WITH THE RULING** (owner, 2026-09-19): of the one real
  question — should `prune()` ITSELF refuse while `is_edit` (unloading disabled at
  the invariant's own definition rather than inherited from its two callers, at the
  cost that a grown window is released only at edit-off, 19 held until the first
  prune after edit_off), or keep the per-widget pins and leave `prune()`
  mode-blind? — the owner ruled: **"I go with your recommendation: refuse in
  `prune()`."** So `prune()` returns without evicting while `view.is_edit` is set,
  AND the per-widget pins of fact 5 stay as they are; both halves get a control
  (the same call with the mode off evicting 19→10). The ruling does not dissolve
  fact 5's per-widget set either: the mode is per-VIEW and the pin is per-CHILD, and
  with `prune()` refusing there is no walk left to pin while editing — the pins are
  what `t5` already measures and what protects the tail at edit-OFF. Accepted cost,
  restated so nobody rediscovers it: a window that grew during an edit is released
  only by the first prune after edit_off (measured 19 → 10).
- **Left**: (1) code, one concern per commit — window-aware
  `undo._insert/_change/_remove` (query with `widget()`, `materialize()` where the
  flow needs the widget, slide `lo` +1 on an insert below the window top / −1 on a
  removal below it, mirroring `on_remove_message`, and take the guard the way
  `materialize()` does — SAVE/RESTORE, per WP-D's hazard that `_grow_up` writes lo
  ABSOLUTELY while prune ADDS); fix `mount_message`'s `index < window_start`
  direction and `index > window_hi`; `message/actions.py:138` answered from the
  DATA plus an audit of 87/89/123/125/127 through the accessors/materialize;
  `on_remove_message` — a removal BELOW the window must not move focus, and no
  mounted neighbour → focus the ChatView (pin WHY in the comment); `prune()` +
  `is_edit` per the answer; verify a materialized widget inherits `is_edit`/
  show-cots (`Message.maybe_mount_content` already reads `chat_view.is_edit` at
  mount) and only THEN write code in `chat_view_actions.py`; (3) NEW
  `tests/unit/chat_window/test_window_edits.py` starting at **t21**, reusing
  `window_harness` — build the state then assert it, mechanisms/ratios not
  constants, invariants sampled only at `rest()`, spend the arrival sample, and a
  control for every zero (TRAPS #13: the same `_insert(3)` on a window that covers
  index 3, the same prune with the mode off, `mount_message` adjacent vs far);
  (4) verify; (5) docs.
- **State hazards**: none. Clean tree; no fixtures; no red suites. The
  `/tmp/wp-e-*` probe files are this WP's own and are re-runnable.
- **Verify**: `bash spit_app/tests/run_tests.sh` TWICE from the repo root AND each
  `chat_window` file individually (the runner's `tail -n 1` hides dead files —
  TESTING.md). Every row unmoved except `unit:chat_window` (270 → 270 + new);
  `chat_smoke` golden md5 `8ae9d1186a59627d30d05dee95f0ad95` unchanged. If a check
  is red, probe the state and fix the setup/instrument or the code — never the
  claim; no constant widened without a re-measured justification beside it.
  Docs on close: TESTING.md `unit:chat_window` row + the new file described,
  AGENTS.md/PROJECT.md rows → "A, B, C, D, E done; F awaits Go",
  UI-ONDEMAND-LOADING WP-E header line + deviations, this entry moved to
  `TASKS-FINISHED.md` with the header back to ONE entry open. The close-out rests
  on the automated headless suites (TRAPS #22). NO DECISIONS entry (A–D filed
  none); WP-F (the 100/1k/5k table, closing P8) stays WP-F's.

## P0b-followup 4 - what the `terminal` tool still needs *for* the ratatui migration  [enhancement list, picked up piece by piece]

The list below was written during P0b and is **verbatim from it**; four items
have moved since — 8, 9, 10 and 12 — and each is marked **where it is marked
done, never where it is still open**. Nothing else has been done, re-checked
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

Once `spit-tui` exists (the Rust front end planned in
`doc/UI-ROUTE-RATATUI.md` and the engine <-> front-end protocol in
`doc/UI-PROTOCOL.md` — both merged into this branch at `51faf79`, so they are
**here**, read them here), this tool stops being a convenience and becomes **the only harness that can see the
real binary running in a real pty** — ratatui's `TestBackend` covers widgets,
the `terminal` tool covers the end-to-end app. Design it for that job now:

1. **`command`, not hardcoded `bash`.** Launch arbitrary argv in the pane
   (`command=["./spit-tui"]`, plus `env={}`, `cwd=`) — "start the UI under test"
   is the primitive; interactive bash is a special case of it.
2. **Geometry you control.** `cols`/`rows` at creation and a `resize` action.
   Re-wrap-on-resize is load-bearing in the new architecture (measured: 746 ms
   to re-wrap 2,000 messages), and it cannot be tested at 24x80 only. During
   this evaluation I had to nest a private tmux server to get 120x40 and
   150x35.
3. **Capture modes: text | styled | bytes.** Today only plain text. `styled`
   (`capture-pane -e`) is how markdown/heading/highlight/border styling gets
   asserted. `bytes` (raw pane output) is how the **Kitty/Sixel graphics path
   gets asserted** — LaTeX and image rendering could not be verified at all in
   this environment because there is no way to see the escape sequences, and
   that is the single biggest unproven risk in the migration.
4. **Cursor as data, not decoration.** Report `cursor_x`/`cursor_y` as fields
   instead of splicing a `█` into the text (which corrupts the line and breaks
   under double-width characters); keep the marker as an option.
5. **`wait_for` instead of `delay`.** Wait until a regex matches the pane or the
   screen is stable for N ms, with a timeout — blind sleeps make streaming tests
   flaky, and streaming (token deltas, follow-bottom, abort) is the main thing
   the new UI must get right.
6. **`send_bytes` / raw mode**, so a test can inject SGR mouse sequences and
   bracketed paste. That is exactly how pyratatui's mouse and paste defects were
   proven (4 injected sequences → 0 delivered; a pasted Enter arriving as
   `Ctrl+J` wipes the line), and the new front end's input layer must be tested
   against the same sequences.
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
  `cwd=`), which is self-contained and unblocks any harness work on `spit-tui`.
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
