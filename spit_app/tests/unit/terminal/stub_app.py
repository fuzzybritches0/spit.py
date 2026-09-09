#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""A stub app and the helpers the terminal suite uses to drive a real tmux.

The Terminal class asks the app for three things -- `app.tmux`, the two sandbox
paths and the per-chat sandbox setting -- so it can be driven without Textual,
which is not a dependency of the tests and is not installed everywhere they run
(the way tests/unit/sandbox/stub_app.py drives Run).

What it does add is a private tmux server. Terminal asks for a socket of its own
now (`server_socket()` = `spit-<pid>`, because a bare `libtmux.Server()` is the
user's tmux and actions.py `kill-server`s it when the app quits), but a suite
still cannot drive that one: the windows are named after whatever the test fancied
at the time, a crashed run leaves them behind, and the only teardown a suite has
is `kill-server`, which must land on a socket this file named. So
`libtmux.Server` is wrapped to FORCE our `socket_name` over whatever was asked for
-- a `setdefault` would let production's name win, and the suite would be driving
the very socket it exists to stay off -- and to record the request, so a check can
pin which socket production wanted without ever driving it (`requested_sockets`,
test_tool_call.py t10).

Every assertion here uses sandbox=False. Inside bwrap the process table belongs
to the sandbox (TRAPS #6): `pane_current_command` and the death of a pane are
exactly the things this suite has to see, and the sandbox is not what the tmux
backend is made of. One suite (test_tool_call.py 2) drives the sandboxed path
for real, because it can, and measures rather than assumes.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

import libtmux

REAL_SERVER = libtmux.Server

# What the code under test asked for, in order, one entry per libtmux.Server()
# it built (None when it built one without a socket). See use_private_server().
requested_sockets = []


ENABLED_TOOLS = ["terminal", "lsterm"]


def tmux_available() -> bool:
    return shutil.which("tmux") is not None


def stub_app(root: str):
    """The three things Terminal asks the app for, and nothing else.

    Two inert extras come with it for a test that drives the dispatcher rather
    than Terminal -- see StubChat. Nothing a test of Terminal needs changes.
    """

    class StubChat:
        # tool_call.ToolCall.call() reads chat.cs("tools") to decide whether the
        # tool is available and touches chat.chat_view on its way without ever
        # using it -- the callback arrives as an argument. Everything else, the
        # "sandbox" name CommonMixIn builds its directories from above all, answers
        # exactly as it did before.
        chat_view = None

        def cs(self, key):
            return ENABLED_TOOLS if key == "tools" else "unittest"

    class StubMain:
        def __init__(self, chat):
            self.chat = chat

        def query_one(self, selector):
            return self.chat

    class StubApp:
        def __init__(self, root):
            self.settings = type("Settings", (), {
                "path": {"sandbox": Path(root) / "sandbox",
                         "sandbox_tmp": Path(root) / "tmp"},
                "tool_settings": {}})
            self.chat = StubChat()
            self.tmux = {}

        def query_one(self, selector):
            return StubMain(self.chat)

    os.makedirs(os.path.join(root, "sandbox"), exist_ok=True)
    os.makedirs(os.path.join(root, "tmp"), exist_ok=True)
    return StubApp(root)


def use_private_server(socket_name: str) -> None:
    """Point every libtmux.Server() at a socket of our own, for this process.

    The socket is FORCED, not defaulted: `Terminal` passes a socket of its own now
    (run/terminal.py server_socket(), because a bare libtmux.Server() is the user's
    tmux and actions.py kill-server's it at exit), and a `setdefault` here would let
    production's name win -- which is exactly the kind of bug this wrapper exists to
    keep out of the user's tmux. So the suite overrides it and records what was
    asked for instead: `requested_sockets` is the list of what the code under test
    passed, and a check can pin the production choice without driving it.
    """

    def private_server(*args, **kwargs):
        requested_sockets.append(kwargs.get("socket_name"))
        kwargs["socket_name"] = socket_name
        return REAL_SERVER(*args, **kwargs)

    libtmux.Server = private_server


def kill_private_server(socket_name: str) -> None:
    if shutil.which("tmux"):
        subprocess.run(["tmux", "-L", socket_name, "kill-server"],
                       capture_output=True)


def default_server_running() -> bool:
    """Is a tmux server up on the user's DEFAULT socket?

    The point of this is the negative: a tool run must not START one there. It
    answers the question rather than asserting False so the check stays correct on
    a machine whose user has their own tmux open -- what is pinned is that the
    number did not change because we ran, not that nobody else has a server.
    """
    if shutil.which("tmux") is None:
        return False
    return subprocess.run(["tmux", "ls"], capture_output=True).returncode == 0


def make_terminal(app, sandbox: bool = False):
    from spit_app.tools.run.terminal import Terminal
    return Terminal(app, "chat1", sandbox)


def pane_of(app, name: str):
    return app.tmux["chat1"]["windows"][name].panes[0]


def screen_of(app, name: str) -> str:
    """The pane as one string.

    capture_pane() returns a list of lines, and `token in lines` then asks
    whether some line is *exactly* that token -- which silently never matches for
    anything that shares its line with a prompt, the common case for a terminal.
    Everything here matches against the joined screen.
    """
    return "\n".join(pane_of(app, name).capture_pane())


def wait_for(what, timeout: float = 15.0, interval: float = 0.15):
    """Poll until `what()` is truthy; return its last value.

    tmux hands a new window its shell asynchronously and a pane's command changes
    when a process starts or dies, so every timing expectation here is a poll with
    a generous ceiling rather than a fixed sleep: a fixed sleep makes the suite
    slow on a loaded machine and flaky on a fast one.
    """
    deadline = time.time() + timeout
    value = what()
    while not value and time.time() < deadline:
        time.sleep(interval)
        value = what()
    return value


def wait_for_text(app, name: str, token: str, timeout: float = 15.0) -> bool:
    return bool(wait_for(lambda: token in screen_of(app, name), timeout=timeout))


def wait_for_prompt(app, name: str, timeout: float = 15.0) -> bool:
    """A new window draws its first prompt asynchronously.

    Keys sent before it exists are not lost, but they land in the shell's line
    editor before bash has drawn anything, and a test that then asserts on the
    order of what appeared has no order to assert on. Wait for the prompt.
    """
    return bool(wait_for(lambda: "$" in screen_of(app, name), timeout=timeout))


def send_raw(app, name: str, keys: str, literal: bool) -> None:
    """Send to the pane behind Terminal's back -- how a control is kept as text."""
    pane_of(app, name).send_keys(keys, enter=False, literal=literal)


def window_exists(app, name: str) -> bool:
    """Is the tmux window still there -- WITHOUT the tool's bookkeeping side effect.

    pane_active() forgets a window it finds dead, which is its job in production
    and a trap in a test: a test that polls it to wait for a session to die has
    quietly cleaned the registry, and the code under test then never meets the
    dead entry it is supposed to survive. Waiting on this instead leaves the
    registry untouched, so the dead window is still in it when the tool is called.
    """
    chat = app.tmux.get("chat1", {})
    window = chat.get("windows", {}).get(name)
    if window is None:
        return False
    chat["session"].refresh()
    return window in chat["session"].windows


def window_dead(app, name: str):
    """Has the registered window's PROCESS exited -- and nothing else.

    Since the windows are created with `remain-on-exit` on, tmux keeps them after
    their shell dies, so "is the window still there" (window_exists) and "is the
    session still alive" are now two different questions with different answers:
    for a dead one the first is True and the second is False. A death-wait has to
    poll the second.

    It cannot poll pane_active() -- that is decision 67's trap, and a sharper one
    now: pane_active() FORGETS the name it finds dead, so a test that waits on it
    cleans up the very state the code under test is meant to be handed. This reads
    the pane and touches no bookkeeping at all.

    None means there is nothing to ask: the name is not registered, or tmux has no
    window for it. True/False is the answer when there is.
    """
    chat = app.tmux.get("chat1", {})
    window = chat.get("windows", {}).get(name)
    if window is None or "session" not in chat:
        return None
    if window not in chat["session"].windows:
        return None
    panes = window.panes
    return panes[0].pane_dead == "1" if panes else None


def kill_window(app, name: str) -> None:
    """Close the tmux window the way a dying shell does, from outside the tool."""
    window = app.tmux["chat1"]["windows"][name]
    window.kill()


pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def summary():
    print()
    print(f"PASS: {pass_}  FAIL: {fail_}")
