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
import tempfile
import time

from stub_app import (check, kill_private_server, make_terminal, pane_of,
                      stub_app, summary, tmux_available, use_private_server,
                      wait_for, wait_for_text)

SOCKET = "spit-unit-terminal-call"

if not tmux_available():
    print("SKIP: no tmux binary on this machine; the terminal suite cannot run")
    print("PASS: 0  FAIL: 0")
    raise SystemExit(0)

use_private_server(SOCKET)

import spit_app.tools.terminal as tool
import spit_app.tools.lsterm as lsterm
import spit_app.tools.run.common as run_common


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
finally:
    kill_private_server(SOCKET)

summary()
