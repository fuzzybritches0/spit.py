#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for what term_screen() returns, and for what a dead session says.

The defect this pins is the empty tool response: term_screen() built the screen
into a local and returned `self.output`, which was assigned exactly once -- to
"" in __init__ -- so every capture of a live pane came back as an empty message
container. A dead pane answered "\n\nINFO: Session dead." with an empty prefix,
which is why a dead session looked like a truncated one.

The second half is where the cache had to move to. A Terminal is constructed
per tool call (spit_app/tools/terminal.py builds one in call()), so an instance
attribute cannot be "the last screen": it is born empty on every call and the
screen of a session that died between two calls dies with the object that saw
it. The cache therefore lives in app.tmux[chat_id], which is what outlives a
call and is what the window registry itself lives in -- and it is per session
name, because one chat runs several terminals and a reused name is a new
session, not the old one's history.
"""
import tempfile

from stub_app import (check, kill_private_server, kill_window, make_terminal,
                      send_raw, stub_app, summary, tmux_available,
                      use_private_server, wait_for, wait_for_text)

SOCKET = "spit-unit-terminal-screen"

if not tmux_available():
    print("SKIP: no tmux binary on this machine; the terminal suite cannot run")
    print("PASS: 0  FAIL: 0")
    raise SystemExit(0)

use_private_server(SOCKET)

try:
    print("=== 1. a live pane returns its screen (the empty-response defect) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        check("t1-session-created", t.term_new("t1"), None)
        t.term_input("t1", "echo mm-screen-token")
        t.term_input("t1", "Enter")
        check("t1-token-reached-the-pane", wait_for_text(app, "t1", "mm-screen-token"), True)
        screen = t.term_screen("t1")
        check("t1-capture-not-empty", len(screen) > 0, True)
        check("t1-capture-carries-the-token", "mm-screen-token" in screen, True)
        check("t1-names-the-session", screen.startswith("Session: t1"), True)

    print("=== 2. the cursor is reported in the capture ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t2")
        screen = t.term_screen("t2")
        check("t2-cursor-marker-present", "█" in screen, True)
        check("t2-screen-is-not-just-the-header", len(screen) > len("Session: t2\n\n"), True)

    print("=== 3. a new Terminal on the same chat sees the same screen ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        first = make_terminal(app)
        first.term_new("t3")
        first.term_input("t3", "echo mm-same-screen")
        first.term_input("t3", "Enter")
        check("t3-token-reached-the-pane", wait_for_text(app, "t3", "mm-same-screen"), True)
        first.term_screen("t3")
        second = make_terminal(app)
        check("t3-second-instance-sees-the-pane",
              "mm-same-screen" in second.term_screen("t3"), True)

    print("=== 4. a dead pane reports the last screen it showed ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t4")
        t.term_input("t4", "echo mm-before-death")
        t.term_input("t4", "Enter")
        check("t4-token-reached-the-pane", wait_for_text(app, "t4", "mm-before-death"), True)
        t.term_input("t4", "exit")
        t.term_input("t4", "Enter")
        check("t4-pane-went-away", wait_for(lambda: not t.pane_active("t4")), True)
        after = t.term_screen("t4")
        check("t4-says-it-is-dead", "INFO: Session dead." in after, True)
        check("t4-still-shows-the-last-screen", "mm-before-death" in after, True)
        # the message IS the cached screen plus the notice, verbatim: the cache
        # is written only by a capture, so the dead path reports what was last
        # really on the pane and invents nothing. It is the capture taken just
        # before the input that killed the session -- including that input's own
        # line -- because keys are sent only after a fresh capture.

    print("=== 5. and a later call sees it too (the cache outlives the call) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        first = make_terminal(app)
        first.term_new("t5")
        first.term_input("t5", "echo mm-last-screen")
        first.term_input("t5", "Enter")
        check("t5-token-reached-the-pane", wait_for_text(app, "t5", "mm-last-screen"), True)
        first.term_screen("t5")
        kill_window(app, "t5")
        next_call = make_terminal(app)
        check("t5-pane-detected-dead", next_call.pane_active("t5"), False)
        report = next_call.term_screen("t5")
        check("t5-says-it-is-dead", "INFO: Session dead." in report, True)
        check("t5-carries-the-last-screen-of-the-dead-session",
              "mm-last-screen" in report, True)
        check("t5-not-an-empty-container", len(report) > len("\n\nINFO: Session dead."), True)

    print("=== 6. a session that never showed anything says so, without a blank prefix ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        report = t.term_screen("t6-never-existed")
        check("t6-says-it-is-dead", "INFO: Session dead." in report, True)
        check("t6-no-empty-prefix-above-the-message", report.startswith("\n"), False)
        check("t6-says-nothing-was-captured", "before anything was captured" in report, True)

    print("=== 7. a reused name is a new session, not the old screen ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t7")
        t.term_input("t7", "echo mm-old-session")
        t.term_input("t7", "Enter")
        check("t7-token-reached-the-pane", wait_for_text(app, "t7", "mm-old-session"), True)
        t.term_screen("t7")
        kill_window(app, "t7")
        wait_for(lambda: not t.pane_active("t7"))
        t.term_new("t7")
        t.term_input("t7", "echo mm-new-session")
        t.term_input("t7", "Enter")
        check("t7-new-session-reachable", wait_for_text(app, "t7", "mm-new-session"), True)
        fresh = t.term_screen("t7")
        check("t7-shows-the-new-screen", "mm-new-session" in fresh, True)
        check("t7-does-not-resurrect-the-dead-one", "mm-old-session" in fresh, False)

    print("=== 8. the cache is per session name ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t8-alpha")
        t.term_new("t8-beta")
        t.term_input("t8-alpha", "echo mm-alpha-only")
        t.term_input("t8-alpha", "Enter")
        check("t8-alpha-token", wait_for_text(app, "t8-alpha", "mm-alpha-only"), True)
        t.term_screen("t8-alpha")
        t.term_screen("t8-beta")
        check("t8-each-name-has-its-own-slot",
              "mm-alpha-only" in app.tmux["chat1"]["last_screen"]["t8-alpha"], True)
        check("t8-the-other-name-kept-its-own-empty-slot",
              app.tmux["chat1"]["last_screen"]["t8-beta"] !=
              app.tmux["chat1"]["last_screen"]["t8-alpha"], True)
        kill_window(app, "t8-beta")
        wait_for(lambda: not t.pane_active("t8-beta"))
        check("t8-beta-died-without-ever-showing-alpha-s-content",
              "mm-alpha-only" in t.term_screen("t8-beta"), False)

    print("=== 9. a pane that dies mid-input still reports through the same path ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t9")
        t.term_input("t9", "echo mm-pre-input-screen")
        t.term_input("t9", "Enter")
        check("t9-token-reached-the-pane", wait_for_text(app, "t9", "mm-pre-input-screen"), True)
        send_raw(app, "t9", "exit", False)
        send_raw(app, "t9", "Enter", False)
        check("t9-input-reported-false", wait_for(
            lambda: t.term_input("t9", "echo mm-after-death") is False), True)
        report = t.term_screen("t9")
        check("t9-says-it-is-dead", "INFO: Session dead." in report, True)
        check("t9-carries-the-pre-input-screen", "mm-pre-input-screen" in report, True)
finally:
    kill_private_server(SOCKET)

summary()
