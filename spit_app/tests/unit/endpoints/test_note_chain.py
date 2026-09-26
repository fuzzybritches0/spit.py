#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t13 - the P13/WP-D wiring, end to end: a real headless `Chat` builds the
token-status hook and a `SystemNotes`, `Chat.context_window()` answers over
`ChatSettings.context_sizes[context_key()]`, `Work.work_stream()` calls
`attach()` immediately before `endpoint.stream()`, and what the hook says
lands on the wire of the NEXT request - driven over the canned server, which
records every POST body.

Numbers are append-only across the whole suite (TRAPS #15): this file owns t13.
t1/t5/t8/t9 are in test_payload.py, t2/t3/t4 in test_stream_parse.py, t6/t7 in
test_requests.py, t10 in test_harvest_usage.py, t11 in test_counts_row.py, t12
in test_system_note.py; harness names are imported, never redefined.

WHAT IS PROVEN HERE AND WHERE
  * under threshold => no note in the POST body, with the control of the same
    chat over 50% carrying exactly one (TRAPS #13);
  * the note is the hook's own text byte-for-byte, a `user` item in the right
    position - right after the message that carried it - via WP-A's unpacking
    (t12 pinned the helper; here it is the whole chain: hook -> generator ->
    stored dict -> prepare_payload -> recorded request body);
  * a second request at the same level adds none, and the one thing that
    separates "asked and silent" from "never asked" is the control that raises
    the level and gets a second note out of the SAME code path;
  * the rank machine on the wire: back at the lower level nothing re-announces
    (never downgrades, never repeats);
  * the `chat.messages` list the UI holds never gains an item - it grows by
    exactly the streamed replies and nothing else; notes live under the private
    key inside the dicts (P13's whole constraint, on the wired path);
  * on a `user` carrier the note is MERGED: the request's message COUNT is the
    same with the note as without it (hazard 1's rule proven on the wire, not
    only in the helper as t12 did);
  * `context_window()` answers the int when the pair is known and None when it
    is not, and an unknown window means SILENCE - with the control of filling
    the same chat's cache and watching the note appear; and no window probe (no
    network) happens on the request path: the accessor reads, it does not ask;
  * the hook is registered ONCE, in the module `HOOKS` list, at chat.py import
    (the WP-D decision, argued in the close-out): importing `chat` registers it
    for every chat, a second chat does not register a second copy, and the
    generator is per-chat while the hook instance is shared (it keeps no state
    about WHICH chat - its memory is its own standing notes).

THE FIXTURES ARE LOADED, NOT GUESSED (TRAPS #13): the canned scenario is
"content" - a text reply with NO usage chunk - so `harvest_usage()` leaves the
counts alone and every fill below is exactly the figure set. The window is
filled into `ChatSettings.context_sizes` after the mount's own probe has cached
its answer (the canned scenario answers 404, so it caches None - which is also
the unknown-window fixture the accessor group needs).

TRAPS #8 (`mm-*` tokens everywhere), #13 (a control beside every absence), #15
(t13 is a new number), #18 (every group runs inside `guarded()`; the row a
runner reads is a floor), #19 (this file needs the venv: it mounts a real Chat
and a real Work - unlike unit:system_note, which must never import any of it).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from endpoint_harness import (CannedServer, check, guarded,  # noqa: E402
                              saved_endpoint, summary)
import endpoint_harness as harness  # noqa: E402

from counts_harness import StubEndpointApp, fixture_chat, settle  # noqa: E402
from smoke_scenario import fixture_settings  # noqa: E402 (via counts_harness's path)

from spit_app.chat.system_note import HOOKS, hook_name  # noqa: E402
from spit_app.chat.token_status import TEXT_INFO, TEXT_WARNING, TokenStatus  # noqa: E402
import spit_app.chat.chat as chat_mod  # noqa: E402  (the import that registers the hook)
from spit_app.chat.work import Work  # noqa: E402

# The window and the fills. 200000 is percentage territory (no small-window
# note, no remaining-token floor): info at >= 100000, warning at >= 160000, so
# 120000 is 60% -> info and 170000 is 85% -> warning, all governed by the
# percentages, none by a floor (WP-C's table, on the wire now).
WINDOW = 200000
FILL_INFO = 120000
FILL_WARNING = 170000

NOTE_INFO = TEXT_INFO.format(used=FILL_INFO, total=WINDOW,
                             remaining=WINDOW - FILL_INFO, pct=60)
NOTE_WARNING = TEXT_WARNING.format(used=FILL_WARNING, total=WINDOW,
                                   remaining=WINDOW - FILL_WARNING, pct=85)

# The four texts open distinctly (WP-C's pin); a hit on any of them is a note.
MARKERS = ("Token status:", "Token warning:", "Critical:",
           "This chat's context window is only")


class ChainApp(StubEndpointApp):
    """StubEndpointApp plus the two attributes a real `Work` asks the app for
    and the smoke stub does not carry: `slots` (ManageCache's bookkeeping dict)
    and `path`. Nothing else: this is the same stub app t11 mounts."""

    def __init__(self, content: dict, endpoints: dict) -> None:
        super().__init__(content, endpoints)
        self.slots = {}
        self.path = "/tmp/mm-chain-not-used"


def make_app(server, content=None) -> ChainApp:
    return ChainApp(chain_content() if content is None else content,
                    {"1": saved_endpoint(f"{server.base}/content/v1")})


def chain_content() -> dict:
    # The smoke fixture: user, assistant, user, assistant(tool_calls), tool -
    # a tool run whose replies are complete, so the tail is noteable and the
    # first line of work_stream() takes the no-pending-tools branch.
    return fixture_chat()


def user_tail_content() -> dict:
    """A chat whose tail is a USER message - the carrier of the merge rule."""
    return {"ctime": "2026-01-01T00:00:00", "settings": fixture_settings(),
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "mm-user-first"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "mm-answer-one"}]},
                {"role": "user", "content": [{"type": "text", "text": "mm-user-latest"}]},
            ]}


