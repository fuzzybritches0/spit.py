# SPDX-License-Identifier: GPL-2.0
# The create-and-submit sequence P14 built inside `tools/handoff.py`, extracted
# here so P19's failure recovery (WP-4) opens its continuation chat through the
# SAME path and not through a second copy of it. Everything about the shape is
# DECISIONS 82 and unchanged by the move: the chat file is written in
# `Manage.save_managed`'s shape, the message enters through the new chat's own
# `ChatTextArea.action_submit` (its persistence, its undo record, its mount
# through the sliding window and the `Work` it starts are the human ctrl+enter
# path's), and NOTHING here knows who asked - the caller that wants the chat to
# end after this sets its own flag, outside, last (82 c).
import time
from spit_app.chat.chat import Chat


def new_chat_id(app) -> str:
    # The id scheme `Manage` gives a new chat (`str(time())` with the dot
    # replaced), plus the one case Manage never faces: two of these inside the
    # same clock tick must not overwrite each other's file.
    chat_id = f"chat-{str(time.time()).replace('.', '-')}"
    while (app.settings.path["chats"] / f"{chat_id}.json").exists():
        chat_id = f"chat-{str(time.time()).replace('.', '-')}"
    return chat_id


async def create_and_submit(app, settings: dict, message: str) -> str|None:
    # The new chat's id, or None when its file could not be written - the only
    # step that can fail, and the reason the caller decides what a failure
    # means (the handoff tool keeps working and says so; a recovery says so
    # too rather than half-opening a chat).
    #
    # `async def`, not a plain function: this is widget work - mounting,
    # focusing, starting a worker - which belongs on the app's event loop.
    new_id = new_chat_id(app)
    # The exact shape `Manage.save_managed` writes for a new chat. The message
    # is NOT written into it: it enters through the new chat's own submit path
    # below, so its persistence, its undo record, its widget mount through the
    # window and the Work it starts are the human path's, not a second
    # implementation of them that could drift.
    if not app.write_json(f"chats/{new_id}.json",
                          {"ctime": time.time(), "settings": settings,
                           "messages": [], "model": None}):
        return None
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
    return new_id
