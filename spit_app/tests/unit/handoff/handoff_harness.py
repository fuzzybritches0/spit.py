# SPDX-License-Identifier: GPL-2.0
"""Shared harness for unit:handoff (imported by the test_*.py files; the
runner's `test_*.py` glob must not match this name - the `endpoint_harness.py`
precedent: a harness inside the glob becomes a check file of its own).

unit:handoff is the SIXTH dependency-listed suite (TRAPS #19): the code under
test is an in-process Textual tool - `spit_app/tools/handoff.py` imports
`Chat`, and the wiring drives `ToolCall`, which loads the whole tool tree.
The gate in run_tests.sh probes `textual, httpx, libtmux, ddgs, playwright` -
what THAT tree imports, not what these files happen to import.

WHAT IS DRIVEN FOR REAL, and why the seams are where they are
  The whole point of P14 is the hand between three live pieces - the tool,
  the Chat/submit/Work machinery, the sidebar - so the suite drives all three
  for real: the real `Chat` widget (with its `ChatView`, window, undo, stream
  callbacks), the real `SidePanel` OptionList, the real `Work`, the real
  `ToolCall` dispatcher loading the real `handoff` module. The ONLY stubbed
  things are what a headless box cannot have:
    * the llama.cpp server - replaced by the canned stdlib server below, on
      127.0.0.1 port 0, replying canned SSE per marker (see CANNED BEHAVIOUR);
    * the local-server path (`app.server`) - `is_running()` answers False, and
      the chat's endpoint is "7", so `Work.local_server_active()` short-circuits
      and the prompt-cache slots are never touched;
    * the settings home - `StubSettings.path` points at ./fixtures/handoff-data
      (generated, removed after the run, KEEP_FIXTURES=1 keeps; nothing lives
      outside ./fixtures/).
  `read_json`/`write_json` are the real app's file mapping (path[0] through
  self.path) over that fixture dir - the chat files the tool writes are real
  files on disk, which is also what `SidePanel.option_list()` reads.

THE DETERMINISM CHOICES (each one is a hazard the entry names)
  * GET  /models answers the one model instantly - a ChatSettings
    `update_models` worker runs on EVERY chat mount and loops 60 x 10 s on an
    empty answer.
  * GET  /props and /slots answer 404 - unknown window => the token-status
    hook is silent (DECISIONS 80 b/81) => every POST this suite asserts on is
    note-free, no matter what the usage numbers become.
  * The POST reply is chosen by MARKER in the request body, so two chats on
    one server are distinguishable by their own content, not by ports.
"""
import asyncio
import json
import os
import re
import shutil
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_HERE, *[".."] * 4))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from spit_app.chat.chat import Chat                # noqa: E402  (driven for real)
from spit_app.side_panel import SidePanel          # noqa: E402  (driven for real)
from spit_app.tool_call import ToolCall            # noqa: E402  (driven for real)

APP_SIZE = (80, 24)
OLD_ID = "chat-mm-handoff-old"
MODEL = "mm-handoff-model"
START_TEXT = "mm-handoff-start-work"
HANDOFF_TEXT = "MM-HANDOFF-MSG continue the work in the new chat"
REPLY_TEXT = "mm-handoff-reply-one"

FIXTURES = Path(_HERE) / "fixtures"
DATA = FIXTURES / "handoff-data"

# ------------------------------------------------------------------ the counters
pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def guarded(group: str, fn) -> None:
    """Run one check group; a crash is ONE red, never a file that dies mid-run
    and reports only the checks that happened to come first (TESTING.md)."""
    try:
        fn()
    except Exception as exception:  # noqa: BLE001 - that is the whole point
        traceback.print_exc()
        check(f"{group}-did-not-crash", f"{type(exception).__name__}: {exception}", "None")


def summary() -> None:
    print()
    print(f"PASS: {pass_}  FAIL: {fail_}")


# ------------------------------------------------------------------ SSE builders
def sse(*chunks) -> bytes:
    return ("".join("data: " + json.dumps(one) + "\n\n" for one in chunks)
            + "data: [DONE]\n\n").encode()


def text_chunk(text: str) -> dict:
    return {"choices": [{"delta": {"content": text}}]}


def tool_chunk(index: int, call_id: str, name: str, arguments: str) -> dict:
    return {"choices": [{"delta": {"tool_calls": [
        {"index": index, "id": call_id, "type": "function",
         "function": {"name": name, "arguments": arguments}}]}}]}


FINISH_CHUNK = {"choices": [{"delta": {}, "finish_reason": "stop"}]}


