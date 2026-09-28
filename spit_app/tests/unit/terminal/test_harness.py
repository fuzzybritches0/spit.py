#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for the harness layer: the terminal tool as a UI-under-test harness.

P0b-followup 4. The backend is `run/terminal.py` (term_new's command/env/cwd and
geometry, Terminal.resize, term_screen's mode/history/marker, capture_text,
diff_screen, wait_for, send_bytes, screen_json, close_chat); the arguments that
reach a caller are wired in `spit_app/tools/terminal.py`. Every section is the
item number of the list in TASKS(-IN-PROGRESS/FINISHED).md, and every section
carries the control TRAPS #13 asks for: a sibling check that fails when the
feature is a no-op.

Measured on this box (tmux 3.7c, libtmux 0.62) and encoded below:

  * `resize-window` on a CLIENTLESS session is PER WINDOW -- one window at 120x40
    and a window created after it still 80x24 (so a capture's width can be an
    assertion's fact, DECISIONS 73; a resize never disturbs another session).
  * a raw row-count drops when the pane gets wider: re-wrap is real work, visible.
  * `capture-pane -e` puts ESC where the plain capture has none (2 vs 0), and
    `-e -C` octal-escapes them ("\\033[31m" as text, no raw ESC at all).
  * `send-keys -l -- <bytes>` delivers a byte stream EXACTLY -- SGR mouse,
    bracketed paste, a NUL-free string with ESC in the middle -- while libtmux's
    key layer LOSES a payload that begins with a flag: "-l mm-A", "-t mm-B" and
    "-- mm-C" all arrived as b'' through `send_keys(literal=True)`. That is the
    control that justifies `send_bytes` going through tmux's own argv.
  * a command that exits BEFORE tmux answers cannot be retained at all:
    term_new(command=["true"]) reports its established error string and registers
    nothing (measured: `no such window: @1`), so "a dead pane reports its exit
    code" is pinned with a command that prints, waits a beat, and exits 7.
  * `wait_for` distinguishes matched/stable/timeout/aborted/dead/bad-pattern, and
    an abort stamped from another thread ends the wait in about one poll (0.6 s
    measured against a 20 s ceiling) -- the cancellable in-flight call, item 10.
  * a first capture has no diff baseline and says so; a styled capture does NOT
    move it; a text capture does.
  * a session started with `command` may have no shell to read what is typed: the
    tty ECHOES the typed text as literal text, so a printf sent to a `sleep 60`
    pane never runs and its styled capture carries no ESC (measured). The capture
    modes are therefore asserted on a session started the default way -- bash --
    where styled-versus-text on one and the same screen is a pair in which either
    half can fail.
  * every section of this file shares ONE private socket, so tmux holds the earlier
    sections' sessions as well: sessions are counted RELATIVE, through the server
    object of a chat that survives, never as an absolute number. An absolute one is
    a property of the file's order, not of the code under test.
"""
import json
import shutil
import tempfile
import threading
import time

from stub_app import (check, kill_private_server, make_terminal, pane_of,
                      screen_of, send_raw, session_window_ids, stub_app, summary,
                      tmux_available, tmux_session_ids, use_private_server,
                      wait_for, wait_for_prompt, wait_for_text, window_dead)

SOCKET = "spit-unit-terminal-harness"

if not tmux_available():
    print("SKIP: no tmux binary on this machine; the terminal suite cannot run")
    print("PASS: 0  FAIL: 0")
    raise SystemExit(0)

use_private_server(SOCKET)

import spit_app.tools.terminal as tool
from spit_app.tools.run.terminal import Terminal, close_chat

try:
    print("=== 1. command, env, cwd: start the program under test (item 1) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        launch = ["sh", "-c", "echo mm-env-[$MM_PROBE_VAR] mm-cwd-$(basename $PWD); exec sleep 60"]
        check("t1-started-with-a-command",
              t.term_new("t1", command=launch, env={"MM_PROBE_VAR": "mm-env-value"}, cwd=root),
              None)
        check("t1-command-and-env-and-cwd-reached-it",
              wait_for_text(app, "t1", "mm-env-[mm-env-value] mm-cwd-" +
                            root.rsplit("/", 1)[-1]), True)
        # The control: the same launch with no env and no cwd sees neither. A
        # session that IGNORES its arguments would pass t1 and fail this.
        t.term_new("t1-plain")
        check("t1-control-no-env-no-cwd-without-the-arguments",
              t.term_new("t1-plain-2", command=["sh", "-c",
                           "echo mm-plain-[$MM_PROBE_VAR]; exec sleep 60"]), None)
        check("t1-control-the-variable-is-really-absent",
              wait_for_text(app, "t1-plain-2", "mm-plain-[]"), True)
        check("t1-control-a-default-session-is-still-bash",
              wait_for_prompt(app, "t1-plain"), True)
        # An argv whose program exits before tmux answers is reported, not raised,
        # and registers nothing (measured `no such window: @1`).
        died = t.term_new("t1-dies", command=["true"])
        check("t1-instant-exit-is-an-error-string", str(died).startswith("ERROR"), True)
        check("t1-instant-exit-names-the-session", "t1-dies" in str(died), True)
        check("t1-instant-exit-registers-nothing",
              "t1-dies" in app.tmux["chat1"]["windows"], False)
        # A command that prints, waits, then exits: remain-on-exit holds ANY argv,
        # so the corpse reports its real screen and its real exit code.
        t.term_new("t1-exit7", command=["sh", "-c", "echo mm-exit-7-token; sleep 0.3; exit 7"])
        check("t1-the-command-pane-died",
              wait_for(lambda: window_dead(app, "t1-exit7") is True), True)
        report = t.term_screen("t1-exit7")
        check("t1-dead-command-reports-its-screen", "mm-exit-7-token" in report, True)
        check("t1-dead-command-reports-its-exit-code", "Exit status: 7." in report, True)

    print("=== 2. geometry: cols/rows and resize, per window (item 2) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t2", cols=120, rows=40)
        wait_for_prompt(app, "t2")
        check("t2-geometry-at-creation-cols", pane_of(app, "t2").pane_width, "120")
        check("t2-geometry-at-creation-rows", pane_of(app, "t2").pane_height, "40")
        t.term_new("t2-other")
        wait_for_prompt(app, "t2-other")
        check("t2-the-next-window-is-untouched",
              (pane_of(app, "t2-other").pane_width, pane_of(app, "t2-other").pane_height),
              ("80", "24"))
        check("t2-resize", t.resize("t2", 160, 30), None)
        check("t2-resize-took", wait_for(
            lambda: (pane_of(app, "t2").pane_width, pane_of(app, "t2").pane_height)
                    == ("160", "30")), True)
        check("t2-resize-is-per-window-not-per-session",
              (pane_of(app, "t2-other").pane_width, pane_of(app, "t2-other").pane_height),
              ("80", "24"))
        # Re-wrap is what the geometry is FOR: the same content occupies fewer raw
        # rows once the pane is wide (measured: a 120-char token wraps at 60).
        t.term_new("t2-wrap", cols=60, rows=24)
        wait_for_prompt(app, "t2-wrap")
        token = "W" * 120
        t.term_input("t2-wrap", f"echo {token}")
        t.term_input("t2-wrap", "Enter")
        wait_for_text(app, "t2-wrap", token)
        wrapped = [l for l in pane_of(app, "t2-wrap").capture_pane() if "W" in l]
        check("t2-wrapped-at-60-columns", len(wrapped) > 1, True)
        t.resize("t2-wrap", 160, 24)
        time.sleep(0.5)
        rewound = [l for l in pane_of(app, "t2-wrap").capture_pane() if "W" in l]
        check("t2-the-history-re-wrapped", len(rewound) < len(wrapped), True)
        dead = Terminal(app, "chat1", False)
        dead.term_new("t2-dead", command=["sh", "-c", "echo mm-dead-before-resize; sleep 0.3; exit 1"])
        wait_for(lambda: window_dead(app, "t2-dead") is True)
        refused = dead.resize("t2-dead", 100, 30)
        check("t2-resize-of-a-dead-session-refuses", str(refused).startswith("ERROR"), True)
        check("t2-and-says-it-is-not-live", "not live" in str(refused), True)

    print("=== 3. capture modes: text | styled | bytes (item 3) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t3")
        wait_for_prompt(app, "t3")
        # Colour from `tput`, not from a literal `\033` typed at the prompt: the
        # echoed COMMAND LINE of a literal printf puts the text `\033` on the grid
        # too (measured: 2 occurrences of it even in a plain-text capture), and a
        # broken `bytes` mode would then still find its octal escape and pass its
        # own check. With tput the only escape sequence on the pane is the painted
        # one, so every count below says what the mode did (TRAPS #13).
        t.term_input("t3", "printf \"$(tput setaf 1)RED mm-style-token$(tput sgr0) plain\\n\"")
        t.term_input("t3", "Enter")
        # Waited for the OUTPUT line, not for the token: the echoed command line
        # carries the token too, and a capture taken the moment it appears can be
        # taken before printf has run (the lesson of DECISIONS 73, in its `t2` form:
        # wait for what the pane did, not for what was typed).
        check("t3-the-colour-ran", wait_for_text(app, "t3", "mm-style-token plain"), True)
        text = t.term_screen("t3")
        styled = t.term_screen("t3", mode="styled")
        bytez = t.term_screen("t3", mode="bytes")
        check("t3-text-carries-the-token", "mm-style-token" in text, True)
        check("t3-text-carries-no-escape", "\x1b" in text, False)
        check("t3-styled-carries-the-escape", "\x1b[31m" in styled, True)
        check("t3-styled-has-more-escapes-than-text",
              styled.count("\x1b") > text.count("\x1b"), True)
        check("t3-bytes-escapes-the-escape-non-printably", "\\033[31m" in bytez, True)
        check("t3-bytes-holds-no-raw-escape", "\x1b" in bytez, False)
        # The two counts, not just the presence: the styled mode shows the sequence
        # RAW and the bytes mode shows the SAME sequence OCTAL-ESCAPED, and the plain
        # one shows neither (measured 2 / 2 / 0 here). Without the equality the
        # bytes-mode check could be satisfied by anything that echoed `\033` at the
        # prompt -- which is what the tput line above removes.
        check("t3-bytes-escapes-every-escape-styled-shows-raw",
              bytez.count("\\033") >= styled.count("\x1b") > 0, True)
        check("t3-the-plain-screen-carries-neither", "\\033[" in text, False)
        # The default is the call that has always been made: `mode="text"` written
        # out is byte-identical to mode left out (TRAPS #14 -- the rendered screen
        # is the contract, and test_screen pins its 93 checks through this same
        # function).
        check("t3-the-default-path-is-byte-identical-to-mode=text",
              t.term_screen("t3"), t.term_screen("t3", mode="text"))
        # The limit, said out loud: every mode reads the pane's GRID. A sequence
        # tmux does not model is consumed by tmux, so NOTHING here asserts on it --
        # no check is written for a Kitty/Sixel byte stream, and none can be.

    print("=== 4. the cursor as data, and the marker as an option (item 4) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t4")
        wait_for_prompt(app, "t4")
        t.term_input("t4", "echo mm-cursor-under")
        wait_for_text(app, "t4", "mm-cursor-under")
        t.term_input("t4", "C-b")          # one character back: the cursor is ON the 'r'
        wait_for(lambda: pane_of(app, "t4").cursor_x == "70")
        state = t.window_state("t4")
        data = json.loads(t.screen_json("t4"))
        check("t4-json-cursor-is-two-integers",
              (data["cursor_x"], data["cursor_y"]), (int(state.cursor_x), int(state.cursor_y)))
        check("t4-json-agrees-with-tmux",
              (data["cursor_x"], data["cursor_y"]),
              (int(pane_of(app, "t4").cursor_x), int(pane_of(app, "t4").cursor_y)))
        marked = t.term_screen("t4")
        plain = t.term_screen("t4", marker=False)
        check("t4-the-marker-is-in-the-default-capture", "█" in marked, True)
        check("t4-marker-False-reports-no-marker", "█" in plain, False)
        check("t4-the-character-under-the-cursor-is-INTACT-without-the-marker",
              "mm-cursor-under\n" in plain + "\n", True)
        check("t4-and-eaten-by-the-splice-with-it", "mm-cursor-under" in marked, False)

    print("=== 5. scrollback and diffs (item 7) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t5")
        wait_for_prompt(app, "t5")
        t.term_input("t5", "echo mm-hist-early; for i in $(seq 1 100); do echo filler-$i; done; echo mm-hist-late")
        t.term_input("t5", "Enter")
        wait_for_text(app, "t5", "mm-hist-late")
        visible = t.term_screen("t5")
        history = t.term_screen("t5", history=300)
        check("t5-visible-loses-the-early-line", "mm-hist-early" in visible, False)
        check("t5-visible-has-the-late-line", "mm-hist-late" in visible, True)
        check("t5-history-finds-the-early-line", "mm-hist-early" in history, True)
        check("t5-history-is-more-rows", len(history.splitlines()) > len(visible.splitlines()), True)
        check("t5-history-is-capped-for-the-context",
              len(t.term_screen("t5", history=5000).splitlines()) <= 502, True)
        # the diff, and its baseline rules
        t.term_new("t5d")
        wait_for_prompt(app, "t5d")
        first = t.diff_screen("t5d")
        check("t5-diff-says-there-is-no-baseline-yet", "first capture" in first, True)
        check("t5-and-still-shows-the-screen", len(first) > len("Session: t5d\n\n"), True)
        t.term_screen("t5d")                       # the text capture sets the baseline
        check("t5-a-quiet-screen-changed-nothing", "no lines changed" in t.diff_screen("t5d"), True)
        t.term_input("t5d", "echo mm-diff-one")
        t.term_input("t5d", "Enter")
        wait_for_text(app, "t5d", "mm-diff-one")
        changed = t.diff_screen("t5d")
        check("t5-the-changed-line-appears-as-an-addition", "+mm-diff-one" in changed, True)
        check("t5-and-the-unchanged-lines-do-not", "filler-" in changed, False)
        t.term_input("t5d", "echo mm-diff-two")
        t.term_input("t5d", "Enter")
        wait_for_text(app, "t5d", "mm-diff-two")
        t.term_screen("t5d", mode="styled")        # must NOT move the baseline
        after_styled = t.diff_screen("t5d")
        check("t5-a-styled-capture-does-not-move-the-baseline",
              "+mm-diff-two" in after_styled and "mm-diff-one" not in after_styled, True)
        t.term_screen("t5d")                       # a TEXT capture does
        check("t5-a-text-capture-moves-the-baseline",
              "no lines changed" in t.diff_screen("t5d"), True)

    print("=== 6. wait_for instead of delay; the abortable wait (items 5 and 10) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t6")
        wait_for_prompt(app, "t6")
        t.term_input("t6", "sleep 1; echo mm-wait-token")
        t.term_input("t6", "Enter")
        kind, rows = t.wait_for("t6", pattern="mm-wait-token", timeout=15)
        check("t6-wait-matched", kind, "matched")
        check("t6-a-matched-wait-returns-the-rows", any("mm-wait-token" in r for r in rows), True)
        started = time.time()
        check("t6-timeout-is-a-kind", t.wait_for("t6", pattern="mm-never-here", timeout=1)[0],
              "timeout")
        check("t6-a-timeout-actually-waited", time.time() - started >= 1.0, True)
        check("t6-bad-regex-is-a-kind", t.wait_for("t6", pattern="([", timeout=2)[0], "bad-pattern")
        check("t6-waiting-for-nothing-is-a-kind", t.wait_for("t6", timeout=2)[0], "bad-pattern")
        check("t6-stable-is-a-kind", t.wait_for("t6", stable_ms=300, timeout=10)[0], "stable")
        # the abort: a flag stamped from another thread, exactly as Chat.action_abort
        # stamps it, ends the wait at the next poll -- not at its timeout.
        threading.Timer(0.4, lambda: app.tmux["chat1"].__setitem__("abort", True)).start()
        started = time.time()
        check("t6-abort-ends-the-wait", t.wait_for("t6", pattern="mm-never", timeout=20)[0],
              "aborted")
        check("t6-abort-was-fast", time.time() - started < 5.0, True)
        check("t6-and-consumed-the-flag", app.tmux["chat1"].get("abort"), None)
        t.term_new("t6-dead")
        wait_for_prompt(app, "t6-dead")
        t.term_send_keys("t6-dead", "exit", False)
        t.term_send_keys("t6-dead", "Enter", False)
        check("t6-waiting-on-a-dying-pane-says-dead",
              t.wait_for("t6-dead", pattern="mm-x", timeout=15)[0], "dead")

    print("=== 7. send_bytes: raw injection, byte-exact (item 6) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        payload = "\x1b[<0;10;10M mm-A \x1b[5~"
        for name, send in (("t7-raw", lambda: t.send_bytes("t7-raw", payload + "\n")),
                           ("t7-keys", lambda: send_raw(app, "t7-keys", payload + "\n", True))):
            t.term_new(name, cwd=root)
            wait_for_prompt(app, name)
            t.term_input(name, f"cat > {root}/{name}.bin")
            t.term_input(name, "Enter")
            time.sleep(0.4)
            send()
            time.sleep(0.5)
            t.term_send_keys(name, "C-d", False)
            wait_for(lambda: open(f"{root}/{name}.bin", "rb").read() != b"", 10)
        got = open(f"{root}/t7-raw.bin", "rb").read()
        check("t7-send_bytes-landed-byte-exactly", got, payload.encode() + b"\n")
        check("t7-the-escape-survived", got.startswith(b"\x1b[<0;10;10M"), True)
        check("t7-the-page-up-sequence-survived", got.endswith(b" \x1b[5~\n"), True)
        # The control that justifies tmux's own argv: libtmux's key layer takes the
        # SAME kind of data and loses a payload that starts with a flag (measured:
        # "-l mm-A", "-t mm-B", "-- mm-C" all arrive as b'').
        t.term_new("t7-dash", cwd=root)
        wait_for_prompt(app, "t7-dash")
        t.term_input("t7-dash", f"cat > {root}/t7-dash.bin")
        t.term_input("t7-dash", "Enter")
        time.sleep(0.4)
        t.send_bytes("t7-dash", "-l mm-dash-payload\n")
        time.sleep(0.5)
        t.term_send_keys("t7-dash", "C-d", False)
        wait_for(lambda: open(f"{root}/t7-dash.bin", "rb").read() != b"", 10)
        check("t7-a-leading-dash-is-data-through-the-raw-argv",
              open(f"{root}/t7-dash.bin", "rb").read(), b"-l mm-dash-payload\n")
        t.term_new("t7-dash-keys", cwd=root)
        wait_for_prompt(app, "t7-dash-keys")
        t.term_input("t7-dash-keys", f"cat > {root}/t7-dash-keys.bin")
        t.term_input("t7-dash-keys", "Enter")
        time.sleep(0.4)
        send_raw(app, "t7-dash-keys", "-l mm-dash-payload\n", True)
        time.sleep(0.7)
        t.term_send_keys("t7-dash-keys", "C-d", False)
        time.sleep(1.0)
        check("t7-control-libtmux-loses-a-leading-dash-payload",
              open(f"{root}/t7-dash-keys.bin", "rb").read(), b"")
        dead = t.send_bytes("t7-nope", "mm-into-nothing\n")
        check("t7-sending-to-a-stranger-is-refused", dead, False)

    print("=== 8. the state as data: screen_json (items 8 and 11) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t8", cols=100, rows=30)
        wait_for_prompt(app, "t8")
        t.term_input("t8", "echo mm-json-token")
        t.term_input("t8", "Enter")
        wait_for_text(app, "t8", "mm-json-token")
        live = json.loads(t.screen_json("t8", wait="mm-json-token"))
        check("t8-state-live", live["state"], "live")
        check("t8-geometry-reported", (live["cols"], live["rows"]), (100, 30))
        check("t8-a-pid-and-a-command", live["pane_pid"] > 0 and len(live["command"]) > 0, True)
        check("t8-the-screen-is-rows", any("mm-json-token" in r for r in live["screen"]), True)
        check("t8-wait-echoed", live["wait"], "mm-json-token")
        check("t8-a-live-pane-has-no-exit-status", "exit_status" in live, False)
        t.term_new("t8-dead", command=["sh", "-c", "echo mm-dead-json; sleep 0.3; exit 5"])
        wait_for(lambda: window_dead(app, "t8-dead") is True)
        died = json.loads(t.screen_json("t8-dead"))
        check("t8-state-dead", died["state"], "dead")
        check("t8-exit-status-is-a-number", died["exit_status"], 5)
        check("t8-signal-and-dead-time-are-fields",
              "signal" in died and isinstance(died["dead_time"], int), True)
        check("t8-a-dead-pane-has-no-cursor", "cursor_x" in died, False)
        check("t8-and-it-still-carries-its-screen", "mm-dead-json" in "".join(died["screen"]), True)
        absent = json.loads(t.screen_json("t8-never"))
        check("t8-state-absent", absent["state"], "absent")
        check("t8-absent-claims-no-geometry", "cols" in absent, False)
        check("t8-absent-names-itself", absent["session"], "t8-never")

    print("=== 9. close_chat: a deleted chat's terminals go with it (item 12) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        mine = make_terminal(app)
        theirs = Terminal(app, "chat2", False)
        mine.term_new("t9-mine")
        theirs.term_new("t9-theirs")
        wait_for_prompt(app, "t9-mine")
        # `screen_of` reads chat1's registry, so chat2's prompt is waited for with
        # chat2's own Terminal: the same question, asked of the entry it belongs to.
        check("t9-the-other-chat-drew-its-prompt",
              wait_for(lambda: "$" in theirs.term_screen("t9-theirs")), True)
        # Counted RELATIVE, never absolutely: every section of this file shares ONE
        # private socket, so tmux here also holds every session the earlier sections
        # made (measured: 10 by this point). What close_chat owns is exactly ONE
        # session fewer and the other chat's session standing -- an absolute "== 2"
        # would only be true on a server that started empty, which is the probe, not
        # the suite. Asked through the SURVIVOR's server object, because chat1's
        # registry entry is what close_chat pops and `tmux_session_ids(app)` reads
        # the registry, not tmux.
        def sessions_now():
            return [s.session_id for s in theirs.server().sessions]
        mine_session = app.tmux["chat1"]["session"].session_id
        theirs_session = app.tmux["chat2"]["session"].session_id
        before = sessions_now()
        check("t9-two-chats-two-sessions",
              mine_session in before and theirs_session in before, True)
        close_chat(app.tmux, "chat1")
        check("t9-the-registry-entry-is-gone", "chat1" in app.tmux, False)
        check("t9-the-session-is-destroyed",
              wait_for(lambda: mine_session not in sessions_now()), True)
        check("t9-and-only-it-was-destroyed",
              sorted(sessions_now()) == sorted(s for s in before if s != mine_session),
              True)
        check("t9-the-other-chat-was-not-touched",
              sorted(app.tmux["chat2"]["windows"]), ["t9-theirs"])
        check("t9-and-the-other-chat-is-still-live", theirs.pane_active("t9-theirs"), True)
        check("t9-the-server-of-the-other-chat-still-answers",
              "Session: t9-theirs" in theirs.term_screen("t9-theirs"), True)
        close_chat(app.tmux, "chat1-never-existed")
        check("t9-closing-a-stranger-harms-nothing", sorted(app.tmux), ["chat2"])
        check("t9-and-nothing-of-the-survivor-was-lost",
              len(session_window_ids(app, "chat2")), 1)
        revived = Terminal(app, "chat1", False)
        check("t9-the-chat-is-usable-again", revived.term_new("t9-again"), None)
        # The same SERVER, not a new one: the revived chat's session answers through
        # the survivor's server object and the relative count is back to what it was.
        check("t9-on-the-same-server",
              app.tmux["chat1"]["session"].session_id in sessions_now() and
              len(sessions_now()) == len(before), True)

    print("=== 10. the tool's own arguments: the wiring in tools/terminal.py ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        tool.SETTINGS["sandbox"]["value"] = False
        check("t10-name-is-still-required", "ERROR" in tool.call(app, {}, "chat1"), True)
        check("t10-half-a-geometry-refused",
              "ERROR" in tool.call(app, {"name": "t10", "cols": 120}, "chat1"), True)
        check("t10-half-a-geometry-created-nothing",
              "t10" in app.tmux.get("chat1", {}).get("windows", {}), False)
        started = tool.call(app, {"name": "t10", "command": ["sh", "-c",
                              "echo mm-tool-env-[$MM_TOOL_VAR]; exec sleep 60"],
                                  "env": {"MM_TOOL_VAR": "mm-tool-value"},
                                  "wait_for": "mm-tool-env", "wait_timeout": 20}, "chat1")
        check("t10-command-and-env-reach-the-pane", "mm-tool-env-[mm-tool-value]" in started, True)
        check("t10-format-json-is-data",
              json.loads(tool.call(app, {"name": "t10", "format": "json", "delay": 0},
                                   "chat1"))["state"], "live")
        check("t10-json-reports-the-geometry-key",
              "cols" in json.loads(tool.call(app, {"name": "t10", "format": "json",
                                                   "delay": 0}, "chat1")), True)
        refused = tool.call(app, {"name": "t10", "command": ["bash"]}, "chat1")
        check("t10-command-on-an-existing-session-is-refused",
              refused.startswith("ERROR"), True)
        check("t10-and-says-it-exists", "already exists" in refused, True)
        sized = tool.call(app, {"name": "t10", "cols": 130, "rows": 35, "format": "json",
                                "delay": 0}, "chat1")
        check("t10-resize-through-the-tool", (json.loads(sized)["cols"], json.loads(sized)["rows"]),
              (130, 35))
        # Two things this pair needs and `t10` cannot give it. (1) The colour has to
        # be RUN by something: `t10` above runs `sleep 60` -- no stdin reader -- so a
        # printf typed into it is echoed by the tty as LITERAL text and never
        # executes; measured, its styled capture carries no ESC because its grid
        # carries no colour, and its text capture agrees with it. (2) The sequence
        # must not be spelled out in the command line either, or the echo of the
        # command supplies the `\033` a broken `bytes` mode is looking for (measured:
        # a literal `printf '\033[35m...'` leaves 2 of those texts on the grid of a
        # PLAIN capture). So: a session started the default way -- bash, the tool's
        # own default argv -- and colour from `tput`, and then the three modes of ONE
        # screen compared against each other: raw ESC in styled, none in text, the
        # same count octal-escaped in bytes.
        def asked(**args):
            return tool.call(app, args, "chat1")
        check("t10-a-session-without-a-command-starts",
              asked(name="t10-col").startswith("Session: t10-col"), True)
        check("t10-and-it-is-a-live-terminal", wait_for_prompt(app, "t10-col"), True)
        asked(name="t10-col", input=["printf \"$(tput setaf 5)mm-tool-colour$(tput sgr0) done\\n\"",
                                     "Enter"])
        # Synced on the ESC itself, and on nothing else: the echoed command line
        # carries the token before bash has run the printf, so waiting for the token
        # waits for the typing, not for the painting. A raw ESC appears on this grid
        # exactly when the colour is on it (the styled mode is the only one that
        # shows one, and the text mode shows the echo with no ESC at all).
        painted = wait_for(lambda: asked(name="t10-col", capture="styled",
                                         delay=0).count("\x1b") > 0)
        check("t10-styled-capture-carries-an-escape", bool(painted), True)
        styled_answer = asked(name="t10-col", capture="styled", delay=0)
        plain = asked(name="t10-col", capture="text", delay=0)
        bytes_captured = asked(name="t10-col", capture="bytes", delay=0)
        check("t10-text-capture-carries-none", plain.count("\x1b"), 0)
        check("t10-the-token-is-on-all-three",
              all("mm-tool-colour" in one for one in (plain, styled_answer, bytes_captured)),
              True)
        check("t10-bytes-capture-escapes-every-escape-of-the-styled-one",
              "\x1b" not in bytes_captured and
              bytes_captured.count("\\033") >= styled_answer.count("\x1b") > 0, True)
        check("t10-a-bad-capture-mode-is-refused",
              "ERROR" in tool.call(app, {"name": "t10", "capture": "kitty"}, "chat1"), True)
        check("t10-a-bad-format-is-refused",
              "ERROR" in tool.call(app, {"name": "t10", "format": "yaml"}, "chat1"), True)
        check("t10-a-NUL-in-send_bytes-is-refused",
              "ERROR" in tool.call(app, {"name": "t10", "send_bytes": ["mm\x00x"]}, "chat1"), True)
        check("t10-send_bytes-must-be-strings",
              "ERROR" in tool.call(app, {"name": "t10", "send_bytes": [7]}, "chat1"), True)
        check("t10-a-bad-regex-is-an-error",
              "ERROR" in tool.call(app, {"name": "t10", "wait_for": "(["}, "chat1"), True)
        check("t10-diff-with-a-capture-mode-is-refused",
              "ERROR" in tool.call(app, {"name": "t10", "diff": True, "capture": "styled"},
                                   "chat1"), True)
        # delay untouched, and replaced only by a wait argument
        app.tmux["chat1"]["abort"] = True
        # Waited for on a token `t10` REALLY has: the one its own command printed.
        # (The printf is not in this pane — see the capture-mode note above — and a
        # wait for a token that is not there measures a timeout, not a match.)
        wait_answer = tool.call(app, {"name": "t10", "wait_for": "mm-tool-env",
                                      "wait_timeout": 20}, "chat1")
        check("t10-the-abort-flag-is-cleared-at-call-start",
              app.tmux["chat1"].get("abort"), None)
        check("t10-a-wait-returns-the-screen",
              "mm-tool-env-[mm-tool-value]" in wait_answer, True)
        check("t10-and-does-not-report-an-abort", "aborted" in wait_answer.lower(), False)
        started = time.time()
        tool.call(app, {"name": "t10", "delay": 2}, "chat1")
        check("t10-delay-still-sleeps-when-no-wait-is-asked", time.time() - started >= 2.0, True)
        started = time.time()
        tool.call(app, {"name": "t10", "delay": 9, "wait_for": "mm-tool-env",
                        "wait_timeout": 20}, "chat1")
        check("t10-a-wait-REPLACES-the-delay", time.time() - started < 2.0, True)
        first_diff = tool.call(app, {"name": "t10-diff", "diff": True}, "chat1")
        check("t10-diff-through-the-tool", "first capture" in first_diff or
              "Session: t10-diff" in first_diff, True)
        check("t10-history-through-the-tool", "Session: t10" in
              tool.call(app, {"name": "t10", "history": 50, "delay": 0}, "chat1"), True)
        bytes_answer = tool.call(app, {"name": "t10", "send_bytes": ["\x1b[<0;1;1M\n"],
                                       "delay": 0}, "chat1")
        check("t10-send_bytes-through-the-tool-answers-a-screen",
              bytes_answer.startswith("Session: t10"), True)

    print("=== 11. the sandbox still launches (item 12: on by default) ===")
    if shutil.which("bwrap"):
        with tempfile.TemporaryDirectory() as root:
            app = stub_app(root)
            sandboxed = Terminal(app, "chat1", True)
            check("t11-sandbox-launch", sandboxed.term_new(
                "t11", command=["sh", "-c", "echo mm-sandbox-[$MM_SB_VAR]; exec sleep 60"],
                env={"MM_SB_VAR": "mm-sandbox-value"}), None)
            check("t11-sandbox-command-and-env-ran",
                  wait_for_text(app, "t11", "mm-sandbox-[mm-sandbox-value]"), True)
    else:
        print("SKIP: bwrap is not installed; the sandboxed launch cannot be checked")

finally:
    kill_private_server(SOCKET)

summary()
