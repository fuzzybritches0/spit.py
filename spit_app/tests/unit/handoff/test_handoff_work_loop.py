# SPDX-License-Identifier: GPL-2.0
"""t10-t15: the handoff through the real work loop - the canned server answers
the OLD chat's first request with a `handoff` tool call, the real `ToolCall`
dispatcher runs the real tool, and what must follow is everything P14 is:
the new chat created, its first message posted and answered, and the old
chat's work stream ENDED - no second request carrying the tool result, ever.

This is where `exit_after_busy` is proven as a mechanism and not just as an
attribute: the only assertion of "this chat ends" that cannot be satisfied by
a tool that merely sets a flag is the absence of the next HTTP request.

The companion half (t15): with TWO tool calls in the one assistant turn and
`handoff` first, `work_stream` returns inside its per-tool loop - the second
call never runs, no second new chat exists, and no body anywhere carries its
message. That is the skip-the-siblings consequence the tool's PROMPT orders
the model to avoid by calling `handoff` alone; here it is pinned, not hoped.
"""
import asyncio
import json

from handoff_harness import (DATA, HANDOFF_TEXT, OLD_ID, REPLY_TEXT, START_TEXT,
                             chat_files, check, guarded, mount_old, new_id_from,
                             run_case, summary, until)
from spit_app.chat.work import Work

SECOND_TEXT = HANDOFF_TEXT + " SECOND-CALL-NEVER-RUNS"


def _roles(messages: list) -> list:
    return [m["role"] for m in messages]


def t10_to_t14_the_work_loop_ends_here():
    async def drive(app, pilot, server):
        server.reply_mode = "tool"
        server.tool_calls = [("call-mm-ho-1", "handoff",
                              json.dumps({"message": HANDOFF_TEXT}))]
        old = await mount_old(app, pilot)
        old._work = Work(old)
        old.work = old.run_worker(old._work.work_stream())

        done = await until(pilot, lambda: old.work.is_finished)
        check("t10-old-work-finished", done, True)
        check("t10-old-work-succeeded", old.work.state.name, "SUCCESS")

        # The mechanism, at the wire: the old chat made EXACTLY ONE request.
        # A work stream that ignored the flag would POST again carrying the
        # tool result - and the marker below would appear in request number 2.
        check("t10-one-request-from-the-old-chat",
              len(server.bodies_with(START_TEXT)), 1)
        check("t11-flag-set", old._work.exit_after_busy, True)

        check("t12-old-transcript", _roles(old.messages),
              ["user", "assistant", "tool"])
        check("t12-assistant-carries-the-handoff-call",
              old.messages[1]["tool_calls"][0]["function"]["name"], "handoff")
        tool_text = old.messages[2]["content"][0]["text"]
        check("t12-tool-result-says-handoff-ok",
              tool_text.startswith("Handoff ok:"), True)
        new_id = new_id_from(tool_text)
        check("t12-tool-result-names-the-new-chat", new_id is not None, True)

        check("t13-exactly-one-new-chat-file", chat_files(),
              sorted([f"{OLD_ID}.json", f"{new_id}.json"]))
        main = app.query_one("#main")
        new_chat = main.query_one(f"#{new_id}")
        check("t13-new-chat-mounted-and-shown",
              (new_chat.is_mounted, new_chat.display, old.display),
              (True, True, False))
        got_reply = await until(
            pilot, lambda: (len(new_chat.messages) >= 2
                            and new_chat.messages[-1]["role"] == "assistant"
                            and new_chat.messages[-1]["content"][0]["text"]
                            == REPLY_TEXT))
        check("t13-new-chat-worked-its-first-message", got_reply, True)
        check("t13-new-chat-transcript", _roles(new_chat.messages),
              ["user", "assistant"])

        # A bounded observation window (half a second of pumped frames), then
        # ask again: the settled count is the answer, not the count taken at
        # the moment the worker finished.
        await pilot.pause(0.5)
        check("t14-two-requests-and-no-more", len(server.bodies), 2)
        check("t14-old-chat-stayed-at-one", len(server.bodies_with(START_TEXT)), 1)
        handoff_posts = server.bodies_with(HANDOFF_TEXT)
        check("t14-the-new-chat-posted-the-handoff-once", len(handoff_posts), 1)
        check("t14-new-chat-first-message-on-the-wire",
              handoff_posts[0]["messages"][-1],
              {"role": "user", "content": [{"type": "text", "text": HANDOFF_TEXT}]})

    asyncio.run(run_case(drive))


def t15_the_sibling_tool_call_is_skipped():
    async def drive(app, pilot, server):
        server.reply_mode = "tool"
        server.tool_calls = [("call-mm-ho-1", "handoff",
                              json.dumps({"message": HANDOFF_TEXT})),
                             ("call-mm-ho-2", "handoff",
                              json.dumps({"message": SECOND_TEXT}))]
        old = await mount_old(app, pilot)
        old._work = Work(old)
        old.work = old.run_worker(old._work.work_stream())

        done = await until(pilot, lambda: old.work.is_finished)
        check("t15-work-finished-despite-the-skipped-call", done, True)
        got_reply = await until(
            pilot, lambda: (len(app.query_one("#main").children) > 1
                            and any(len(c.messages) >= 2
                                    for c in app.query_one("#main").children
                                    if c.id != OLD_ID)))
        check("t15-the-first-handoff-still-ran", got_reply, True)

        # One assistant turn asked for TWO handoffs; exactly one new chat
        # exists, exactly one tool result was written (the loop returned
        # inside it), and the second call's message never reached any wire.
        check("t15-exactly-one-new-chat", len(chat_files()), 2)
        check("t15-only-one-tool-result", _roles(old.messages),
              ["user", "assistant", "tool"])
        check("t15-second-call-never-ran-anywhere",
              server.bodies_with("SECOND-CALL-NEVER-RUNS"), [])
        # control: the FIRST message did reach the wire - so the absence
        # above is the skip, not a broken marker (TRAPS #13).
        check("t15-CONTROL-first-call-reached-the-wire",
              len(server.bodies_with(HANDOFF_TEXT)), 1)

    asyncio.run(run_case(drive))


if __name__ == "__main__":
    guarded("t10-t14-work-loop", t10_to_t14_the_work_loop_ends_here)
    guarded("t15-sibling-skip", t15_the_sibling_tool_call_is_skipped)
    summary()
