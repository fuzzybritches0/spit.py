# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.work import work_stream
import spit_app.message as message
import spit_app.utils as utils
from spit_app.settings.settings_app import EndpointSettings

bindings = [
        ("ctrl+enter", "continue", "Continue"),
        ("ctrl+escape", "abort", "Abort"),
        ("ctrl+m", "settings_endpoints", "Endpoints"),
        ("ctrl+i", "undo", "Undo"),
        ("ctrl+r", "redo", "Redo"),
        ("ctrl+q", "exit_app", "Quit"),
        ("ctrl+enter", "save_edit", "Save"),
        ("ctrl+escape", "cancel_edit", "Cancel"),
        ("ctrl+g", "edit_content", "Edit content"),
        ("ctrl+h", "edit_cot", "Edit CoT"),
        ("ctrl+j", "edit_tool", "Edit tool call"),
        ("ctrl+x", "copy_listing", "Copy"),
        ("ctrl+x", "remove_last", "Remove turn"),
        ("escape", "change_focus", "Focus")
]

class ActionsMixIn:
    def action_copy_listing(self) -> None:
        id = self.focused.id
        if id.startswith("code-listing-"):
            id = id[13:]
            listing = self.code_listings
        elif id.startswith("latex-listing-"):
            id = id[14:]
            listing = self.latex_listings
        id = id.split("-")
        self.copy_to_clipboard(listing[int(id[0])][int(id[1])])

    async def action_undo(self) -> None:
        await utils.undo(self)

    async def action_redo(self) -> None:
        await utils.redo(self)

    def action_cancel_edit(self):
        self.edit = False
        self.text_area.text = self.text_area_temp

    async def action_save_edit(self) -> None:
        id=int(self.edit_container.id[11:])
        utils.append_undo(self, "change", self.messages[id], id)
        if self.edit_ctype == "tool_calls" or self.edit_role == "tool":
            try:
                self.messages[id][self.edit_ctype] = json.loads(self.text_area.text)
            except:
                return None
        else:
            self.messages[id][self.edit_ctype] = self.text_area.text
        utils.write_chat_history(self)
        self.text_area.text = self.text_area_temp
        await message.render_message(self, self.messages[id])
        self.edit = False

    def action_edit_content(self) -> None:
        self.edit_message("content")

    def action_edit_cot(self) -> None:
        self.edit_message("reasoning")

    def action_edit_tool(self) -> None:
        self.edit_message("tool_calls")

    def edit_message(self, ctype: str) -> None:
        id=int(self.focused.id[11:])
        self.edit_role = self.messages[id]["role"]
        self.text_area_temp = self.text_area.text
        if ctype == "tool_calls" or self.edit_role == "tool":
            self.text_area.text = json.dumps(self.messages[id][ctype])
        else:
            self.text_area.text = self.messages[id][ctype]
        self.edit = True
        self.edit_ctype = ctype
        self.edit_container = self.focused
        self.text_area.focus()

    def action_change_focus(self) -> None:
        self.focused_message = self.focused
        self.text_area.focus()

    async def action_continue(self) -> None:
        if (self.text_area.text and
            (not self.messages or self.messages[-1]["role"] == "assistant")):
            utils.save_message(self, {"role": "user", "content": self.text_area.text})
            await message.render_message(self, self.messages[-1])
            self.text_area.text = ""
        self.work = self.run_worker(work_stream(self))
    
    async def action_abort(self) -> None:
        self.work.cancel()
        await message.remove_last_turn(self)
        self.refresh_bindings()

    async def action_remove_last(self) -> None:
        utils.append_undo(self, "remove", self.messages[-1])
        del self.messages[-1]
        utils.write_chat_history(self)
        await message.remove_last_turn(self)
        
    async def action_settings_endpoints(self) -> None:
        await self.push_screen(EndpointSettings())
    
    async def action_exit_app(self) -> None:
        self.exit()

    def is_working(self) -> bool:
        if self.work and self.work.is_running:
            return True
        return False

    def get_id_edit(self) -> int | None:
        if (self.focused and self.focused.id and
            "message-id-" in self.focused.id):
            return int(self.focused.id[11:])
        return None

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        match action:
            case "abort":
                return self.is_working()
            case "undo":
                if self.is_working() or self.edit:
                    return False
                if self.undo_index == -1:
                    return False
            case "redo":
                if self.is_working() or self.edit:
                    return False
                if self.undo_index == len(self.undo)-1:
                    return False
                if len(self.undo) == 0:
                    return False
            case "copy_listing":
                if (not self.focused or not self.focused.id or
                    not "-listing-" in self.focused.id):
                    return False
            case "edit_content":
                if self.is_working() or self.edit:
                    return False
                id=self.get_id_edit()
                if id == None or not self.messages[id]["content"]:
                    return False
            case "edit_cot":
                if self.is_working() or self.edit:
                    return False
                id=self.get_id_edit()
                if id == None or not "reasoning" in self.messages[id]:
                    return False
            case "edit_tool":
                if self.is_working() or self.edit:
                    return False
                id=self.get_id_edit()
                if id == None or not "tool_calls" in self.messages[id]:
                    return False
            case "save_edit":
                return self.edit
            case "cancel_edit":
                return self.edit
            case "remove_last":
                if self.edit or self.is_working():
                    return False
                if len(self.chat_view.children) == 0:
                    return False
                if not self.focused == self.chat_view.children[-1]:
                    return False
            case "continue":
                active = self.settings.active_endpoint
                if (self.is_working() or self.edit or not
                        self.settings.endpoints[active]["values"]["endpoint_url"]):
                    return False
                if not self.messages and not self.text_area.text:
                    return False
                if self.messages:
                    if self.messages[-1]["role"] == "user" and self.text_area.text:
                        return False
                    if (self.messages[-1]["role"] == "assistant" and
                        not self.text_area.text and
                        not "tool_calls" in self.messages[-1]):
                        return False
            case "exit_app":
                if self.edit or self.is_working():
                    return False
        return True
