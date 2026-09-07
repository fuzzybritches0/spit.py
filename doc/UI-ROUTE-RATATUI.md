# UI-ROUTE-RATATUI.md - leaving Textual for a ratatui front end over a protocol

Part of the spit.py documentation set (see `PROJECT.md`). The plan and the gates
for an agent to execute. The contract itself is in `UI-PROTOCOL.md`; the *why*
is `DECISIONS` 65. Assessment and measurements: 2026-09-07, on this machine.

## Why move at all (measured, not felt)

Same corpus, same widget structure (`ChatView > Message > Content > Process >
Part`, `Part` = the app's own `MarkdownIt("gfm-like")` factory), Textual 8.2.8
headless:

| messages | widgets | mount the history | one page-down |
|---|---|---|---|
| 100 | 1,700 | 6.0 s | 327 ms |
| 400 | 6,800 | 23.5 s | 1,145–1,919 ms |
| 1,000 | **17,000** | 61.5 s | **2,794–4,576 ms** |

17 widgets per message: that is the Markdown widget exploding into a tree, and
the cost grows with the *whole* history, not with what is on screen. Replacing
`Markdown` with `Static` still scales (3,000 widgets at 1,000 messages, 500–700
ms per page-down) — so roughly two thirds is Markdown and one third is the
retained tree, which is why partial loading needed a patch to Textual itself.

Same content on a virtualised immediate-mode view (pre-wrapped lines, prefix-sum
heights, only the messages intersecting the viewport rendered):

| 2,000 messages / 32,000 visual lines | frame |
|---|---|
| scroll at 0 / 25 / 50 / 75 / 95 / 100 % | 0.34 / 0.29 / 0.31 / 0.28 / 0.30 / 0.29 ms |
| 5,000 messages / 80,000 lines | 0.38 / 0.42 / 0.37 ms |
| build all 2,000 (parse + wrap + text) | 0.99 s, RSS 56 MB |
| one streaming tick (append, re-parse, re-wrap, repaint) | 2.25 ms |
| idle 30 fps repaint | 1.7 % of one core |

**Three orders of magnitude, flat at any history length.** A frame budget at
30 fps is 33 ms; this spends about 1 % of it. Note also the negative result:
the *naive* port — the whole chat in one wrapped paragraph — measured 5.97 ms at
the top and 48.3 ms at 95 % depth, i.e. the same O(document) shape as Textual.
**Virtualisation is not an optimisation we add later, it is the design.** If a
future agent finds themselves re-rendering the whole history per frame, they
have left the route.

## The shape

```
spit.py (Python)                       spit-tui (Rust, ratatui)
  chats, settings, endpoints             viewport + wrap/height cache
  llama.cpp server control               keymap, focus, screens, theme
  tool calling, Run/bwrap sandbox        markdown → styled lines (pulldown-cmark + syntect)
  tmux terminal backend                  TextArea input, images (ratatui-image)
  LaTeX PNG (ziamath + cairosvg)  ⇄      clipboard (OSC52), scrollback anchoring
             JSONL over stdin/stdout  (UI-PROTOCOL.md)
```

* The Rust side is **dumb**: renders, reads input, measures and wraps. It never
  executes anything — no bwrap, no subprocess, no model calls, no tmux. The
  sandbox boundary does not move and the front end needs no privileges.
* Markdown, highlighting and wrapping live in Rust. Raw text on the wire, styling
  on the screen — so a streamed delta is one short line of JSON.
* **The tool layer does not change at all.** `spit_app/tools/**`, `run/`, the
  sandbox and the tmux backend import no Textual (verified 2026-09-07), so the
  509 tool checks and the 131 argument checks stay green for the entire
  migration. That is the safety net; do not give it up by "tidying" tools.
* Textual stays installed and working until the last screen is ported.
  `spit.py` = new UI, `spit.py --ui=textual` = old UI. Reversible to the end.
* Front-end tree starts as a sibling, `/home/kurt/spit-tui`, until packaging is
  settled. Nothing Rust lives inside `spit.py` in M0–M1.

## Milestones

Each is a branch (`ui-m0-…`, `ui-m1-…`), one concern per commit, `main`
untouched, nothing pushed. "Verify" is the whole suite
(`bash spit_app/tests/run_tests.sh`) — the tool-suite counts must not move —
plus the milestone's own gate.

### M0 - Gate (timeboxed, ~2 days). Do not skip, do not extend.

Build the smallest thing that can fail, in `/home/kurt/spit-tui`:

1. Virtualised list of 5,000 synthetic messages at the owner's terminal size,
   measuring per-frame cost including the wrap/measure cache. **Pass: <1 ms at
   any offset.**
2. Keyboard scroll (Up/Down/PageUp/PageDown/Home/End) plus **mouse wheel and
   click**, and **bracketed paste into `tui-textarea`**. Pass: all three behave;
   specifically a three-line paste arrives as three lines, not one — that is the
   test the Python binding fails (`DECISIONS` 65).
3. `pulldown-cmark` + `syntect` rendering our markdown subset — headings, nested
   lists, tables, fenced code with highlighting, CJK and emoji widths — and the
   `~~~~~` tool-fence language of DECISIONS 59 rendered as designed. Pass: the
   `~~~~~` convention survives and the fence count stays even per tool call.
4. LaTeX: PNG produced by the existing Python path → displayed through
   `ratatui-image` on **both** Kitty and Sixel (Foot). Pass: visible on both,
   or a clear account of which protocol fails where.
5. A live token stream from an unchanged `Work` worker over JSONL, with
   **abort working** (partial message committed, tool's process group killed).

Commit the probes (`ui-m0-probes/`) and their numbers into the repo so the
baselines above stay reproducible. **If (1) or (2) fails, stop** and take up
*Fallback ladder*.

### M1 - Protocol and a headless engine (no UI yet)

* Write `UI-PROTOCOL.md` v1 for real (it is a draft): ids, `hello` handshake and
  capabilities, `state.snapshot`, `part.delta`/`part.done`, `busy`,
  `ui.request`/`ui.reply`, `resync.request`, forms, assets, error codes.
* `spit.py --engine serve [--stdio|--socket]`: the engine without a front end.
  Extract the truth out of the Textual widgets — `chat.messages`, undo, settings
  — so the widgets become a projection rather than the owner of state. This is
  the deep change in the Python tree, and it is what makes the old UI and the new
  one run side by side.
* Stable `message_id`/`call_id` assigned and persisted (see `UI-PROTOCOL.md`);
  backfill on load, `chats/*.json` format version bumped with a migration that
  leaves old files readable.
* `--print-events` and 5–10 recorded streams as fixtures; new
  `tests/unit/protocol/` suite: handshake, streaming, abort, chat switch, edit
  round-trip, client disconnect during a modal request, malformed input
  (unknown `t`, bad id, oversized line) → the engine answers `error` and lives.
* **Gate:** the whole app's behaviour reachable headlessly; a 30-line Python
  script can hold a conversation with the engine.

### M2 - `spit-tui` chat MVP (dogfood gate)

Virtualised message list, streaming with follow-bottom that **breaks on manual
scroll and re-arms on `End`**, input editor with history and bracketed paste,
keymap + status line, one theme, reasoning/tool blocks per the `~~~~~`
convention, clipboard (`y` on a code block). Screens: chat only; everything else
stays in Textual behind `--ui=textual`.
**Gate:** use it as the daily driver for a week. Measure per-frame cost and
input latency on the biggest real chat file on disk and write the numbers into
the commit message. Reject it here if it does not feel better — cheaply.

### M3 - Forms, then the settings screens die

Implement the `form` renderer (field types per `UI-PROTOCOL.md`) with
engine-side validation moved out of `manage/validation.py`, then port one screen
per commit: chat settings → endpoints → server/llama.cpp → downloads → manage
trees → modals. Delete each Textual twin in the same commit that lands its
replacement, so there is exactly one screen per concern at all times.
**Gate:** `--ui=textual` is reachable but nothing needs it.

### M4 - Assets and the remaining surfaces

Images (attachments, `asset.ready`), LaTeX on both graphics protocols, the side
panel, and — if wanted — a `term.*` terminal view backed by the tmux tools.
**Gate:** feature parity with Textual on the features the README advertises.

### M5 - Cut over

Remove Textual and `textual-image` from dependencies, delete `styles.css` and the
widget modules, move the render-model tests that were aimed at Textual stubs onto
the new model, rewrite the README's install section (Rust build or prebuilt
binary), update `PROJECT.md`/`CONVENTIONS.md`/`TESTING.md` ground truth, and
close the route entry in `TASKS-FINISHED.md` with the numbers.

## Prerequisite: the `terminal` tool

`TASKS-IN-PROGRESS` **P0b** must land before M2, and its enhancement list is
written with this migration in mind. Once the front end is a real binary in a
real pty, the `terminal` tool is the **only** harness that can see it: ratatui
has `TestBackend`/`assert_buffer!` for widget-level assertions in Rust, but the
end-to-end truth — does `spit-tui` start, stream, scroll, paste, and die cleanly
— is captured through tmux. That needs: launching argv (not hardcoded `bash`),
controlled `cols`/`rows` and resize, capture modes (plain / SGR attributes / raw
bytes, the last being how Kitty and Sixel get asserted at all), cursor as data,
`wait_for` instead of a blind `delay`, raw byte injection for mouse and bracketed
paste, diff captures, process state (`pane_pid`, exit code), chat-namespaced
window names, cancellable waits, guaranteed teardown, and structured output.
Do M2's acceptance testing without it and you are blind exactly where the
migration is riskiest.

## Test strategy across the seam

| layer | how | where |
|---|---|---|
| engine truth, protocol, streaming, abort | Python, recorded JSONL fixtures | `tests/unit/protocol/` |
| tool layer, sandbox, tmux backend | unchanged, already green | `tests/tools/*`, `tests/unit/sandbox/`, `tests/unit/terminal/` (P0b) |
| widgets: wrap, measure, viewport math, markdown → styled lines | `TestBackend` + `assert_buffer!`, no pty | `spit-tui/tests` |
| end-to-end: the real binary in a real pty | `terminal` tool / `tmux` + `capture-pane`, incl. `-e` for attributes and raw bytes for graphics | `spit-tui/tests/e2e`, driven from `run_tests.sh` |

The old suite's discipline transfers verbatim: distinctive tokens in assertions
(TRAPS #8), generated fixtures only (#10), byte-level terminator assertions
(#11), append-only test numbers (#15), and prove behaviour changes by
differential over every fixture rather than by a green suite (#18) — the
differential for M1 is "engine-driven Textual renders the same chat as
before, byte-identical `chats/*.json`".

## Packaging

Linux-only already, and the app already needs `libcairo2`, `bubblewrap`, `tmux`
and `playwright`, so a Rust front end is not the worst thing in the install
list. Ship: `cargo build --release` documented, prebuilt `x86_64` (and
`aarch64` if wanted) binaries on the release page, `spit.py` locating the binary
via `$SPIT_TUI` → `PATH` → `../spit-tui/target/release/spit-tui`, and a
**protocol version handshake** so an old binary against a new engine says so in
words instead of misbehaving. Textual remains an optional extra until M5.

## Risks

| risk | mitigation |
|---|---|
| Two toolchains, two test runners, a binary to distribute | Linux-only, one build command, prebuilt binaries; keep `--ui=textual` installable |
| Protocol churn: every UI need tempts a new field | `UI-PROTOCOL.md` is reviewed per change; additive → minor; a new field must name the client that needs it |
| Blocking the engine on a UI answer (`ui.request`) | every request is cancellable, timeout-able, and a disconnect means "no"; test it |
| Losing behaviour that is deliberate (`~~~~~` fences, `Running process…` lines, undo semantics, terminator handling in tools) | they are named as must-not-change in M0 gate 3 and re-verified at M2/M5; DECISIONS 59 and the P0 entry are the spec |
| Rust iteration slower than Python | keep the crate small and dumb; `cargo run` on the probes is seconds; the hot logic is measured, not guessed |
| ratatui API churn (0.30 is recent) | pin exact versions in `Cargo.lock`, isolate ratatui behind one module of ours |
| The gate is passed, then the work sags between M3 and M5 | one screen per commit, each leaving the app usable; the old UI is never deleted early |

## Fallback ladder (in order, each measured)

1. **Stay on Textual, cut the widget count.** Replace `Part(Markdown)` with our
   own line-based renderer: 4.6 s → 0.7 s per page-down at 1,000 messages
   (measured). About a day, keeps everything, and still scales with the total
   tree — a mitigation with a hard ceiling, not a fix.
2. **pyratatui, with our own input layer.** The numbers above are real and it is
   one process, but it delivers **no mouse events and a paste that destroys the
   line** (Enter arrives as `Ctrl+J`, and tui-textarea wipes the line on it),
   has no clipboard, no `Select`/`Input`/`Switch`, no syntax highlighting,
   markdown without tables or styled headings, and **no headless render target**
   (`Terminal()` takes no backend; a redirected stdout raises `BackendError`) —
   plus one maintainer, 52 commits, nothing since 2026-06-05, CI set to manual
   dispatch, and a `Table` constructor that does not exist at runtime. Owning
   mouse, paste and the test harness in Python to rescue it is most of option 3's
   work with the renderer still in the wrong process.
3. **ratatui here** (this route).
4. **urwid** — mature (4.0.2), LGPL-2.1, and it has the one primitive Textual
   lacks (`ListWalker`: lazy, discardable rows) plus real mouse and paste. A
   legitimate conservative answer if the two-toolchain cost is refused; same
   forms-as-data idea applies to its settings screens.
5. **Inline viewport, either way.** The front end can render into the terminal's
   own scrollback (`insert_before`) instead of the alternate screen, so finished
   history scrolls natively and costs nothing to keep. ratatui can; the Python
   binding cannot (its inline-viewport PR is open and unanswered).

## Ground rules for whoever executes this

Never `git pull`/`git push`; never work on `main`; `git branch -a` before naming
a branch; one concern per commit with `git commit -F file`; full suite before and
after, tool-suite counts unmoved; `dry_run` for destructive operations; the
sandbox stays on; read `TRAPS.md` before touching code and grep `DECISIONS.md`
before changing something that looks odd. If a milestone's gate fails, say so in
`TASKS-IN-PROGRESS.md` with the measurement and stop — a documented stop is a
result.
