# TASKS-PLANNED.md

Tasks known to be wanted but not started. Light skeleton per task; the
referenced guides carry the detail. On starting a task: move its entry to
`TASKS-IN-PROGRESS.md`, create a branch first (never touch `main`, never
push), and keep the State field honest so an abandoned task is recoverable.

---

## P0 - DONE - garbled streaming render: tool-call arguments and streamed tool output

Branch `task-streaming-render-bugs` (`69bd1ba`, `ba87435`, `8cadc85`,
`c5a5443`), **merged into `main`**; resolution in `TASKS-FINISHED.md` (root
causes, the 278 checks of `tests/unit/render/`, the two accepted limits), the
fence-pairing rule in DECISIONS 59, and DECISIONS 71 for why it was closed by
the agent that held it rather than waiting on a human checklist that nobody had
asked for.

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

## P13 - System notes the model is told: the generator, its hooks, and the token-status hook  [owner-requested 2026-09-25; **WP-A DONE 2026-09-25** (`Go!` was given 2026-09-25) - resolution in `TASKS-FINISHED.md`; WP-B/C/D/E NOT authorised, no `Go!`]

**Owner rulings of 2026-09-25, which overrule parts of the plan below — read these
first.** (i) **The injected note's role is `user`, not `system`, always** — the owner's
call, and the practice they have used by hand: abort, type a `user` message after the
`tool` message, continue inference; their words on what it said, which worked: *"You have
10k tokens left. This is critical. Write a fenced handoff message NOW!"* Why `user` can
follow a `tool` message, and what it costs, is worked out under **hazard 1** below. (ii)
**Percentage thresholds alone are the wrong instrument on a small window** — 90% of 32k
leaves ~3k, which is not enough to write a handoff in, so each level triggers on
**percentage OR remaining tokens, whichever comes first**, plus a notice for windows too
small to work in at all: see **the levels** below. (iii) **Wording: delegated to the
implementer**, to be pinned word-for-word in WP-C and re-pinned when the owner revisits
it. (iv) **When the P14 handoff tool lands, the critical text adopts it** — the fenced
block is the stand-in, and swapping the two is a text change, not a mechanism change.
(v) P15 (`unit:prompt`) is closed and merged; `main` carries it.

**WP-A is DONE** (closed 2026-09-25 on `p13-wp-a-note-unpacking`, cut from
`docs-p13-owner-rulings-handoff-wp-a` tip `1522932`; resolution in `TASKS-FINISHED.md` —
`unit:endpoints` 343 → 394 with the new `test_system_note.py`, t12). **WP-B/C/D/E are NOT
authorised yet** — no `Go!` for any of them; ask before the first code change.

**The goal**: the model itself learns how full its window is while it works, so that
it wraps up and writes a handoff instead of dying mid-task. Three pieces: a **generator**
that turns hook output into notes, one **hook** (the token status, with the
percentage-OR-remaining levels below), and the **unpacking** that puts those notes on the
wire as `user` messages. The handoff tool the critical note will point at is P14; this
entry is the mechanism only.

