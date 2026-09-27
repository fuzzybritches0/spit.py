# SPDX-License-Identifier: GPL-2.0
"""t1-t9: the handoff tool called directly - what it writes, sends, shows,
and refuses. The new chat is driven for real (real submit path, real `Work`,
real stream against the canned server), so "sent" is proven by the POST the
server records and by the streamed reply landing in the new chat, not by an
attribute the tool could have set without anything happening.

Numbering: t1-t9 are this file's; the work-loop end-to-end is t10-t15 in
`test_handoff_work_loop.py` (append-only numbers, TRAPS #15).
"""
import asyncio
import copy
import json

from handoff_harness import (DATA, HANDOFF_TEXT, OLD_ID, REPLY_TEXT, START_TEXT,
                             FakeWork, check, guarded, handoff_call, mount_old,
                             new_id_from, run_case, summary, until, chat_files)


def t1_to_t4_the_successful_handoff():
    """One call on a mounted chat: file, message, flag, sidebar - and the
    stream that proves the message was SENT, not merely stored."""
    async def drive(app, pilot, server):
        old = await mount_old(app, pilot)
        old._work = FakeWork()
        settings_before = copy.deepcopy(old.csettings)
        files_before = chat_files()
        result = await handoff_call(app, {"message": HANDOFF_TEXT}, OLD_ID)

        check("t1-result-says-handoff-ok", (result or "").startswith("Handoff ok:"), True)
        new_id = new_id_from(result)
        check("t1-result-names-the-new-chat", new_id is not None, True)
        check("t1-new-file-exists", (DATA / "chats" / f"{new_id}.json").is_file(), True)
        check("t1-exactly-one-new-file", chat_files(),
              sorted(files_before + [f"{new_id}.json"]))

        content = json.loads((DATA / "chats" / f"{new_id}.json").read_text())
        expected_settings = copy.deepcopy(settings_before)
        expected_settings["desc"]["value"] = "Handoff: mm-old-desc"
        # Inheritance is the WHOLE settings block - endpoint, model, model
        # settings, prompt, tools, sandbox - and nothing else differs.
        check("t1-settings-inherited-except-desc", content["settings"],
              expected_settings)
        check("t1-ctime-is-fresh", content["ctime"] > 1758000000.0, True)
        # the tool writes "model": None like Manage.save_managed; the first
        # write_chat_history (the submit below) is the real app's, and it
        # stores ctime/settings/messages only - so either spelling of "no
        # model" is right, anything else is a wrong dict.
        check("t1-model-key-none-or-absent", content.get("model"), None)

        main = app.query_one("#main")
        new_chat = main.query_one(f"#{new_id}")
        check("t2-first-message-is-the-handoff", new_chat.messages[0],
              {"role": "user", "content": [{"type": "text", "text": HANDOFF_TEXT}]})
        check("t2-text-area-was-cleared", new_chat.text_area.text, "")
        check("t2-undo-records-the-insert",
              [new_chat.undo.undo_list[0][0], new_chat.undo.undo_list[0][2]],
              ["insert", 0])

        check("t3-this-chat-ends", old._work.exit_after_busy, True)

        side_panel = app.query_one("#side-panel")
        index = side_panel.get_option_index(new_id)
        check("t4-sidebar-highlights-the-new-chat", side_panel.highlighted, index)
        # get_option reads by option ID (the chat id), highlighted indexes -
        # the two are different lookups and this asserts both.
        check("t4-sidebar-option-carries-the-desc",
              "Handoff: mm-old-desc" in side_panel.get_option(new_id).prompt, True)
        check("t4-new-chat-is-shown", new_chat.display, True)
        check("t4-old-chat-is-hidden", old.display, False)
        check("t4-only-two-chats-mounted",
              [c.id for c in main.children], [OLD_ID, new_id])

        # SENT, proven at the wire: one POST carrying the handoff as its last
        # message, the inherited model, and the inherited tool selection. The
        # control against a vacuous "no note" body (TRAPS #13): the POST count
        # for the marker is exactly one, and the body is the exact pair
        # (system prompt, user handoff) - an accidental extra message reddens.
        got_post = await until(pilot, lambda: bool(server.bodies_with(HANDOFF_TEXT)))
        check("t5-the-handoff-was-posted", got_post, True)
        posts = server.bodies_with(HANDOFF_TEXT)
        check("t5-exactly-one-handoff-post", len(posts), 1)
        body = posts[0]
        check("t5-post-carries-the-inherited-model", body.get("model"),
              json.loads((DATA / "chats" / f"{new_id}.json").read_text())["settings"]["model"]["value"])
        check("t5-post-last-message-is-the-handoff",
              body["messages"][-1],
              {"role": "user", "content": [{"type": "text", "text": HANDOFF_TEXT}]})
        check("t5-post-tools-inherited",
              [t["function"]["name"] for t in body.get("tools", [])], ["handoff"])
        check("t5-old-chat-never-posted", server.bodies_with(START_TEXT), [])

        got_reply = await until(
            pilot, lambda: (len(new_chat.messages) >= 2
                            and new_chat.messages[-1]["role"] == "assistant"
                            and new_chat.messages[-1]["content"][0]["text"]
                            == REPLY_TEXT))
        check("t6-the-new-chat-received-its-reply", got_reply, True)
        check("t6-stream-finished-the-message",
              new_chat.messages[-1]["content"][0]["text"], REPLY_TEXT)
        # the text is already in the dict when signal 2 lands; the FILE is
        # rewritten at signal 0 (message_finish). Read the file on a wait,
        # never instantly - that instant read was a measured flake.
        persisted = await until(
            pilot, lambda: [m["role"] for m in json.loads(
                (DATA / "chats" / f"{new_id}.json").read_text())["messages"]]
            == ["user", "assistant"])
        check("t6-reply-was-persisted", persisted, True)

    asyncio.run(run_case(drive))


