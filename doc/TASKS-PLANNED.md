# TASKS-PLANNED.md

Tasks known to be wanted but not started. Light skeleton per task; the
referenced guides carry the detail. On starting a task: move its entry to
`TASKS-IN-PROGRESS.md`, create a branch first (never touch `main`, never
push), and keep the State field honest so an abandoned task is recoverable.

> **No entry below waits on a `Go!`.** The owner's ruling of 2026-09-28 dropped
> the per-task gate — *"You may work now independently without asking the user
> for any permission. One thing remains the same: only the user may merge your
> work into main"* (DECISIONS 83, and `AGENTS.md`/`PROJECT.md`). Where an entry
> below still says "its own `Go!`", read **its own task, on its own branch**:
> picking it up needs no permission, and merging it needs the owner's.

---

## P0 - DONE - garbled streaming render: tool-call arguments and streamed tool output

## P19 - DONE - Failure recovery: an endpoint failure must not need a human  [closed 2026-09-30; on `main`]

Implemented as the four packages the entry planned and **closed 2026-09-30** on
`task-endpoint-retry-p19wp2`: WP-1 the `create_and_submit` helper extracted from
`handoff`, WP-2 the typed endpoint failures + the retry loop + the slot leak,
WP-3 the `journal` tool, WP-4 the recovery chat through `chat/recovery.py`.
**Resolution: `TASKS-FINISHED.md`** (the P19 entry) and **DECISIONS 84/85/86**;
new ground-truth rows `unit:journal` 69 and `unit:recovery` 55, `unit:endpoints`
512, `unit:prompt` 38. The owner has merged that line into `main` — WP-1…WP-4 are
reachable from `main`'s history (`git log --oneline -- spit_app/chat/recovery.py`),
and `doc/TASKS-IN-PROGRESS.md` carries no open entry.
---

## P20 - The canned servers' `do_GET` prints a `BrokenPipeError` traceback on a green suite

**Not started.** Found 2026-09-30 while re-running the full suite to close
`fix-token-harvest-call-site`, where it briefly read as a regression of that
branch; it is not one (measured below). A one-line fix, already half-written by
its neighbours.

- **The symptom**: `bash spit_app/tests/run_tests.sh` exits **0** with every row
  at its `doc/TESTING.md` number, but stderr carries a
  `BrokenPipeError: [Errno 32] Broken pipe` traceback from
  `spit_app/tests/unit/handoff/handoff_harness.py`'s `do_GET` 404 branch
  (`self._send(404, …)` → `self.wfile.write(raw)`), printed by stdlib
  `socketserver`, which catches it and carries on. It comes from `unit:recovery`
  and `unit:handoff`, which import that harness.
- **The measurement**: 20 consecutive `unit:recovery` runs on
  `fix-token-harvest-call-site` → **1 run with stderr**, 19 clean; the same 20
  runs in a clean worktree of `main` (`git worktree add`) → **1 run with
  stderr**, 19 clean. Same rate on both sides, same frame, and the branch does
  not touch `handoff_harness.py`: pre-existing, environmental (the client hangs
  up before the 404 body lands), NOT a regression of anything. The same flake is
  already recorded twice in `TASKS-FINISHED.md` — in the P14 entry (2 of 14 runs,
  2026-09-27) and in the 2026-09-30 harvest close-out — where it was explained
  and deliberately left unfixed **because a code change then needed a `Go!`**.
  That gate is gone (DECISIONS 83), so there is no reason left not to fix it.
- **The fix**: wrap the `do_GET` `_send` in the
  `except (BrokenPipeError, ConnectionResetError): pass` that `do_POST` in the
  SAME file already has, with the same comment (the recording of the request
  already happened, which is all the assertions read). Check the two other
  canned servers while there — `unit/endpoints/endpoint_harness.py` and
  `unit/handoff/handoff_harness.py` are the same shape, and
  `endpoint_harness`'s `_send` has the guard on **neither** verb.
- **Verify**: no check count moves — this only silences a traceback the suite
  never asserted on, so every row stays at its `doc/TESTING.md` number, and the
  full suite must stay `SUITE-EXIT:0` with **stderr empty over ~20 runs** of
  `unit:recovery` and `unit:handoff`, which is the before/after measurement
  (1-in-20 today). Take the before figure from a clean worktree of `main`, not
  from the branch — TRAPS #14's lesson is that the two trees must be built from
  different objects for the comparison to mean anything.

---

## P21 - `doc/TOOLS.md` still documents the tool as `insert_line`; its `NAME` is `insert_lines`

**Not started.** Found 2026-09-30 while making `doc/TESTING.md`'s ground-truth
table mechanically comparable with a run (that fix is already in: the row is
`insert_lines` and `tools total` is 536 again).

- **The fact**: `51bcda0` ("tools: rename insert_line -> insert_lines") renamed
  `spit_app/tools/insert_line.py` → `insert_lines.py`, and a tool's `NAME` is
  `__file__.split("/")[-1][:-3]` — so the tool the app loads, the settings key
  `load_user_settings(app, NAME, SETTINGS)` writes under, and the `DESC` function
  name are all **`insert_lines`** now. `doc/TOOLS.md` still says `insert_line` in
  nine places: the inventory table (line 21), the attribute matrix (111), the
  shared-helpers and read_files prose (83, 206, 577), its **spec section 12**
  heading and its two call examples (669, 696-697), and the rename tool's
  dry-run contrast (809).
