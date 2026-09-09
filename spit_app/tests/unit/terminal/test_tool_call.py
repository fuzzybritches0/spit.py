#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for the terminal and lsterm tool modules: the arguments and the errors.

Three defects lived in the argument handling of `call()`, all of the same family
-- a value that was read and then not used:

  * `dealy = arguments["delay"]`, so the caller's delay was dropped on the floor
    and every call slept the default one second, whether it was asked to wait or
    not;
  * `if "delay" in arguments and arguments["delay"]`, so an explicit `delay=0`
    looked like "no delay given" and slept a second anyway -- the one value a
    caller writes when it wants no wait;
  * `terminal.term_new(name)`'s return value discarded. term_new returns
    check_bwrap()'s error string and creates nothing, and call() then indexed
    `app.tmux[chat_id]["windows"]`, which had never been populated -- so a
    machine without bwrap got a KeyError where it should have got "install
    bubblewrap".

lsterm had the mirror-image bug: it walked `windows.keys()` while the liveness
check it called deleted the dead entry it was looking at, so the first dead
session in a chat made the *listing* raise `RuntimeError: dictionary changed size
during iteration` -- the tool you call to find out what is alive was the thing
that died. It now asks Terminal for the names, snapshotted before any check, and
the liveness rule exists in one place instead of two.
"""
import shutil
import os
import tempfile
import time

from stub_app import (check, default_server_running, kill_private_server,
                      make_terminal, pane_of, requested_sockets, stub_app,
                      summary, tmux_available, use_private_server, wait_for,
                      wait_for_text)

SOCKET = "spit-unit-terminal-call"

if not tmux_available():
    print("SKIP: no tmux binary on this machine; the terminal suite cannot run")
    print("PASS: 0  FAIL: 0")
    raise SystemExit(0)

use_private_server(SOCKET)

import spit_app.tools.terminal as tool
import spit_app.tools.lsterm as lsterm
import spit_app.tools.run.common as run_common
from spit_app.tools.run.common import CommonMixIn

REAL_SANDBOX_ENV = CommonMixIn.SANDBOX_ENV


def without_bwrap():
    """Hide bwrap from check_bwrap() without uninstalling anything."""
    saved = run_common.shutil.which
    run_common.shutil.which = lambda name: None if name == "bwrap" else saved(name)
    return saved


try:
    print("=== 1. delay=0 is honoured (the truthy-check defect) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        tool.call(app, {"name": "t1", "input": ["echo mm-zero-delay", "Enter"]}, "chat1")
        wait_for_text(app, "t1", "mm-zero-delay")
        started = time.time()
        answer = tool.call(app, {"name": "t1", "delay": 0}, "chat1")
        elapsed = time.time() - started
        check("t1-delay-0-does-not-sleep-a-second", elapsed < 0.5, True)
        check("t1-still-returned-the-screen", "mm-zero-delay" in answer, True)

    print("=== 2. delay=2 waits (the `dealy` typo) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        tool.call(app, {"name": "t2"}, "chat1")
        started = time.time()
        tool.call(app, {"name": "t2", "delay": 2}, "chat1")
        elapsed = time.time() - started
        check("t2-asked-for-two-slept-two", elapsed >= 2.0, True)
        check("t2-did-not-sleep-only-the-default", elapsed < 3.5, True)

    print("=== 3. no delay asked for keeps the documented one-second default ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        tool.call(app, {"name": "t3"}, "chat1")
        started = time.time()
        tool.call(app, {"name": "t3"}, "chat1")
        elapsed = time.time() - started
        check("t3-default-delay-is-about-a-second", 0.9 <= elapsed < 2.0, True)

    print("=== 4. a missing bwrap is reported, not a KeyError ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        saved = without_bwrap()
        try:
            answer = tool.call(app, {"name": "t4", "input": ["echo mm-no-bwrap", "Enter"]},
                               "chat1")
        except Exception as exc:
            answer = f"RAISED {type(exc).__name__}: {exc}"
        finally:
            run_common.shutil.which = saved
        check("t4-names-bwrap", "bwrap" in answer, True)
        check("t4-is-an-error", answer.startswith("ERROR"), True)
        check("t4-not-a-keyerror", "KeyError" in answer, False)
        check("t4-no-session-was-created", "t4" in app.tmux.get("chat1", {}).get("windows", {}),
              False)

    print("=== 7. a pane_active check on a chat that has no tmux entry ===")
    with tempfile.TemporaryDirectory() as root:
        t = make_terminal(stub_app(root))
        check("t7-returns-false-not-keyerror", t.pane_active("anything"), False)
        check("t7-screen-of-the-unknown-chat-says-dead",
              "INFO: Session dead." in t.term_screen("anything"), True)

    print("=== 8. the arguments call() refuses ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        check("t8-no-name", "ERROR" in tool.call(app, {}, "chat1"), True)
        check("t8-empty-name", "ERROR" in tool.call(app, {"name": ""}, "chat1"), True)
        check("t8-input-not-a-list",
              "ERROR" in tool.call(app, {"name": "t8", "input": "echo mm-not-a-list"}, "chat1"),
              True)

    print("=== 9. a session whose shell dies while tmux is creating it ===")
    # new_window() reads back the window it just made. If the shell died in the
    # meantime -- a sandbox_env.sh that cannot exec, a command that exits before
    # tmux answers -- libtmux raises TmuxObjectDoesNotExist out of new_window
    # itself (measured on tmux 3.7b/libtmux 0.62 for a shell that cannot exec AND
    # for one that execs and exits at once). That escaped term_new and call() and
    # reached the model as a traceback. term_new's contract is an error STRING,
    # which is what check_bwrap() returns for the same class of "cannot start".
    # Both shapes are pinned because they look identical from the outside and only
    # one of them is a race.
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        for shape, env in (("cannot-exec", "/nonexistent/zz-sandbox_env.sh"),
                           ("exits-at-once", "/bin/false")):
            t.SANDBOX_ENV = env
            try:
                answer = t.term_new(f"t9-{shape}")
            except Exception as exc:
                answer = f"RAISED {type(exc).__name__}: {exc}"
            check(f"t9-{shape}-is-an-error-string", str(answer).startswith("ERROR"), True)
            check(f"t9-{shape}-did-not-raise", "RAISED" in str(answer), False)
            check(f"t9-{shape}-names-the-session", f"t9-{shape}" in str(answer), True)
            check(f"t9-{shape}-no-window-registered",
                  f"t9-{shape}" in app.tmux.get("chat1", {}).get("windows", {}), False)
            # and the chat is still usable afterwards: the failed start must not
            # have poisoned the session it created
            t.SANDBOX_ENV = REAL_SANDBOX_ENV
            check(f"t9-{shape}-chat-still-usable", t.term_new(f"t9-after-{shape}"), None)

    print("=== 10. the tmux server it builds is one we own, not the user's ===")
    # A bare `libtmux.Server()` is the user's DEFAULT tmux server. The tool
    # created its sessions there, so (a) our windows lived among theirs, named
    # after whatever the model called them, and (b) actions.py action_exit_app
    # calls `self.tmux[chat_id]["server"].kill()` -- libtmux Server.kill() is
    # `tmux kill-server` -- so QUITTING SPIT.PY TOOK DOWN THE USER'S TMUX. The
    # wrapper in stub_app forces its own socket (a setdefault would let
    # production's name win, and the suite would be driving the very socket it is
    # supposed to be isolated from) and records what was asked; these checks are
    # how the production choice is pinned without ever driving it.
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        default_before = default_server_running()
        del requested_sockets[:]
        t = make_terminal(app)
        t.term_new("t10")
        check("t10-a-server-was-built", len(requested_sockets) >= 1, True)
        check("t10-it-named-a-socket", None in requested_sockets, False)
        check("t10-not-the-user-default-socket",
              all(str(s).startswith("spit-") for s in requested_sockets), True)
        check("t10-the-socket-is-this-process-s",
              all(str(s).endswith(str(os.getpid())) for s in requested_sockets), True)
        # one server per process, one session per chat: a second chat asks for the
        # SAME socket, so five chats do not mean five tmux servers
        from spit_app.tools.run.terminal import Terminal
        Terminal(app, "chat2", False).term_new("t10-chat2")
        check("t10-every-chat-shares-one-server", len(set(requested_sockets)), 1)
        check("t10-both-chats-got-a-window",
              sorted(app.tmux["chat1"]["windows"]) + sorted(app.tmux["chat2"]["windows"]),
              ["t10", "t10-chat2"])
        # the user's own server is untouched: it is not what we just used
        check("t10-ran-no-server-on-the-user-s-default-socket",
              default_server_running(), default_before)

finally:
    kill_private_server(SOCKET)

summary()