async def wait_for_probe_cached(app, pilot):
    """Let the mount's own probe file its answer (None here - the canned
    scenario 404s both routes) BEFORE the test overwrites the cache, so no
    late probe can clobber the window the test sets."""
    settings = app.chat.chat_settings
    key = settings.context_key()
    for _ in range(100):
        if key in settings.context_sizes:
            return settings
        await pilot.pause()
    return settings


def set_window(app, size) -> None:
    settings = app.chat.chat_settings
    settings.context_sizes[settings.context_key()] = size


def set_fill(app, used) -> None:
    app.chat.token_usage["context"] = used


async def one_request(app, pilot) -> None:
    """One real send: a real `Work` (built per send, exactly as the UI does it)
    running its real `work_stream()` - which is the ONLY place attach() lives.
    The scenario has no usage chunk, so harvest_usage leaves the fill alone."""
    work = Work(app.chat)
    await work.work_stream()
    await settle(pilot)


def last_wire(server) -> list:
    return server.bodies[-1]["messages"]


def wire_roles(wire) -> list:
    return [m["role"] for m in wire]


def note_items(wire) -> list:
    """Wire items that ARE a note: their own `user` item whose whole content is
    a note text. (A merged note is not one - it lives inside its carrier.)"""
    return [m for m in wire if isinstance(m.get("content"), str)
            and any(marker in m["content"] for marker in MARKERS)]


def marker_hits(obj) -> int:
    return sum(json.dumps(obj, ensure_ascii=False).count(m) for m in MARKERS)


def window_gets(server) -> list:
    """Recorded GETs that are window probes - /props and /slots. The model
    refresh (/models, its worker looping on an empty answer) is not a window
    probe and is excluded."""
    return [g for g in server.gets()
            if ("/props" in g or "/slots" in g) and not g.endswith("/models")]