- **Why it is not a pure find-and-replace**: the rename moved a *settings key*.
  `git show 51bcda0 --stat` is seven files, file-to-file, and **no migration of
  any kind** — so settings a user had saved under `insert_line` (`prompt`,
  `sandbox`, the tool's own fields) are orphaned under the name the app no longer
  asks about, and nothing says so. Whether that is a bug to fix or an accepted
  cost of renaming a tool is the owner's call, not a doc edit's; what this entry
  owns is that `TOOLS.md` must stop naming a tool that does not exist. Measured
  today: `grep -rn "insert_line\b" --include=*.py spit_app/` (excluding
  `insert_lines`) returns **nothing** — no code keys on the old string any more,
  so the drift is purely in the docs.
- **Scope**: `doc/TOOLS.md` only. `doc/DECISIONS.md` names the tool
  `insert_line` in 30/31/32/44/45/46/52 too, and it is **append-only** — those
  entries record what was decided under the name of the day and are not rewritten.
- **Verify**: `bash spit_app/tests/run_tests.sh` unchanged (`unit:prompt` walks
  `spit_app/tools/` and counts one `## ` heading per tool, so it answers for the
  live name already and must not move); no code change is expected at all.

---

## P8 - DONE - On-demand message loading with a top-anchored scroll container

**Implemented and measured 2026-09-14 → 2026-09-20** as the six-package pipeline
`doc/UI-ONDEMAND-LOADING.md` (WP-A…WP-F): `AnchoredScroll`, the index-accessor
seam, the sliding window `messages[lo, hi)`, the scroll triggers and the settle
prune, the edits/undo/removal sites across the edges, and the measurement pass that
closes it. Branch chain `task-anchored-scroll-widget` →
`task-index-accessor-refactor` → `task-sliding-window-core` →
`task-scroll-load-prune-triggers` → `task-edit-undo-removal-across-window-edges` →
`task-window-measurement-numbers-close-p8`, all awaiting the owner's merge, `main`
untouched. **Resolution: `TASKS-FINISHED.md`** (the WP entries, and WP-F's numbers:
7–15 mounted at every scroll depth at 1k and at 5k, 121–127× faster to open a
5,000-message chat, 81–82× faster to page down, 11.5× less memory) **and DECISIONS
76**. The question and the proven mechanism stay below verbatim: they are the reason
the pipeline was started, and the mechanism paragraph is still the only place the
`process_layout` seam is written down.

**Question** (investigation, no repo code touched): `VerticalScroll` keeps its
`scroll_y` when widgets are mounted above the viewport, so the visible content
shifts down and the view appears to scroll up — which kills the "load older
messages on demand" route. Can an alternative scroll container hold its
*visual* position across top-mounts?

**Answer: yes, with a small `VerticalScroll` subclass; no Textual patch is
needed** (this amends the parenthetical in DECISIONS 65 that partial loading
"required a patch to Textual itself" — the public hook was already there in
8.2.8). Measured headless with the app's own Textual 8.2.8, probes in
`/tmp/anchor-probe/probe.py` + `probe6.py` (rebuildable from the design below).
**Full transition plan and work-package split (A–F): `doc/UI-ONDEMAND-LOADING.md`.**

### The mechanism (textual 8.2.8, file:line from `~/.venv-spit`)

- Layout runs *inside compositing*: `Compositor._arrange_root` calls
  `widget.arrange()` (`_compositor.py:602`), which calls the public hook
  `widget.process_layout(placements)` (`_arrange.py:96`) **before** the
  compositor translates placements by `-widget.scroll_offset`
  (`_compositor.py:631`). A `scroll_y` change made inside `process_layout`
  therefore lands in the *same drawn frame* — zero intermediate jump frames.
- This is not a private trick: Textual's own bottom anchor (streaming
  follow-bottom, already used by `ChatView.__init__` via `self.anchor()`)
  rewrites `scroll_y` at exactly that point — `_compositor.py:609-619` —
  with `set_reactive(Widget.scroll_y, v)` + `scroll_target_y` +
  `vertical_scrollbar._reactive_position`. The subclass mirrors that code,
  but pins an arbitrary child at its current visual offset instead of the
  bottom edge.
- `set_reactive` (not `scroll_to`/`scroll_relative`) is deliberate: every
  user-scroll path funnels through `Widget._scroll_to`, which calls
  `release_anchor()` (`widget.py:2750`); the correction must not release the
  built-in bottom anchor, and it doesn't.
- Scroll-only reflow (`reflow_visible`, the wheel fast path) reuses the cached
  arrangement (`Widget.arrange` cache, `widget.py:1347`), so `process_layout`
  does NOT run on pure scrolling — the pin never fights the user. Layout
  changes (mount, child resize) invalidate ancestors via
  `_clear_arrangement_cache()` (`widget.py:4574`), which is what re-runs
  `process_layout`.

### The design (the whole widget)

```python
class AnchoredScroll(VerticalScroll):
    # one-shot mode: arm, then the next layout (e.g. after mounting older
    # messages) restores the visual position in the same frame.
    def arm_top_anchor(self):
        anchor = next((c for c in self.children
                       if c.region.bottom > self.region.y), None)
        if anchor is None:
            return
        self._anchor_widget = anchor
        self._anchor_content_y = round(self.scroll_y + anchor.region.y - self.region.y)
        self._anchor_active = True

    def process_layout(self, placements):
        if self._anchor_active:
            for p in placements:
                if p.widget is self._anchor_widget:
                    delta = p.region.y - self._anchor_content_y
                    if delta:
                        self.set_reactive(Widget.scroll_y, self.scroll_y + delta)
                        self.set_reactive(Widget.scroll_target_y, self.scroll_y + delta)
                        if self.show_vertical_scrollbar:
                            self.vertical_scrollbar._reactive_position = self.scroll_y + delta
                    self._anchor_active = False
                    break
        return placements
```

