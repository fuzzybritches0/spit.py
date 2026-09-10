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
import subprocess
import tempfile

from stub_app import (check, counted_tmux_invocations, kill_private_server,
                      kill_window, make_terminal, registered_ids_are_all_the_windows,
                      registered_window_id, requested_sockets, send_raw,
                      session_window_ids, stub_app, summary, tmux_panes,
                      tmux_available, tmux_session_ids, tmux_window_names,
                      use_private_server, wait_for, wait_for_prompt, wait_for_text,
                      window_dead, window_id_of)

SOCKET = "spit-unit-terminal-screen"

if not tmux_available():
    print("SKIP: no tmux binary on this machine; the terminal suite cannot run")
    print("PASS: 0  FAIL: 0")
    raise SystemExit(0)

use_private_server(SOCKET)

import spit_app.tools.lsterm as lsterm
from spit_app.tools.run.terminal import Terminal

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

    print("=== 6. a name that never existed says there is no such session ===")
    # RE-WORDED, not deleted (state layer, DECISIONS 70). This asserted "INFO:
    # Session dead." for a name that had never been started, which reports a death
    # that never happened -- and a reported death is something a model acts on: it
    # goes looking for the crash of a session that was never a session. The number,
    # the section and the shape stay; what is pinned is the real intent: a clear
    # report, naming the session, with no blank prefix, saying what would start one
    # -- and NOT claiming a death. `test_tool_call` t7 is the same call from the
    # other side and was re-worded the same way (the handoff named that one; this
    # is its twin, made from the same two lines of code).
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        report = t.term_screen("t6-never-existed")
        check("t6-says-there-is-no-such-session", "INFO: No such session." in report, True)
        check("t6-no-empty-prefix-above-the-message", report.startswith("\n"), False)
        check("t6-says-what-would-start-one", "Send input" in report, True)
        check("t6-does-not-invent-a-death", "INFO: Session dead." in report, False)

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

    # ------------------------------------------------------------------
    # 14 onwards: the state layer (DECISIONS 70). These read the REGISTRY and
    # read TMUX and compare them, which is only possible from outside the tool:
    # what is pinned is the SHAPE of what app.tmux holds (ids, not objects), the
    # NAMES tmux shows for our windows, the COST of a call in `tmux` invocations,
    # and the guard that keeps one chat's stale id from pointing at another
    # chat's live window. All of them are red on the object layer: there the
    # registry held libtmux Window objects, tmux called the windows `bash`, a
    # capture cost 6+2 invocations, and the stray window tmux creates with every
    # session sat in it unnamed.
    print("=== 14. the registry holds window ids, tmux calls the windows by our names ===")
    # The registry is `name -> window_id` (strings), because ids are what tmux
    # never reuses and objects are what was measured lying. `window_name=name`
    # makes tmux say what the registry says -- before it, anyone looking at our
    # socket saw windows called `bash` while the tool called them `alpha`. And
    # since the window tmux creates along with every session is destroyed once a
    # real window exists, a listing of the session holds EXACTLY the registered
    # windows: no unnamed window 0 holding the session (and the server) open.
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t14-alpha")
        t.term_new("t14-beta")
        ids = list(app.tmux["chat1"]["windows"].values())
        check("t14-registry-holds-strings", all(isinstance(i, str) for i in ids), True)
        # the isinstance guard comes FIRST in the next line on purpose: on the
        # object layer these are Window objects, and `i.startswith` there is an
        # AttributeError that aborts the file instead of a recorded FAIL -- the
        # differential must be able to SEE the reds, not die on them. Same reason
        # distinctness goes through window_id_of, which reads `.window_id` off an
        # object and the string itself off an id (a Window may not be hashable).
        check("t14-strings-are-window-ids",
              all(isinstance(i, str) and i.startswith("@") for i in ids), True)
        check("t14-ids-are-distinct", len(set(window_id_of(i) for i in ids)), 2)
        check("t14-tmux-uses-our-names", tmux_window_names(app),
              {"t14-alpha": "t14-alpha", "t14-beta": "t14-beta"})
        check("t14-no-unregistered-window-in-the-session",
              registered_ids_are_all_the_windows(app), True)

    print("=== 15. the last terminal reported takes its session -- and the server -- down ===")
    # With the stray window gone (t14), the ORDINARY end of a chat is: its last
    # window is reported dead, retire() kills it, the session dies with it, and
    # since ours was the server's only session the server goes too (the next
    # listing answers `no server running on /tmp/tmux-.../spit-...`). The entry
    # must survive that in exactly the right way: actions.py indexes
    # `chat["server"]` unguarded at exit, so the KEY must stay -- and stay the
    # SAME Server object, because `new_session()` on it starts tmux again on the
    # same socket instead of a second Server being built. The cache survives
    # (invariant 4: a repeat call repeats what was reported), and the chat has to
    # become usable again.
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        del requested_sockets[:]
        check("t15-started", t.term_new("t15"), None)
        wait_for_prompt(app, "t15")
        old_session = app.tmux["chat1"]["session"].session_id
        server = app.tmux["chat1"]["server"]
        send_raw(app, "t15", "exit 4\n", True)
        check("t15-the-death-was-reported", wait_for(
            lambda: "INFO: Session dead." in t.term_screen("t15")), True)
        check("t15-tmux-has-no-such-session-any-more",
              old_session in tmux_session_ids(app), False)
        check("t15-the-entry-still-has-its-server-key", "server" in app.tmux["chat1"], True)
        # .get(), not []: the OLD rebuild dropped the key, and indexing it would
        # raise KeyError out of the differential instead of recording the red.
        check("t15-and-it-is-the-same-object", app.tmux["chat1"].get("server") is server, True)
        report = app.tmux["chat1"]["last_screen"]["t15"]
        check("t15-the-cache-keeps-the-report-with-the-status",
              "Exit status: 4." in report, True)
        check("t15-a-repeat-repeats-the-report-verbatim", t.term_screen("t15"), report)
        check("t15-the-chat-is-usable-again", t.term_new("t15b"), None)
        check("t15-still-the-one-and-only-server", len(set(requested_sockets)), 1)

    print("=== 16. what a capture and a listing COST (the other half of the reason) ===")
    # Behaviour can stay green while the cost doubles back, so count the `tmux`
    # processes themselves. The object layer's term_screen was 6 invocations
    # (libtmux's fat list-sessions/list-windows/list-panes and their refreshes)
    # plus 2 `display-message` calls for the cursor splice -- 45 ms, measured at
    # 69 ms here for the same work. The snapshot layer is TWO: one narrow
    # `list-panes -a` (liveness, exit status, geometry, cursor, for every window
    # of every chat at once) and the `capture-pane` itself -- ~17 ms. One
    # `lsterm` over three windows is ONE listing, not one per window (probe
    # printed 1).
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t16-a")
        t.term_new("t16-b")
        t.term_new("t16-c")
        wait_for_prompt(app, "t16-a")
        with counted_tmux_invocations() as calls:
            screen = t.term_screen("t16-a")
        check("t16-the-screen-still-arrives", screen.startswith("Session: t16-a"), True)
        check("t16-exactly-two-invocations", len(calls), 2)
        check("t16-one-narrow-listing", calls.count("list-panes"), 1)
        check("t16-no-per-session-or-per-window-listings",
              calls.count("list-sessions") + calls.count("list-windows"), 0)
        check("t16-no-display-message-for-the-cursor", calls.count("display-message"), 0)
        with counted_tmux_invocations() as calls:
            listing = lsterm.call(app, {}, "chat1")
        check("t16-the-listing-still-lists-all-three",
              all(n in listing for n in ("t16-a", "t16-b", "t16-c")), True)
        check("t16-one-listing-for-the-whole-listing", calls.count("list-panes"), 1)
        check("t16-and-nothing-else", len(calls), 1)

    print("=== 17. a stale id cannot point a chat at another chat's window ===")
    # A tmux server numbers from zero AGAIN when it starts (measured, twice): the
    # next session is `$0`, the next window `@1`. So a registry that outlives its
    # server can hold `@1` for a name of its own while `@1` on the NEW server
    # belongs to ANOTHER CHAT's live window. That is exactly what this fakes --
    # chat1's name re-pointed at chat2's window_id -- and window_is_ours() has to
    # survive it on both of its guards: the capture must not read the other
    # chat's screen, the send must not type into it, and the retire path must not
    # destroy it. Reading a stranger's window as your own is the very defect this
    # file exists to remove, aimed at a fellow chat.
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        mine = make_terminal(app)
        theirs = Terminal(app, "chat2", False)
        mine.term_new("t17-mine")
        theirs.term_new("t17-theirs")
        wait_for_prompt(app, "t17-mine")
        send_raw(app, "t17-mine", "echo mm-chat1-only\n", True)
        check("t17-mine-token", wait_for_text(app, "t17-mine", "mm-chat1-only"), True)
        theirs.term_input("t17-theirs", "echo mm-chat2-only")
        theirs.term_input("t17-theirs", "Enter")
        theirs_id = window_id_of(app.tmux["chat2"]["windows"]["t17-theirs"])
        check("t17-theirs-token", wait_for(
            lambda: "mm-chat2-only" in "\n".join(
                tmux_panes(app)[theirs_id].capture_pane())), True)
        mine.term_screen("t17-mine")        # cache MY OWN screen
        # Copy the ENTRY, not the id string: on the new layer that IS the id, and
        # on the object layer it is the Window object -- so the same line re-points
        # chat1 at chat2's window in BOTH shapes, which is what lets the
        # differential show the old code answering the alias with the other chat's
        # screen (every check below red) instead of crashing on a str.
        app.tmux["chat1"]["windows"]["t17-mine"] = app.tmux["chat2"]["windows"]["t17-theirs"]
        alias = mine.term_screen("t17-mine")
        check("t17-the-alias-does-not-read-the-other-chat", "mm-chat2-only" in alias, False)
        check("t17-the-alias-says-dead-from-its-own-cache",
              "INFO: Session dead." in alias, True)
        check("t17-and-reports-what-it-really-last-saw", "mm-chat1-only" in alias, True)
        check("t17-the-alias-refuses-input",
              mine.term_send_keys("t17-mine", "mm-poison", True), False)
        theirs_after = "\n".join(tmux_panes(app)[theirs_id].capture_pane())
        check("t17-nothing-was-typed-into-the-other-chat", "mm-poison" in theirs_after, False)
        check("t17-the-other-chat-s-window-survives", theirs_id in tmux_panes(app), True)
        check("t17-lsterm-for-chat1-lists-nothing",
              lsterm.call(app, {}, "chat1"), "No active sessions found!")
    # The OTHER guard, on its own: a chat whose STAMP is not the listing's server
    # answers dead for EVERY name -- the whole registry came from a dead server,
    # even where an id happens to name a window that exists on this one. And
    # reading it destroys nothing: a name the tool cannot verify is a name it
    # must not kill.
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t17-live")
        wait_for_prompt(app, "t17-live")
        send_raw(app, "t17-live", "echo mm-still-live\n", True)
        check("t17-token-on-the-live-pane", wait_for_text(app, "t17-live", "mm-still-live"), True)
        live_id = registered_window_id(app, "t17-live")
        app.tmux["chat1"]["stamp"] = ("999999", "1")      # not the listing's server
        screen = t.term_screen("t17-live")
        check("t17-a-wrong-stamp-answers-dead", "INFO: Session dead." in screen, True)
        check("t17-a-wrong-stamp-does-not-read-the-live-pane",
              "mm-still-live" in screen, False)
        check("t17-a-wrong-stamp-refuses-input", t.term_send_keys("t17-live", "x", True), False)
        check("t17-a-wrong-stamp-lists-nothing",
              lsterm.call(app, {}, "chat1"), "No active sessions found!")
        check("t17-and-destroys-nothing-it-cannot-verify", live_id in tmux_panes(app), True)
finally:
    kill_private_server(SOCKET)

summary()
