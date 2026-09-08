#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""A stub app and the helpers the terminal suite uses to drive a real tmux.

The Terminal class asks the app for three things -- `app.tmux`, the two sandbox
paths and the per-chat sandbox setting -- so it can be driven without Textual,
which is not a dependency of the tests and is not installed everywhere they run
(the way tests/unit/sandbox/stub_app.py drives Run).

What it does add is a private tmux server. Terminal builds its server with
`libtmux.Server()`, which means the user's own tmux server, and a test suite has
no business creating windows in it: the windows are named after whatever the
test fancied at the time and a name that collides with a window the user is
working in would be sent input by a test. So `libtmux.Server` is wrapped here to
pass `socket_name`, which is the one deviation from production and the reason
the suite can `kill-server` at the end without touching anything of the user's.

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


def tmux_available() -> bool:
    return shutil.which("tmux") is not None


def stub_app(root: str):
    """The three things Terminal asks the app for, and nothing else."""

    class StubChat:
        def cs(self, key):
            return "unittest"

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
    """Point every libtmux.Server() at a socket of our own, for this process."""

    def private_server(*args, **kwargs):
        kwargs.setdefault("socket_name", socket_name)
        return REAL_SERVER(*args, **kwargs)

    libtmux.Server = private_server


def kill_private_server(socket_name: str) -> None:
    if shutil.which("tmux"):
        subprocess.run(["tmux", "-L", socket_name, "kill-server"],
                       capture_output=True)


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