async def t13_chain():
    """The whole chain over the tool-tailed fixture: silence under threshold
    (with the over-threshold control), the note on the wire byte-for-byte in
    the right position, the same level adding none (with the higher-level
    control), never downgrading, and the UI's list growing by replies only."""
    app = None
    server = SERVER
    async with app_ctx(server) as (app, pilot):
        chat = app.chat
        original_ids = [id(m) for m in chat.messages]

        # -- the accessor: None while nothing is known, the int once it is.
        check("t13-accessor-answers-none-when-the-pair-is-unknown",
              chat.context_window(), None)
        settings = await wait_for_probe_cached(app, pilot)
        settings.context_sizes[settings.context_key()] = WINDOW
        check("t13-accessor-answers-the-known-int", chat.context_window(), WINDOW)

        # -- under threshold: silence, and the request lives.
        server.reset()
        set_fill(app, 0)
        await one_request(app, pilot)
        wire = last_wire(server)
        check("t13-under-threshold-no-note-on-the-wire", len(note_items(wire)), 0)
        check("t13-under-threshold-wire-is-just-the-conversation",
              wire_roles(wire), ["user", "assistant", "user", "assistant", "tool"])
        check("t13-under-threshold-no-private-key-reaches-the-wire",
              any("system" in m for m in wire), False)
        check("t13-under-threshold-no-private-key-written-in-the-app-list",
              any("system" in m for m in chat.messages), False)
        check("t13-request-path-starts-no-window-probe", window_gets(server), [])
        check("t13-one-send-is-exactly-one-post", len(server.posts()), 1)
        check("t13-under-threshold-reply-appended", len(chat.messages), 6)

        # CONTROL (TRAPS #13): the same chat, the same code path, 60% -> the
        # very next POST body carries exactly one note. Without this every
        # silence above would be about a chain that never spoke at all.
        server.reset()
        set_fill(app, FILL_INFO)
        await one_request(app, pilot)
        wire = last_wire(server)
        check("t13-CONTROL-over-50-percent-the-wire-carries-exactly-one-note",
              len(note_items(wire)), 1)
        check("t13-note-is-its-own-user-item-immediately-after-the-carrier",
              (wire[-1], wire[-2]["role"]),
              ({"role": "user", "content": NOTE_INFO}, "assistant"))
        check("t13-note-item-carries-role-and-content-only",
              sorted(wire[-1]), ["content", "role"])
        check("t13-no-consecutive-user-pair-with-the-note",
              any(a == "user" and b == "user"
                  for a, b in zip(wire_roles(wire), wire_roles(wire)[1:])), False)
        check("t13-note-stands-in-the-carrier-dict-under-the-private-key",
              chat.messages[5]["system"],
              [{"hook": "token_status", "level": "info", "text": NOTE_INFO}])
        check("t13-the-list-grows-by-the-reply-only", len(chat.messages), 7)

        # same level again: asked and silent - no second note anywhere.
        server.reset()
        await one_request(app, pilot)
        wire = last_wire(server)
        check("t13-same-level-second-request-adds-none", len(note_items(wire)), 1)
        check("t13-the-old-note-still-rides-in-its-own-history-position",
              wire[6], {"role": "user", "content": NOTE_INFO})
        check("t13-second-request-still-exactly-one-post", len(server.posts()), 1)

        # CONTROL for the silence above: the same walk DOES speak again when
        # the level outranks what stands - so "adds none" means "asked, and
        # nothing new to say", not "attach never ran".
        server.reset()
        set_fill(app, FILL_WARNING)
        await one_request(app, pilot)
        wire = last_wire(server)
        check("t13-CONTROL-higher-level-speaks-again-two-notes-on-the-wire",
              len(note_items(wire)), 2)
        check("t13-warning-note-lands-after-the-newest-tail",
              (wire[-1], wire[-2]["role"]),
              ({"role": "user", "content": NOTE_WARNING}, "assistant"))
        check("t13-warning-text-is-the-pinned-text-at-exact-figures",
              wire[-1]["content"], NOTE_WARNING)

        # back at the lower level: never downgrades, never re-announces info.
        server.reset()
        set_fill(app, FILL_INFO)
        await one_request(app, pilot)
        wire = last_wire(server)
        check("t13-back-at-the-same-level-adds-none", len(note_items(wire)), 2)
        check("t13-info-is-never-announced-twice",
              sum(m["content"] == NOTE_INFO for m in note_items(wire)), 1)

        # -- the UI's index space: same five dicts in front, still THE SAME
        # LIST the ChatView projects, and no note ever became an item.
        check("t13-the-first-five-dicts-are-untouched-identities",
              [id(m) for m in chat.messages[:5]], original_ids)
        check("t13-no-note-ever-became-a-message",
              any(isinstance(m.get("content"), str)
                  and any(k in m["content"] for k in MARKERS)
                  for m in chat.messages), False)
        check("t13-the-view-still-projects-the-same-list",
              chat.chat_view.messages is chat.messages, True)


async def t13_user_carrier_merge():
    """Hazard 1 on the wire: with a `user` tail the note is MERGED, so the
    request's message COUNT is the same with the note as without it - and the
    text is inside the carrier's own content, not a second consecutive `user`."""
    async with app_ctx(SERVER, user_tail_content()) as (app, pilot):
        await wait_for_probe_cached(app, pilot)
        set_window(app, WINDOW)
        set_fill(app, FILL_INFO)
        await one_request(app, pilot)
        wire = last_wire(SERVER)
        check("t13-user-carrier-the-wire-grows-by-no-item",
              len(wire), 3)
        check("t13-user-carrier-roles-unchanged",
              wire_roles(wire), ["user", "assistant", "user"])
        check("t13-user-carrier-no-standalone-note-item",
              any(m == {"role": "user", "content": NOTE_INFO} for m in wire), False)
        check("t13-user-carrier-note-merged-into-the-carriers-content",
              wire[2]["content"],
              [{"type": "text", "text": f"mm-user-latest\n\n{NOTE_INFO}"}])
        check("t13-user-carrier-control-the-note-text-IS-on-the-wire",
              marker_hits(wire), 1)
        check("t13-user-carrier-no-consecutive-user-pair",
              any(a == "user" and b == "user"
                  for a, b in zip(wire_roles(wire), wire_roles(wire)[1:])), False)
        check("t13-user-carrier-wire-carrier-carries-role-and-content-only",
              sorted(wire[2]), ["content", "role"])
        # and the app keeps its own copy separate.
        chat = app.chat
        check("t13-user-carrier-app-dict-keeps-its-own-content",
              chat.messages[2]["content"],
              [{"type": "text", "text": "mm-user-latest"}])
        check("t13-user-carrier-app-dict-keeps-the-note-entry",
              chat.messages[2]["system"],
              [{"hook": "token_status", "level": "info", "text": NOTE_INFO}])
        check("t13-user-carrier-list-grows-by-the-reply-only",
              len(chat.messages), 4)


