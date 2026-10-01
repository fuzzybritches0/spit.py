#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t1-t6 - P19/WP-4: the recovery, driven through the real work loop.

WHAT IS PROVEN HERE AND WHERE
  t1  the AUTO-SUBMIT path, over the wire: a chat whose request was refused with
      a transient 503 leaves a continuation chat whose file exists, whose
      settings differ from the dead chat's in EXACTLY `desc` and
      `recovered_from`, whose FIRST message is the brief (the dead chat's id, its
      transcript path, the failure as the endpoint spelled it, the requests it
      took, the token counts, the last turns, and "Continue the work"), whose
      brief the canned server RECORDED as a POST body, and no modal anywhere
      (`app.exception` is None). The dead chat gained the in-chat notice as its
      LAST message - on disk, not only on screen - and the attempt's corpse is
      not in the transcript the brief quoted;
  t2  the ABSENCE of a second recovery chat, and NOT by timing: the continuation
      chat in t1 is submitted into the same refusing server, so it fails for real
      and reaches the recovery itself - and its own `recovered_from` makes it
      report instead of recovering. The check waits for THAT failure's notice and
      then counts the chat files: two. The control that the count could have been
      three is t1's own first recovery;
  t3  depth 1 from the start: a chat PRE-STAMPED with `recovered_from` fails and
      creates NO chat file at all, posts the notice that says the chain ends, and
      does not crash. (The depth cap is what stops a dead endpoint spawning one
      chat per failed request forever - alteration 2 of the P19 entry);
  t4  the DRAFT path, with the canned server STOPPED: the probe is the only thing
      that can tell "refused" from "not there", and it answers the second one -
      so the continuation chat EXISTS, its `messages` are EMPTY, its text area
      holds the brief, and NO POST carries the brief anywhere. The control that
      this absence is the draft and not a broken marker is t1, where the same
      marker is recorded on the wire;
  t5  the journal rides the brief when the file exists, written by the REAL
      `journal` tool, and the control beside it: a chat that kept none gets a
      sentence saying so and NOT `read_journal`'s prose addressed to a writer;
  t6  the notice is A MESSAGE and the sliding window's invariant holds around it:
      the mounted range is still a slice of the data, the notice has its widget,
      and its position is the tail of the file.

The retry counts themselves are `unit:endpoints` t14's; this suite sets
`retry_attempts` to 1 (no delay) so what it waits for is the recovery and not
the sleep. Every failure is driven the human drives it - `text_area.text` and
`action_submit()` - so no group hands `recover()` a convenient object.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import recovery_harness as R    # noqa: E402
from recovery_harness import (DATA, FIRST_TEXT, JOURNAL_LEFT, JOURNAL_MARK,  # noqa: E402
                              LONG_TAIL, MODEL, OLD_ID, SECOND_TEXT, TURN_TEXT,
                              check, chat_names, fail_a_turn, first_message,
                              guarded, last_message, message_text, mount_old,
                              new_id_from, other_chat, posted_briefs, quiesce,
                              recovery_reported,
                              read_chat, recovery_appeared, run_case,
                              settings_diff, settings_of, summary, until,
                              write_journal)


