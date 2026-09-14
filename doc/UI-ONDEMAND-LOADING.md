# UI-ONDEMAND-LOADING.md — windowed (on-demand) message loading for `ChatView`

**The window SLIDES. On-demand means both halves: mounting messages that come
into view AND unmounting the ones the user moved away from, at BOTH ends, so
the mounted widget count stays bounded independent of history length.** (The
first revision of this plan had `window_start` only ever shrinking — widgets
grew upward and were never released. The owner corrected that 2026-09-14: a
non-sliding window defers the cost, it does not bound it, and "keep the widget
count minimal so the app remains responsive" is the whole point. Everything
below reflects the sliding window; the tail-alignment shortcut the first
revision relied on is explicitly retired below.)

Plan and work-package split for implementing on-demand message loading on top
of the proven top-anchored scroll container (`TASKS-PLANNED.md` P8: mechanism,
design and measurements — feasibility PROVEN 2026-09-14, headless, Textual
8.2.8; probes `/tmp/anchor-probe/probe.py`, `probe6.py`, `probe7.py`). This document is the
transition plan; **every work package (WP) below still needs its own branch
and the owner's `Go!` before the first code change.** Written 2026-09-14; file
facts verified against the tree on that date.

## Why this is a view-layer-only change (the load-bearing facts)

Read from source, not assumed:

1. `Chat.__init__` (`chat/chat.py`) loads the whole `chats/<id>.json` into
   `self.messages` (plain dicts). The data layer stays **complete and
   in-memory**; only the *widget tree* becomes a window. No JSON format change,
   no storage change.
2. `Work` (`chat/work.py`) holds `self.messages = chat.messages` (the same
   list) and the endpoint streams against it; it reaches the UI **only** via
   `chat_view.callback(index, signal)` / `post_message(RemoveMessage(i))`.
   Verified: `work.py` never touches `children`. So streaming needs no window
   awareness beyond "the callback's index may address an unmounted message".