# ----------------------------------------------------------------- canned server
class CannedServer:
    """127.0.0.1, port 0, daemon thread; records every POST body.

    CANNED BEHAVIOUR: a POST whose body contains `tool_marker` while
    `reply_mode == "tool"` is answered with an assistant turn carrying
    `self.tool_calls` (a list of (id, name, arguments-json)); every other POST
    is answered with one content delta of `reply_text`. The first chat request
    of the work-loop case contains START_TEXT and gets the tool call; the new
    chat's request contains HANDOFF_TEXT (not START_TEXT) and gets the plain
    reply. /models answers the single model; /props and /slots 404 (the
    determinism choice in the module docstring).
    """

    def __init__(self) -> None:
        self.bodies = []
        self.gets = []
        self.reply_mode = "plain"
        self.tool_calls = []
        self.tool_marker = START_TEXT
        self.reply_text = REPLY_TEXT
        self._server = HTTPServer(("127.0.0.1", 0), self._handler())
        self.port = self._server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> "CannedServer":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def bodies_with(self, marker: str) -> list:
        return [body for body in self.bodies if marker in json.dumps(body)]

    def _reply(self, body: dict) -> tuple:
        if self.reply_mode == "tool" and self.tool_marker in json.dumps(body):
            chunks = [tool_chunk(i, call_id, name, arguments)
                      for i, (call_id, name, arguments) in enumerate(self.tool_calls)]
            return (200, sse(*chunks, FINISH_CHUNK), "text/event-stream")
        return (200, sse(text_chunk(self.reply_text)), "text/event-stream")

    def _handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args) -> None:
                pass

            def _send(self, code: int, body, ctype: str = "application/json") -> None:
                raw = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                self.wfile.flush()

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw or b"{}")
                except json.JSONDecodeError:
                    body = {"__not-json__": raw.decode("utf-8", "replace")}
                outer.bodies.append(body)
                code, payload, ctype = outer._reply(body)
                try:
                    self._send(code, payload, ctype)
                except (BrokenPipeError, ConnectionResetError):
                    # the client (an httpx stream) left; the READING of the
                    # request and the recording above already happened, and
                    # that is all the assertions ask.
                    pass

            def do_GET(self) -> None:
                route = self.path.split("?")[0]
                outer.gets.append(route)
                if route.endswith("/models"):
                    # The one answer that lets every chat's update_models
                    # worker return instead of looping 60 x 10 s.
                    self._send(200, {"models": [{"id": MODEL, "capabilities": ["text"]}]})
                    return
                self._send(404, {"error": {"message": f"mm-no-route {route}"}})

        return Handler


# ---------------------------------------------------------------- fixture chat
def old_chat_content() -> dict:
    # The shape a real chat file carries (Manage.save_managed's keys), with
    # the settings block Manage.NEW builds. Endpoint "7" = the canned server
    # endpoint the app below registers.
    settings = {
        "desc": {"stype": "string", "empty": False, "desc": "Description",
                 "value": "mm-old-desc"},
        "endpoint": {"stype": "select_no_default", "desc": "Endpoint",
                     "ameth": "endpoint_list", "value": "7"},
        "model": {"stype": "select_no_default", "desc": "Model",
                  "ameth": "model_list", "wmeth": "work_model_list", "value": MODEL},
        "model_settings": {"stype": "select", "desc": "Model Settings",
                           "ameth": "model_settings_list", "value": None},
        "prompt": {"stype": "select", "desc": "System Prompt",
                   "ameth": "prompt_list", "value": None},
        "tools": {"stype": "select_list", "desc": "Allowed tools",
                  "ameth": "tools_list", "value": ["handoff"]},
        "sandbox": {"stype": "string", "empty": False,
                    "desc": "Sandbox home directory", "value": "default"},
    }
    return {"ctime": 1758000000.0, "settings": settings,
            "messages": [{"role": "user",
                          "content": [{"type": "text", "text": START_TEXT}]}],
            "model": None}


def make_data() -> None:
    if FIXTURES.exists():
        shutil.rmtree(FIXTURES)
    (DATA / "chats").mkdir(parents=True)
    (DATA / "custom_tools").mkdir()
    (DATA / "chats" / f"{OLD_ID}.json").write_text(
        json.dumps(old_chat_content(), indent=4))


def teardown() -> None:
    if not os.environ.get("KEEP_FIXTURES"):
        shutil.rmtree(FIXTURES, ignore_errors=True)


def chat_files() -> list:
    return sorted(p.name for p in (DATA / "chats").iterdir())


# ------------------------------------------------------------------- stub app
class StubSettings:
    def __init__(self) -> None:
        self.path = {"chats": DATA / "chats", "custom_tools": DATA / "custom_tools"}
        self.active_chat = None
        self.tool_settings = {}
        self.models = {}
        self.prompts = {}
        self.llamacpp = {}
        self.endpoints = {}

    def save(self) -> None:
        pass