def t1_the_auto_submit_recovery():
    async def drive(app, pilot, server):
        old = await fail_a_turn(app, pilot)
        appeared = await recovery_appeared(pilot)
        check("t1-a-recovery-chat-appeared", appeared, True)
        if not appeared:
            return
        new_id = other_chat(chat_names())

        # The settings inheritance, as a set of key NAMES: only these two may
        # differ, and anything else that drifted is named by the check.
        check("t1-settings-differ-only-in-desc-and-recovered_from",
              settings_diff(settings_of(OLD_ID), settings_of(new_id)),
              ["desc", "recovered_from"])
        new_settings = settings_of(new_id)
        check("t1-desc-says-what-this-chat-is",
              new_settings["desc"]["value"], "Recovery: mm-old-desc")
        check("t1-recovered_from-names-the-chat-it-came-from",
              new_settings["recovered_from"],
              {"value": OLD_ID, "stype": "string", "desc": "Recovered from"})
        check("t1-the-inherited-endpoint-and-model-are-untouched",
              (new_settings["endpoint"]["value"], new_settings["model"]["value"]),
              ("7", MODEL))

        # The brief, as the new chat's FIRST message.
        brief = first_message(new_id)
        check("t1-the-brief-is-the-first-message-of-its-chat",
              read_chat(new_id)["messages"][0]["role"], "user")
        for fact, marker in (("the dead chat's id", OLD_ID),
                             ("the transcript path", f"chats/{OLD_ID}.json"),
                             ("the failure class", "TransientFailure"),
                             ("the failure text", "mm-recovery-unavailable"),
                             ("the token line", "Token counts when it died"),
                             ("the ask", "Continue the work")):
            check(f"t1-the-brief-carries-{fact}", marker in brief, True)
        check("t1-the-brief-quotes-the-turns-it-had",
              (FIRST_TEXT in brief, SECOND_TEXT in brief, TURN_TEXT in brief),
              (True, True, True))
        check("t1-the-brief-cuts-a-long-turn-and-says-so",
              ("…[cut]" in brief, LONG_TAIL in brief), (True, False))
        check("t1-the-brief-does-not-quote-the-corpse",
              brief.count("assistant:"), 1)

        # The brief reached the endpoint: it was SUBMITTED, not just staged.
        check("t1-the-brief-was-posted", len(posted_briefs(server)) >= 1, True)
        check("t1-CONTROL-the-refused-request-is-recorded-too",
              len(server.bodies_with(TURN_TEXT)) >= 1, True)

        # No modal: the failure was carried by the notice instead.
        check("t1-no-modal-was-pushed", app.exception, None)

        # The dead chat's notice, on disk - WAITED for, because the new chat's
        # FILE is written before the notice is appended to the old one: asserting
        # on the tail the moment the file appears reads a chat whose notice has
        # not been written yet, and that race is a red on a busy machine rather
        # than a finding.
        seen = await recovery_reported(pilot)
        check("t1-the-dead-chat-gained-its-notice", seen, True)
        notice = message_text(last_message(OLD_ID))
        check("t1-the-dead-chat-gained-the-notice", "Recovery:" in notice, True)
        check("t1-the-notice-names-the-new-chat", new_id_from(notice), new_id)
        check("t1-the-notice-says-it-was-submitted", "DRAFT" in notice, False)
        check("t1-the-corpse-is-out-of-the-dead-chat",
              [m["role"] for m in read_chat(OLD_ID)["messages"]],
              ["user", "assistant", "user", "user"])

    asyncio.run(run_case(drive))


def t2_the_second_failure_recovers_not_at_all():
    """The depth cap as a fact about the WORLD, not about a branch: t1's
    continuation chat is submitted into the same refusing server, so it fails
    for real, and the wait below waits for THAT failure's notice. Only then is
    the chat-file count asserted - an absence proved after the thing that could
    have produced it has already happened."""
    async def drive(app, pilot, server):
        await fail_a_turn(app, pilot)
        appeared = await recovery_appeared(pilot)
        check("t2-the-first-recovery-happened", appeared, True)
        if not appeared:
            return
        new_id = other_chat(chat_names())
        ended = await until(pilot, lambda: "chain ends" in
                            message_text(last_message(new_id)))
        check("t2-the-continuation-chat-failed-too", ended, True)
        # Waited-for absence: its failure reached the recovery and the depth cap
        # answered. Then, and only then, the count.
        await pilot.pause(0.5)
        check("t2-no-third-chat-was-ever-created", chat_names(),
              sorted([OLD_ID, new_id]))
        check("t2-the-continuation-chat-says-it-ends-the-chain",
              "chain ends" in message_text(last_message(new_id)), True)
        check("t2-and-still-no-modal-anywhere", app.exception, None)

    asyncio.run(run_case(drive))


def t3_depth_one_from_the_start():
    """A chat that IS a recovery fails. No chat file, a notice, no crash."""
    async def drive(app, pilot, server):
        await fail_a_turn(app, pilot)
        await recovery_reported(pilot)
        await pilot.pause(0.5)
        check("t3-a-pre-stamped-recovery-creates-no-chat", chat_names(), [OLD_ID])
        notice = message_text(last_message(OLD_ID))
        check("t3-the-notice-says-the-chain-ends", "chain ends" in notice, True)
        check("t3-the-notice-still-quotes-the-failure",
              "TransientFailure" in notice, True)
        check("t3-no-modal-was-pushed", app.exception, None)

    asyncio.run(run_case(drive, recovered_from="chat-mm-the-ancestor"))


def t4_the_draft_when_the_probe_hears_nothing():
    """Same code, server stopped. The request now fails as a `ConnectionFailure`
    and the probe's GET is refused as well, and THAT - not the status code - is
    what turns the submit into a draft."""
    async def drive(app, pilot, server):
        old = await mount_old(app, pilot)
        server.stop()                      # nothing is reachable any more
        old.text_area.text = TURN_TEXT
        await old.text_area.action_submit()
        appeared = await recovery_appeared(pilot)
        check("t4-the-draft-chat-was-created", appeared, True)
        if not appeared:
            return
        new_id = other_chat(chat_names())
        # The FILE appears before the mount and before the notice: `create_and_submit`
        # writes it as its first act. The notice is the LAST act of a successful
        # recovery, so waiting for it is what makes every assertion below a fact
        # about a finished recovery rather than about the moment a file was created.
        seen = await recovery_reported(pilot)
        check("t4-the-dead-chat-gained-its-notice", seen, True)
        check("t4-the-draft-chat-has-NO-messages",
              read_chat(new_id)["messages"], [])
        main = app.query_one("#main")
        draft_area = main.query_one(f"#{new_id}").text_area
        # What makes a DRAFT a draft is the brief sitting UNSUBMITTED in the text
        # area, so the text area must hold the brief - and it holds the transcript
        # too, so the marker is the path line, not the turn's own text (which the
        # quoted transcript repeats).
        check("t4-the-brief-is-in-the-text-area",
              (f"chats/{OLD_ID}.json" in draft_area.text,
               "Recovered from:" in draft_area.text), (True, True))
        check("t4-the-text-area-holds-the-ask",
              "Continue the work" in draft_area.text, True)
        check("t4-NO-post-carries-the-brief-anywhere", posted_briefs(server), [])
        notice = message_text(last_message(OLD_ID))
        check("t4-the-notice-says-it-is-a-draft", "DRAFT" in notice, True)
        check("t4-the-notice-gives-the-new-id", new_id_from(notice), new_id)
        check("t4-no-modal-was-pushed", app.exception, None)

    asyncio.run(run_case(drive))