async def t13_unknown_window():
    """The dash on the request path: window unknown => the hook is silent even
    over threshold and the request lives; fill the same chat's cache (no
    probe, no network) and the note appears - the accessor is the hook's door.
    """
    async with app_ctx(SERVER) as (app, pilot):
        chat = app.chat
        await wait_for_probe_cached(app, pilot)   # the mount's probe answered None
        check("t13-unknown-window-accessor-answers-none", chat.context_window(), None)
        SERVER.reset()
        set_fill(app, FILL_INFO)                  # over 50%, but no denominator
        await one_request(app, pilot)
        wire = last_wire(SERVER)
        check("t13-unknown-window-silence-even-over-threshold",
              len(note_items(wire)), 0)
        check("t13-unknown-window-the-request-lives", len(chat.messages), 6)
        check("t13-unknown-window-costs-no-extra-post", len(SERVER.posts()), 1)

        # CONTROL: the same chat, the same fill, a window now - speaks.
        SERVER.reset()
        set_window(app, WINDOW)
        await one_request(app, pilot)
        wire = last_wire(SERVER)
        check("t13-CONTROL-filling-the-window-speaks-at-once",
              len(note_items(wire)), 1)
        check("t13-filling-the-cache-starts-no-probe", window_gets(SERVER), [])


async def t13_registration():
    """The WP-D registration decision, pinned: the module `HOOKS` list, once,
    at chat.py import - not one registration per chat. The generator is
    per-chat (it is bound to its chat); the hook instance is shared, because
    it keeps no state about WHICH chat (its memory is its own standing notes,
    WP-C) - so a second chat must not, and does not, register a second copy."""
    check("t13-hooks-list-carries-the-token-status-hook",
          [hook_name(h) for h in HOOKS], ["token_status"])
    check("t13-registered-instance-is-a-token-status",
          isinstance(HOOKS[0], TokenStatus), True)
    async with app_ctx(SERVER) as (app_one, _pilot):
        chat_one = app_one.chat
    # a second chat, after the first is gone: one entry, not two.
    async with app_ctx(SERVER) as (app_two, _pilot):
        chat_two = app_two.chat
    check("t13-a-second-chat-registers-no-second-hook",
          [hook_name(h) for h in HOOKS], ["token_status"])
    check("t13-every-chat-carries-the-one-registered-instance",
          (chat_one.token_status is chat_two.token_status is HOOKS[0]), True)
    check("t13-the-generator-is-per-chat",
          chat_one.system_notes is not chat_two.system_notes, True)
    check("t13-the-generator-is-bound-to-its-chat",
          chat_two.system_notes.chat is chat_two, True)


class app_ctx:
    """`async with app_ctx(server) as (chat_app, pilot)` - a fresh ChainApp
    mounted on the shared canned server."""

    def __init__(self, server, content=None) -> None:
        self.server = server
        self.content = content
        self.app = None
        self.ctx = None

    async def __aenter__(self):
        self.app = make_app(self.server, self.content)
        self.ctx = self.app.run_test()
        pilot = await self.ctx.__aenter__()
        await settle(pilot)
        return self.app, pilot

    async def __aexit__(self, *exc):
        result = await self.ctx.__aexit__(*exc)
        self.app = None
        return result


def describe() -> str:
    return ("INPUT MAPPING (TRAPS #13): window " + str(WINDOW) + " (percentage "
            "territory, no floors, no small-window note); fills 0 / "
            + str(FILL_INFO) + " (60% -> info) / " + str(FILL_WARNING)
            + " (85% -> warning); canned scenario `content` (a text reply, NO "
            "usage chunk, so harvest_usage never moves a fill); every absence "
            "above has the control that puts a note in the same body. The wire "
            "is read from the canned server's RECORDED POST bodies.")


SERVER = None


def main():
    global SERVER
    print(describe())
    SERVER = CannedServer().start()
    try:
        guarded("t13-chain", lambda: run(t13_chain))
        guarded("t13-merge", lambda: run(t13_user_carrier_merge))
        guarded("t13-unknown-window", lambda: run(t13_unknown_window))
        guarded("t13-registration", lambda: run(t13_registration))
    finally:
        SERVER.stop()
    summary()
    return 1 if harness.fail_ else 0


def run(coroutine_fn):
    import asyncio
    asyncio.run(coroutine_fn())


if __name__ == "__main__":
    sys.exit(main())