**The constraint that shapes it** (the owner's): a note may NOT become an item of
`chat.messages`. That list is the index space the whole UI addresses — the sliding
window `messages[lo, hi)` projects it by dict identity (`window_consistent()`),
`StreamCallback`/`RemoveMessage` carry those indexes, `Undo` stores them, and
`ToolCall`/`LlamaCppEndpoint` hold a `message_index` into it mid-stream. A new item in
the middle of that list while a stream runs is the bug, not the feature.

**The mechanism** (the owner's design, adopted, with the role ruled to `user`): a note
is written INTO the message dict it follows, under a key the sender strips — `"system"`,
a list of `{"hook": <name>, "level": <name>, "text": <str>}` entries — and
`endpoints/llamacpp.py:LlamaCppEndpoint:prepare_payload` unpacks each entry, right AFTER
the message that carries it, either into its own `{"role": "user", "content": <text>}`
item or, when the carrier's own role is `user`, merged into that carrier's content — the
adjacency rule worked out under hazard 1. `prepare_payload` already deepcopies every
message (the `reasoning` → `reasoning_key` rename lives in that loop), so the app-side
dict keeps its note, the wire copy never carries the private key, and `chat.messages`
keeps its length and its identities — nothing in the UI can see any of it. The word
"system" in the private key names what it is for (a message to the model, a system
message in the ordinary-language sense); the ROLE on the wire is `user`.

Why the note rides on a message instead of being rebuilt fresh per request: a note is
written **once, at the tail**, at the moment it becomes true, and from then on it is
history. The prompt prefix therefore never changes, so llama.cpp's automatic prefix
cache and this app's own `/slots?action=restore` cache (`endpoints/manage_cache.py`)
stay valid — a note re-injected at a moving position, or merged into the leading
system prompt, would break the whole cached prompt on every request.

**The numbers, and what they may not be**: used = `chat.token_usage["context"]`, the
server's own `prompt_tokens + completion_tokens` of the last call (DECISIONS 80 c);
total = the window the server reported, read through a `Chat.context_window()`
accessor over `ChatSettings.context_sizes[context_key()]` — no network on the request
path. **Unknown total ⇒ silence**, exactly as the dash is a dash on the counts row
(DECISIONS 80 b): a guessed denominator is a lie about when the chat dies. The figure
is the fill at the END of the last reply, so it under-counts the newest user text and
tool results; the note says that in words rather than inventing an estimate.

**Four consequences of storing the note in the message dict — stated, not discovered
later.** (1) `write_chat_history()` persists notes with the chat, so they survive a
reload; `token_usage` does NOT (DECISIONS 80's carry-over), so a reloaded chat starts
at zero counts and the thresholds re-arm while the old notes sit in the history as
factual statements about the past. That is consistent and it must be written down, not
"fixed" by an agent. (2) `Undo` deepcopies the message it records, so undoing a
`change` to a noted message can take the note with it — the note is a nudge, not data,
and the accepted answer is to let it go. (3) `action_abort` removes the tail message,
and with it any note attached to it; the next request re-asks the hooks and re-writes
one. (4) An edit never shows or edits a note (`Message` renders
`reasoning`/`content`/`tool_calls` only), which is also why nothing in the UI notices
any of this.

**The two hazards this entry found, and how it answers them**

1. **`system` after position 0 is refused by strict templates — so the note's role is
   `user`, and `user` has its own adjacency rule, which the unpacking obeys.**
   The finding: the Qwen3.x template in llama.cpp carries
   `{{- raise_exception('System message must be at the beginning.') }}` (line 85 of
   `models/templates/Qwen3.5-4B.jinja`) and the server fails the WHOLE request with
   400/500 — reproductions in llama.cpp #27367, #20733, #18895, QwenLM/Qwen3.8 #244, all
   of them agent harnesses injecting mid-conversation context exactly like this one.
   Hoisting into the leading block or shipping a patched template are the workarounds in
   those threads, and both are wrong here. **The owner's ruling replaces both: the note
   is injected as `user`.**
   - **Is `user` legal after a `tool` message?** Yes. The grammar every tool-capable
     template implements is `assistant(tool_calls)` → `tool`* → anything; the `tool` run
     ends at the first non-`tool` message, and a `user` turn closing it is the ordinary
     next-human-turn shape in the OpenAI contract. The owner's own manual practice is
     the live proof on their models: abort, type the "10k tokens left… write a handoff"
     line as a user message after the tool result, continue inference — worked.
   - **What `user` costs instead**: it swaps the *system-must-be-first* rule for the
     **no two consecutive `user` messages** rule, which the alternation family enforces
     with its own `raise_exception` (mistral-instruct/gemma-it: *"Conversation roles must
     alternate…"*). A `user` note creates exactly that pair whenever the message it rides
     on is itself a `user` message — the first send of a chat, or `action_continue` on a
     user message.
   - **The rule that keeps it out of reach (WP-A):** **merge when the carrier's role is
     `user`, emit a separate item when it is `tool` or `assistant`.** The separate item
     is then only ever preceded by `tool` or `assistant` — both legal — and the merged
     note cannot create a pair because it is not an item. Merging means appending the
     note text to the carrier's own content (a new text part if the content is a list, a
     `\n\n` append if it is a string), on the deepcopied wire message only — the stored
     message keeps its separate `system` entry.
   - **The residual, stated rather than hidden**: a note emitted as an item stays in the
     history, so a HUMAN `user` message typed later lands directly after it —
     `note(user) → user` — the abort-then-type shape, and the carrier rule cannot reach
     it. The owner has been producing precisely that shape by hand for months without a
     template refusing it, so the accepted position is: `user` is the role, this shape is
     a filed limit for the alternation family, and the escape hatch if one ever bites is
     merge-always (`off` in follow-up (a) below).
   - **Correction to this entry's first draft, on the cache.** It claimed merging would
     "break the whole cached prompt". It does not: prefix caching is positional, so
     everything before the modified message is still valid and only the carrier's own
     tokens re-prefill — usually one tool result. What genuinely invalidates the cache is
     rewriting position 0 (the leading prompt) or moving a note that is already in the
     history. So the merge rule above costs a message, not a prompt, and the
     once-at-the-tail rule stays for the reason it was made (a note never moves), not for
     the one first written.
2. **The template also wants an assistant's `tool_calls` and their `tool` replies
   adjacent.** The generator only ever notes the LAST message, and at that moment the
   last message is a `user`, a `tool`, or an `assistant` without `tool_calls` (a
   request can only be pending once the pending tool calls have been run:
   `work_stream()` runs them before `endpoint.stream()`), so the note never lands
   inside a tool run. Pin it (WP-A pins the shape, WP-D pins the live sequence) rather
   than trust it.

**Package split** — five, each one sitting, each far under the token budget; all the
code together is ~120 lines.

- **WP-A — the unpacking (the only piece that touches the wire). `Go!` GIVEN 2026-09-25,
  DONE 2026-09-25** (`p13-wp-a-note-unpacking`, code `0afaef8`; the two helpers on
  `LlamaCppEndpoint` are `append_note()`/`merge_into_content()`, the test file is
  `test_system_note.py` t12, 51 checks — resolution in `TASKS-FINISHED.md`).
  `endpoints/llamacpp.py`: in the `prepare_payload()` loop, `_message.pop("system")` and
  for each entry in order — if the carrier's own role is `user`, **merge** the text into
  the wire copy's content (append onto the last `{"type": "text"}` part, or add one when
  there is none, or `\n\n`-append when the content is a plain string); otherwise append a
  new `{"role": "user", "content": text}` item after it. The role is the owner's ruling
  and the merge is the adjacency rule under hazard 1; both belong in ONE small helper
  method so WP-D has one thing to call and the suite one thing to pin. Nothing writes a
  note yet, so today's behaviour is unchanged and provable.
  Tests: `unit:endpoints`, new file `test_system_note.py`, **t12** (append-only,
  TRAPS #15): a note on a `tool`/`assistant` carrier becomes a `user` item AFTER it and
  never a `system` one; several notes keep their order; **a note on a `user` carrier
  creates no second `user` item** — the text lands in the carrier's own content and the
  message count does not grow; the private key is never on the wire; the app-side dict
  keeps both its note and its own content unmodified (the deepcopy, as t1 does for
  `reasoning`); a message with no note gives a byte-identical payload — the differential
  against the pinned baseline `b799526` (`endpoint_harness`) says the no-note case moved
  nothing; notes coexist with the `reasoning` rename; the leading system prompt stays at
  index 0; no `tool` message is ever separated from the `assistant` whose `tool_calls` it
  answers, and the after-the-carrier position is pinned even for an assistant carrying
  `tool_calls` (a consequence stated, not hidden).
- **WP-B — the generator and the hook contract.** New `spit_app/chat/system_note.py`,
  importing NOTHING of Textual/httpx (TRAPS #19 — it must run on the bare
  interpreter): `class SystemNotes` with `__init__(chat)` and `attach()`, a module
  `HOOKS` list, and per-message `hook.notice(chat, messages, index)` returning text or
  `None`. Invariants pinned by a NEW suite `tests/unit/system_note/` (bare python3,
  `run_tests.sh` + `test_generator.py`): hooks are asked at every message position; a
  hook speaks **at most once per message** (the walk is idempotent, so N requests
  never duplicate a note); `None`/empty writes NOTHING — no empty `"system"` key;
  `len(chat.messages)` and every `id(message)` are unchanged (the note never becomes a
  message — the whole point, and the check that keeps WP-A's premise true); a raising
  hook is NOT swallowed — a broken hook must not survive by silently doing nothing
  (the same posture as the `{}`-endpoint KeyError pinned as a limit in DECISIONS 80 b).
- **WP-C — the token-status hook.** `spit_app/chat/token_status.py`.

  **The levels (owner ruling: percentage OR remaining, whichever comes first).** Each
  level has a percentage trigger AND an absolute remainder floor, and it triggers at the
  LOWER of the two fills:

  | level | rank | percentage | remaining floor | fires at fill |
  |---|---|---|---|---|
  | `small_window` | orthogonal | — | — | `total <= 32768`, once, regardless of fill |
  | `info` | 1 | 50% | — | 50% |
  | `warning` | 2 | 80% | 20 000 | `min(0.8·total, total − 20000)` |
  | `critical` | 3 | 90% | 10 000 | `min(0.9·total, total − 10000)` |

  Worked out, because the whole point is that the two instruments disagree on small
  windows:

  | total | `info` | `warning` | `critical` | governed by |
  |---|---|---|---|---|
  | 32k | 50% (16.4k) | **39%** (12.8k) | **69%** (22.8k) | the floors |
  | 64k | 50% (32.8k) | **69%** (45.5k) | **85%** (55.5k) | the floors |
  | 128k | 50% | 80% | 90% | the percentages |
  | 200k | 50% | 80% | 90% | the percentages |

  **Consequence, and it is a design rule, not a wart**: on a small window a HIGHER-ranked
  level triggers at a LOWER fill than a lower-ranked one (32k: `warning` at 39%, `info` at
  50%). So the state machine advances **by level rank, never by trigger order** — the
  highest level whose trigger holds is announced, and only if its rank is strictly above
  every rank already announced. On a 32k window the first note the model ever sees is the
  `warning`, and `info` is shadowed forever; that is correct, and WP-C pins it on a 32k
  fixture (announce-order is `warning, critical`, with `info` never emitted).
  `small_window` is not a rank: it is a one-shot statement about the window's SIZE, fired
  the first time the fill is known at all, and it never repeats or upgrades.
  The four numbers (`32768 / 0.5 / 20000 / 10000`) are module constants: tuning them is a
  one-line change plus the re-pin of the texts that quote them (settings are follow-up
  (c); the owner's floors, "10k", are theirs, and the 2× relation between the two floors
  is the implementer's choice, stated so it can be argued with).

  **The texts** (wording delegated by the owner 2026-09-25; pinned word-for-word in the
  suite — model-facing text is code — and re-pinned when the owner revisits it; P14
  replaces the fenced-block clause in `critical` with the tool call). They give the model
  the verdict and the action, never arithmetic; the owner's own working line is the model
  for `critical`: *"You have 10k tokens left. This is critical. Write a fenced handoff
  message NOW!"*

  - `small_window`: *"This chat's context window is only {total} tokens. That is small
    enough to run out during ordinary work, so work narrowly: read the range you need,
    not whole files; open few files at a time; do not repeat a read you already have;
    keep what you print short."*
  - `info`: *"Token status: {used} of {total} used ({pct}%), {remaining} left (the
    server's figure at the end of the last reply — the newest tool results are not in it
    yet). Nothing urgent: spend what is left on the task, not on re-reading."*
  - `warning`: *"Token warning: {used} of {total} used ({pct}%), {remaining} left. Start
    closing out: no new files unless the task cannot go on without them, targeted reads
    instead of whole files, and begin writing down what you have done and what is still
    left, while you still have room to say it properly."*
  - `critical`: *"Critical: {used} of {total} used ({pct}%), {remaining} tokens left.
    Stop working now. Write a fenced handoff message NOW: the task in one line, what you
    changed (paths), what is unfinished, the exact next step, and anything you learned
    that is not in the repo. Do not call any more tools and do not start new work after
    the handoff — the chat dies inside this reply."*
  (`{used}`/`{total}`/`{remaining}` plain integers, `{pct}` an integer percent. The
  "do not continue after the handoff" half is load-bearing: the owner's observation was
  that models which were not told it wrote a handoff and then kept working until the
  crash.)

  Tests in `unit:system_note`: silent below every trigger / at 0 usage / when the total
  is `None` (with the TRAPS #13 control that the same fixture with a known total DOES
  speak); each level fires exactly once and never downgrades; the 32k fixture's
  announce-order; the 10 000/20 000 floors beat the percentages exactly where the table
  above says; `small_window` fires once and only for `total <= 32768`; the four texts
  pinned byte-for-byte at a fixture where every number is distinct so a substitution
  mistake cannot pass.
- **WP-D — the wiring, and the proof the chain works.** `Chat.__init__`: the
  `TokenStatus` and `SystemNotes` instances (session state, next to `token_usage`, for
  the DECISIONS 80 c reason — a `Work` is built per send) and `Chat.context_window()`;
  `Work.work_stream()`: `self.chat.system_notes.attach()` immediately before
  `await self.endpoint.stream()` — the position is load-bearing: the tool loop
  re-enters `work_stream()`, so this asks the hooks before EVERY request, including
  the ones inside a tool loop, where the window actually fills up. Tests:
  `unit:endpoints` **t13**, end to end over the canned server (it records POST bodies):
  under threshold ⇒ no note in the body; over 50% ⇒ exactly one system note in the
  right position of the next request's `messages`; a second request at the same level
  adds none; the `chat.messages` list the UI holds never gains an item; and on a `user`
  carrier the note is merged, so the request's message COUNT is the same with the note as
  without it (the hazard-1 rule, proven on the wire and not only in the helper). Prove
  the UI is untouched: `chat_smoke`'s `golden.txt` md5 unmoved, `chat_window` row unmoved.
- **WP-E — the docs.** DECISIONS 81 (the note-in-the-message-dict contract and why not
  an index; the once-at-the-tail rule and the prefix-cache argument; silence when the
  window is unknown; **the owner's role ruling — notes ride the wire as `user`, why
  `system` cannot, and the `user`→`user` merge rule that keeps the alternation family
  happy**; **the percentage-OR-remaining levels, why the ranks advance out of trigger
  order on a small window, and the small-window notice**; the strict-template evidence;
  the residual abort-then-type limit); cross-linked from DECISIONS 80's counts row;
  `TESTING.md` ground truth with the new `unit:system_note` row and the `unit:endpoints`
  delta; `PROJECT.md` map; this entry closed by its holder.

**Follow-ups to file when WP-E runs** (not part of P13): (a) `note_mode` endpoint setting
`separate` / `merge` / `off` — `user` is the decided role, and this is the escape hatch
for the one shape hazard 1 cannot reach (a human `user` turn typed right after a note)
plus the kill switch for an endpoint that objects; (b) render the notes in the UI so the
user sees what the model was told (they are invisible today: `Message` renders
`reasoning`/`content`/`tool_calls` only); (c) the level numbers as settings; (d) **P14,
the handoff tool**, whose arrival replaces the fenced-block clause of the critical text.

**Verify**: full `bash spit_app/tests/run_tests.sh` from the repo root, every row
byte-for-byte except `unit:endpoints` (up by t12/t13) and the new `unit:system_note`
row; `chat_smoke`'s golden md5 unmoved. (`unit:prompt`'s old red is gone: P15 closed and
the owner merged it, so `main` now reads 33 like the table.)

**Gotchas**: TRAPS #19 (the WP-B/WP-C modules must import no Textual/httpx or the new
suite silently needs the venv — gate it the way the five existing dependency suites
do); #13 (every silent case needs the control that makes it speak); #15 (t12/t13 are
new numbers, never reused); #18 (read a row as a floor — a crash hides behind
`tail -n 1`); #14 (the no-note payload differential is the proof the wire format did
not move); DECISIONS 80 (b)/(c) for the counts and the dash; the note text is
model-facing text, i.e. code.

