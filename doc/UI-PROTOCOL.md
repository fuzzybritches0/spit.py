# UI-PROTOCOL.md - the engine ↔ front-end contract

Part of the spit.py documentation set (see `PROJECT.md`). This is the seam that
makes the front end replaceable: the **engine** (Python: chats, settings,
endpoints, llama.cpp server control, tool calling, the sandbox) talks to a
**front end** (first: ratatui; later: GTK4; always: a headless test client) over
one JSON protocol. Read `UI-ROUTE-RATATUI.md` for the plan and the gates.

The rule that decides every argument about this file: **the engine owns truth
and side effects; the front end owns the terminal and nothing else.** If the
front end is computing whether a message is complete, which tool call is
running, or what the history looks like after an edit, the protocol is wrong.

## Principles

1. **One protocol, many clients.** Ratatui now, GTK4 next, a headless client in
   the test suite always. Anything a front end needs that the protocol cannot
   express is a protocol bug, not a client problem.
2. **Deltas are a convenience, never the truth.** The engine's `messages` list
   is canonical; a client that misses a byte recovers by `resync.request`, not
   by guessing. **Drop frames, never text.**
3. **Raw text across the wire, styling on the screen.** Markdown, tool
   arguments and tool output travel as plain text. Spans, colours, fences,
   borders and syntax highlighting are the front end's business. This is the
   opposite of "ship styled spans" and it is what keeps the streaming path tiny.
4. **The model-facing text does not change.** `DECISIONS` 59's `~~~~~` fence
   language and the `Running process…` / `Process exited with code N.` lines in
   `run/run.py` stay exactly as they are in the LLM's message. They become
   *rendering* semantics for the client, not new wire content.
5. **Forms are data.** Settings screens travel as a schema, not as per-toolkit
   code (see *Forms*). This is the single biggest lever for the GTK4 goal.
6. **The engine must survive a hostile or stupid client**: unknown message type,
   bad id, oversized line → `error`, never a crash. Pinned by tests.

## Transport

* **Default:** the client spawns `spit.py --engine serve` and speaks JSONL on
  its stdin/stdout. Simple, no ports, one process tree, engine dies with the UI.
* **Also supported:** a Unix socket at `$XDG_RUNTIME_DIR/spit/engine.sock` for
  clients that attach and detach (a GUI that opens a window per chat, the test
  client). Same JSONL framing, one object per line.
* Framing: UTF-8, **one JSON object per line**, no raw newlines (escaped),
  length cap 1 MiB per line; over-cap is refused with `error{code:"too_big"}`,
  and binary payloads never travel in the stream — they go by path (*Assets*).
* No client may assume the transport is a pipe, a socket, synchronous, or
  ordered faster than a frame. No engine may assume the client is a terminal.

## Handshake

```jsonc
→ {"t":"hello","proto":[1,0],"client":"spit-tui","caps":["view.portfolio","graphics.protocol","mouse","paste.bracketed","resize","forms.v1"]}
← {"t":"hello.ok","proto":1,"engine":"0.2","caps":["server.manage","tool.image","assets.latex","forms.v1"],"ids":{"chats":["c1","c2"],"active":"c1"}}
```

* `proto` is `[major, minor]`; the engine fails the handshake on an unusable
  major with a message that says what to upgrade.
* `caps` is how a client says what it can do — GTK4 will not claim
  `graphics.protocol`; the headless client claims nothing. **The engine adapts
  behaviour, never truth, to capabilities** (e.g. no `assets.latex` → send the
  LaTeX source as text, which is what `latex.py` already falls back to).
* Every message carries `"t"` (type). Unknown `t` → `error{code:"unknown_type"}`;
  types prefixed `x_` are ignore-and-log extensions, so a newer client can talk
  to an older engine.

## Identifiers

The current JSON chat files address messages by **list index**, which is not
stable across edit/delete/insert — and the whole UI currently passes indices
around. The protocol needs stable ids, assigned by the engine and persisted:

| id | scope | assigned |
|---|---|---|
| `chat_id` | a conversation | already exists |
| `message_id` (`m<N>`) | one message, survives edits and neighbours being removed | engine, backfilled on load |
| `part` | `reasoning` \| `content` \| `tool_calls` | fixed enum, additive only |
| `call_id` (`t<N>`) | one tool call inside `tool_calls` | engine |
| `req_id` | one `ui.request` awaiting a reply | engine |
| `seq` | per `(message_id, part)`, monotonic | engine |

A `seq` gap is how a client notices it fell behind; that triggers resync.

## Engine → front end

