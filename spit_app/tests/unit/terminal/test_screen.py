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
                      use_private_server, wait_for, wait_for_prompt,
                      wait_for_text, window_dead)

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

    # ------------------------------------------------------------------
    # 10 onwards: what `remain-on-exit` bought. The distinction that matters in
    # every one of them is between the screen the CACHE holds -- something we
    # happened to capture while the session was alive -- and the screen tmux still
    # has on the dead pane. t4/t5/t9 above pin the cache path and stay as they
    # were; these pin the real one, so a token that was NEVER captured while the
    # session ran still arrives.
    print("=== 10. a session that dies on its own reports what it really printed ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t10")
        wait_for_prompt(app, "t10")
        # ONE call, and that call is the death: nothing is ever captured while this
        # session lives, so anything in the report can only come from the pane.
        send_raw(app, "t10", "echo mm-never-captured-alive; exit 4\n", True)
        check("t10-says-it-is-dead", wait_for(
            lambda: "INFO: Session dead." in t.term_screen("t10")), True)
        report = t.last_screen("t10")
        check("t10-carries-the-screen-it-never-showed-us",
              "mm-never-captured-alive" in report, True)
        # the exit code is asserted from TMUX's own line, not from our prose: that
        # line is the authority, and it is on the pane, so it cannot be invented by
        # the report writer.
        check("t10-tmux-s-own-line-states-the-status",
              "Pane is dead (status 4" in report, True)
        check("t10-the-notice-states-the-status", "Exit status: 4." in report, True)
        check("t10-it-is-the-session-s-own-screen", report.startswith("Session: t10"), True)

    print("=== 11. tmux's dead notice does not eat the first line any more ===")
    # tmux writes `Pane is dead (status N, ...)` INTO the pane and that scrolls the
    # grid up by one line. Measured on tmux 3.7b with 1, 2, 3 and 10 lines printed:
    # a visible-only capture lost the FIRST line every time, and for a one-line
    # session it lost the only line -- which is exactly the crash-report case this
    # feature exists for. The report therefore captures from the scrollback.
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t11")
        wait_for_prompt(app, "t11")
        send_raw(app, "t11", "printf 'mm-one-and-only-line\\n'; exit 2\n", True)
        check("t11-one-line-session-still-reports-it", wait_for(
            lambda: "mm-one-and-only-line" in t.term_screen("t11")), True)
        t.term_new("t11b")
        wait_for_prompt(app, "t11b")
        send_raw(app, "t11b", "printf 'mm-first-of-three\\nmm-second\\nmm-third\\n'; exit 2\n",
                 True)
        check("t11b-waited-for-the-report", wait_for(
            lambda: "INFO: Session dead." in t.term_screen("t11b")), True)
        both = t.last_screen("t11b")
        check("t11b-kept-the-first-line", "mm-first-of-three" in both, True)
        check("t11b-kept-the-last-line", "mm-third" in both, True)

    print("=== 12. a death by signal does not report an empty exit status ===")
    # pane_dead_status is set for a normal exit and may be EMPTY for a death by
    # signal, which is why the notice is conditional. Whatever tmux says for a
    # signalled shell, it must never read "Exit status: ."
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t12")
        wait_for_prompt(app, "t12")
        # `ulimit -c 0` first: the window's CWD is the tmux SERVER's, which is the
        # directory the suite was started in, and a segfaulting shell drops a core
        # file there. (It did. The repo root filled with them.)
        send_raw(app, "t12", "ulimit -c 0; kill -SEGV $$\n", True)
        check("t12-reports-the-death", wait_for(
            lambda: "INFO: Session dead." in t.term_screen("t12")), True)
        report = t.last_screen("t12")
        check("t12-no-empty-exit-status", "Exit status: ." in report, False)
        check("t12-still-says-it-is-dead", "INFO: Session dead." in report, True)

    print("=== 13. reusing a dead name is a new session, not the corpse's screen ===")
    # t7 covers reuse after the window is gone. With the window retained this is the
    # case that could resurrect the old screen: the tmux window is still there, so a
    # reuse that merely re-registered it would answer with the dead session's last
    # screen -- and the model would be reading a finished session's output believing
    # it had just started a new one.
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t13")
        wait_for_prompt(app, "t13")
        send_raw(app, "t13", "echo mm-the-old-session; exit 3\n", True)
        check("t13-old-session-died-and-was-reported", wait_for(
            lambda: "mm-the-old-session" in t.term_screen("t13")), True)
        check("t13-reuse-succeeds", t.term_new("t13"), None)
        check("t13-new-session-draws-a-prompt", wait_for_prompt(app, "t13"), True)
        send_raw(app, "t13", "echo mm-the-new-session\n", True)
        check("t13-new-token-arrived", wait_for_text(app, "t13", "mm-the-new-session"), True)
        fresh = t.term_screen("t13")
        check("t13-shows-the-new-screen", "mm-the-new-session" in fresh, True)
        check("t13-does-not-resurrect-the-old-screen",
              "mm-the-old-session" in fresh, False)
        check("t13-no-dead-notice-on-a-live-session", "INFO: Session dead." in fresh, False)
finally:
    kill_private_server(SOCKET)

summary()