class StubServer:
    def is_running(self) -> bool:
        return False


class FakeWork:
    """For the direct-call cases: `handoff.call` only ever touches
    `_work.exit_after_busy`; the real work loop is t10-t15's subject, driven
    there with the real `Work` instead."""

    def __init__(self) -> None:
        self.exit_after_busy = False
        self.busy = False
        self.is_running = False


class HandoffApp(App[None]):
    """Chat + SidePanel + ToolCall + Work are the real classes; only the
    server, the settings home and the endpoint list are stubs (module
    docstring: WHAT IS DRIVEN FOR REAL)."""

    def __init__(self, server: CannedServer) -> None:
        super().__init__()
        self.settings = StubSettings()
        self.settings.endpoints["7"] = {
            "name": {"value": "mm-handoff-ep", "stype": "string"},
            "endpoint_url": {"value": f"{server.base}/ep/v1", "stype": "string"},
            "key": {"value": "", "stype": "string"},
            "timeout": {"value": 5, "stype": "uinteger"},
            "reasoning_key": {"value": "reasoning_content", "stype": "string"},
            "context_size": {"value": 0, "stype": "uinteger"},
        }
        self.path = self.settings.path
        self.server = StubServer()
        self.slots = {}
        self.tmux = {}
        self.exception = None
        self.tool_call = ToolCall(self)

    # the real app's file mapping (SpitApp.read_json / write_json) over the
    # fixture dir - the chat files are really written and really read back.
    def read_json(self, path: str):
        parts = path.split("/")
        file = self.path[parts[0]] / parts[1] if len(parts) > 1 else self.path[parts[0]]
        return json.loads(file.read_text())

    def write_json(self, path: str, content) -> bool:
        parts = path.split("/")
        file = self.path[parts[0]] / parts[1] if len(parts) > 1 else self.path[parts[0]]
        file.write_text(json.dumps(content, indent=4))
        return True

    def endpoint_list(self) -> dict:
        return dict(self.settings.endpoints)

    def endpoint_list_tuple(self) -> tuple:
        return tuple((e["name"]["value"], key)
                     for key, e in self.settings.endpoints.items())

    def get_endpoint(self, endpoint_id: str) -> dict:
        return self.settings.endpoints[endpoint_id]

    def compose(self) -> ComposeResult:
        with Horizontal(id="app"):
            yield SidePanel()
            yield Vertical(id="main")


async def run_case(fn) -> None:
    """One fresh fixture dir, one fresh canned server, one fresh app. The
    finally-quiesce runs even when the case itself failed: a case that dies
    mid-stream must not then have its OWN error replaced by a teardown race
    (measured - the IndexError of a StreamCallback landing during shutdown
    masked the assertion that actually failed first)."""
    make_data()
    server = CannedServer().start()
    try:
        app = HandoffApp(server)
        async with app.run_test(size=APP_SIZE) as pilot:
            await pilot.pause()
            try:
                await fn(app, pilot, server)
            finally:
                try:
                    await quiesce(pilot, app)
                except Exception:  # noqa: BLE001 - never mask the case's own error
                    pass
    finally:
        server.stop()
        teardown()


async def mount_old(app, pilot) -> Chat:
    """The human path of opening the calling chat (the SidePanel path):
    mount the real Chat, open its view."""
    main = app.query_one("#main")
    await main.mount(Chat(OLD_ID))
    old = main.query_one(f"#{OLD_ID}")
    await old.chat_view.load()
    await pilot.pause()
    return old


async def until(pilot, predicate, timeout: float = 20.0) -> bool:
    """Poll the predicate against pilot pauses - synchronise to the app's
    state, never to a blind sleep (decision 73's rule, read the other way:
    the deadline is a failure bound, not a wait)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await pilot.pause(0.05)
    return predicate()


async def quiesce(pilot, app, timeout: float = 20.0) -> bool:
    """Wait until no mounted chat has a live worker, then let the message pump
    drain a few frames. Ending a case mid-stream is how you get teardown races
    (a StreamCallback processed while the widget tree is already going down)
    reported as the case's own crash; quiesce is the state to wait for. The
    deadline makes a missed quiescence a reported red, not a hang."""
    main = app.query_one("#main")

    def idle():
        return all(getattr(c, "work", None) is None or c.work.is_finished
                   for c in main.children)
    done = await until(pilot, idle, timeout)
    for _ in range(8):
        await pilot.pause()
    return done


def new_id_from(text: str):
    match = re.search(r"`(chat-[^`]+)`", text or "")
    return match.group(1) if match else None


async def handoff_call(app, arguments: dict, chat_id: str):
    """The real `call` of the real tool module, as the dispatcher reaches it."""
    return await app.tool_call.tools["handoff"]["call"](app, arguments, chat_id)
