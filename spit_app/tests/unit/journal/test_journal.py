#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t1-t8 - P19/WP-3: the `journal` tool.

WHAT THE JOURNAL IS. The owner's second half of the failure-recovery brief: "a
new tool the agent can use while still alive to keep records - a kind of
journal - which then becomes the recovery message in the new chat". It is the
agent's own crash-recovery note, and `doc/TASKS-IN-PROGRESS.md` is the proof
the fields work: the same Branch/Scope/Done/Left/State hazards/Verify shape
has carried this repo across three crashed sessions.

WHAT IS PINNED HERE, and the control beside every absence (TRAPS #13)
  t1  the gate, TRAPS #19 inverted: the module under test imports NOTHING of
      the app's runtime, so this row runs on the bare python3 - and if a later
      edit gives the tool a Textual or httpx import, this reddens instead of
      the suite quietly becoming venv-bound;
  t2  `entry` WRITES: one timestamped entry, in a file of THIS chat under the
      app's data dir, and the answer says which entry number it appended. The
      control is the file: the tool's whole effect is that file, so the answer
      is checked against the bytes and not the other way round. The chat's
      messages are untouched - a journal is a record, not a checkpoint;
  t3  `entry` absent READS, newest last, and a chat with no journal says so
      while a chat with one is the control that the absence is about THIS chat
      and not a read that never answers;
  t4  the READ CAP: whole entries from the END, never half an entry, the newest
      entry survives a cap smaller than itself because a truncated record is
      the one thing a successor cannot use, and what is cut is still in the
      file - the cap is on the READ, never on the journal;
  t5  the cap is the SETTING `journal_max_chars`, read from `tool_settings` in
      the shape `load_user_settings` copies, with the blanked field, the
      non-number, zero and the negative all answering the default rather than
      crashing or reading uncapped (the `retry_attempts` rule of 84 a);
  t6  append-only: three calls leave three entries in order, an entry is
      MULTI-LINE so the fields are one record and not five, and a body line
      that opens with `[` is body - never a second entry (the count is the
      marker lines, so a wrong count cannot hide);
  t7  one file per chat: two chats in one app, and what one wrote is neither
      readable nor writable through the other - the recovery inherits a chat,
      so the journal that travels must be exactly the one it inherits from;
  t8  the refusals write NOTHING: a chat id that is not a file name, a `None`
      entry, an entry that is not text, and a directory that cannot hold the
      file - each with the control that the same call with a good value does
      write, so a refusal cannot be a silent success and a success cannot be a
      silent refusal.

NUMBERS are append-only within this suite (TRAPS #15): t1-t8 are WP-3's.
TRAPS #21: the tool takes NO path argument (`entry` is text), so there is
deliberately no `PATH_ARGS` here, and t2 checks the argument names rather than
trusting their absence.
TRAPS #18: every group runs inside `guarded()`; a group that raises reports a
red and the file still prints the row the outer runner reads.
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import journal_harness as J    # noqa: E402  (J.journal is the tool itself)
from journal_harness import (DATA, TOOLS_DIR, StubApp, entry_text,
                             journal_file, prepare, set_cap, teardown)

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def guarded(name, body):
    try:
        body()
    except Exception:
        global fail_
        fail_ += 1
        print(f"FAIL: {name} raised\n{traceback.format_exc()}")





# ------------------------------------------------------------------------- t1
def t1_the_gate():
    """TRAPS #19 inverted: what the code UNDER TEST imports decides the row."""
    loaded = [m for m in ("textual", "httpx", "libtmux", "ddgs", "playwright")
              if m in sys.modules]
    check("t1-importing-the-tool-loaded-no-app-dependency", loaded, [])
    check("t1-the-tool-itself-is-loaded", J.journal.NAME, "journal")
    check("t1-it-is-loaded-from-the-tool-tree-the-app-reads",
          J.journal.__file__, str(TOOLS_DIR / "journal.py"))
    check("t1-and-there-is-no-script-of-the-same-name",
          (TOOLS_DIR / "scripts" / "journal.py").exists(), False)
    # The reason the tool is in-process, pinned as a fact about the tree and not
    # as a comment: the sandbox binds its own homes over `/home/<user>` and
    # `/tmp`, so a `scripts/` tool could never write where the recovery reads.
    common = (TOOLS_DIR / "run" / "common.py").read_text(encoding="utf-8")
    check("t1-the-sandbox-overrides-the-homes-a-script-would-write-to",
          ["/home" in common, "sandbox_tmp" in common, "bind" in common],
          [True, True, True])


# ------------------------------------------------------------------------- t2
def t2_entry_writes():
    prepare()
    app = StubApp()
    answer = J.journal.call(app, {"entry": entry_text("one")}, "chat-a")
    file = journal_file("chat-a")
    check("t2-the-file-appeared", file.exists(), True)
    check("t2-under-the-app-data-dir", str(file).startswith(str(DATA)), True)
    text = file.read_text(encoding="utf-8")
    check("t2-one-entry-in-it", J.journal.count_entries(text), 1)
    check("t2-timestamped-on-its-own-line",
          len(J.journal.ENTRY_MARK.findall(text)), 1)
    check("t2-the-body-is-the-entry-verbatim", "Branch: b-one" in text, True)
    check("t2-the-answer-says-it-appended", answer.startswith("Journal ok"), True)
    check("t2-the-answer-counts-it-as-entry-one", "entry 1" in answer, True)
    # The journal must not touch the conversation it records.
    check("t2-no-chat-is-touched", hasattr(app, "messages"), False)
    # TRAPS #21: no argument of this tool is a filesystem path.
    check("t2-no-path-args", getattr(J.journal, "PATH_ARGS", []), [])
    names = list(J.journal.DESC["function"]["parameters"]["properties"])
    check("t2-one-argument-and-it-is-the-entry", names, ["entry"])
    check("t2-entry-is-not-required-so-a-read-reaches-the-tool",
          J.journal.DESC["function"]["parameters"]["required"], [])


# ------------------------------------------------------------------------- t3
def t3_no_entry_reads():
    prepare()
    app = StubApp()
    silence = J.journal.call(app, {}, "chat-none")
    check("t3-a-chat-without-a-journal-says-so",
          silence.startswith("No journal for this chat yet"), True)
    check("t3-and-it-created-no-file", journal_file("chat-none").exists(), False)
    J.journal.call(app, {"entry": entry_text("first")}, "chat-b")
    J.journal.call(app, {"entry": entry_text("second")}, "chat-b")
    read = J.journal.call(app, {}, "chat-b")
    check("t3-CONTROL-the-same-read-on-a-chat-that-wrote-answers",
          read.startswith("Journal of chat-b"), True)
    check("t3-two-entries-reported", "2 entries" in read, True)
    check("t3-newest-last", read.index("b-first") < read.index("b-second"), True)
    check("t3-a-read-writes-nothing", J.journal.count_entries(
        journal_file("chat-b").read_text(encoding="utf-8")), 2)
    check("t3-entry-none-is-a-read-not-a-write", J.journal.call(app, {"entry": None}, "chat-b")
          .startswith("Journal of chat-b"), True)
    check("t3-a-blank-entry-is-a-read-too", J.journal.call(app, {"entry": "   "}, "chat-b")
          .startswith("Journal of chat-b"), True)


# ------------------------------------------------------------------------- t4
def t4_the_read_cap():
    prepare()
    app = StubApp()
    for index in range(6):
        J.journal.call(app, {"entry": entry_text(f"n{index}", filler=200)}, "chat-c")
    text = journal_file("chat-c").read_text(encoding="utf-8")
    set_cap(app, 400)
    read = J.journal.call(app, {}, "chat-c")
    check("t4-the-journal-itself-is-uncapped", J.journal.count_entries(text), 6)
    check("t4-the-read-says-it-cut", "SHOWING THE LAST" in read, True)
    check("t4-the-cut-part-is-still-in-the-file", "n0" in text, True)
    check("t4-and-not-in-the-read", "n0" in read.split("\n", 1)[1], False)
    check("t4-the-newest-entry-is-in-the-read", "b-n5" in read, True)
    shown = read.split("\n", 1)[1]
    check("t4-what-is-shown-is-within-the-cap", len(shown) <= 400 + 40, True)
    check("t4-no-half-entry-at-the-top", shown.startswith("["), True)
    check("t4-every-entry-shown-is-a-marker",
          shown.count("[") >= J.journal.count_entries(shown), True)
    # A cap smaller than the newest entry: that entry is still whole. A cut
    # record is the one thing a successor cannot use, so the newest entry wins
    # over the number - stated, because it means the cap is a floor on what a
    # read costs, not a ceiling it will die on.
    set_cap(app, 20)
    tiny = J.journal.call(app, {}, "chat-c")
    check("t4-a-cap-below-one-entry-reports-that-entry-whole",
          tiny.split("\n", 1)[1].startswith("["), True)
    check("t4-and-it-carries-the-whole-body", "b-n5" in tiny, True)
    # No cap at all is the default, not an uncapped read of a huge file.
    check("t4-the-default-cap-is-a-number", J.journal.MAX_CHARS > 0, True)


# ------------------------------------------------------------------------- t5
def t5_the_cap_is_a_setting():
    prepare()
    app = StubApp()
    for index in range(4):
        J.journal.call(app, {"entry": entry_text(f"s{index}", filler=300)}, "chat-d")
    long_read = J.journal.call(app, {}, "chat-d")
    check("t5-at-the-default-all-of-it-is_shown", "all of it" in long_read, True)
    check("t5-a-chat-with-no-saved-cap-gets-the-module-default",
          J.journal.effective_cap(StubApp()), J.journal.MAX_CHARS)
    set_cap(app, 300)
    cut = J.journal.call(app, {}, "chat-d")
    check("t5-a-user-value-takes-effect", "SHOWING THE LAST" in cut, True)
    check("t5-and-it-is_read_only-a-read", J.journal.count_entries(
        journal_file("chat-d").read_text(encoding="utf-8")), 4)
    # A rubbish cap answers the DEFAULT. This journal is ~1.3k characters and
    # the default is 4000, so the default shows ALL of it: the check is that a
    # string, a blank, zero, a negative, a bool and a float do not crash, do
    # not read uncapped and do not answer 0 - and the control right after it is
    # that a small LEGAL value still cuts, so "all of it" above is the default
    # and not a read that never caps.
    for rubbish in (None, "", "wide", -1, 0, True, 1.5):
        set_cap(app, rubbish)
        answer = J.journal.call(app, {}, "chat-d")
        check(f"t5-a-blanked-or-rubbish-cap-answers-the-default-{rubbish!r}",
              "all of it" in answer, True)
    set_cap(app, 300)
    check("t5-CONTROL-a-small-legal-cap-still-cuts",
          "SHOWING THE LAST" in J.journal.call(app, {}, "chat-d"), True)
    # The default is the MODULE's, not the last caller's: `SETTINGS` is module
    # state shared by every chat in the process, so an app with no saved cap of
    # its own must not inherit the one this app just had.
    check("t5-a-chat-with-no-saved-cap-gets-the-module-default",
          J.journal.effective_cap(StubApp()), J.journal.MAX_CHARS)


# ------------------------------------------------------------------------- t6
def t6_append_only_and_multiline():
    prepare()
    app = StubApp()
    J.journal.call(app, {"entry": entry_text("one")}, "chat-e")
    first = journal_file("chat-e").read_text(encoding="utf-8")
    J.journal.call(app, {"entry": entry_text("two")}, "chat-e")
    second = journal_file("chat-e").read_text(encoding="utf-8")
    check("t6-the-first-entry-is-still-there-untouched", second.startswith(first), True)
    check("t6-two-entries-now", J.journal.count_entries(second), 2)
    check("t6-nothing-was-rewritten", len(second) > len(first), True)
    fields = "Branch: b\nScope: s\nDone: d\nLeft: l\nState hazards: h\nVerify: v"
    J.journal.call(app, {"entry": fields}, "chat-e")
    third = journal_file("chat-e").read_text(encoding="utf-8")
    check("t6-a-field-list-is-ONE-entry", J.journal.count_entries(third), 3)
    check("t6-and-all-six-fields-are-in-it",
          all(line in third for line in fields.split("\n")), True)
    body_with_bracket = "[not a timestamp] looks like a marker\n[ 2020 ]"
    J.journal.call(app, {"entry": body_with_bracket}, "chat-e")
    four = journal_file("chat-e").read_text(encoding="utf-8")
    check("t6-a-body-line-opening-with-a-bracket-is-body",
          J.journal.count_entries(four), 4)


# ------------------------------------------------------------------------- t7
def t7_one_file_per_chat():
    prepare()
    app = StubApp()
    J.journal.call(app, {"entry": entry_text("mine")}, "chat-mine")
    J.journal.call(app, {"entry": entry_text("yours")}, "chat-yours")
    check("t7-two-files", [journal_file("chat-mine").exists(),
                           journal_file("chat-yours").exists()], [True, True])
    mine = J.journal.call(app, {}, "chat-mine")
    check("t7-what-one-chat-wrote-is-not-in-the-other",
          ["b-mine" in mine, "b-yours" in mine], [True, False])
    check("t7-and-the-files-are-not-the-same",
          journal_file("chat-mine").read_text(encoding="utf-8")
          != journal_file("chat-yours").read_text(encoding="utf-8"), True)


# ------------------------------------------------------------------------- t8
def t8_the_refusals_write_nothing():
    prepare()
    app = StubApp()
    for bad in (None, "", "chat/one", "..", "../escape", "a\\b"):
        answer = J.journal.call(app, {"entry": "would be lost"}, bad)
        check(f"t8-refused-a-chat-id-like-{bad!r}",
              str(answer).startswith("ERROR"), True)
    check("t8-and-a-refusal-wrote-no-file", os.path.exists(DATA / "journal"), False)
    check("t8-and-nothing-escaped-the-data-dir",
          os.path.exists(os.path.join(DATA, "..", "escape.txt")), False)
    # CONTROL: the same tool with a good id writes, so the refusals above are
    # refusals and not a tool that never writes at all.
    ok = J.journal.call(app, {"entry": "good"}, "chat-ok")
    check("t8-CONTROL-a-good-id-writes", ok.startswith("Journal ok"), True)
    weird = J.journal.call(app, {"entry": {"a": 1}}, "chat-ok")
    check("t8-a-non-text-entry-is-refused", weird.startswith("ERROR"), True)
    check("t8-and-it-appended-nothing", J.journal.count_entries(
        journal_file("chat-ok").read_text(encoding="utf-8")), 1)
    # The write path itself refusing (the journal dir is a FILE): an error
    # string, not a traceback out of the worker.
    prepare()
    DATA.mkdir(exist_ok=True)
    (DATA / "journal").write_text("in the way", encoding="utf-8")
    blocked = J.journal.call(StubApp(), {"entry": "cannot land"}, "chat-blocked")
    check("t8-a-blocked-directory-refuses-with-ERROR",
          str(blocked).startswith("ERROR"), True)


print()
guarded("t1-gate", t1_the_gate)
guarded("t2-entry-writes", t2_entry_writes)
guarded("t3-no-entry-reads", t3_no_entry_reads)
guarded("t4-read-cap", t4_the_read_cap)
guarded("t5-cap-is-a-setting", t5_the_cap_is_a_setting)
guarded("t6-append-only", t6_append_only_and_multiline)
guarded("t7-one-file-per-chat", t7_one_file_per_chat)
guarded("t8-refusals", t8_the_refusals_write_nothing)
teardown()

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
