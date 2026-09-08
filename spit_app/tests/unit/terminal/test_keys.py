#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for term_input(): what reaches the pane as a key and what as text.

term_input() decides between the two by stripping the key names and the modifier
prefix out of the argument and asking whether anything is left -- and the strip
threw its result away (`_inp.replace(key, "")`, five times over) because `str` is
immutable. `inp` was still the whole chord, so `len(_inp) <= 1` could never be
true for one, and Ctrl-C -- the thing this tool's own PROMPT advertises, "Send a
signal [\"C-c\"]" -- was typed into the pane as the four characters C - c. Every
bare key name still worked (it returns earlier), so the bug was invisible until
someone needed an interrupt.

A control character is not visible on a screen, so this suite asserts on the
effects a screen can show: a foreground process that dies, a cursor that moved,
an EOF that closed the shell. Section 5 is the control -- the same bytes sent as
literal text, which must NOT interrupt -- because an assertion that sleeps die
when nothing kills them proves nothing.

Two things a pane is owed and these tests honour:

  * the prompt first. A new window draws its shell prompt asynchronously and keys
    sent before it exists are typed into a line editor that has not drawn a line,
    so an ordering assertion made through a fresh window has no order to assert
    on until wait_for_prompt() says the prompt is there.
  * its own semantics for Esc. bash reads a lone Esc and then merges the NEXT
    character into it as Alt-<char> -- measured here: "echo mm-after-esc" typed
    straight after an Esc reached the prompt as "cho mm-after-esc". That is the
    terminal's, not this tool's, behaviour, and it is why the Esc test asserts
    the delivery (the key arrives, its name is not typed) and not what some
    program inside the pane does next.
"""
import tempfile

from stub_app import (check, kill_private_server, make_terminal, pane_of,
                      screen_of, send_raw, stub_app, summary, tmux_available,
                      use_private_server, wait_for, wait_for_prompt,
                      wait_for_text)

SOCKET = "spit-unit-terminal-keys"

if not tmux_available():
    print("SKIP: no tmux binary on this machine; the terminal suite cannot run")
    print("PASS: 0  FAIL: 0")
    raise SystemExit(0)

use_private_server(SOCKET)

try:
    print("=== 1. plain text still arrives as text ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t1")
        check("t1-prompt-drawn", wait_for_prompt(app, "t1"), True)
        t.term_input("t1", "echo mm-plain-text-ok")
        t.term_input("t1", "Enter")
        check("t1-text-echoed", wait_for_text(app, "t1", "mm-plain-text-ok"), True)

    print("=== 2. a bare key name is a key (the branch that always worked) ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t2")
        check("t2-prompt-drawn", wait_for_prompt(app, "t2"), True)
        t.term_input("t2", "echo mm-key-enter")
        check("t2-nothing-ran-before-the-enter-key",
              wait_for(lambda: "mm-key-enter\n" in screen_of(app, "t2"),
                       timeout=1.0), False)
        t.term_input("t2", "Enter")
        check("t2-enter-key-ran-it", wait_for_text(app, "t2", "mm-key-enter"), True)

    print("=== 3. C-a moves the cursor, so it arrived as Ctrl-A and not as text ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t3")
        check("t3-prompt-drawn", wait_for_prompt(app, "t3"), True)
        t.term_input("t3", "abcdef")
        check("t3-typed-the-line", wait_for_text(app, "t3", "abcdef"), True)
        t.term_input("t3", "C-a")
        t.term_input("t3", "X")
        t.term_input("t3", "Enter")
        check("t3-cursor-was-at-the-front", wait_for_text(app, "t3", "Xabcdef"), True)
        check("t3-not-the-chord-appended-as-text",
              wait_for_text(app, "t3", "abcdefC-a", timeout=1.0), False)
        check("t3-no-literal-chord-anywhere",
              "C-a" in screen_of(app, "t3"), False)

    print("=== 4. C-c interrupts a running command ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t4")
        check("t4-prompt-drawn", wait_for_prompt(app, "t4"), True)
        t.term_input("t4", "sleep 60")
        t.term_input("t4", "Enter")
        check("t4-sleep-was-running",
              wait_for(lambda: pane_of(app, "t4").pane_current_command == "sleep"), True)
        t.term_input("t4", "C-c")
        check("t4-sleep-was-interrupted", wait_for(
            lambda: pane_of(app, "t4").pane_current_command != "sleep"), True)
        check("t4-the-chord-was-not-typed-as-text",
              "C-c" in screen_of(app, "t4"), False)

    print("=== 5. control: the same bytes as text must NOT interrupt ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t5")
        check("t5-prompt-drawn", wait_for_prompt(app, "t5"), True)
        t.term_input("t5", "sleep 60")
        t.term_input("t5", "Enter")
        check("t5-sleep-was-running",
              wait_for(lambda: pane_of(app, "t5").pane_current_command == "sleep"), True)
        send_raw(app, "t5", "C-c", True)
        wait_for(lambda: "C-c" in screen_of(app, "t5"))
        check("t5-literal-text-left-it-running",
              pane_of(app, "t5").pane_current_command == "sleep", True)
        send_raw(app, "t5", "C-c", False)
        check("t5-the-same-key-as-a-key-did-interrupt", wait_for(
            lambda: pane_of(app, "t5").pane_current_command != "sleep"), True)

    print("=== 6. C-d ends the shell, so it arrived as EOF and not as text ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t6")
        check("t6-prompt-drawn", wait_for_prompt(app, "t6"), True)
        t.term_input("t6", "C-d")
        check("t6-session-ended", wait_for(lambda: not t.pane_active("t6")), True)

    print("=== 7. a longer string that merely starts like a chord is text ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t7")
        check("t7-prompt-drawn", wait_for_prompt(app, "t7"), True)
        t.term_input("t7", "echo C-c-is-not-only-a-chord")
        t.term_input("t7", "Enter")
        check("t7-echoed-as-text",
              wait_for_text(app, "t7", "C-c-is-not-only-a-chord"), True)

    print("=== 8. Esc and Escape are delivered as keys, not spelled out ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t8")
        check("t8-prompt-drawn", wait_for_prompt(app, "t8"), True)
        t.term_input("t8", "Esc")
        check("t8-session-still-alive", t.pane_active("t8"), True)
        check("t8-esc-was-not-typed", "Esc" in screen_of(app, "t8"), False)
        t.term_input("t8", "Escape")
        check("t8-still-alive-after-escape", t.pane_active("t8"), True)
        check("t8-escape-was-not-typed", "Escape" in screen_of(app, "t8"), False)

    print("=== 9. input to a dead session is refused, not raised ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        t = make_terminal(app)
        t.term_new("t9")
        check("t9-prompt-drawn", wait_for_prompt(app, "t9"), True)
        t.term_input("t9", "exit")
        t.term_input("t9", "Enter")
        check("t9-session-gone", wait_for(lambda: not t.pane_active("t9")), True)
        check("t9-input-returns-false", t.term_input("t9", "echo mm-too-late"), False)
finally:
    kill_private_server(SOCKET)

summary()
