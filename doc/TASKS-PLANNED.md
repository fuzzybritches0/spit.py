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
