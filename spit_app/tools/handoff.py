# SPDX-License-Identifier: GPL-2.0
# P14: the handoff tool. The owner's manual loop - a dying chat writes a handoff
# message, a human copies it into a new chat - becomes one tool call: the new
# chat is CREATED HERE with this chat's settings, the message is SENT HERE as
# its first user message through the chat's own submit path, and this chat's
# work ENDS HERE via the flag action_abort already uses (work.py checks it
# after every tool call). DECISIONS 82 is the why of the three choices that
# could have gone differently: whole-csettings inheritance (desc excepted),
# reuse of ChatTextArea.action_submit, and the flag set last, only on success.
NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": (
            "Hand this work over to a new chat. The new chat inherits every "
            "setting of this chat (endpoint, model, model settings, system "
            "prompt, allowed tools, sandbox), receives `message` as its first "
            "user message and starts working on it immediately, and opens in "
            "the foreground with its sidebar entry highlighted. This chat's "
            "work ENDS when the call returns. Call it alone: any other tool "
            "call in the same reply is skipped."),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": (
                        "The handoff message. It arrives in the new chat as a "
                        "plain user message and a fresh agent continues from "
                        "it alone, so include: the task in one line, what you "
                        "changed (paths), what is unfinished, the exact next "
                        "step, and anything you learned that is not in the repo.")
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Sidebar description for the new chat. Optional; "
                        "defaults to 'Handoff: ' plus this chat's description.")
                }
            },
            "required": ["message"]
        }
    }
}

PROMPT = (
    "Use this tool to hand work to a new chat when a token-status note says "
    "the context window is critical, or when the user asks for a handoff. "
    "Compose the complete handoff message BEFORE calling: a fresh agent must "
    "be able to continue from it alone - the task in one line, what you "
    "changed (paths), what is unfinished, the exact next step, and anything "
    "you learned that is not in the repo. Call `handoff` alone, not together "
    "with other tools; any other call in the same reply is skipped. After it "
    "returns, this chat is ending: do not call any more tools and do not "
    "start new work.")

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" }
}

from copy import deepcopy
from spit_app.chat.handoff import create_and_submit
from spit_app.tool_call import load_user_settings

async def call(app, arguments: dict, chat_id: str) -> str|None:
    # `async def`, not a plain function: tool_call.py dispatches a plain
    # `call` through asyncio.to_thread, and this is widget work - mounting,
    # focusing, starting a worker - which belongs on the app's event loop.
    load_user_settings(app, NAME, SETTINGS)
    message = arguments.get("message")
    if not isinstance(message, str) or not message.strip():
        return ("ERROR: `message` is required and must not be blank - the "
                "handoff IS its message. Nothing was created and this chat "
                "continues.")
    chat = app.query_one("#main").query_one(f"#{chat_id}")
    settings = deepcopy(chat.csettings)
    desc = arguments.get("description")
    if not (isinstance(desc, str) and desc.strip()):
        desc = f"Handoff: {settings['desc']['value']}"
    settings["desc"]["value"] = desc
    # The create-and-submit sequence lives in `spit_app/chat/handoff.py` since
    # P19/WP-1, so that P19's recovery opens its continuation chat through the
    # same code and not through a copy of it. The `settings` dict is the whole
    # inheritance decision (DECISIONS 82 b) and stays here, with the desc rule.
    new_id = await create_and_submit(app, settings, message)
    if new_id is None:
        return ("ERROR: could not write the new chat's file under `chats/`. "
                "Nothing was handed off and this chat continues.")
    # LAST, and only on success: a failed handoff must never end a working
    # chat. work_stream() checks this flag after every tool call and returns
    # there, so this reply ends after its tool result and no further request
    # is ever sent for this chat. `chat._work` is the Work running this call
    # - `chat.work` is the Worker around it; None is not a reachable state
    # here (a tool call only ever runs inside its chat's Work).
    chat._work.exit_after_busy = True
    return (f"Handoff ok: new chat `{new_id}` created with this chat's "
            "settings, your message sent to it as its first message, the new "
            "chat shown and highlighted. This chat's work ends now - do not "
            "call any more tools.")
