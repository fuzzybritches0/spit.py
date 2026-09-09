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
                      wait_for_prompt, wait_for_text, window_dead, window_exists)

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
        # window_dead, not window_exists and not pane_active. The sessions are made
        # with `remain-on-exit` on the window, so tmux KEEPS the window after the
        # shell dies: "is the window there" is now the wrong question (it stays
        # True), and pane_active() is the right answer arrived at the wrong way -- it
        # FORGETS the name and harvests the corpse, so a test polling it would tidy
        # away the exact state the listing is supposed to be handed (decision 67's
        # trap, with a new twist). window_dead only reads.
        check("t1-dead-pane-is-dead", wait_for(lambda: window_dead(app, "t1-dead") is True), True)
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
            check(f"t2-{dying}-is-gone", wait_for(lambda: window_dead(app, dying) is True), True)
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

    print("=== 5. liveness is the pane, not the window ===")
    # `remain-on-exit` is what the sessions are created with, so tmux KEEPS a dead
    # session's window: "is the window still there" and "is the session still alive"
    # are different questions now, and the listing must answer the second one. The
    # other half of this is the disposition. The listing is often the only thing that
    # ever sees a death -- the model is told to call it first -- so forgetting a dead
    # name has to harvest the corpse's real screen into the cache AND destroy the
    # window, or the evidence goes unread and the session fills with corpses nobody
    # can reach any more. Measured before that: three chats and one death left 5
    # windows in the session, and reusing the dead name made it 6.
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t5-live")
        t.term_new("t5-dies")
        check("t5-both-prompts-drawn",
              wait_for_prompt(app, "t5-live") and wait_for_prompt(app, "t5-dies"), True)
        sess = app.tmux["chat1"]["session"]
        # let THIS one die while the other keeps running -- the state a chat is in
        # when the model calls lsterm after a session died on its own
        t.term_input("t5-dies", "exit 2")
        t.term_input("t5-dies", "Enter")
        check("t5-waited-for-the-pane-to-die",
              wait_for(lambda: window_dead(app, "t5-dies") is True), True)
        check("t5-tmux-still-holds-the-dead-window", window_exists(app, "t5-dies"), True)
        sess.refresh()
        windows_before = len(sess.windows)
        answer = lsterm.call(app, {}, "chat1")
        check("t5-lists-the-live-one", "t5-live" in answer, True)
        check("t5-does-not-list-the-corpse", "t5-dies" in answer, False)
        check("t5-harvested-the-corpse-into-the-cache",
              "INFO: Session dead." in app.tmux["chat1"].get("last_screen", {}).get("t5-dies", ""),
              True)
        sess.refresh()
        check("t5-destroyed-the-corpse", len(sess.windows), windows_before - 1)
        check("t5-dropped-the-name", "t5-dies" in app.tmux["chat1"]["windows"], False)
        check("t5-the-live-one-is-still-listed", "t5-live" in lsterm.call(app, {}, "chat1"), True)

finally:
    kill_private_server(SOCKET)

summary()