A persistent variant (pin re-baselined at the end of each frame via
`watch_scroll_y` → `call_after_refresh`) also survives content that grows
*later* above the viewport (images/LaTeX landing after the mount); it is in
`probe6.py`. If the anchor widget is removed while armed: disarm (skip the
correction) rather than compensate against a phantom.

### Measurements (headless, `App.run_test`, 20 messages × 3 rows in a 10-row
viewport, scrolled to y=15, mount a 4-row message at index 0; a spy on
`App._display` records every emitted frame)

| probe | result |
|---|---|
| plain `VerticalScroll` | defect: `scroll_y` stays 15, anchor child pushed 4 rows down; **every painted frame shows the jump** — it persists until the user scrolls |
| `AnchoredScroll`, mount 1 above | `scroll_y` 15→19, anchor stays at viewport top, **0 jump frames** |
| `AnchoredScroll`, `batch()` mount 3 above | same, 15→27, 0 jump frames |
| with the built-in bottom anchor also armed (the `ChatView.__init__` state) | correction lands; user scroll released the bottom anchor as usual |
| after a correction: `scroll_relative`, then append at bottom with `anchor()` | manual scroll exact; follow-bottom still sticks |
| persistent pin: user scroll / mount above / late growth above / unpin | 21 respected / 21→25 no shift / 25→29 no shift / defect returns — 2 corrections total, 0 jump frames |

### Scope and hazards for the implementation task (separate branch, needs `Go!`)

- `ChatView` becomes the subclass; `load()` arms before the batched mount.
  Keep follow-bottom (`anchor()`) as is — the compositor applies it *after*
  `process_layout`, so at the very bottom the bottom anchor wins (top-loads
  only happen away from the bottom, so in practice they never contend).
- On-demand loading itself (when to fetch, where the window starts, chat
  switch, undo/edit interactions) is the real work; the container is the
  solved half. This is a Textual-side mitigation — it does NOT re-open
  DECISIONS 65 (the whole-tree cost of *mounted* messages stays; the win is
  mounting fewer of them).
- A viewport **resize** reflows every message; decide there whether the pin
  compensates (it will, if armed) — semantics, not a bug.
- **Verify**: probes rebuilt as a checkable suite + full `bash
  spit_app/tests/run_tests.sh` green (counts from `doc/TESTING.md` unmoved).

---

## P9 - Burst page-in: `_page_count()` sizes a page from regions that are not laid out yet  [found by WP-F 2026-09-20; needs its own `Go!`]

- **The gap** (measured, not theorised): N wheel events delivered **between two
  frames** queue N `_load_at_edge` callbacks through `call_after_refresh`, and each
  sizes its own page from `_page_count()` — the prune margin divided by the MEAN
  mounted height — while the regions of a just-mounted batch have not been laid out,
  so the mean reads ~0.7 rows and `int(margin / mean) + 1` saturates at
  `INITIAL_WINDOW` (50). Measured at 1k: **10 events fired inside one frame carried
  the window to (603, 942) with 339 mounted children**, against the 10–13 every
  settled sample of the same fixture reads. The next settle's prune releases it and
  `window_consistent()` held in every sample, so this is a transient cost, not a
  broken window. Found while choosing the transport for the WP-F walk
  (`/tmp/wp-f-probe-{burst,balloon,wholo,queued}.py`), which is why every number in
  DECISIONS 76 is taken with **one notch per pause** — that shape queues exactly one
  page operation per frame, verified at batch sizes 1/2/5/10/40: zero callbacks still
  queued when `at_rest()` first reads True.
- **Also open, same root**: `at_rest()` (`not _window_page_op and _settle_timer is
  None`) is not a quiescence oracle across a queued burst — the flag is False in the
  gaps between the queued callbacks, so `rest()` can sample twice inside two gaps.
  Any fix should make the predicate ask about queued page operations, not only about
  the one in flight.
- **The question to answer before writing code**: can a real front end deliver more
  than one wheel event per frame? Unmeasured here — this environment has no real
  terminal to drive (TRAPS #22). If a hand's flick can, the fix is to size a page
  from LAID-OUT regions only (fall back to a constant when the mean is implausible,
  e.g. below one row per message) and/or coalesce the queued `_load_at_edge`
  callbacks per frame; if it cannot, this becomes a documented limit and the transport
  note above is the reason the shipped numbers are trustworthy.
- **Verify**: new checks in `tests/unit/chat_window/` (append-only numbers, TRAPS #15)
  driven by a burst transport, asserting a bound on the settled mounted count and
  that `at_rest()` does not read True while page operations are still queued; then
  re-run the WP-F walk and confirm the 7–15 band is unchanged, and re-measure the
  DECISIONS 76 table if anything about the page size moves.
- **Gotchas**: TRAPS #24 (mount `spit_app/styles.css` or every viewport computation
  is vacuous), TRAPS #13 (every zero needs a control that can fail — here it is the
  same burst with the page count pinned to a constant), and WP-E's instrument lesson
  (a row that exercises a trigger must `thaw_triggers` and assert the triggers live
  first, or the harness answers for the thing under test).

---

## P10 - `run_script`'s python gets the shared sandbox tmp as `sys.path[0]`  [found alongside DECISIONS 78; needs its own `Go!`]

