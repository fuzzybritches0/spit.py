# SPDX-License-Identifier: GPL-2.0
import json
from spit_app.work import work_stream
import spit_app.message as message
import spit_app.utils as utils
from spit_app.config.config_app import ConfigApp

bindings = [
        ("ctrl+enter", "continue", "Continue"),
        ("ctrl+escape", "abort", "Abort"),
        ("ctrl+m", "config_app", "Config"),
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

    def action_cancel_edit(self):
        self.edit = False
        self.text_area.text = ""

    async def action_undo(self) -> None:
        await utils.state_undo(self)

    async def action_redo(self) -> None:
        await utils.state_redo(self)

    async def action_save_edit(self) -> None:
        id=int(self.edit_container.id[3:])
        if self.edit_ctype == "tool_calls" or self.edit_role == "tool":
            try:
                self.state[id][self.edit_ctype] = json.loads(self.text_area.text)
            except:
                return None
        else:
            self.state[id][self.edit_ctype] = self.text_area.text
        utils.append_undo_state(self)
        utils.write_chat_history(self)
        if self.edit_role == "user" or self.edit_role == "tool":
            role = "request"
        else:
            role = "response"
        await self.edit_container.remove_children()
        prepend = append = ""
        if self.edit_ctype == "tool_calls":
            prepend = "- TOOL CALL: `"
            append = "`"
        if self.edit_role == "tool":
            prepend = "- RESULT: `"
            append = "`"
        new_content = self.text_area.text
        self.text_area.text = ""
        await utils.render_message(self, role, prepend + new_content + append)
        self.edit = False

    def action_edit_content(self) -> None:
        self.edit_message("content")

    def action_edit_cot(self) -> None:
        self.edit_message("reasoning_content")

    def action_edit_tool(self) -> None:
        self.edit_message("tool_calls")

    def edit_message(self, ctype: str) -> None:
        id=int(self.focused.id[3:])
        self.edit_role = self.state[id]["role"]
        self.edit_message_undo = self.state[id][ctype]
        if ctype == "tool_calls" or self.edit_role == "tool":
            self.text_area.text = json.dumps(self.state[id][ctype])
        else:
            self.text_area.text = self.state[id][ctype]
        self.edit = True
        self.edit_ctype = ctype
        self.edit_container = self.focused
        self.text_area.focus()

    def action_change_focus(self) -> None:
            self.text_area.focus()
    
    async def action_continue(self) -> None:
        if self.text_area.text:
            utils.save_message(self, {"role": "user", "content": self.text_area.text})
            await utils.render_message(self, "request", self.text_area.text)
            self.text_area.text = ""
        if (self.text_area.text or self.state[-1]["role"] == "user" or
            self.state[-1]["role"] == "tool" or "tool_calls" in self.state[-1]):
            self.work = self.run_worker(work_stream(self))
    
    async def action_abort(self) -> None:
        self.work.cancel()
        count_state = len(self.state)
        if self.state[0]["role"] == "system":
            count_state-=1
        while len(self.chat_view.children) > count_state:
            await message.remove_last_turn(self)
        self.refresh_bindings()

    async def action_remove_last(self) -> None:
        del self.state[-1]
        utils.append_undo_state(self)
        utils.write_chat_history(self)
        await message.remove_last_turn(self)
        
    async def action_config_app(self) -> None:
        await self.push_screen(ConfigApp())
    
    async def action_exit_app(self) -> None:
        self.exit()

    def is_working(self) -> bool:
        if self.work and self.work.is_running:
            return True
        return False

    def get_id_edit(self) -> int | None:
        if self.focused and "id-" in self.focused.id:
            return int(self.focused.id[3:])

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "abort":
            return self.is_working()
        elif action == "undo":
            if self.is_working() or self.edit or self.undo_index == 0:
                return False
        elif action == "redo":
            if self.is_working() or self.edit or self.undo_index == len(self.undo)-1:
                return False
        elif action == "copy_listing":
            if not self.focused or not "-listing-" in self.focused.id:
                return False
        elif action == "edit_content":
            if self.is_working() or self.edit:
                return False
            id=self.get_id_edit()
            if not id or not self.state[id]["content"]:
                return False
        elif action == "edit_cot":
            if self.is_working() or self.edit:
                return False
            id=self.get_id_edit()
            if not id or not "reasoning_content" in self.state[id]:
                return False
        elif action == "edit_tool":
            if self.is_working() or self.edit:
                return False
            id=self.get_id_edit()
            if not id or not "tool_calls" in self.state[id]:
                return False
        elif action == "save_edit":
            return self.edit
        elif action  == "cancel_edit":
            return self.edit
        elif action == "remove_last":
            if not self.focused == self.chat_view.children[-1]:
                return False
        elif action == "continue":
            active = self.config.active_config
            if (self.is_working() or self.edit or not
                    self.config.configs[active]["values"]["endpoint_url"]):
                return False
            if self.text_area.text and self.state[-1]["role"] == "system":
                return True                                 # Begin of chat
            if (self.text_area.text and self.state[-1]["role"] == "assistant" and
                    self.state[-1]["content"]):
                return True                                 # Normal turn
            if self.state[-1]["role"] == "user":
                return True                                 # There is a user request
            if (self.state[-1]["role"] == "assistant" and
                    "tool_calls" in self.state[-1] and not self.text_area.text):
                return True                                 # There are TOOL CALLS to call
            if self.state[-1]["role"] == "tool" and not self.text_area.text:
                return True                                 # There are TOOL CALL results to process
            return False
        return True