def t7_the_blank_message_refuses_everything():
    """No message, no handoff: no file, no widget, no flag, no sidebar entry -
    the refusal cannot half-happen, and the working chat keeps working."""
    async def drive(app, pilot, server):
        old = await mount_old(app, pilot)
        old._work = FakeWork()
        result = await handoff_call(app, {"message": "   "}, OLD_ID)
        check("t7-blank-is-an-error", (result or "").startswith("ERROR:"), True)
        check("t7-no-file", chat_files(), [f"{OLD_ID}.json"])
        check("t7-no-widget", len(app.query_one("#main").children), 1)
        check("t7-flag-untouched", old._work.exit_after_busy, False)
        check("t7-old-chat-still-shown", old.display, True)
        # The control: the very same call shape WITHOUT the blank succeeds, so
        # the refusal above belongs to the blank and not to the harness.
        old._work = FakeWork()
        result = await handoff_call(app, {"message": HANDOFF_TEXT}, OLD_ID)
        check("t7-CONTROL-the-same-call-with-text-succeeds",
              (result or "").startswith("Handoff ok:"), True)
        check("t7-CONTROL-a-file-exists-now", len(chat_files()), 2)

    asyncio.run(run_case(drive))


def t8_the_description_argument_labels_the_new_chat():
    async def drive(app, pilot, server):
        old = await mount_old(app, pilot)
        old._work = FakeWork()
        result = await handoff_call(app, {"message": HANDOFF_TEXT,
                                          "description": "mm-custom-desc"}, OLD_ID)
        new_id = new_id_from(result)
        content = json.loads((DATA / "chats" / f"{new_id}.json").read_text())
        check("t8-description-argument-wins", content["settings"]["desc"]["value"],
              "mm-custom-desc")
        side_panel = app.query_one("#side-panel")
        check("t8-sidebar-shows-it",
              "mm-custom-desc" in side_panel.get_option(new_id).prompt, True)
        # control: a non-string description falls back to the prefixed default
        old._work = FakeWork()
        main = app.query_one("#main")
        for cont in main.children:
            cont.display = True
        result = await handoff_call(app, {"message": HANDOFF_TEXT,
                                          "description": 42}, OLD_ID)
        other_id = new_id_from(result)
        other = json.loads((DATA / "chats" / f"{other_id}.json").read_text())
        check("t8-CONTROL-junk-desc-falls-back",
              other["settings"]["desc"]["value"], "Handoff: mm-old-desc")

    asyncio.run(run_case(drive))


def t9_two_handoffs_never_share_an_id():
    """The id is `str(time())` with the dot replaced, bumped while the name is
    taken: two handoffs back to back create two chats, two files, and only the
    newest stays in the foreground."""
    async def drive(app, pilot, server):
        old = await mount_old(app, pilot)
        old._work = FakeWork()
        first = new_id_from(await handoff_call(app, {"message": HANDOFF_TEXT + " A"}, OLD_ID))
        second = new_id_from(await handoff_call(app, {"message": HANDOFF_TEXT + " B"}, OLD_ID))
        check("t9-distinct-ids", first != second, True)
        check("t9-both-files-exist", chat_files(),
              sorted([f"{OLD_ID}.json", f"{first}.json", f"{second}.json"]))
        main = app.query_one("#main")
        check("t9-only-the-newest-is-shown",
              [c.display for c in main.children], [False, False, True])

    asyncio.run(run_case(drive))


if __name__ == "__main__":
    guarded("t1-t4-successful-handoff", t1_to_t4_the_successful_handoff)
    guarded("t7-blank-refusal", t7_the_blank_message_refuses_everything)
    guarded("t8-description-argument", t8_the_description_argument_labels_the_new_chat)
    guarded("t9-id-uniqueness", t9_two_handoffs_never_share_an_id)
    summary()