3. The current invariant is `ChatView.children[i] is Message(chat.messages[i])`
   for ALL i (`ChatView.messages` IS `chat.messages`). The window change is:
   `children[i] is Message(messages[lo + i])`, mounted range `[lo, hi)` —
   **both bounds free, the window slides.** `children[-1]` is then only the
   last *mounted* message; every "the last message" intent must address the
   data index explicitly (see the coupling table's sharp edges).
4. `CallbackMixIn.is_present(index)` (`chat/callback.py:13`) is already a
   half-acknowledgement that a message may have no widget; it assumes prefix
   alignment (`index < len(children)`), which becomes "index in `[lo, hi)`".
5. **A `Message` widget is a disposable projection of its dict**:
   `Message(chat, message_dict)` + `finish()` rebuilds the widget completely
   from the dict alone — that is exactly what `load()` already does for the
   whole history. **Unloading is therefore just `child.remove()`, and reloading
   is the normal mount path plus anchor compensation.** No widget state needs
   serializing, with three named exceptions that must be pinned (protected
   from eviction): the focused widget, any widget with `is_edit` (editing
   state lives *inside* the widget), and — while `chat.is_working()` — the
   streaming tail.
6. `Work` only ever mutates the **last message dict** (`work.py` reads
   `self.messages[-1]`). A streaming update to an unmounted message is
   data-only and cannot tear: the widget, when it re-enters the window,
   renders the finished dict.

## The coupling surface (WP-B checklist; ~30 sites, 7 files)

Message-index → widget via `chat_view.children[...]`. **The three
`children[-1]` sites are the sharp edge of the sliding window** — with both
ends evicting, "last mounted" ≠ "last chat message" once the user has scrolled
away and the bottom was pruned; they need explicit last-message handling, not
accessor-translation:

| file | sites | note |
|---|---|---|
| `chat/callback.py` | `is_present` 13–16; finish 17–18; start 22–24; focus 27–30; process 33–36 | window-aware accessor; updates to unmounted messages are **data-only** (fact 6) — skip the widget, it rebuilds from the dict on re-entry |
| `chat/chat.py` | `action_abort` 118–119 (`children[-1]`) | must address the last MESSAGE: `await materialize(len(messages)-1)` first (abort while scrolled away = bring the streaming tail back, then remove); pinned during `is_working()` anyway (fact 5), materialize covers the edge |
| `chat/chat_text_area.py` | 30–32 (`children[-1]`) | submit already `scroll_end`s to the bottom → materialize-last there; the two fold naturally |
| `chat/chat_view.py` | `on_remove_message` 34–35, 43; `focus_this` 65; `load()` 84–87 | removal must handle un-indexed/out-of-window |
| `chat/chat_view_actions.py` | 58, 63 (prev/next focus); 75, 77 (`action_add`); `show_cots`/`reset_message_edit` iterate ALL children | iteration becomes window-only + replay-on-materialize |
| `chat/message/actions.py` | 87, 89 (`add_message_next`); 123, 125, 127 (`add_message_prev`); 138 (`children[index+1]`) | the index-editing flows — WP-E |
| `chat/undo.py` | `_change` 19–22; `_insert` 31–33; `_remove` 36–41 | undo of an out-of-window message → materialize |

(`message/actions.py` `children[1]` etc. at 24, 43, 54, 70 are `Message`-internal,
not window-relevant; `chat_settings.py` hits are unrelated.)

## Target API (all on the windowed `ChatView`)

```python
class ChatView(AnchoredScroll):            # WP-A changes the base class
    window: tuple[int, int]                # [lo, hi); mounted == messages[lo:hi]

    def widget(self, index: int) -> Message | None      # None when out of window
    async def materialize(self, index: int) -> Message  # grow window to cover it:
        # above the top: arm_top_anchor() first, batch-mount, lo -= k
        # below the bottom: load_newer(k) — symmetric
    async def load_older(self, count: int) -> None      # materialize a page above
    async def load_newer(self, count: int) -> None      # materialize a page below
    async def prune(self) -> None                       # evict BOTH ends beyond the
        # protected zone (viewport ± PRUNE_MARGIN), never a pinned widget (fact 5)
    async def mount_message(self, index)                # existing, made window-aware
```

## The sliding-window model and its invariants

`mounted == messages[lo:hi]`, both bounds free. Around the viewport (content
rows) the window keeps `PRUNE_MARGIN` of widgets on each side; scrolling
grows it past that, `prune()` releases back to it. Mounted count is then a
function of viewport + margin, **never of history length** — which is the
stated goal. Each rule is arithmetic or measured:

1. **Mount above and evict above are the same event to the view**: the
   anchor's content-space y moves by `delta` (positive or negative) and
   `scroll_y += delta` lands in the same layout pass. The anchor mechanism
   (P8) is direction-agnostic; probe 7 measured the eviction direction:
   evicting 12 rows above held the view (`scroll_y` 30→18 = exactly −12),
   **zero jump frames**; 20 mount+prune cycles held the tracked anchor with
   **zero** bad frames and a **flat mounted count** across cycles (13 at
   viewport 10 / margin 20 — the window, not the history).
2. **Evict below the viewport needs no compensation**: `scroll_y` is a prefix
   height, so removing rows strictly below `scroll_y + viewport_h` changes
   neither it nor the visible content, and the clamp cannot bite while at
   least one viewport of content remains below (`scroll_y ≤ new_total −
   viewport_h` holds by arithmetic; `PRUNE_MARGIN ≥ viewport_h` guarantees
   it). Measured (probe 7): evicting 26 widgets below produced **zero
   corrections and zero movement**.
3. **Remount into a gap below** (`load_newer`) is compensated like rule 1
   (measured: 0 jump frames).
4. `load()` mounts the last `INITIAL_WINDOW` and `scroll_end`s (open-at-bottom
   UX unchanged); from there the window slides both ways.
5. **Never evict**: the focused widget, any widget with `is_edit`, and — while
   `chat.is_working()` — the last message (fact 5). Simplest safe superset:
   `is_edit` disables `prune()` entirely (a `Go`-time decision, WP-E).
6. `is_edit`/show-cots state is applied at mount time already
   (`Message.maybe_mount_content` reads `chat_view.is_edit`), so a persisted
   per-view flag replay is all `materialize` needs for edit-mode children —
   and why edited widgets are pinned rather than rebuilt.
7. **Clamp-zone hazard (found by probe 7, prevented by margin):** corrections
   are `validate_scroll_y`-clamped to `[0, max_scroll_y]`; near the edges of
   a *too-small* window (content barely bigger than the viewport) a
   legitimate compensation can be clamped and tear the view. Invariant: the
   window always holds ≥ viewport + 2×margin rows of *mounted* content
   (margin ≥ viewport height) — pruning back through this invariant is what
   the probe's churn cycle was made to respect.
8. **Known UX cost, stated:** the scrollbar thumb and `max_scroll_y` then
   describe the WINDOW, not the whole history — the thumb grows/shrinks and
   "drag to top" lands at the window top, not message 0. Convention for chat
   scrolls (wheel/keyboard + the existing ctrl+up/ctrl+down message jumps do
   long trips). If history-proportional scrolling is wanted later, the
   upgrade is estimated-height **spacer widgets** above/below the window (the
   classic virtualised-list trick) — a design step, not a rewrite.

## Work packages

Sizing assumes a fresh 256k agent: onboarding = `AGENTS.md` +
`doc/PROJECT.md`, `CONVENTIONS.md`, `TRAPS.md`, `TESTING.md` + the named
source files (~35–60k incl. suite runs). Each WP: own branch, own `Go!`, full
`bash spit_app/tests/run_tests.sh` before/after, counts per `TESTING.md`.
**No WP starts until the previous one it depends on is merged to the working
branch chain** (branches stack; `main` untouched throughout).

### WP-A — the anchored container widget  [depends: none; parallel with B]
- **Scope**: new `spit_app/chat/anchored_scroll.py` (the P8 widget: one-shot
  `arm_top_anchor()` + persistent `pin()`/`unpin()`; disarm-if-anchor-gone);
  new `spit_app/tests/unit/anchored/` (venv-dependent, FAIL-with-remedy
  pattern of `unit:terminal`; headless `App.run_test` probes rebuilt as
  checks); `run_tests.sh` row. `ChatView` NOT touched yet.
- **Read list**: P8 entry in `TASKS-PLANNED.md`; `doc/TESTING.md` (the venv
  pattern); `tests/unit/terminal/stub_app.py` (harness precedent).
- **Accept**: probes green: defect reproduced on plain `VerticalScroll`; 0 jump
  frames with the widget, single + batched mounts, growth-above, user-scroll
  re-baseline, bottom-anchor coexistence — **and the probe-7 eviction checks:
  evict-above holds the view (negative delta), evict-below moves nothing,
  remount-below holds**. Suite otherwise unmoved.

### WP-B — index-accessor refactor, ZERO behaviour change  [depends: none; parallel with A]
- **Scope**: the ~30 sites above → `ChatView.widget(index)` / `widget_index()`
  accessors with `window_start = 0` hard-wired (so behaviour is provably
  identical); assertion `len(children) == len(messages) - window_start`.
- **Read list**: this doc's coupling table + the 7 files in full.
- **Accept**: full suite green; **differential proof** the refactor is
  behaviour-preserving (TRAPS #14/#18): scripted app-level smoke over a fixture
  chat (mount/edit/remove/undo/abort) byte-identical before/after — a
  headless-harness check, lives with the new `unit:anchored`-style UI suite.
- **Hazards**: do not "fix" anything noticed en route — file it; one concern
  per commit means one commit per file-group here.

### WP-C — the sliding-window core  [depends: A + B]
- **Scope**: `window = (lo, hi)` state; `load()` = last `INITIAL_WINDOW`
  (start 50, constant; settings surface later if wanted) + `scroll_end`;
  `load_older(count)` / `load_newer(count)` with the arm→batch-mount→disarm
  dance at either end; `prune()` per the invariants (margins, pinned-widget
  rules of fact 5, clamp-zone rule 7); `materialize()`; re-entrancy guard;
  **the three `children[-1]` sharp edges** (`action_abort`, submit,
  `message_start`) → explicit last-message handling; chat-switch interplay
  (`side_panel.py:86–88`, `handlers.py:27–28` mount a fresh `Chat` per open —
  verify whether stale Chat views stack in `#main`, and keep whatever holds
  today).
- **Read list**: this doc's model + invariants; `chat_view.py`, `callback.py`,
  `chat.py`, `chat_text_area.py`, `side_panel.py`, `handlers.py`, WP-A widget
  source; UI-ROUTE-RATATUI.md "M1" paragraph (this window is the same
  state/view seam — note it in the commit, do not pre-build the protocol).
- **Accept**: new UI-suite checks: open a 1k-message fixture → ≤ 50 mounted +
  `scroll_end`; `load_older(25)` → anchor holds (frame-spy: 0 jump frames),
  `lo` −25, JSON untouched; **`prune()` after a slide → mounted count returns
  to ≤ window size, evicted-above/below behave per rules 1–2 (probe-7
  semantics at the ChatView level), pinned set never evicted**;
  abort-while-scrolled-up materializes the tail then aborts; `materialize(k)`
  correct at both edges.

### WP-D — load/prune triggers and scroll UX  [depends: C; parallel with E]
- **Scope**: `watch_scroll_y` thresholds → `load_older` near the window top /
  `load_newer` near its bottom; `prune()` after every settled scroll (and
  after every load); stop cleanly at `lo == 0` / `hi == len(messages)`; no
  triggers while streaming/`is_edit`/already loading; follow-bottom
  (`anchor()`) untouched — verify the release semantics interact (P8: wheel
  release path is `scroll()`).
- **Read list**: P8 measurements + this doc's invariants; `chat_view.py` after C.
- **Accept**: scripted pilot: continuous wheel-scroll up through a 1k fixture
  loads pages **and prunes the bottom**, mounted count **flat at every depth**
  (probe-7 churn as a ChatView check), 0 jump frames throughout; scroll back
  down reloads symmetrically; keyboard scroll at true ends does nothing;
  streaming append still sticks to bottom.

### WP-E — edits, undo, removal across the window edges  [depends: C; parallel with D]
- **Scope**: `undo._insert/_change/_remove` and `message/actions.py`
  add/remove flows → `widget()`/`materialize()`; focus survival when the
  focused widget leaves the window (focus ChatView or nearest);
  `show_cots`/`reset_message_edit` replay on materialize; the `is_edit`
  interaction (editing should pin a window that covers the edit — a `Go`-time
  decision: simplest is `is_edit` disables unloading entirely).
- **Read list**: `undo.py`, `message/actions.py`, `chat_view_actions.py`, C's API.
- **Accept**: scripted checks: undo-insert an old (out-of-window) message → it
  materializes at the right index and the view does not jump; remove at edge;
  edit_on/off round-trip with a grown window.

### WP-F — measurements, numbers, decision record, close P8  [depends: C+D+E]
- **Scope**: DECISIONS-65-style table at 100/1k/5k messages: windowed mount
  time + page-down + **mounted widget count at every scroll depth (the
  headline number — must be flat in history length; this is the goal the
  owner stated and the reason the window slides)** + RSS, vs full mount, same
  corpus, headless; write the numbers into `TASKS-FINISHED.md` (close P8) and
  a DECISIONS entry recording this as the Textual-side bridge (does NOT
  re-open DECISIONS 65 — the ratatui route stands; M1's state extraction now
  has a working precedent to reuse).
- **Accept**: numbers in the docs, mounted count demonstrated flat at 1k and
  5k depths; full suite green; P8 entry closed.

Parallelism summary: **A ∥ B → C → D ∥ E → F** (6 packages; ≤ 6 agents, or
3–4 agents taking two each — A+B and D+E pair well for one head each).

**Execution mode chosen by the owner (2026-09-14): strictly SERIAL, one agent
at a time, order A → B → C → D → E → F** (the ∥ was permission, not demand;
serial satisfies all dependencies). Handoff convention: each agent starts
from the previous agent's branch tip (branches stack; `main` untouched — the
merge stays the owner's) and, on completing its WP, writes the next agent's
initial message (a fenced block given to the owner) carrying: branch chain +
last commit sha, any deviation from the planned API, hazards discovered so
far, and the next WP's scope per this doc. The canonical state is
`TASKS-IN-PROGRESS.md`, never the chat message.

## Standing hazards for every WP here

- UI tests need the venv (`~/.venv-spit`, `create_venv.sh`); the suite rows
  must degrade FAIL-with-remedy, never silent zero (TRAPS #19 pattern).
- `Chat.messages` is the SAME list object as `ChatView.messages` — nothing may
  window the *data*. Assert it (identity check) in the new suite.
- **`children[-1]` is a loaded gun under a sliding window**: it is the last
  MOUNTED message, not the last chat message. The three sites (coupling
  table) must address the last message by data index + `materialize`; a
  mechanical accessor translation that keeps `children[-1]` compiles, passes
  a short-chat smoke, and breaks exactly when the bottom has been pruned.
  The streaming-tail pin (fact 5) narrows the window of exposure; it does
  not replace the explicit handling.
- Prune discipline is the twin hazard: evicting anything intersecting or
  above the viewport, or pruning inside the clamp-zone invariant (rule 7),
  moves the view — margins and the pinned set are load-bearing, assert them
  in the suite, and keep the frame-spy checks (0 jump frames) as the tripwire.
- Keep `is_edit` semantics (reasoning display etc.) decided at mount time;
  materialize must inherit current view flags.
- No owner sign-off of finished work; close your own WP entry when its
  `Verify` is met (TRAPS #22). `Go!` per WP before the first code edit.
