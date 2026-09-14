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

## P8 - On-demand message loading with a top-anchored scroll container  [feasibility proven 2026-09-14; implementation awaits the owner's `Go!`]

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
  solved half. This is a Textual-side mitigation next to fallback rung 1 of
  `UI-ROUTE-RATATUI.md` — it does NOT re-open DECISIONS 65 (the whole-tree
  cost of *mounted* messages stays; the win is mounting fewer of them).
- A viewport **resize** reflows every message; decide there whether the pin
  compensates (it will, if armed) — semantics, not a bug.
- **Verify**: probes rebuilt as a checkable suite + full `bash
  spit_app/tests/run_tests.sh` green (counts from `doc/TESTING.md` unmoved).

---

## P7 - MOVED to doc/UI-ROUTE-RATATUI.md — leave Textual for a ratatui front end  [high priority, architecture]

Decided 2026-09-07 (DECISIONS 65). The plan, the gates (M0–M5), the measurements
and the fallback ladder are in **`doc/UI-ROUTE-RATATUI.md`**; the front-end
contract is **`doc/UI-PROTOCOL.md`**.

- **Prerequisite**: **P0b**, the `terminal` tool returning an empty message
  container, filed on branch `task-terminal-empty-output`. Merge that branch
  first: P0b is also the harness the new front end is tested with
  (`UI-ROUTE-RATATUI.md`, "Prerequisite: the `terminal` tool").
- **Do not start before the owner approves M0** (a ~2-day gated spike).
- **Verify**: the M0 gate in the route doc; the full suite unchanged throughout
  (the tool layer imports no Textual, so its counts are the safety net).

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