```jsonc
{"t":"state.snapshot","chat_id":"c1","messages":[
  {"id":"m7","role":"assistant","parts":[
    {"kind":"reasoning","text":"…","done":false},
    {"kind":"content","text":"# Hello\n\n**bold**","done":true},
    {"kind":"tool_calls","calls":[{"call_id":"t3","name":"terminal",
        "arguments":"{\"name\":\"build\"}","state":"running"}]}]},
 {"id":"m8","role":"user","parts":[{"kind":"content","text":"hi","done":true}],
  "attachments":[{"asset_id":"a1","mime":"image/png","path":"/…/a1.png"}]}]}

{"t":"message.append","chat_id":"c1","message_id":"m9","role":"assistant"}
{"t":"part.delta","message_id":"m9","part":"content","seq":41,"text":" the model"}
{"t":"part.done","message_id":"m9","part":"content","seq":57}
{"t":"message.replace","message_id":"m7","parts":[…]}      // after an edit/undo
{"t":"message.remove","message_id":"m9"}
{"t":"busy","chat_id":"c1","working":true}                 // drives the Abort key
{"t":"tool.begin","message_id":"m9","call_id":"t4","name":"run_command"}
{"t":"tool.end","message_id":"m9","call_id":"t4","ok":true}
{"t":"asset.ready","asset_id":"a2","mime":"image/png","path":"/…/a2.png",
 "px":[820,260],"hint":{"cells_h":8},"source":"\\int_0^1 x\\,dx"}            // LaTeX keeps its source for copy
{"t":"chats.changed","chats":[{"id":"c1","title":"…","active":true}]}
{"t":"server.state","running":false,"slot":"0","model":null,"log_tail":["…"]}
{"t":"ui.request","req_id":"r1","kind":"choose_image","spec":{"accept":["image/*"]}}
{"t":"stream.aborted","chat_id":"c1","message_id":"m9"}
{"t":"stream.error","chat_id":"c1","message_id":"m9","code":"endpoint_unreachable","message":"…"}
{"t":"result","id":"c-17","ok":true,"data":{}}
{"t":"error","id":"c-17","code":"not_found","message":"no such message_id"}
```

**Content parts are `reasoning | content | tool_calls`, plus `image` as an
attachment, not a part.** `tool_calls` travels structured (name, raw arguments
string, state) so the client can draw the argument block, the `~~~~~` fences,
and the "running" state without parsing anything. The raw `arguments` string is
exactly the string the model receives — do not reformat it en route.

## Front end → engine

Every command has a client-chosen `id`; the answer is `result` or `error`, and
commands are idempotent where that is cheap (setting a value twice is fine).

```jsonc
{"id":"c-1","t":"message.send","chat_id":"c1","text":"hello","attachments":["a1"]}
{"id":"c-2","t":"stream.abort","chat_id":"c1"}
{"id":"c-3","t":"message.edit","chat_id":"c1","message_id":"m7","text":"…"}
{"id":"c-4","t":"message.delete","chat_id":"c1","message_id":"m7"}
{"id":"c-5","t":"undo","chat_id":"c1"}    {"t":"redo"}
{"id":"c-6","t":"chat.create"}  {"t":"chat.open","chat_id":"c2"}  {"t":"chat.rename"}  {"t":"chat.delete"}
{"id":"c-7","t":"chat.settings.set","chat_id":"c1","key":"system_prompt","value":"…"}
{"id":"c-8","t":"form.get","scope":{"tool":"run_command"}}     // → {"t":"form","fields":[…]}
{"id":"c-9","t":"form.set","scope":{"tool":"run_command"},"values":{"sandbox":true}}
{"id":"c-10","t":"endpoint.add"|"endpoint.update"|"endpoint.delete"|"endpoint.use"}
{"id":"c-11","t":"server.start"|"server.stop"|"server.status"}
{"id":"c-12","t":"asset.put","mime":"image/png","path":"/…pick.png"}    // → asset_id
{"id":"c-13","t":"ui.reply","req_id":"r1","result":{"path":"/…"}}        // or {"cancel":true}
{"id":"c-14","t":"resync.request","reason":"seq_gap"}                    // → fresh state.snapshot
{"id":"c-15","t":"ping","mono":1234.5}                                   // → {"t":"pong",…}
```

Namespace reserved for later: `term.*` (surfacing the tmux terminal tool in the
UI), `model.*` (download/quantise), `x_*` (experimental).

## Streaming, ordering, backpressure

* One `part.delta` per chunk would be one message per token. The engine
  **coalesces at the frame rate the client asked for** (`hello.caps` →
  default 30 Hz) and caps in-flight bytes at ~256 KB per chat. When the client
  is slower, the engine keeps buffering (it is the truth) and the client
  resyncs; the engine never drops text to keep the pipe moving.
* `seq` is per `(message_id, part)` and strictly increasing. A client seeing a
  jump sends `resync.request` and repaints from the snapshot. The client is
  allowed to coalesce multiple deltas into one repaint — and must, or a long
  reply becomes a per-token relayout.
* `part.done` always arrives (also on abort and error) so a client can close the
  fence it opened; DECISIONS 59's parity argument depends on "every open gets a
  close", which the protocol guarantees instead of leaving to the formatter.
* `busy` brackets a working stream so the front end's Abort key can be
  enabled/disabled without inspecting message internals.
* A dead client must not wedge the engine: writes that fail end the stream
  (SIGPIPE-safe), and the engine keeps the chat consistent on disk.

