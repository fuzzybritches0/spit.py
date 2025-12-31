# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.chat.work import work_stream
import spit_app.chat.message as message
import spit_app.chat.undo as undo
import spit_app.chat.render as render

def is_working(self) -> bool:
    if self.work and self.work.is_running:
        return True
    return False

def get_id_edit(self) -> int | None:
    if (self.app.focused and self.app.focused.id and
        "message-id-" in self.app.focused.id):
        return int(self.app.focused.id[11:])
    return None

bindings = [
        ("ctrl+escape", "abort", "Abort"),
        ("escape", "change_focus", "Focus")
]
bindings_text_area = [
        ("ctrl+enter", "continue", "Continue"),
        ("ctrl+enter", "save_edit", "Save"),
        ("ctrl+escape", "cancel_edit", "Cancel"),
]
bindings_chat_view = [
        ("u", "undo", "Undo"),
        ("r", "redo", "Redo"),
        ("e", "edit_content", "Edit content"),
        ("c", "edit_cot", "Edit CoT"),
        ("t", "edit_tool", "Edit tool call"),
        ("y", "copy_listing", "Copy"),
        ("x", "remove_last", "Remove turn"),
]

class ActionsMixIn:
    def action_change_focus(self) -> None:
        self.text_area.focus()

    async def action_abort(self) -> None:
        self.work.cancel()
        await message.remove_last_turn(self)
        self.refresh_bindings()

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "abort":
                return is_working(self)
        return True

class ChatViewActionsMixIn:
    def action_copy_listing(self) -> None:
        id = self.app.focused.id
        if id.startswith("code-listing-"):
            id = id[13:]
            listing = self.chat.code_listings
        elif id.startswith("latex-listing-"):
            id = id[14:]
            listing = self.chat.latex_listings
        id = id.split("-")
        self.app.copy_to_clipboard(listing[int(id[0])][int(id[1])])

    async def action_undo(self) -> None:
        await undo.undo(self.chat)

    async def action_redo(self) -> None:
        await undo.redo(self.chat)

    def action_edit_content(self) -> None:
        self.edit_message("content")

    def action_edit_cot(self) -> None:
        self.edit_message("reasoning")

    def action_edit_tool(self) -> None:
        self.edit_message("tool_calls")

    def edit_message(self, ctype: str) -> None:
        id=int(self.app.focused.id[11:])
        self.chat.edit_role = self.chat.messages[id]["role"]
        self.chat.text_area.text_area_temp = self.chat.text_area.text
        if ctype == "tool_calls" or self.chat.edit_role == "tool":
            self.chat.text_area.text = json.dumps(self.chat.messages[id][ctype])
        else:
            self.chat.text_area.text = self.chat.messages[id][ctype]
        self.chat.edit = True
        self.chat.edit_ctype = ctype
        self.chat.edit_container = self.app.focused
        self.chat.text_area.focus()

    async def action_remove_last(self) -> None:
        undo.append_undo(self.chat, "remove", self.chat.messages[-1])
        del self.chat.messages[-1]
        self.chat.write_chat_history()
        await message.remove_last_turn(self.chat)

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "undo":
                if is_working(self.chat) or self.chat.edit:
                    return False
                if self.chat.undo_index == -1:
                    return False
            case "redo":
                if is_working(self.chat) or self.chat.edit:
                    return False
                if self.chat.undo_index == len(self.chat.undo)-1:
                    return False
                if len(self.chat.undo) == 0:
                    return False
            case "copy_listing":
                if (not self.app.focused or not self.app.focused.id or
                    not "-listing-" in self.app.focused.id):
                    return False
            case "edit_content":
                if is_working(self.chat) or self.chat.edit:
                    return False
                id=get_id_edit(self)
                if id is None or not self.chat.messages[id]["content"]:
                    return False
            case "edit_cot":
                if is_working(self.chat) or self.chat.edit:
                    return False
                id=get_id_edit(self)
                if id is None or not "reasoning" in self.chat.messages[id]:
                    return False
            case "edit_tool":
                if is_working(self.chat) or self.chat.edit:
                    return False
                id=get_id_edit(self)
                if id is None or not "tool_calls" in self.chat.messages[id]:
                    return False
            case "remove_last":
                if not self.chat.query_one("#chat-view").children:
                    return False
                if self.chat.edit or is_working(self.chat):
                    return False
                if len(self.chat.query_one("#chat-view").children) == 0:
                    return False
                if not self.app.focused is self.chat.query_one("#chat-view").children[-1]:
                    return False
        return True

class TextAreaActionsMixIn:
    def action_cancel_edit(self):
        self.chat.edit = False
        self.text = self.text_area_temp

    async def action_save_edit(self) -> None:
        id=int(self.chat.edit_container.id[11:])
        undo.append_undo(self.chat, "change", self.chat.messages[id], id)
        if self.chat.edit_ctype == "tool_calls" or self.chat.edit_role == "tool":
            try:
                self.chat.messages[id][self.chat.edit_ctype] = json.loads(self.text)
            except:
                return None
        else:
            self.chat.messages[id][self.chat.edit_ctype] = self.text
        self.chat.write_chat_history()
        self.text = self.text_area_temp
        await render.message(self.chat, self.chat.messages[id])
        self.chat.query_one("#chat-view").children[id].focus()
        self.chat.focused_message = self.chat.query_one("#chat-view").children[id]
        self.chat.edit = False

    async def action_continue(self) -> None:
        if (self.text and
            (not self.chat.messages or self.chat.messages[-1]["role"] == "assistant")):
            self.chat.save_message({"role": "user", "content": self.text})
            await render.message(self.chat, self.chat.messages[-1])
            self.chat.query_one("#chat-view").scroll_end(animate=False)
            self.text = ""
        self.chat.work = self.run_worker(work_stream(self.chat))

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "save_edit":
                return self.chat.edit
            case "cancel_edit":
                return self.chat.edit
            case "continue":
                if is_working(self.chat) or self.chat.edit:
                    return False
                if not self.chat.messages and not self.text:
                    return False
                if self.chat.messages:
                    if self.chat.messages[-1]["role"] == "user" and self.text:
                        return False
                    if (self.chat.messages[-1]["role"] == "assistant" and
                        not self.text and
                        not "tool_calls" in self.chat.messages[-1]):
                        return False
        return True