def t5_the_journal_rides_the_brief_when_there_is_one():
    async def drive(app, pilot, server):
        write_journal(app, f"Branch: {JOURNAL_MARK}\nLeft: {JOURNAL_LEFT}")
        await fail_a_turn(app, pilot)
        appeared = await recovery_appeared(pilot)
        check("t5-a-recovery-with-a-journal-appeared", appeared, True)
        if not appeared:
            return
        await recovery_reported(pilot)
        brief = first_message(other_chat(chat_names()))
        check("t5-the-journal-is-in-the-brief", JOURNAL_MARK in brief, True)
        check("t5-the-whole-entry-is-there", JOURNAL_LEFT in brief, True)
        check("t5-the-brief-says-whose-journal-it-is",
              f"Journal of {OLD_ID}" in brief, True)
        check("t5-CONTROL-no-word-about-a-missing-journal",
              "No journal was kept" in brief, False)

    asyncio.run(run_case(drive))


def t5b_no_journal_means_one_plain_sentence():
    """The control of t5, and the reason `journal_part` exists: `read_journal`
    answers a chat with no journal with a paragraph ADDRESSED TO THE AGENT who
    would write one. Appended to a brief that reads as a journal whose entries
    are advice, so the line here is the app's own and says nothing exists."""
    async def drive(app, pilot, server):
        await fail_a_turn(app, pilot)
        appeared = await recovery_appeared(pilot)
        check("t5b-a-recovery-without-a-journal-appeared", appeared, True)
        if not appeared:
            return
        await recovery_reported(pilot)
        brief = first_message(other_chat(chat_names()))
        check("t5b-the-brief-says-no-journal-was-kept",
              "No journal was kept" in brief, True)
        check("t5b-the-writer-s-facing-prose-is-not-pasted-in",
              "journal_max_chars" in brief, False)
        check("t5b-CONTROL-the-transcript-still-rode-it", FIRST_TEXT in brief, True)

    asyncio.run(run_case(drive))


def t6_the_notice_keeps_the_tree():
    """The notice is appended as a message, so the ChatView's invariant is
    untouched by it - and both halves are asserted: the widget tree still
    projects the WHOLE history one child per message, AND the notice itself has
    a widget at the tail (the absence would pass on a view that mounted nothing
    at all)."""
    async def drive(app, pilot, server):
        old = await fail_a_turn(app, pilot)
        appeared = await recovery_appeared(pilot)
        check("t6-the-recovery-appeared", appeared, True)
        if not appeared:
            return
        await recovery_reported(pilot)
        for _ in range(6):
            await pilot.pause()
        view = old.chat_view
        check("t6-the-tree-still-projects-the-whole-history",
              len(view.children) == len(old.messages)
              and all(child.message is old.messages[position]
                      for position, child in enumerate(view.children)), True)
        tail = len(old.messages) - 1
        check("t6-the-notice-is-the-tail-of-the-data",
              "Recovery:" in message_text(old.messages[tail]), True)
        check("t6-the-notice-has-its-widget",
              view.children[tail].message is old.messages[tail], True)
        check("t6-the-notice-is-a-user-message", old.messages[tail]["role"], "user")

    asyncio.run(run_case(drive))


if __name__ == "__main__":
    guarded("t1-auto-submit", t1_the_auto_submit_recovery)
    guarded("t2-depth-cap", t2_the_second_failure_recovers_not_at_all)
    guarded("t3-pre-stamped-depth-one", t3_depth_one_from_the_start)
    guarded("t4-draft", t4_the_draft_when_the_probe_hears_nothing)
    guarded("t5-journal", t5_the_journal_rides_the_brief_when_there_is_one)
    guarded("t5b-no-journal", t5b_no_journal_means_one_plain_sentence)
    guarded("t6-tree", t6_the_notice_keeps_the_tree)
    summary()