- **The exposure** (measured, this box). DECISIONS 78 closed the stdin door for the
  13 script tools. `run_script` and `run_command` deliver the script **as a file**,
  and file mode puts the *script's own directory* first on `sys.path` — for
  `run_script`'s python that is `sandbox_tmp`, which bwrap binds to `/tmp`. So a `.py`
  file named after a stdlib module anywhere in that directory is imported instead of
  the stdlib: with a `types.py` planted there, `python3 /tmp/<script>` dies exactly
  like the file-tool bug did, and `python3 -P /tmp/<script>` does not. Measured on
  this chat's sandbox tmp: **117 leftover `.py` files** from earlier sessions (the
  debug note that started this investigation is itself about that litter), and
  collisions with stdlib module names **today: none** — a loaded gun, not a misfire.
  One `types.py`/`enum.py`/`copy.py` written there by any session breaks every later
  `run_script python3` call in the chat, and whoever inherits it is told nothing.
- **Why it was left open rather than fixed with 78**: the fix changes what a user
  script can import, which is a semantics decision, not a bug fix. `-P` on
  `run_script`'s python closes the door and, with it, the accidental "import the
  helper I left in `/tmp` last call" route that works today. A **private per-call
  delivery directory** (`mkdtemp()` under `sandbox_tmp`) closes it identically without
  touching the flags — measured: the real `search_replace` script ran clean from a
  poisoned cwd with `sys.path[0]` = its own fresh directory — and ends the same
  cross-call route. Both answers are the same trade.
