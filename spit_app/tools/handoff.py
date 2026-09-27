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

import time
from copy import deepcopy
from spit_app.chat.chat import Chat
from spit_app.tool_call import load_user_settings

def new_chat_id(app) -> str:
    # The id scheme `Manage` gives a new chat (`str(time())` with the dot
    # replaced), plus the one case Manage never faces: two handoffs inside
    # the same clock tick must not overwrite each other's file.
    chat_id = f"chat-{str(time.time()).replace('.', '-')}"
    while (app.settings.path["chats"] / f"{chat_id}.json").exists():
        chat_id = f"chat-{str(time.time()).replace('.', '-')}"
    return chat_id

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
    new_id = new_chat_id(app)
    # The exact shape `Manage.save_managed` writes for a new chat. The handoff
    # message is NOT written into it: it enters through the new chat's own
    # submit path below, so its persistence, its undo record, its widget mount
    # through the window and the Work it starts are the human path's, not a
    # second implementation of them that could drift.
    if not app.write_json(f"chats/{new_id}.json",
                          {"ctime": time.time(), "settings": settings,
                           "messages": [], "model": None}):
        return (f"ERROR: could not write `chats/{new_id}.json`. Nothing was "
                "handed off and this chat continues.")
    side_panel = app.query_one("#side-panel")
    side_panel.option_list()         # the entry exists now that the file does
    main = app.query_one("#main")
    await main.mount(Chat(new_id))
    new_chat = main.query_one(f"#{new_id}")
    # Foreground the new chat: the display-toggle of `SidePanel.set_active`,
    # with the focus given to the new chat itself (an empty Chat focuses its
    # text area, so the user lands in a ready chat while the reply streams).
    for cont in main.children:
        cont.display = (cont is new_chat)
    side_panel.highlighted = side_panel.get_option_index(new_id)
    side_panel.can_focus = False
    new_chat.focus()
    new_chat.text_area.text = message
    await new_chat.text_area.action_submit()
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