---

## P14 - New tool: `handoff` — an agent hands the work to the next agent  [owner-described 2026-09-25; not started; needs `Go!`]

The owner's stated intent, verbatim from the P13 briefing: *"later we will introduce a
tool call that lets you handoff information to the next agent so they may continue
with the work. This will give you more autonomy and helps in automating what I've been
doing by hand since now — telling the model that tokens run out and that they should
handoff the work to the next agent, asking them to write a handoff message which I put
into the next agent's chat. We want to automate this and avoid having the agent die mid
work."*

- **What P13 already does for it**: the `critical` note (P13/WP-C) is the trigger that
  exists today; it tells the model to write the summary as a fenced block. P14 gives that
  summary somewhere to GO instead of into the chat's last message, and when it lands the
  note's text is updated to call it (owner ruling 2026-09-25: "we can adopt the message
  when the tool call lands") — a text change plus its pinned-check re-pin, no mechanism
  change.
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
- **Verify**: full `bash spit_app/tests/run_tests.sh` green (its own new suite; note
  the tip-red of P15 so a reader knows what a `unit:prompt` row means); new suite's
  checks in its summary line; both `TASKS-FINISHED.md` and the P13 follow-up list
  updated.
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

## P1 - patch: the `is_header_pair` adjacency edge  [open, deliberate]

- **Scope**: `spit_app/tools/scripts/patch.py` (+ its test suite)
- **Status**: left open ON PURPOSE during the patch redesign. Not a forgotten bug.
- **Verify**: `cd ~/spit.py/spit_app/tests/tools/patch && bash run_tests.sh` (80 green);
  a fix adds tests without reusing freed numbers 5-9 (append-only).
- **Gotchas**: TRAPS #13/#15; DECISIONS 37 and the section below.
- **How to start**: read the verbatim record below first; the natural fix is to
  require a genuine file header to be followed by a `@@` hunk header or end of
  input. Prove the change by differential over every fixture (TESTING.md).

### 4. OPEN — the `is_header_pair` adjacency edge in `patch`

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
