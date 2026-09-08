#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for lsterm: the listing that died while it was listing.

lsterm kept its own copy of the liveness test and walked `windows.keys()` while
calling it -- and the liveness test deletes the dead window it discovers from
that same dict. So the first time a chat had a session that had died, the tool
the model is told to call *in order to find out what is alive* raised
`RuntimeError: dictionary changed size during iteration`:

  Traceback ... in call
    if pane_active(app, chat_id, window):
  RuntimeError: dictionary changed size during iteration

Measured on the code before this commit, that is exactly what happens -- the
listing is not merely wrong, it does not return. The names are now snapshotted
before any check, in one implementation that both tools share, so the rule
"this window is live, and if it is not, forget it" exists once instead of twice
with one of the two copies crashing.
"""
import tempfile

from stub_app import (check, kill_private_server, make_terminal, stub_app,
                      summary, tmux_available, use_private_server, wait_for,
                      wait_for_prompt, wait_for_text, window_exists)

SOCKET = "spit-unit-terminal-lsterm"

if not tmux_available():
    print("SKIP: no tmux binary on this machine; the terminal suite cannot run")
    print("PASS: 0  FAIL: 0")
    raise SystemExit(0)

use_private_server(SOCKET)

import spit_app.tools.lsterm as lsterm

try:
    print("=== 1. a dead session does not break the listing ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t1-alive")
        t.term_new("t1-dead")
        check("t1-alive-prompt-drawn", wait_for_prompt(app, "t1-alive"), True)
        t.term_input("t1-alive", "echo mm-alive-window")
        t.term_input("t1-alive", "Enter")
        check("t1-alive-window-echoed", wait_for_text(app, "t1-alive", "mm-alive-window"), True)
        t.term_input("t1-dead", "exit")
        t.term_input("t1-dead", "Enter")
        # window_exists, not pane_active: the code under test has to be handed a
        # registry that still holds the dead window, which is the state a chat is
        # in when the model calls lsterm after a session died on its own. Polling
        # pane_active here would clean up the very thing being tested.
        check("t1-dead-window-is-gone", wait_for(lambda: not window_exists(app, "t1-dead")), True)
        check("t1-dead-window-is-still-in-the-registry",
              "t1-dead" in app.tmux["chat1"]["windows"], True)
        answer = lsterm.call(app, {}, "chat1")
        check("t1-listing-returned-a-string", isinstance(answer, str), True)
        check("t1-lists-the-live-one", "t1-alive" in answer, True)
        check("t1-does-not-list-the-dead-one", "t1-dead" in answer, False)
        check("t1-listing-is-repeatable", "t1-alive" in lsterm.call(app, {}, "chat1"), True)
        check("t1-dropped-the-dead-window-from-the-registry",
              "t1-dead" in app.tmux["chat1"]["windows"], False)

    print("=== 2. two dead sessions, because one was enough to crash it ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t2-a")
        t.term_new("t2-b")
        t.term_new("t2-keep")
        check("t2-keep-prompt-drawn", wait_for_prompt(app, "t2-keep"), True)
        for dying in ["t2-a", "t2-b"]:
            t.term_input(dying, "exit")
            t.term_input(dying, "Enter")
            check(f"t2-{dying}-is-gone", wait_for(lambda: not window_exists(app, dying)), True)
        check("t2-both-corpses-still-in-the-registry",
              {"t2-a", "t2-b"} <= set(app.tmux["chat1"]["windows"]), True)
        answer = lsterm.call(app, {}, "chat1")
        check("t2-lists-what-is-left", "t2-keep" in answer, True)
        check("t2-lists-nothing-else", "t2-a" in answer or "t2-b" in answer, False)

    print("=== 3. nothing to list, in both the ways that mean nothing to list ===")
    with tempfile.TemporaryDirectory() as root:
        check("t3-chat-with-no-tmux-at-all",
              lsterm.call(stub_app(root), {}, "never-had-one"),
              "No active sessions found!")
        app = stub_app(root)
        make_terminal(app)
        check("t3-chat-with-no-windows", lsterm.call(app, {}, "chat1"),
              "No active sessions found!")

    print("=== 4. the listing names exactly the windows that are live ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t4-one")
        t.term_new("t4-two")
        check("t4-one-prompt", wait_for_prompt(app, "t4-one"), True)
        check("t4-two-prompt", wait_for_prompt(app, "t4-two"), True)
        answer = lsterm.call(app, {}, "chat1")
        check("t4-lists-both", "t4-one" in answer and "t4-two" in answer, True)
        check("t4-both-still-registered",
              len(app.tmux["chat1"]["windows"]), 2)
finally:
    kill_private_server(SOCKET)

summary()