- **Decide first**: is "modules importable from the shared sandbox tmp" a feature or
  an accident? Feature → document the limit and the collision rule, change nothing.
  Accident → take the private directory (it also stops the tmp accumulating other
  sessions' files into every later `sys.path[0]`).
- **Verify**: append-only numbers in `tests/unit/run_script/` (TRAPS #15) — plant a
  stdlib-named module in the delivery directory and assert it is **not** imported,
  with the control asserting it **is** under the plain interpreter (TRAPS #13), then
  the real payloads still run and every other row byte-for-byte (TRAPS #18).

---

## P11 - A sandboxed `terminal` pane starts clean, an unsandboxed one inherits: pick one  [found alongside DECISIONS 78; needs its own `Go!`]

- **The asymmetry** (measured). `term_new()` builds `bwrap_args() + ["bash"]` in
  sandbox mode — **no `sandbox_env.sh`** — while the `sandbox=False` branch builds
  `[self.SANDBOX_ENV] + ["bash"]`, which sources `~/.sandbox_env` and cds to
  `~/.sandbox_cwd`. So in the default configuration a new pane starts in
  `/home/<user>` with no carried exports: measured, a pane created right after
  `export SPIT_TEST=carried; cd /tmp/wp-cwd-test` answers `cwd=/home/kurt`,
  `SPIT_TEST=[unset]`, while a `run_command` in the same chat answers both. Nothing
  in the docs or in either tool's PROMPT says which of the two is intended.
- **Why it matters**: the `cd`-carry-over promise lives in `run_command`'s PROMPT, and
  a model has no way to know the pane is a different shell than the one it just
  `cd`-ed. `run_command` and `run_script` both go through `sandbox_env.sh` in both
  modes; `terminal` is the only tool whose launcher depends on the sandbox setting.
- **The two honest answers**: route the pane's shell through `sandbox_env.sh` in both
  modes (a pane then starts where the chat's shell last was, and a long-lived pane
  inherits whatever directory that was — harmless for bash, and a poisoned cwd there
  is no longer a file-tool problem thanks to DECISIONS 78, but it is a decision); or
  keep the clean start and **say so** in the `terminal` PROMPT and in
  `RUNTIME-RUN-COMMAND.md`, which currently describes the pane as running bash
  "bwrap-sandboxed by default" without mentioning the state. A third answer — the
  present one — is a behaviour that depends on a setting whose stated purpose is
  something else.
- **Verify**: append-only checks in `tests/unit/terminal/` (needs the test venv,
  TRAPS #19) asserting the chosen answer for both settings, with the pane's own
  `pwd`/`echo $VAR` as the read — and no assertion of a pane's timing (decision 73:
  synchronise to the pane's state, never to the test's clock).

---

## P12 - DONE - Token counts: how many are used, and how many exist  [owner-approved 2026-09-22; closed 2026-09-24]

Implemented 2026-09-22 → 2026-09-24 as the six-step chain the entry sketched,
on `task-token-counts-p12` (`b799526`…`a643666` + the close-out, cut from
`docs-plan-token-usage-context-size`, which carries the planning at `c7e7d74`),
awaiting the owner's merge; `main` untouched throughout. **Resolution:
`TASKS-FINISHED.md`** (the steps, the deviations collected in one place, the
accepted limits, and the ONE question left open for the owner — the counts
row's 80-column rendering, with its measurements so it can be decided without
re-measuring) **and DECISIONS 80**. New ground-truth row: `unit:endpoints` 343,
the fifth dependency-listed suite.

---

## P13 - DONE - System notes the model is told: the generator, its hooks, and the token-status hook  [owner-requested 2026-09-25; closed 2026-09-25 by WP-E, the last of the five packages]

Implemented 2026-09-25 as the five-package chain the owner chained by handoff
message, all of it on **`p13-wp-a-note-unpacking`** (cut from
`docs-p13-owner-rulings-handoff-wp-a` at `1522932`), awaiting the owner's merge;
`main` untouched throughout, nothing pushed.

- **WP-A** the unpacking — `0afaef8`: `prepare_payload()` pops the private key
  `system` from the deepcopy and puts each note right after its carrier, `user`
  always, merged into the carrier's content when the carrier is `user`.
  `unit:endpoints` 343 → 394 (`test_system_note.py`, t12, 51).
- **WP-B** the generator and the hook contract — `a6ec179` + the row `7046bcb`:
  `chat/system_note.py`, `attach()`, module `HOOKS`, `Note(level, text)`, the
  five invariants. New row `unit:system_note` 96 (t1–t9, bare interpreter).
- **WP-C** the token-status hook — `6f1a0ed` + the row `ad56e2d`:
  `chat/token_status.py`, the percentage-OR-remaining levels, the rank machine,
  the four texts byte-for-byte, no instance state. `unit:system_note` 96 → 219
  (t10–t18, 123).
- **WP-D** the wiring and the proof — `bcdc441` + the row `dadc11b`: `Chat`
  builds the generator and the hook reference, `Chat.context_window()`, the ONE
  `HOOKS` registration at `chat.py` import (one shared stateless instance),
  `attach()` immediately before `await self.endpoint.stream()`.
  `unit:endpoints` 394 → **442** (`test_note_chain.py`, t13, 48).
- **WP-E** the docs — this record: **DECISIONS 81** (cross-linked from 80, both
  ways), `PROJECT.md`'s note chain, `TESTING.md`'s post-wiring sentence, and the
  four follow-ups below filed.

**Resolution: `TASKS-FINISHED.md`** (the five WP entries carry the argues —
WP-A's merge rule, WP-B's contract, WP-C's memory-is-the-notes, WP-D's
registration decision — and this entry's close-out carries the chain) **and
DECISIONS 81**, which is where the WHY now lives: the note-in-the-message-dict
contract and why not an index, once-at-the-tail and the prefix-cache argument,
silence when the window is unknown (the dash, 80 b), the owner's role ruling
with the strict-template evidence and the `user`→`user` merge, the
percentage-OR-remaining levels and the rank machine with the worked
32k/64k/128k/200k table, and the residual abort-then-type limit. The plan's
hazards and drafts are superseded by that entry and by the shipped code; the
four texts are model-facing text, i.e. code, pinned in t16 and re-pinned when
the owner revisits them.

**Follow-ups, filed by WP-E as entries of their own** (none of them P13's
unfinished work; each needs its own `Go!`): **P16** the `note_mode` endpoint
setting (`separate`/`merge`/`off`), **P17** rendering the notes in the UI,
**P18** the level numbers as settings, and **P14** the handoff tool, whose
arrival replaces the fenced-block clause of the `critical` text (ruling iv: a
text change and its re-pin, not a mechanism change).

---

## P16 - `note_mode` endpoint setting: `separate` / `merge` / `off`  [filed by P13/WP-E 2026-09-25; needs its own `Go!`]

- **Why it exists**: the role is decided (`user`, DECISIONS 81 c) and the merge
  rule keeps every shape the app itself writes legal, but one shape is outside
  the rule's reach — a note that shipped as its own `user` item stays in the
  history, and the HUMAN turn typed after it is `note(user) → user`, the
  abort-then-type pair (DECISIONS 81 f). A strict alternation template could
  refuse that. The owner has produced the shape for months without a refusal, so
  nothing is broken today; this is the **escape hatch** for the day one bites,
  and the **kill switch** for an endpoint that objects to notes at all.
- **The three modes** (in `endpoints/llamacpp.py`, where `append_note()` already
  is): `separate` = today's rule (merge on a `user` carrier, its own `user` item
  otherwise); `merge` = always merge into the carrier's content, so no note is
  ever an item and no `user` pair is ever possible (the cost: a note on a
  `tool`/`assistant` carrier is no longer a separate turn the model reads as
  addressed to it — and there is nowhere to merge a note whose carrier is an
  assistant with no content and `tool_calls`; decide that case explicitly);
  `off` = `prepare_payload()` drops the private key and ships nothing — the
  generator still runs and the notes still persist, which is what makes `off`
  debuggable rather than mute.
- **Decide first**: a setting per endpoint (like `context_size`, `timeout`:
  honour it in `append_note()`; remember the skip list in `construct_payload` —
  DECISIONS 80 d says a field that is not an inference parameter must be listed
  or it leaks to the server), and what a chat does when its endpoint has no
  opinion (default = today's `separate`, so nothing changes for an endpoint
  saved before the field existed, the same `.get()` posture as `context_size`).
- **Verify**: `unit:endpoints` t12/t13 keep their numbers (TRAPS #15: new
  checks get new numbers, and t13's merge/pair checks must stay green on the
  default); new checks per mode in the same files, each with the control that
  the other modes differ; then the full suite with every other row unmoved.
- **Gotchas**: TRAPS #13 (the `off` case needs the control that notes are still
  being WRITTEN — assert the private key in `chat.messages` while the wire has
  none, or "no note on the wire" cannot fail), #14 (the no-note payload
  differential against the pinned baseline `b799526` is the proof the wire
  format did not move for anybody who does not set the field), 80 d (skip list).

---

## P17 - Render the system notes in the UI  [filed by P13/WP-E 2026-09-25; needs its own `Go!`]

- **Today a note is invisible**, and that is load-bearing for P13's constraint,
  not an oversight: `Message` renders `reasoning`/`content`/`tool_calls` only, so
  nothing in the UI sees the private key, no index moves, no edit shows a note
  the user did not type. The cost is that the user cannot see what the model was
  told, and the notes are in the chat's JSON on disk.
- **Decide first** (it is a display question with a data edge in it): where the
  note renders (its own block after the carrier, styled as the system that it is,
  not as the model's own words — a note shown as content reads as something the
  model said), whether the private key stays the storage or the render asks for
  a separate shape (it must stay: the key is the whole contract, DECISIONS 81 a),
  and what the copy/export path does with notes.
- **Scope**: `spit_app/chat/message/` (the content list `Message.contents`), the
  render pipeline it feeds, and `unit:render` / `unit:chat_smoke` — **careful**:
  `chat_smoke`'s `golden.txt` is a differential against `f201700`, so a render
  change there is a deliberate re-pin with its reason written, never a silent
  refresh.
- **Verify**: `unit:render` and `unit:chat_smoke` moves only by new checks;
  `unit:system_note` and `unit:endpoints` (which own the note's data and wire
  behaviour) must not move at all — a change that reaches them is changing the
  contract, not the display.
- **Gotchas**: TRAPS #13, #15, and DECISIONS 71 (c) — this is a code change and
  a taste call, so the `Go!` and the look belong to the owner.

---

## P18 - The level numbers as settings  [filed by P13/WP-E 2026-09-25; needs its own `Go!`]

- **The four numbers are module constants** in `spit_app/chat/token_status.py`:
  `SMALL_WINDOW_TOTAL = 32768`, `INFO_PERCENT = 0.5`, `WARNING_REMAINING =
  20000`, `CRITICAL_REMAINING = 10000` (plus `WARNING_PERCENT 0.8` /
  `CRITICAL_PERCENT 0.9`). The owner's are `32768 / 0.5 / 10000`; the
  `20000 = 2 × 10000` relation is the implementer's, stated in DECISIONS 81 e so
  it can be argued with. Tuning today is a one-line code change plus the re-pin
  of the texts that quote them.
- **Decide first**: the scope of the setting (per endpoint like `context_size`,
  or app-wide — a window is an endpoint fact, a *policy* about how loudly to
  warn is arguably not); whether `small_window` is a threshold the user may not
  want at all (off = a sentinel, never a magic 0); and what happens to the
  announce record when the numbers change mid-chat (nothing special: the record
  is the standing notes and the levels are re-derived from them, so a widened
  floor just speaks later — say it, because "I lowered the threshold and it did
  not re-warn" is the report this invites).
- **The trap that makes this not-free**: the four texts quote the figures in
  words (`critical` says nothing numeric except the substituted figures, but the
  module constants and the pinned texts are one mechanism), and `t12`–`t15` pin
  the **exact tokens** at 32k/64k/128k/200k. Settings mean the suite must test
  the machine's DEFAULTS, not whatever the developer's settings file says — so
  the tests set the values explicitly rather than reading them, and the default
  row is pinned as it is now.
- **Verify**: `unit:system_note` moves by new checks only; every other row
  unmoved; the announce-order pin (`t14-order-32k`) stays green with the default
  numbers and is re-run with a deliberately silly setting (e.g. a 64k
  `small_window`) to prove the settings are actually read.
- **Gotchas**: TRAPS #15 (append-only numbers), #13 (a settings test that never
  proves the setting was READ is the classic vacuous green), DECISIONS 80 d if
  the field lands on an endpoint (`construct_payload` skip list).

---

## P14 - DONE - New tool: `handoff` — an agent hands the work to the next agent  [owner-described 2026-09-25; `Go!` given 2026-09-26; closed 2026-09-27]

Implemented 2026-09-26 → 2026-09-27 on **`task-handoff-tool-p14`** (cut from
`main` `98631e6`, P13 merged): `ff0a4b8` the entry opened, `961eac1`
`spit_app/tools/handoff.py` and its new `spit_app/tests/unit/handoff/`
(**60 checks**, the sixth dependency-listed suite), `6a994f7` the `critical`
note re-worded to call the tool with the `t16` re-pin in the same commit,
`8a8f904` the decision record and the tool spec, then the close-out; awaiting
the owner's merge, `main` untouched throughout, nothing pushed. **Resolution:
`TASKS-FINISHED.md`** (the mechanic, the two corrections of the brief —
`chat._work` not `chat.work`, and `desc` becoming `"Handoff: <desc>"` rather
than inherited verbatim — the three consequences the design owns: sibling tool
calls in the same reply are skipped, the old chat's widget survives, and a chat
without the tool selected cannot hand off) **and DECISIONS 82**; the spec is
`TOOLS.md` #15. Ruling iv arrived here: *what P13 already does for it* below is
superseded in one respect only — the `critical` note now names the tool and the
fenced block survives as the fallback for a chat that has not `handoff`
selected, the load-bearing stop-clause byte-identical, the mechanism
untouched. The original entry stays below as it was written: it is the owner's
brief verbatim and the three-way decision it posed, and the answer — (b), the
NEXT chat, created here — is why DECISIONS 82 exists.

The owner's stated intent, verbatim from the P13 briefing: *"later we will introduce a
tool call that lets you handoff information to the next agent so they may continue
with the work. This will give you more autonomy and helps in automating what I've been
doing by hand since now — telling the model that tokens run out and that they should
handoff the work to the next agent, asking them to write a handoff message which I put
into the next agent's chat. We want to automate this and avoid having the agent die mid
work."*

- **What P13 already does for it** (shipped, P13 closed 2026-09-25): the
  `critical` note is the trigger that exists today — `TEXT_CRITICAL` in
  `spit_app/chat/token_status.py`, pinned byte-for-byte by `unit:system_note`
  t16 — and it tells the model to write the summary as a **fenced block**. P14
  gives that summary somewhere to GO instead of into the chat's last message, and
  when it lands the note's text is updated to call the tool (owner ruling iv,
  2026-09-25: "we can adopt the message when the tool call lands") — **a text
  change plus its pinned-check re-pin, not a mechanism change**: the generator,
  the rank machine, the private key and the unpacking all stay exactly as
  DECISIONS 81 records them. Re-pin `t16` in the same commit as the new text, and
  keep the load-bearing half — *do not call any more tools and do not start new
  work after the handoff* — inside whatever the new wording is.
- **Decide first** (the entry's real work): where does a handoff land? (a) the tool
  writes a handoff document under the app's data dir (next to the chats) and echoes it
  so it is also in the transcript; (b) it creates the NEXT chat with the handoff as its
  first message, so the human's part shrinks to opening it; (c) it writes a file the
  next agent is pointed at by the P13 note's text. The three differ in how much of the
  owner's manual loop they remove, and (b) touches the chat lifecycle — that is a
  decision, not a detail.
- **Scope** (per CONVENTIONS.md): `spit_app/tools/<name>.py` + its script under
  `spit_app/tools/scripts/` + `spit_app/tests/tools/<name>/` (exactly three files),
  `PATH_ARGS` if it takes paths, `OUTPUT_TYPE_HINT` if it is not Markdown, `dry_run` if
  it is destructive.
- **Verify**: full `bash spit_app/tests/run_tests.sh` green at the
  `doc/TESTING.md` numbers (its own new suite row; `unit:prompt` reads its pinned
  **33** — P15 closed and the owner merged it); new suite's checks in its summary
  line; `TASKS-FINISHED.md` updated, and so is the `critical` text's pin at
  `unit:system_note` t16 (see the ruling-iv bullet above).
- **Gotchas**: TRAPS #21 (PATH_ARGS), #10 (generated fixtures only), #19 (a tool module
  cannot be imported by the bare interpreter); the tool's PROMPT/PROMPT_INST are
  model-facing text = code, pinned by `tests/unit/prompt/`.

---

## P15 - DONE - `unit:prompt` was red at the tip: `TOOL_PROMPT` emitted with no tool behind it  [found and fixed 2026-09-25; `Go!` given and used the same day]

**Resolution: `TASKS-FINISHED.md`** ("P15 — the tool header with no tool under it"), on
branch `fix-tool-prompt-header-p15` (`a83c42e` the planning docs, `b969e00` the fix),
awaiting the owner's merge; `main` untouched. `unit:prompt` is back at its pinned
**33/0** and the full suite reads exactly the `doc/TESTING.md` table with stderr empty.
The record of what was measured stays below verbatim — it is the reason the fix guards
on `blocks` and not on the selection.


- **The measurement** (this box, tip `6bb1b62`): `unit:prompt: PASS: 32  FAIL: 1`,
  against the ground truth `doc/TESTING.md` pins at **33** — the red is
  `t6-mm_tool_without_the_capability_excluded`. It is not environmental: the same suite
  run from a clean tree of `6bb1b62^` reports **PASS: 33  FAIL: 0**.
- **The cause** — the tip commit `6bb1b62` ("chat: work: fix no tools selected"), in
  `spit_app/chat/work.py:prompt()`: `prompt = TOOL_PROMPT + "\n\n".join(blocks)` moved
  INSIDE `if self.cs("tools"):`, so the header is now emitted whenever a tool is
  *selected*, even when the capability filter drops every one of them. The rule the
  suite pins is the older one — `TOOL_PROMPT` opens the tool instructions and has no
  business appearing when there are none. The same shape bites the live app: a chat
  with only a multimodal tool selected on a text-only model sends the model "All of
  your function calls are rendered…" with `payload["tools"]` **absent** — the model is
  told to call functions that do not exist.
- **The fix** (measured: restores `PASS: 33  FAIL: 0`, in a scratch copy, with the
  owner's own crash-guard for `cs("tools")` being None/empty kept intact): hoist
  `blocks = []` above the `if self.cs("tools"):` and guard the header on the blocks —
  `if blocks: prompt = TOOL_PROMPT + "\n\n".join(blocks)`. One concern, one commit.
  The duplication the commit left behind (`__init__` computes `tools_descs` and
  `prompt()` re-filters the same predicate) is the reason this could drift at all;
  whether to unify the two is a second, larger decision and should stay out of the
  fix-commit.
- **Verify**: `cd ~/spit.py/spit_app/tests/unit/prompt && bash run_tests.sh` → 33/0,
  then the full suite with every row at the `doc/TESTING.md` numbers.
- **Gotchas**: the check is pinned, so no test is re-pinned for this — the code moves
  to the test, not the other way round (TRAPS #18: the row is the floor).

---

## P7 - RETIRED - leave Textual for a different front end  [number retired, 2026-09-20; a replacement route is a later, owner-level task]

The route this number carried is **gone by the owner's decision of 2026-09-20**:
the plan and the engine <-> front-end contract it pointed at are deleted, and
DECISIONS 77 records the retirement. Nothing here proposes what replaces them —
**the next route is the owner's to choose and a task of its own**; it is not
pick-up work, and no gate, spike or prerequisite is defined for it.

- **What still stands**: DECISIONS 65's *measurements* of the Textual tree (the
  entry is marked superseded, its numbers are not disputed) and DECISIONS 76's
  finding that the window bounds the mounted count without touching the
  per-message cost. The roadmap line in `README.md` ("GUI/TUI alternative to
  Textual") is where the intent now lives, as an owner-level item (see P6).
- **Do not**: resurrect the deleted plan from git history to use as a starting
  point, or open a replacement entry, before the owner names the route.

---

## P1 - DONE - patch: the `is_header_pair` adjacency edge  [closed 2026-10-01]

Fixed on `fix-patch-header-pair-adjacency-p1` (`a1f1032` the script, tests and
the tool's PROMPT sentence, then the docs commit). `patch` **80 -> 107**
(t40-t45; 14 of the new checks red against `main`'s script), full suite exit 0
with every other row at the `doc/TESTING.md` numbers, `chat_smoke`'s golden md5
`8ae9d1186a59627d30d05dee95f0ad95` unmoved. **Resolution: `TASKS-FINISHED.md`**
and **DECISIONS 87**, which is where the why now lives: what was measured before
writing anything (the consequence was a *silent no-op reported as success*, not
the loud failure this entry predicted), why the entry's own suggested fix was not
taken (it refuses t11, a patch that applies today), the rule that replaced it (the
file decides which readings are open; one open reading is the answer, two is a
refusal naming the `@@` remedy), and the 58-row differential. The verbatim record
below stays as it was written — it is the shape, and the words "Consequence is a
loud no-match failure" are what the next agent should measure, not trust.

### 4. CLOSED — the `is_header_pair` adjacency edge in `patch`

`is_header_pair()` decides a `--- old`/`+++ new` **pair** is a file header and skips
it. A *headerless* hunk that removes a line starting with `--` directly above an
added line starting with `++` produces exactly that shape as body content:

```
---x        (removing "--x")
+++y        (adding  "++y")
 keep
```

and the two lines are skipped as if they were a file header. Consequence is a loud
no-match failure, not corruption, and the shape is rare. Left unfixed on purpose so
it is a decision rather than an oversight; if it is ever fixed, the natural fix is to
require that a genuine file header be followed by a `@@` hunk header or end the
input, not merely be a pair.

---

## P2 - DONE - `rename` implemented  [medium priority]

Branch `rename-tool`, commit `7c1d062` (docs in the follow-up commit);
resolution in `TASKS-FINISHED.md`, spec in TOOLS.md #14, policy
rationale DECISIONS 60. The drafted spec below (verbatim) stays here.

## P3 - New tool: `copy`  [medium priority, not started]
## P4 - New tool: `code_parser`  [low priority, not started]

- **Scope**: new files `spit_app/tools/<name>.py` +
  `spit_app/tools/scripts/<name>.py` + `spit_app/tests/tools/<name>/`
  (exactly three files: `setup.json`, `run_tests.sh`, `create_fixtures.sh`).
- **Verify**: full suite `bash ~/spit.py/spit_app/tests/run_tests.sh` stays green;
  new suite's checks counted in its summary line.
- **Gotchas**: TRAPS #21 (PATH_ARGS), #2 (`git commit -F` is house style,
  author with write_file; the pollution trap it warned about is resolved),
  #10 (generated fixtures only); follow CONVENTIONS.md module
  contract end to end; both destructive file tools need `dry_run`.
- **Drafted specs (verbatim)**:

## Tools Planned (Not Yet Implemented)

### 1. `rename` (Medium Priority)
**Purpose**: Rename/move files

**Parameters**:
- `old_path` (required): Current file path
- `new_path` (required): New file path
- `dry_run` (optional): Preview without renaming. Default: `False`

**Output**: Success/error message

---

### 2. `copy` (Medium Priority)
**Purpose**: Copy files with options

**Parameters**:
- `source` (required): Source file path
- `destination` (required): Destination path
- `preserve_permissions` (optional): Keep permissions. Default: `False`
- `dry_run` (optional): Preview without copying. Default: `False`

**Output**: Success/error, bytes copied

---

### 3. `code_parser` (Low Priority)
**Purpose**: Parse code structure

**Parameters**:
- `path` (required): File path
- `language` (optional): Language (python, javascript, etc.)

**Output**: Functions, classes, imports, dependencies

---

---

## P5 - DONE - run_script: the `interpreters` setting restricts the prompt, not the call  [medium priority, security-adjacent]

Branch `fix-run-script-interpreter-allow-list`: `5494c9a` (the enforcement and
38 checks, suite 83 -> 121) and `52ca61c` (DECISIONS 64, TOOLS.md,
RUNTIME-RUN-COMMAND.md, TESTING.md). The call was made in favour of
enforcement -- the field is a permission, so the tool obeys it, and the refusal
quotes the list back. The question as written stays below (verbatim, with the
`enforces nothing` of the first bullet now historical), because the reasoning
that made it a decision is the thing worth keeping.

Found while fixing the wrapper (DECISIONS 63, branch
`fix-prompt-join-and-run-script`) and deliberately left out of that commit --
one concern each, and this one is a policy call, not a bug fix.

- **The gap** (as found; closed by `5494c9a`): `SETTINGS["interpreters"]` (default `bash, python3, perl`) is
  used for exactly one thing -- substituting the `[interpreters]` token in
  PROMPT_INST. The call itself checks only `shutil.which(interpreter)`, so any
  interpreter on `PATH` runs: the setting tells the model what it is *offered*
  and enforces nothing.
- **The call to make**: is the sandbox the boundary and the list a hint (then
  the setting's description should say so, since a user tightening it believes
  they have restricted the tool), or is membership enforced? If enforced: a set
  comparison against the user's own setting, an error naming it and listing
  what is allowed, and checks in `tests/unit/run_script/` -- which already
  stubs `shutil.which`, so the shapes are there.
- **Verify**: `cd ~/spit.py && bash spit_app/tests/run_tests.sh` (unit:run_script
  83 must not move unless checks are added; ground truth TESTING.md).

---

## P6 - Longer-term roadmap (from the repo README, no specs yet)

- More advanced agent capabilities
- GUI/TUI alternative to Textual
- Audio

These are owner-level roadmap items, not pick-up-and-code tasks; do not start
them without explicit instruction.