## The five sharp edges (design these before any rendering code)

1. **Abort mid-stream.** `stream.abort` maps to today's
   `Chat.action_abort` / `exit_after_busy` + `kill_process_group` (see
   `RUNTIME-RUN-COMMAND.md`). Semantics to pin: the partial message **is
   committed as it stands**, `part.done` fires, `stream.aborted` fires, and any
   in-flight tool gets its process group killed. A client that is closed while
   streaming does not abort the stream unless it says so (`hello.caps:
   "abort_on_detach"`), so a GUI can close a window and reopen the chat to a
   finished reply.
2. **Switching chats while streaming.** Streams are not bound to the view.
   Every event carries `chat_id`; the client paints the active one and keeps
   receiving the others (badge/`busy` state per chat). `chat.open` is a pure
   view change plus a `state.snapshot` for that chat. This is what makes the
   GTK4 "one window per chat" idea cost nothing later.
3. **Edit and undo round-trip.** The client asks (`message.edit`), the engine
   mutates and answers with `message.replace` + `result`; the client never
   mutates its own copy first. Undo/redo stay in the engine (it owns
   `chat/undo.py`), so undo works across clients and after a restart. If the
   edit lands on a message whose parts are still streaming, the engine refuses
   with `code:"busy"`.
4. **Engine asks the UI for something** (`ui.request`): image picker,
   confirmation, progress, error screen. It is a request with a `req_id` and a
   `spec`, and the engine treats `ui.reply{cancel:true}` — *and a client
   disconnect* — as "the user said no". Today this is `push_screen_wait`, which
   only works because both sides share a process; across the seam it must be an
   explicit, cancellable, timeout-able request or a modal becomes a deadlock.
5. **Resize.** A terminal resize is a client problem (re-wrap, re-measure) and
   must not ping the engine at all; the GTK4 client has no such event. So
   geometry never crosses the protocol. The engine's only interest in layout is
   the `cells_h` hint on assets, which is advisory.

## Forms: why the settings screens become data

`manage/`, `llamacpp/`, `download/`, `chat_settings.py` and the modals are
~1,600 lines of hand-built Textual forms — the largest single cost in the
migration, and it would have to be written **twice** for two toolkits. Instead
the engine describes each screen and the client renders it:

```jsonc
← {"t":"form","fields":[
  {"key":"model","label":"Model file","type":"path","value":"…","path_kind":"file"},
  {"key":"ctx","label":"Context size","type":"int","value":4096,"min":256,"max":131072},
  {"key":"endpoint","label":"Endpoint","type":"select","value":"0",
   "choices":[{"value":"0","label":"local server"},{"value":"c1","label":"OpenAI"}]},
  {"key":"sandbox","label":"Run in sandbox","type":"bool","value":true,
   "warn":"DANGER: Do not deactivate!"},
  {"key":"interpreters","label":"Allowed interpreters","type":"text","value":"bash, python3, perl","empty":false},
  {"key":"kv","label":"Headers","type":"kvlist","value":{"X-Key":"…"}}]}
→ {"id":"c-8","t":"form.set","scope":{"tool":"run_command"},"values":{"sandbox":true}}
```

Field types: `text multiline int float bool path select multiselect kvlist
list buttons` — enough for every screen in the app today, small enough to
implement once per toolkit, and each type has engine-side validation so a
client cannot write a broken settings file (the existing `manage/validation.py`
becomes server-side truth, tested in the existing Python style).

This is also what turns "port the settings screens" from two rewrites into one:
`M2` renders this schema in ratatui, and GTK4 gets the same screens for free.

## Assets

Images and LaTeX PNGs never travel as base64. The engine writes
`$XDG_CACHE_HOME/spit/assets/<sha1>.png` and sends `asset.ready` with the path,
pixel size and a cell hint. The client picks its own presentation (Kitty
graphics, Sixel, iTerm2, half-blocks, or "file saved at …"). LaTeX events carry
`source`, because the `y`-copies-the-LaTeX binding needs the original text, not
the rendered image. Attachments are `asset.put` → `asset_id`, so the picker UI
stays in the client and the engine only ever sees a path it can read.

## Versioning and fixtures

* Additive change → minor. Renamed or removed field, new required field, or
  changed semantics → major, and the handshake fails loudly.
* `spit.py --engine serve --print-events` writes the event stream to stdout as
  JSONL so a run can be recorded. **Recorded streams are the test fixtures**:
  `tests/unit/protocol/` (Python) asserts the engine emits what it should, and
  the Rust front end replays the same files against a headless client — which
  is how both sides get tested without a terminal, and the reason the protocol
  doc has to be written first.

## Explicit non-decisions

* Not a web API, not gRPC, no protobuf: JSONL over a pipe is debuggable with
  `tee`, which matters for a project whose debugging tool is `log.txt`.
* No plugin system, no remote engine, no auth. Single user, local process, and
  the sandbox in `run/` stays the security boundary.
* The engine does not choose a front end and does not care how many there are.
